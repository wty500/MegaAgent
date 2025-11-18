import subprocess
import threading
import sys
import time
def enqueue_output(out, queue, ready_event):
    while True:
        char = out.read(1)  # 每次读取一个字符
        if char == '':
            break
        queue.append(char)
        ready_event.set()
    out.close()

def interactive_subprocess(program_path):
    process = subprocess.Popen(
        [sys.executable, program_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,  # 无缓冲，实时输出
        text=True
    )
    
    # 用来存储输出字符的列表
    output_chars = []
    output_ready = threading.Event()
    
    # 启动一个线程来捕获输出
    output_thread = threading.Thread(target=enqueue_output, args=(process.stdout, output_chars, output_ready))
    output_thread.start()
    try:
        # 进行多轮交互
        while True:
            output_ready.wait()
            time.sleep(1)
            # 显示目前为止程序的输出
            sys.stdout.write(''.join(output_chars))
            output_chars.clear()
            sys.stdout.flush()
            output_ready.clear()

            # 获取用户的输入
            user_input = input()
            if user_input.lower() == 'exit':
                break

            # 向程序发送输入
            process.stdin.write(user_input + '\n')
            process.stdin.flush()
            
    except KeyboardInterrupt:
        print("交互被用户中断")
    finally:
        process.stdin.close()
        process.terminate()
        process.wait()
        output_thread.join()

if __name__ == "__main__":
    interactive_subprocess('files/main.py')  # 替换为实际的路径
