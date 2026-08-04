import argparse
import json
import os
import shutil
import subprocess
import sys
import time

import pandas as pd

# file paths
val_file_path = 'travel_planner_val.xlsx'
config_file_path = 'config.py'
main_script_path = 'main.py'
output_folder = './'
plan_folder = 'files/plan.json'

# rewrite additional_prompt for one row
def update_additional_prompt(config_content, row):
    query = row['query']
    ref_info = row['reference_information']
    new_prompt = '''
Your company's current goal is to develop a travel plan in 'plan.json', in the format:

{{"plan":[{{"day": 1, "current_city": "from [City A] to [City B]", "transportation": "Flight Number: XXX, from A to B", "breakfast": "-", "attraction": "Name, City;Name, City;...;Name, City;", "lunch": "Name, City", "dinner": "Name, City", "accommodation": "Name, City"}}, {{"day": 2, "current_city": "City B", "transportation": "-", "breakfast": "Name, City", "attraction": "Name, City;Name, City;", "lunch": "Name, City", "dinner": "Name, City", "accommodation": "Name, City"}}, ...]}}
where "-" denotes not applicable(like the accommodation of the last day, or the meal on the plane/car).
'''+f'''
Here are the customers' requirements:
{query} You cannot choose the same restaurant for two different meals. Keep the transportation mode consistent across the whole trip: if you take a flight on any day, do not use self-driving on any day (you cannot fly and drive your own car in the same trip), and vice versa.

Here are all the needed information. You cannot query more. Be careful with room rules and Minimum Nights Stay!
{ref_info}

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


def plan_file_is_valid(path):
    """Minimal structural check used for skip/salvage decisions."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return isinstance(data.get('plan'), list) and len(data['plan']) > 0
    except Exception:
        return False


def kill_process_tree(proc):
    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                   capture_output=True)


def run_row(index, row, config_content, timeout):
    """Run main.py for one benchmark row. Returns a status string."""
    updated_config_content = update_additional_prompt(config_content, row)
    with open(config_file_path, 'w', encoding='utf-8') as f:
        f.write(updated_config_content)

    # main.py removes log.txt unconditionally at startup
    if not os.path.exists('log.txt'):
        with open('log.txt', 'w', encoding='utf-8') as f:
            f.write('')

    env = dict(os.environ)
    env['PYTHONUTF8'] = '1'
    os.makedirs('run_logs', exist_ok=True)
    console_path = os.path.join('run_logs', f'console_row{index}.txt')

    status = 'ok'
    started = time.time()
    with open(console_path, 'w', encoding='utf-8', errors='replace') as console:
        proc = subprocess.Popen([sys.executable, main_script_path],
                                stdout=console, stderr=subprocess.STDOUT,
                                env=env)
        try:
            rc = proc.wait(timeout=timeout)
            if rc != 0:
                status = f'exit code {rc}'
        except subprocess.TimeoutExpired:
            kill_process_tree(proc)
            proc.wait()
            status = f'timeout after {timeout}s'
    elapsed = time.time() - started

    # Collect the produced plan (also salvages timeout/crash runs whose
    # plan.json was already written)
    copied = False
    if os.path.exists(plan_folder) and plan_file_is_valid(plan_folder):
        output_plan_path = os.path.join(output_folder, f'plan{index}.json')
        shutil.copy(plan_folder, output_plan_path)
        copied = True

    # Archive the run log for post-mortems
    try:
        if os.path.exists('log.txt'):
            shutil.copy('log.txt', os.path.join('run_logs', f'log_row{index}.txt'))
    except Exception:
        pass

    if copied and status != 'ok':
        status += ' (plan salvaged)'
    elif not copied:
        status += '; no valid plan produced' if status != 'ok' else 'no valid plan produced'
    print(f"Row {index}: {status} [{elapsed/60:.1f} min]", flush=True)
    return copied


def parse_args():
    parser = argparse.ArgumentParser(description='TravelPlanner benchmark runner')
    parser.add_argument('--start', type=int, default=0, help='first row index (inclusive)')
    parser.add_argument('--end', type=int, default=None, help='last row index (exclusive)')
    parser.add_argument('--only', type=str, default=None,
                        help='comma-separated row indices to (re)run, overrides --start/--end')
    parser.add_argument('--timeout', type=int, default=10800,
                        help='per-row timeout in seconds (default 3h)')
    parser.add_argument('--force', action='store_true',
                        help='rerun rows even if a valid plan{i}.json exists')
    parser.add_argument('--retries', type=int, default=2,
                        help='extra passes over rows that still have no valid plan')
    return parser.parse_args()


def main():
    args = parse_args()

    # load the validation set
    val_data = pd.read_excel(val_file_path)

    # read config.py once (the anchors are stable, so rewriting is idempotent)
    with open(config_file_path, 'r', encoding='utf-8') as file:
        config_content = file.read()

    if args.only:
        indices = [int(x) for x in args.only.split(',') if x.strip() != '']
    else:
        end = len(val_data) if args.end is None else min(args.end, len(val_data))
        indices = list(range(args.start, end))

    for attempt in range(1 + max(0, args.retries)):
        pending = []
        for index in indices:
            plan_path = os.path.join(output_folder, f'plan{index}.json')
            if not args.force and plan_file_is_valid(plan_path):
                continue
            pending.append(index)
        if not pending:
            break
        if attempt > 0:
            print(f"Retry pass {attempt}: {len(pending)} rows still missing "
                  f"valid plans: {pending}", flush=True)
        for index in pending:
            run_row(index, val_data.iloc[index], config_content, args.timeout)
        args.force = False  # retries only target still-invalid rows

    missing = [i for i in indices
               if not plan_file_is_valid(os.path.join(output_folder, f'plan{i}.json'))]
    done = len(indices) - len(missing)
    print(f"\nDone: {done}/{len(indices)} rows have valid plans.", flush=True)
    if missing:
        print(f"Still missing: {missing}", flush=True)
        print(f"Rerun with: python execute.py --only "
              f"{','.join(str(i) for i in missing)}", flush=True)


if __name__ == '__main__':
    main()
