import psutil
import subprocess

def terminate_subprocess(process):
    import subprocess
    import psutil
    parent = psutil.Process(process.pid)
    children = parent.children(recursive=True)
    for child in children:
        child.terminate()
    process.terminate()
    try:
        process.wait(timeout = 1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout = 1)

