import config
import requests
import os
import json
import logging
import time
written_files = dict()
used_names = set()
tools = []
input_token=0
output_token=0

def gen_tools(agent_name):
    if config.share_file:
        wf = []
        for agent, files in written_files.items():
            agent_files = [f for f in files if 'todo' not in f.lower() and 'status' not in f.lower()]
            wf.extend(agent_files)
    else:
        if agent_name in written_files:
            wf = [f for f in written_files[agent_name] if 'todo' not in f.lower() and 'status' not in f.lower()]
        else:
            wf = []
    global tools
    tools = [
        {
                "name": "exec_python_file",
                "description": "Execute a Python file and get the result. Cannot detect bugs. Be sure to review the code or use write_file to write the file first. If the program requires user input, please use this function first, and then use 'input' function to pass your input.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The filename of the Python file to be executed."
                        }
                    }
            }
        },
        {
                "name": "input",
                "description": "Input a string to the running Python code. Only available after exec_python_file is called.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The string to be input."
                        }
                    }
                }
        },
        {
                "name": "read_file",
                "description": f"Read the content of a file. Return file content and file hash. To modify a file, please first read it, then write it(using the same hash).\nYou have created these files:{wf}\nYou can also read any files created by other agents.",
                "parameters": {
                            "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The filename to be read."
                        }
                    }
                },
                "required": [
                    "filename"
                ]
        },
        {
                "name": "write_file",
                "description": f"Write raw content to a file. If the file exists, only overwrite when overwrite = True and hash value (get it from read_file) is correct. ",
                "parameters": {
                            "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The filename to be written."
                        },
                        "content": {
                            "type": "string",
                            "description": r"The content to be written. Use \n instead of \\n for a new line."
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "Optional. Whether to overwrite the file if it exists. Default is False. If True, base_commit_hash is required."
                        },
                        "base_commit_hash": {
                            "type": "string",
                            "description": "Optional. The hash value of the file to be modified(get it from read_file). Required when overwrite = True."
                        }
                    }
                },
                "required": [
                    "filename",
                    "content"
                ]
        },
        {"name": "change_task_status",
                "description": "Change the content of your task status. It should include what you have done, and what you should do later, in case you would forget.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todo": {
                            "type": "string",
                            "description": "You TODO list. You must finish all the tasks and clear this list before calling the 'terminate' function."
                        },
                        "done": {
                            "type": "string",
                            "description": "The tasks you have done. You can write anything you want to remember."
                        }
                    }
                },
                "required": [
                    "content"
                ]
        },
        {
                "name": "add_agent",
                "description": "If your task is too complex, you can recruit agents to the conversation as your subordinates and help you. Return the real name. To add multiple agents, please call this function multiple times. After that, you MUST talk to them using function calls. You do not need to add your collaborators in the prompt, since they have been added by the CEO.",
                "parameters": {
                            "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the agent to be added. Do not use space. Do not use the same name as any existing agent."
                        },
                        "description": {
                            "type": "string",
                            "description": "The description of the agent, for your reference."
                        },
                        "initial_prompt": {
                            "type": "string",
                            "description": '''
                            The initial prompt and memory of that agent. Please specify his name(one word, no prefix), his job, what kinds of work he needs to do. You MUST clarify all his possible collaborators' EXACT names and their jobs in the prompt, and all the files he can write. The format should be like (The example is for Alice in another novel writing project):
                            You are Alice, a novelist. Your job is to write a single chapter of a novel with 1000 words according to the outline (outline.txt) from Carol, the architect designer, and pass it to David (chapter_x.txt), the editor. Please only follow this routine. Your collarborators include Bob(the Boss), Carol(the architect designer) and David(the editor).
                            Please note that every agent is lazy, and will not care anything not mentioned by your prompt. To ensure the completion of the project, the work of each agent should be non-divisable, detailed in specific action(like what file to write) and limited to a simple and specific instruction(For instance, instead of "align with the overall national policies", please specify those policies).
                            '''
                        }
                    }
                },
                "required": [
                    "name",
                    "description",
                    "initial_prompt"
                ]
        },
        {
                "name": "talk",
                "description": "Leave a message to specific agents for feedback. They will reply you later on.",
                "parameters":{
                    "type": "object",
                    "properties": {
                        "messages": {
                            "type": "string",
                            "description": "All the messages to be sent. The format must look like: <talk goal=\"Name\">TalkContent</talk><talk goal=\"Name\">TalkContent</talk>"
                        }
                    }
                },
                "required": [
                    "messages"
                ]
        },
        {
                "name": "terminate",
                "description": "End your current conversation. Please ensure all your tasks in your TODO list have been done and cleared.",
        }
    ]


def _get_llm_response(messages, enable_tools=True, agent_name=''):
    api_key = config.api_key
    url = config.url
    headers = {'Content-Type': 'application/json',
            'Authorization':f'Bearer {api_key}'}
    gen_tools(agent_name)
    if enable_tools:
        body = {
            'model': config.model,
            "messages": messages,
            "functions": tools,
            "temperature": 0,
        }
    else:
        body = {
            'model': config.model,
            "messages": messages,
            "temperature": 0,
        }
    try:
        response = requests.post(url, headers=headers, json=body)
        # print(response.content)
        return response.json()
    except Exception as e:
        return {'error': e}

def get_llm_response(messages, enable_tools=True, agent_name=''):
    response = _get_llm_response(messages, enable_tools, agent_name)
    while 'choices' not in response:
        logging.error(response)
        # time.sleep(3)
        response = _get_llm_response(messages, enable_tools, agent_name)
    # if response['choices'][0]['message']['content']:
    #     logging.info(response['choices'][0]['message']['content'])
    global input_token,output_token
    input_token+=response['usage']['prompt_tokens']
    output_token+=response['usage']['completion_tokens']
    logging.info(f"Input token: {input_token}, Output token: {output_token}")
    return response
    