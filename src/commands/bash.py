import subprocess
from typing import List


def execute(args: list[str]) -> str:
    bash_cmd = " ".join(args)
    if not bash_cmd:
        return "⚠️ No args for /bash."

    result = subprocess.run(bash_cmd, shell=True, capture_output=True, text=True)
    return (result.stdout + result.stderr).strip()
