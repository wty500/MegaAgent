import pandas as pd
import os
import shutil
import subprocess
from human_eval.data import write_jsonl, read_problems

problems = read_problems()

num_samples_per_task = 1
questions = [
    dict(task_id=task_id,prompt=problems[task_id]["prompt"])
    for task_id in problems
    for _ in range(num_samples_per_task)
]

# 文件路径
config_file_path = 'config.py'
main_script_path = 'main.py'
output_folder = './'
plan_folder = 'files/ans.json'

# 读取 config.py 文件
with open(config_file_path, 'r', encoding='utf-8') as file:
    config_content = file.read()

# 修改 additional_prompt 的函数
def update_additional_prompt(config_content, task_id, question):
    question = question.replace("'''", '"""')
    new_prompt = '''
Your company's current goal is to complete the rest of a python function with 100% accuracy and put it in a json file named "ans.json" with a given task id.

For example, for the prompt
"def return1():\n"
with task id = "example/0", you should put the following in "ans.json":
{"task_id": "example/0", "completion": "\treturn 1"}
as you can see, you must not put the prompt "def return1():\n" itself into "ans.json".
'''+f'''
**Here is the customers' required function:**
{question}

Your company's goal is to complete the rest of it with 100% accuracy. The task id is: "{task_id}"

You MUST use exactly <talk goal="Name">TalkContent</talk> format to talk to others, like:

<talk goal="Alice">Alice, I have completed 'a.txt'. Please check it for your work and talk to me again if needed. </talk>. 

Otherwise, they will not receive your message, and the conversation will terminate. "Name" should only be ONE specific employee. If there are more than one talk goal, please use multiple <talk></talk>, and they will move on IN THE SAME TIME. 

You must use function calls in JSON for file operations.

Leave a remarkable TODO wherever there is an unfinished task. Please keep updating your TODO list until everything is done. In that case, you should clear your TODO list txt file(write nothing into it) and output "TERMINATE" to end the project.
'''
    updated_content = config_content.replace(
        config_content[config_content.find("additional_prompt = r'''") + len("additional_prompt = r'''"):config_content.find("'''", config_content.find("additional_prompt = r'''") + len("additional_prompt = r'''"))],
        new_prompt
    )
    return updated_content

# 针对每一行进行处理
for index, question in enumerate(questions):
    # Check if plan{index}.json already exists
    # output_plan_path = os.path.join(output_folder, f'plan{index}.json')
    # if os.path.exists(output_plan_path):
    #     print(f"plan{index}.json already exists, skipping...")
    #     continue

    # 修改 config.py 文件
    updated_config_content = update_additional_prompt(config_content, question['task_id'], question['prompt'])
    
    # 临时保存更新后的 config.py
    temp_config_path = f'config.py'
    with open(temp_config_path, 'w', encoding='utf-8') as file:
        file.write(updated_config_content)
    
    # 运行 main.py
    try:
        subprocess.run(["python", main_script_path], check=True)
        
        # 复制生成的 plan.json 到目标文件
        if os.path.exists(plan_folder):
            # with open
            output_plan_path = os.path.join(output_folder, f'plan{index}.json')
            shutil.copy(plan_folder, output_plan_path)
            print(f"Plan for row {index} saved as {output_plan_path}.")
        else:
            print(f"Plan for row {index} not found. Ensure main.py created the file.")
    except subprocess.CalledProcessError as e:
        print(f"Error running main.py for row {index}: {e}")
    except FileNotFoundError:
        print(f"File not found during processing of row {index}. Ensure paths are correct.")
    