import os

# API configuration - reads from environment variable for security
# In production, set OPENAI_API_KEY environment variable
# Override: api_key = 'sk-your_api_key_here' for testing only
api_key = os.getenv('OPENAI_API_KEY', 'sk-your_api_key_here')

# Model configuration - defaults to GPT-5.1
# Override by setting MODEL environment variable or modifying this value
# Supported models: gpt-5.1, gpt-5, gpt-4, gpt-4-turbo, etc.
model = os.getenv('MODEL', 'gpt-5.1')

url = 'https://api.openai.com/v1/chat/completions'

# Web search configuration - uses OpenAI GPT-5 web search tool
# Set ENABLE_WEB_SEARCH=true to enable web search in agent prompts
# Set WEB_SEARCH_PROVIDER to choose provider (openai, bing, google, serper)
enable_web_search = os.getenv('ENABLE_WEB_SEARCH', 'false').lower() == 'true'
web_search_provider = os.getenv('WEB_SEARCH_PROVIDER', 'openai')

MAX_MEMORY = 10
MAX_ROUNDS = 20
MAX_SUBORDINATES = 5
share_file = True # Whether to share files across agents
ceo_name = "Bob"
initial_prompt = r'''
You are Bob, the leader of a software development club. Your club's current goal is to develop a Gobang game with a very strong AI, no frontend, and can be executed by running 'main.py'. Remember to test it. You are now recruiting employees and assigning work to them. For each employee(including yourself), please write a prompt. Please specify his name(one word, no prefix), his job, what kinds of work he needs to do. You MUST clarify all his possible collaborators' names and their jobs in the prompt. The format should be like (The example is for Alice in another novel writing project):

<agent name="Alice">
You are Alice, a novelist. Your job is to write a single chapter of a novel with 1000 words according to the outline (outline.txt) from Carol, the architect designer, and pass it to David (chapter_x.txt), the editor. Please only follow this routine. Your collarborators include Bob(the Boss), Carol(the architect designer) and David(the editor).
</agent>

Please note that every employee is lazy, and will not care anything not mentioned by your prompt. To ensure the completion of your project, the work of each employee should be **non-divisable**, detailed in specific action(like what file to write. Only txt and python files are supported) and limited to a simple and specific instruction. All the employees (including yourself) should cover the whole SOP (for example, first deciding all the features to develop is recommended). Speed up the process by adding more employees to divide the work.
'''

additional_prompt = r'''
Your club's current goal is to develop a Gobang game with a very strong AI, no frontend, and can by executed by running 'main.py'. The project should be executable in files.

You can only output function calls in your response. DO NOT output anything else directly.

Leave a remarkable TODO in your TODO list(by using the change_task_status function) whenever there is an unfinished task. Please keep updating your TODO list until everything is done. In that case, you should clear your TODO list txt file(write nothing into it) and call the 'terminate' function.

Please note that ALL your output must be function calls. Do not output directly! For example, if you want to talk to someone, you should call the 'talk' function.
'''