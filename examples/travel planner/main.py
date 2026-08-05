import config
import re
from llm import *
import threading
import logging
from utils import *
import chromadb
import time
import os

def delete_all_files_in_folder(folder_path):
    # Get all files in the folder
    files = os.listdir(folder_path)
    
    for file in files:
        file_path = os.path.join(folder_path, file)
        # Check if it is a file to prevent deleting folders
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"{file} has been deleted.")
        else:
            print(f"{file} is not a file and has been skipped.")
    result = subprocess.run(['git', '-C', 'files', 'commit', '-a', '-m', "init repo"], capture_output=True, text=True)
    
    
# Example usage
folder_path = 'files'  # Specify the folder path
delete_all_files_in_folder(folder_path)
os.remove('log.txt')

# Note: Ensure the 'files' folder exists and is empty before running
logger = logging.getLogger()
logger.setLevel(logging.INFO)
rf_handler = logging.StreamHandler()
f_handler = logging.FileHandler('log.txt')
logger.addHandler(rf_handler)
logger.addHandler(f_handler)
begin_time = time.time()
chroma_client = chromadb.Client()

employee_dict = {}
# Runtime recruitment (add_agent) support: serialize employee_dict mutation and
# cap total headcount to prevent runaway recruitment.
recruit_lock = threading.Lock()
MAX_EMPLOYEES = 15
employee_dict[config.ceo_name] = {
    'memory': [{"role": "user", "content": config.initial_prompt}],
    'lock': threading.Lock(),
    'pending': False,
    'history': chroma_client.create_collection(name=config.ceo_name)
}

# The roster call must yield <employee> text, so tools are disabled here —
# same as the root engine's project-launch call. With tools offered, the
# model tends to call add_agent instead of writing the roster, and this
# engine's launch phase only parses text.
llm_output = get_llm_response(employee_dict[config.ceo_name]['memory'], False)['choices'][0]['message']['content']
logging.info(f"{config.ceo_name}:\n{llm_output}")

employee_dict[config.ceo_name]['memory'].append({"role": "assistant", "content": llm_output})
employee_dict[config.ceo_name]['history'].add(documents=[f"{config.ceo_name}:\n{llm_output}"], ids=[str(time.time())])

employee_pattern = re.compile(r'<employee name="(\w+)">(.*?)</employee>', re.DOTALL)
employees = employee_pattern.findall(llm_output)

for employee in employees:
    employee_dict[employee[0]] = {
        'initial_prompt': f"{employee[1]}\n{config.additional_prompt}",
        'memory': [{"role": "system", "content": f"{employee[1]}\n{config.additional_prompt}\nYou can write your TODO list in todo_{employee[0]}.txt. \n"}],
        'lock': threading.Lock(),
        'pending': False,
        'history': chroma_client.create_collection(name=employee[0]) if employee[0] != config.ceo_name else employee_dict[config.ceo_name]['history']
    }

beginner_pattern = re.compile(r'<beginner>(\w+)</beginner>')
beginners = beginner_pattern.findall(llm_output)
beginner_list = [beginner for beginner in beginners if beginner in employee_dict]

threads = []

def add_memory(employee_name, output):
    # Add memory to the employee's memory list
    # implemented TODO list
    if output == '' or output == 'TERMINATE':
        return
    employee = employee_dict[employee_name]
    employee['memory'].append(output)
    # employee['memory'] = [memory for memory in employee['memory'] if memory['role'] != 'tool']
    content = f"{employee_name}:\n{output['content']}"
    
    if len(employee['memory']) > config.MAX_LEN and employee['memory'][-1]['role'] == 'user':
        try:
            f = open(f"files/todo_{employee_name}.txt", 'r')
            todo_list = f.read()
            f.close()
        except FileNotFoundError:
            todo_list = ''
        
        if todo_list == '':
            todo_list = f'You have not written any TODO list yet. If you still have something to do, please write it in todo_{employee_name}.txt\n'
        else:
            commit_hash = subprocess.check_output(['git', '-C', 'files', 'rev-parse', 'HEAD'], text=True).strip()
            todo_list = f'Your TODO list:\n{todo_list}\nYou can change it in todo_{employee_name}.txt, by providing its current hash:{commit_hash}(will change if you edit TODO list)\n'
        if employee['memory'][-1]['content'] != None:
            relevant_history = employee['history'].query(query_texts=[employee['memory'][-1]['content']], n_results=1)
            # chroma returns empty result lists on a fresh collection; the
            # bare [0][0] index would kill this employee's worker thread
            if relevant_history['documents'] and relevant_history['documents'][0]:
                summary = f"Here are some relevant chat history:\n{relevant_history['documents'][0][0]}\nBelow is the most recent chat history:\n"
            else:
                summary = "Here is the most recent chat history:\n"
        else:
            summary = "Here is the most recent chat history:\n"
        for memory in employee['memory']:
            if memory['role'] == 'tool':
                memory['role'] = 'user'
        employee['memory'] = [{"role": "system", "content": employee['initial_prompt']+todo_list}] + [{"role": "user", "content": summary}] + employee['memory'][-config.MAX_LEN+2:]
    
    employee['history'].add(documents=[content], ids=[str(time.time())])

