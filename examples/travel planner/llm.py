import config
import os
import sys
import json
import logging
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)
import llm_core

# NOTE: utils.write_file records outputs as written_files[agent_name] = set(...),
# i.e. it treats this as a dict keyed by agent (same as the root framework). The
# original example declared it as a set(), so every successful write raised
# "'set' object does not support item assignment" and returned that string as a
# fake error. A dict makes the existing bookkeeping work and lets write_file
# report success correctly.
written_files = dict()
tools = []

def gen_tools():
    global tools
    tools = [
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "exec_python",
        #         "description": "Execute raw Python code and get the result. Return the result as a string, or an error message. DO NOT accept user input or interaction. If you do not want to execute, PLEASE USE write_file instead.",
        #         "parameters": {
        #                     "type": "object",
        #             "properties": {
        #                 "code": {
        #                     "type": "string",
        #                     "description": "The raw Python code to be executed. DO NOT USE ```."
        #                 }
        #             }
        #         },
        #         "required": [
        #             "code"
        #         ]
        #     }
        # },
        {
                "name": "exec_python_file",
                "description": "Execute a Python file and get the result. Cannot detect bugs. Be sure to review the code first. If the program requires user input, please use this function first, and then use 'input' function to pass your input.",
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
                "description": "Read the content of a file. Return file content and file hash. Existing files:\n"+str(written_files)+"\nTo modify a file, please first read it, then write it(using the same hash)." if written_files else "No existing files are available. Please write a file first.",
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
                "description": f"Write raw content to a file. If the file exists, only overwrite when overwrite = True and hash value (get it from read_file) is correct. Existing files: {written_files} Do not include ``` in the content.",
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
        {
                "name": "add_agent",
                "description": "If the task is too complex for the current team, recruit a new collaborator to help you. Provide their name, a short description, and a detailed initial prompt. After recruiting, you MUST reach them with <talk goal=\"Name\">...</talk> to assign work. Returns the real (possibly auto-renamed) name.",
                "parameters": {
                            "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the agent to be added. One word, no spaces. Do not reuse an existing name."
                        },
                        "description": {
                            "type": "string",
                            "description": "A short description of the agent, for your reference."
                        },
                        "initial_prompt": {
                            "type": "string",
                            "description": "The initial prompt for that agent. Specify his name, his job, exactly what files he must write, and all his collaborators' EXACT names and jobs. Keep his work non-divisible, specific and simple."
                        }
                    }
                },
                "required": [
                    "name",
                    "description",
                    "initial_prompt"
                ]
        }
    ]


def _get_llm_response(messages, enable_tools=True):
    gen_tools()
    return llm_core.chat_completion(messages, config.model,
                                    llm_core.wrap_tools(tools) if enable_tools else None,
                                    api_key=config.api_key, base_url=config.base_url,
                                    reasoning_effort=getattr(config, 'reasoning_effort', None))

def get_llm_response(messages, enable_tools=True):
    response = _get_llm_response(messages, enable_tools)
    while 'choices' not in response:
        logging.error(response)
        time.sleep(1)
        response = _get_llm_response(messages, enable_tools)
    return response
    