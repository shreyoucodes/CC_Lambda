import os
import uuid
import subprocess
import shutil
import textwrap

BASE_PATH = "./execution_engine/runtime"

def generate_code(language, code):
    uid = str(uuid.uuid4())
    workdir = os.path.join(BASE_PATH, uid)
    os.makedirs(workdir, exist_ok=True)

    if language == "python":
        filename = "function.py"
        docker_image = "python:3.9-slim"
        full_code = f"def handler():\n{textwrap.indent(code, '    ')}\n\nprint(handler())"
    elif language == "javascript":
        filename = "function.js"
        docker_image = "node:16"
        full_code = f"function handler() {{\n{textwrap.indent(code, '    ')}\n}}\nconsole.log(handler());"
    else:
        raise Exception("Unsupported language")

    file_path = os.path.join(workdir, filename)
    with open(file_path, "w") as f:
        f.write(full_code)

    return uid, file_path, docker_image, filename

def execute_in_docker(uid, docker_image, filename, timeout=5):
    workdir = os.path.join(BASE_PATH, uid)
    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{os.path.abspath(workdir)}:/usr/src/app",
                "-w", "/usr/src/app",
                docker_image,
                "timeout", f"{timeout}",
                "python" if filename.endswith(".py") else "node", filename
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 2  # Buffer time for Python subprocess
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
    except subprocess.TimeoutExpired:
        output = ""
        error = "Function execution timed out."
    finally:
        shutil.rmtree(workdir)

    return output, error

