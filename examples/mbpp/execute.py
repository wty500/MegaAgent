import pandas as pd
import os
import shutil
import subprocess
from datasets import load_dataset
import sys

dataset_sanitized = load_dataset("google-research-datasets/mbpp", "sanitized")

# 文件路径
config_file_path = 'config.py'
main_script_path = 'main.py'
output_folder = './'
plan_folder = 'files/ans.py'

# 读取 config.py 文件
with open(config_file_path, 'r', encoding='utf-8') as file:
    config_content = file.read()

# 修改 additional_prompt 的函数
def update_additional_prompt(config_content, question, test_case):
    question = question.replace("'''", '"""')
    new_prompt = f'''
Your company's current goal is to complete the a python function with 100% accuracy and put it in "ans.py".

**Here is the customers' required function:**
{question}

You must pass the following unit test cases before terminating the project:
{test_case}

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

sum = 0
passed = 0
# 针对每一行进行处理
for index, row in enumerate(dataset_sanitized['test']):
    # 修改 config.py 文件
    updated_config_content = update_additional_prompt(config_content, row['prompt'], row['test_list'])
    
    # 临时保存更新后的 config.py
    temp_config_path = f'config.py'
    with open(temp_config_path, 'w', encoding='utf-8') as file:
        file.write(updated_config_content)
    
    sum += 1
    # 运行 main.py
    while True:
        subprocess.run(["python", main_script_path], check=True)
        
        # 复制生成的 plan.json 到目标文件
        if os.path.exists(plan_folder):
            output_plan_path = os.path.join(output_folder, f'plan{index}.py')
            shutil.copy(plan_folder, output_plan_path)
            with open(output_plan_path, 'r') as f:
                program_content = f.read()
            try:
                for case in row['test_list']:
                    with subprocess.Popen([sys.executable, '-c', program_content+'\n'+case], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE) as proc:
                        try:
                            proc.wait(timeout=5)  # 5 second timeout
                            if proc.returncode != 0:
                                raise AssertionError("Test failed")
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            raise AssertionError("Test timed out")
                passed += 1
                break
            except AssertionError:
                print(f"Test case {index} failed")
                break
        else:
            print(f"Cannnot find {plan_folder}")
            
print(f"Passed {passed}/{sum} test cases")
