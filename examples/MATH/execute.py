import pandas as pd
import os
import shutil
import subprocess
from datasets import load_dataset
import sys
import random
import json

dataset_sanitized = load_dataset("HuggingFaceH4/MATH-500", split='test')
# Set a fixed random seed for reproducibility
random.seed(42)
# Get the total number of examples in the dataset
total_examples = len(dataset_sanitized)

# Randomly select 100 unique indices
selected_indices = random.sample(range(total_examples), min(100, total_examples))

# Print the selected indices for reference
print(f"Randomly selected {len(selected_indices)} examples from the dataset")
print(f"Selected indices: {selected_indices}")
dataset_sanitized= dataset_sanitized.select(selected_indices)

# 文件路径
config_file_path = 'config.py'
main_script_path = 'main.py'
output_folder = './'
plan_folder = 'files/ans.txt'

# 读取 config.py 文件
with open(config_file_path, 'r', encoding='utf-8') as file:
    config_content = file.read()

# 修改 additional_prompt 的函数
def update_additional_prompt(config_content, question):
    question = question.replace("'''", '"""')
    new_prompt = r'''
Your company's current goal is to solve a math problem with 100% accuracy and put solving process and the final answer in "ans.txt". The final answer should be put in \\boxed{}.'''+f'''

**Here is the original problem:**
{question}

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
for index, row in enumerate(dataset_sanitized):
    # Check if plan{index}.json already exists
    # output_plan_path = os.path.join(output_folder, f'plan{index}.json')
    # if os.path.exists(output_plan_path):
    #     print(f"plan{index}.json already exists, skipping...")
    #     continue
    # 修改 config.py 文件
    updated_config_content = update_additional_prompt(config_content, row['problem'])
    
    # 临时保存更新后的 config.py
    temp_config_path = f'config.py'
    with open(temp_config_path, 'w', encoding='utf-8') as file:
        file.write(updated_config_content)

    subprocess.run(["python", main_script_path], check=True)
    
    sum += 1
    while not os.path.exists(plan_folder):
        print(f"plan{index}.json not found")
        subprocess.run(["python", main_script_path], check=True)
    with open(plan_folder, 'r', encoding='utf-8') as file:
        plan_content = file.read()
        
    # Check if the answer contains \boxed{}
    while "\\boxed{" not in plan_content:
        print(f"Answer for problem {index} doesn't contain \\boxed{{}}, rerunning...")
        # Delete the plan file
        if os.path.exists(plan_folder):
            os.remove(plan_folder)
        # Rerun the subprocess
        subprocess.run(["python", main_script_path], check=True)
        # Wait for file to be created
        while not os.path.exists(plan_folder):
            print(f"Waiting for answer file to be created...")
            subprocess.run(["python", main_script_path], check=True)
        # Read the file again
        with open(plan_folder, 'r', encoding='utf-8') as file:
            plan_content = file.read()
    
    output = {'predicted_answer:': plan_content, 'solution': row['solution']}
    json.dump(output, open(f'plan{index}.json', 'w'), indent=4)
            
print(f"Passed {passed}/{sum} test cases")
