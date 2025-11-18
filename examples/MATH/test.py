import subprocess
import threading
import sys
import time
def enqueue_output(out, queue, ready_event):
    while True:
        char = out.read(1)  # Read one character at a time
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
        bufsize=0,  # Unbuffered, real-time output
        text=True
    )

    # List for storing output characters
    output_chars = []
    output_ready = threading.Event()

    # Start a thread to capture output
    output_thread = threading.Thread(target=enqueue_output, args=(process.stdout, output_chars, output_ready))
    output_thread.start()
    try:
        # Perform multi-round interaction
        while True:
            output_ready.wait()
            time.sleep(1)
            # Display the program output so far
            sys.stdout.write(''.join(output_chars))
            output_chars.clear()
            sys.stdout.flush()
            output_ready.clear()

            # Get user input
            user_input = input()
            if user_input.lower() == 'exit':
                break

            # Send input to the program
            process.stdin.write(user_input + '\n')
            process.stdin.flush()

    except KeyboardInterrupt:
        print("Interaction interrupted by user")
    finally:
        process.stdin.close()
        process.terminate()
        process.wait()
        output_thread.join()

if __name__ == "__main__":
    interactive_subprocess('files/main.py')  # Replace with the actual path
