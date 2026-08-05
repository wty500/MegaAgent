import chromadb
import time
import threading
import re
from llm import *
from utils import *
import config
import logging
chroma_client = chromadb.Client()

class Memory:
    def __init__(self, agent_name, initial_message):
        self.history = []
        self.history_pool = chroma_client.create_collection(name=agent_name)
        self.initial_message = initial_message
        self.name = agent_name
        self.subordinates = {}
        self.initialize_logger(agent_name)

    def add_memory(self, memory):
        if (memory['role'] not in ('function', 'tool') and memory['content'] != None):
            self.history_pool.add(documents=[memory['content']], ids=[str(time.time())])
        self.logger.info(str(memory))
        self.history.append(memory)
    
    def add_subordinate(self, name, description, initial_prompt):
        self.subordinates[name] = description
        agent_dict[name] = Agent(name, initial_prompt+config.additional_prompt+"\nYour supervisor is: "+self.name)

    def get_subordinates(self):
        ret = ""
        for i in self.subordinates:
            ret+=f"{i}: {self.subordinates[i]}\n"
        return ret

    def add_dialogue(self, speaker, message):
        content = f"{speaker}: {message}"
        self.history.append({"role": "user", "content": content})
        self.logger.info(content)
        self.history_pool.add(documents=[content], ids=[str(time.time())])
    
    def get(self):
        init = self.initial_message

        try:
            with git_lock:
                f = open(f"files/todo_{self.name}.txt", 'r')
                todo_list = f.read()
                f.close()
        except FileNotFoundError:
            todo_list = ''
        if todo_list and todo_list != '':
            init+=f"\n\nHere is your current todo list: {todo_list}"

        try:
            with git_lock:
                f = open(f"files/status_{self.name}.txt", 'r')
                task_status = f.read()
                f.close()
        except FileNotFoundError:
            task_status = ''
        if task_status and task_status != '':
            init+=f"\n\nHere is your current task status(what you have done): {task_status}\nYou can use 'change_task_status' function to update it."
        else:
            init+=f"\n\nYou do not have a task status yet. You can use 'change_task_status' function to update it."

        if self.subordinates:
            init+="\n\nYou have added these subordinates. Do not add them again:\n"
            for i in self.subordinates:
                init+=f"{i}"
                if self.subordinates[i]!="":
                    init+=f": {self.subordinates[i]}"
                init+=",\n"
            init+="\nYou can talk to them by using the function called talk."

        if self.history and self.history[-1]['content']:
            relevant_history = self.history_pool.query(query_texts=self.history[-1]['content'], n_results=1)
            # chroma returns empty result lists on a fresh collection; the
            # bare [0][0] index would kill this agent's worker thread
            if relevant_history and relevant_history['documents'] and relevant_history['documents'][0]:
                init+=f"\n\nHere is a relevant memory: \n{relevant_history['documents'][0][0]}\nBelow is the recent dialogue."

        memory = [{"role": "system", "content": init}]
        for i in self.history[-config.MAX_MEMORY:]:
            memory.append(i)

        return memory
    
    def initialize_logger(self, name):
        self.logger = logging.getLogger(name)

        # Create a file handler for logging
        file_handler = logging.FileHandler(f"logs/{name}.log", encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create a console handler for logging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create a formatter that includes the time
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add the handlers to the logger
        self.logger.addHandler(file_handler)
        # self.logger.addHandler(console_handler)
    
        # Set the logger level
        self.logger.setLevel(logging.INFO)

class Agent(Memory):
    def __init__(self, name, initial_message):
        super().__init__(name, initial_message)
        self.message_queue = []
        self.state = "idle"
        self.lock = threading.Lock()
        self.package = None
        # self.logger.info(f"Agent {name} initialized with initial message: {initial_message}")   
    
    def enqueue(self, speaker, message):
        with self.lock:
            self.message_queue.append({"role": speaker, "content": message})
        if self.state == "idle":
            threading.Thread(target=self.run, args=()).start()

    def execute(self, tool_name, tool_info, arguments):
        tool_name = tool_name.lower()
        tool_info['name'] = tool_name
        try:
            if tool_name == 'exec_python_file':
                filename = arguments['filename']
                try:
                    result, self.package = start_interactive_subprocess(filename)
                except Exception as e:
                    result = f"Error: {e}"
                tool_info['content'] = str(result)
                # self.logger.info(f"{filename}\n---Result---\n{result}")

            elif tool_name == 'input':
                content = arguments['content']
                if self.package:
                    try:
                        result, self.package = send_input(content,self.package)
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = "Error: No process to input."
                tool_info['content'] = str(result)
                # self.logger.info(f"Input:\n{content}\n---Result---\n{result}")

            elif tool_name == 'read_file':
                tool_info['name'] = 'read_file'
                filename = arguments['filename']
                content, hashvalue = read_file(filename)
                result = f"{filename}\n---Content---\n{content}\n---base_commit_hash---\n{hashvalue}"
                tool_info['content'] = result
                # self.logger.info(result)
            
            elif tool_name == 'change_task_status':
                old_content, hashvalue = read_file(f"todo_{self.name}.txt")
                write_file(f"todo_{self.name}.txt", arguments['todo'], True, hashvalue, agent_name=self.name)

                old_content, hashvalue = read_file(f"status_{self.name}.txt")
                write_file(f"status_{self.name}.txt", arguments['done'], True, hashvalue, agent_name=self.name)

                tool_info['content'] = f"Success."
                # self.logger.info(f"Change todo list to: {arguments['todo']}\nChange task status to: {arguments['done']}")
                
            elif tool_name == 'write_file':
                tool_info['name'] = 'write_file'
                filename = arguments['filename']
                content = arguments['content']
                if 'overwrite' in arguments:
                    overwrite = arguments['overwrite']
                    base_commit_hash = arguments['base_commit_hash'] if 'base_commit_hash' in arguments else None
                    result = write_file(filename, content, overwrite, base_commit_hash, agent_name=self.name)
                else:
                    result = write_file(filename, content, agent_name=self.name)
                tool_info['content'] = result
                self.logger.info(f"{filename}\n---Content---\n{content}\n---Result---\n{result}")

            elif tool_name == 'add_agent':
                if len(self.subordinates) > config.MAX_SUBORDINATES:
                    tool_info['name'] = 'add_agent'
                    result = tool_info['content'] = f'Error: You have already recruited {config.MAX_SUBORDINATES} agents. No more agents can be recruited.\nRecruited agents: {self.get_subordinates()}'
                else:
                    tool_info['name'] = 'add_agent'
                    tool_info['content'] = 'Success.'
                    agent_name = arguments['name']
                    if agent_name in used_names:
                        # tool_info['content'] = f"Error: {agent_name} already exists. Please use another name."
                        # logging.error(f"Error: {agent_name} already exists. Please use another name.")
                        agent_name = agent_name + '_' + str(time.time())[-5:]
                        tool_info['content'] = f"Warning: {arguments['name']} already exists. Automatically change to {agent_name}.\nSuccess."
                    self.add_subordinate(agent_name,arguments['description'], arguments['initial_prompt'])
                    self.logger.info(f"Add agent: {agent_name} success, with description: {arguments['description']}, and initial_prompt: {arguments['initial_prompt']}")
            elif tool_name == 'talk':
                pattern = re.compile(r'<talk goal=(?:"([^"]+)"|\'([^\']+)\')>(.*?)</talk>', re.IGNORECASE | re.DOTALL)
                matches = re.findall(pattern, arguments['messages'])
                tool_info['name'] = 'talk'
                result = arguments['messages']
                if matches:
                    tool_info['content'] = 'Successfully sent. You may terminate now to wait for the response, or complete the rest of your TODO list first.'
                else:
                    tool_info['content'] = 'Error: No matched <talk goal="Name"></talk> found in your response. You must talk in this specific XML format.'
                for match in matches:
                    name = match[0] if match[0] else match[1]
                    content = match[2].strip()
                    
                    if name in agent_dict:
                        agent_dict[name].enqueue("user", f"{self.name} : {content}")
                    else:
                        raise ValueError(f"Error: {name} is not a valid agent name")
                     
            elif tool_name == 'terminate':
                try:
                    with git_lock:
                        f = open(f"files/todo_{self.name}.txt", 'r')
                        content = f.read()
                        f.close()
                except FileNotFoundError:
                    content = ''
                # if content != None and content != '':
                #     tool_info['content'] = f"Error: You have not finished your TODO list. That is:\n\n{content}\n\n Please finish it and clear it by calling 'change_task_status' function."
                # else:
                return {}
            else:
                raise ValueError(f"Error: {tool_name} is not a valid function name")
            return tool_info
        except Exception as e:
            self.logger.error(e)
            return {"role": "user", "content": "Error:"+str(e)}

    def run(self):
        if(self.state!="idle"):
            return
        self.state = "running"
        while self.message_queue:
            previous_memory = self.get()
            
            with self.lock:
                new_message = self.message_queue
                self.message_queue = []
            
            for i in new_message:
                self.add_memory(i)
                
            req = previous_memory + new_message
            round = 0
            self.package = None
            assistant_output = None

            while round < config.MAX_ROUNDS:
                response = get_llm_response(req, agent_name=self.name)
                assistant_output = response['choices'][0]['message']
                llm_output = assistant_output['content']
                self.add_memory(assistant_output)
                req = self.get()
                if llm_output != None:
                    self.logger.info(f"Assistant: {llm_output}")
                if not assistant_output.get('tool_calls'):
                    self.add_dialogue("user", "Error: No function call found in the response. You must use function calls to work and communicate with other agents. If you have nothing to do now, please call 'terminate' function.")
                    req = self.get()
                    round += 1
                else:
                    break

            round = 0
            while round < config.MAX_ROUNDS:
                terminated = False
                for tool_call in assistant_output.get('tool_calls', []):
                    tool_name = tool_call['function']['name']
                    arguments = json.loads(tool_call['function']['arguments'])
                    tool_info = self.execute(tool_name, {"role": "tool", "tool_call_id": tool_call['id']}, arguments)
                    if tool_info == {}:
                        terminated = True
                        break
                    self.add_memory(tool_info)
                    req += [tool_info]
                if terminated:
                    break
                round += 1
                response = get_llm_response(req, agent_name=self.name)
                assistant_output = response['choices'][0]['message']
                llm_output = assistant_output['content']
                self.add_memory(assistant_output)
                req += [assistant_output]
                while not assistant_output.get('tool_calls'):
                    req += [{"role":"user", "content": "Error: No function call found in the response. You must use function calls to work and communicate with other agents. If you have nothing to do now, please call 'terminate' function."}]
                    response = get_llm_response(req, agent_name=self.name)
                    assistant_output = response['choices'][0]['message']
                    llm_output = assistant_output['content']
                    self.add_memory(assistant_output)
                    round += 1

        self.state = "idle"

agent_dict = {}