def work(employee_name, callback=None):
    # Main work function for each employee
    if callback == employee_name:
        callback = None
    employee = employee_dict[employee_name]
    employee['lock'].acquire()
    if employee['pending'] == False:
        employee['lock'].release()
        return
    employee['pending'] = False
    response = get_llm_response(employee['memory'])
    assistant_output = response['choices'][0]['message']
    llm_output = assistant_output['content']
    if llm_output == None:
        llm_output = ''
    add_memory(employee_name, assistant_output)
    if assistant_output['content']:
        logging.info(f"{employee_name}:\n{assistant_output['content']}")
    result = package = None
    rounds = 0
    while assistant_output.get('tool_calls') and rounds < config.MAX_ROUNDS:
        rounds += 1
        for tool_call in assistant_output['tool_calls']:
            tool_name = tool_call['function']['name']
            tool_info = {"role": "tool", "tool_call_id": tool_call['id']}

            try:
                arguments = json.loads(tool_call['function']['arguments'])

                if tool_name == 'exec_python_file':
                    tool_info['name'] = 'exec_python_file'
                    filename = arguments['filename']
                    try:
                        result, package = start_interactive_subprocess(filename)
                    except Exception as e:
                        result = f"Error: {e}"
                    # result = exec_python_file(filename)
                    tool_info['content'] = str(result)
                    result = f"{filename}\n---Result---\n{result}"
                elif tool_name == 'input':
                    tool_info['name'] = 'input'
                    content = arguments['content']
                    if package:
                        try:
                            result, package = send_input(content,package)
                        except Exception as e:
                            result = f"Error: {e}"
                    else:
                        result = "Error: No process to input."
                    tool_info['content'] = str(result)
                    result = f"Input:\n{content}\n---Result---\n{result}"
                elif tool_name == 'read_file':
                    tool_info['name'] = 'read_file'
                    filename = arguments['filename']
                    content, hashvalue = read_file(filename)
                    result = f"{filename}\n---Content---\n{content}\n---base_commit_hash---\n{hashvalue}"
                    tool_info['content'] = result
                elif tool_name == 'write_file':
                    tool_info['name'] = 'write_file'
                    filename = arguments['filename']
                    content = arguments['content']
                    if 'overwrite' in arguments:
                        overwrite = arguments['overwrite']
                        base_commit_hash = arguments['base_commit_hash'] if 'base_commit_hash' in arguments else None
                        result = write_file(filename, content, overwrite, base_commit_hash)
                    else:
                        result = write_file(filename, content)
                    tool_info['content'] = result
                    result = f"{filename}\n---Content---\n{content}\n---Result---\n{result}"
                elif tool_name == 'add_agent':
                    tool_info['name'] = 'add_agent'
                    with recruit_lock:
                        if len(employee_dict) > MAX_EMPLOYEES:
                            result = f"Error: the team already has {MAX_EMPLOYEES} members. No more agents can be recruited."
                        else:
                            new_name = arguments['name']
                            note = ''
                            if new_name in employee_dict:
                                new_name = new_name + '_' + str(time.time())[-5:]
                                note = f"Warning: {arguments['name']} already exists. Automatically renamed to {new_name}.\n"
                            new_prompt = f"{arguments['initial_prompt']}\n{config.additional_prompt}\nYour supervisor is: {employee_name}"
                            employee_dict[new_name] = {
                                'initial_prompt': new_prompt,
                                'memory': [{"role": "system", "content": f"{new_prompt}\nYou can write your TODO list in todo_{new_name}.txt. \n"}],
                                'lock': threading.Lock(),
                                'pending': False,
                                'history': chroma_client.create_collection(name=new_name)
                            }
                            result = f"{note}Success. {new_name} has been recruited. You MUST now talk to {new_name} with <talk goal=\"{new_name}\">...</talk> to assign work."
                    tool_info['content'] = result
                else:
                    raise ValueError(f"Error: {tool_name} is not a valid function name")
                employee['memory'].append(tool_info)
            except ValueError as e:
                employee['memory'] = employee['memory'][:-1]
                employee['memory'].append({"role": "user", "content": str(e)})
            except Exception as e:
                logging.error(e)
                employee['memory'].append({"role": "user", "content": str(e)})

            # too much token cost, but deduct file IO. Use for your own need
            # llm_output += f"\n{tool_name}:\n{result}"

        response = get_llm_response(employee['memory'])
        assistant_output = response['choices'][0]['message'] if 'message' in response['choices'][0] else response['choices'][0]['messages'][-1]
        # llm_output += f"\n{employee_name}:\n{assistant_output['content']}"
        if assistant_output['content'] != None:
            llm_output += assistant_output['content'] + '\n'
        add_memory(employee_name, assistant_output)
        logging.info(f"{tool_name}:\n{result}")
        if assistant_output['content']:
            logging.info(f"{employee_name}:\n{assistant_output['content']}")
    
    if package:
        try:
            package[0].terminate()
        except Exception as e:
            logging.error(f"Error: {e}")
    pattern = re.compile(r'<talk goal="([^"]+)">(.*?)</talk>', re.IGNORECASE | re.DOTALL)
    matches = re.findall(pattern, assistant_output['content'] or '')
    
    if not matches:
        employee['lock'].release()
        
        if "TERMINATE" not in llm_output and not employee['pending']:
            employee['pending'] = True
            logging.error('Error: No matched <talk goal="Name"></talk> found')
            employee['memory'].append({"role": "user", "content": 'Error: No matched <talk goal="Name"></talk> found in your response. You must name someone to relay in this specific format. If you do not want to talk to others, please output "TERMINATE".'})
            work(employee_name, callback)
        else:
            if callback and llm_output != 'TERMINATE':
                add_memory(callback, {"role": "user", "content": f"{employee_name}:\n{llm_output}"})
                work(callback)
        return
    
    call_backed = False
    ok = True
    for match in matches:
        name = match[0]
        content = match[1].strip()
        
        if name in employee_dict:
            if name == callback:
                call_backed = True
            add_memory(name, {"role": "user", "content": f"{employee_name}:\n{llm_output}"})
            
            if not employee_dict[name]['pending']:
                threads.append(threading.Thread(target=work, args=(name, employee_name)))
                employee_dict[name]['pending'] = True
                threads[-1].start()
        else:
            logging.error(f"Error: '{name}' not found in employee_dict")
            employee['memory'].append({"role": "user", "content": f"Error: \"{name}\" not found in employee_dict. \"Name\" should only be ONE specific employee. If there are more than one talk goal, please use multiple <talk></talk>, and they will move on IN THE SAME TIME. If you are done with current work, please only output: TERMINATE"})
            ok = False
            employee['pending'] = True
    
    if not call_backed and callback:
        add_memory(callback, {"role": "user", "content": f"{employee_name}:\n{llm_output}"})
    
    employee['lock'].release()

    if not ok:
        work(employee_name, callback)


for beginner in beginner_list:
    threads.append(threading.Thread(target=work, args=(beginner,)))
    employee_dict[beginner]['pending'] = True

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

while True:
    threads = []
    for employee_name in employee_dict:
        try:
            f = open(f"files/todo_{employee_name}.txt", 'r')
            todo_list = f.read()
            f.close()
        except FileNotFoundError:
            todo_list = ''
        if todo_list != '':
            employee_dict[employee_name]['memory'].append({"role": "user", "content": f"Please complete your TODO list:\n{todo_list}\nYou can change it in todo_{employee_name}.txt.\nIf you have completed all, please clear your TODO list(write nothing into it) to end the project."})
            employee_dict[employee_name]['pending'] = True
            threads.append(threading.Thread(target=work, args=(employee_name,)))
    for thread in threads:
        thread.start()
    if not threads: 
        employee_dict[config.ceo_name]['memory'].append({"role": "user", "content": "All employees have terminated. Please review 'plan.json' files by read_file and see if there is anything unfinished(like a 'XXX' placeholder, or missing a required field), or needs further improvements(check the budget!). In that case, please talk to your employees. Make sure the project is completely finished and ready to release, and then you may output 'TERMINATE' to end the project."})
        employee_dict[config.ceo_name]['pending'] = True
        work(config.ceo_name)
        if "TERMINATE" in (employee_dict[config.ceo_name]['memory'][-1]['content'] or ''):
            break
    for thread in threads:
        thread.join()

end_time = time.time()
logging.info(f"Time elapsed: {end_time-begin_time} seconds")
# print('-----------------')
# for employee in employee_dict.values():
#     print(employee['history'].get())
#     print('-----------------')
