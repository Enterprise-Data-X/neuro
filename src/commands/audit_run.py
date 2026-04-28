import os
import json
from ..core import project
from ..core.policy import Policy


def get_latest_audit(workspace):
    files = sorted(os.listdir(workspace), reverse=True)
    return files[0] if files else None


def run(file_name=None):
    cwd = os.getcwd()

    if not project.is_initialized(cwd):
        print("❌ Neuro is not initialized.")
        return

    settings = project.get_settings(cwd)

    workspace = os.path.join(cwd, ".neuro/workspace")

    if not file_name:
        file_name = get_latest_audit(workspace)

    if not file_name:
        print("❌ No audit files found")
        return

    path = os.path.join(workspace, file_name)

    if not os.path.exists(path):
        print("❌ Audit file not found")
        return

    data = json.load(open(path))

    # Placeholder for execution engine
    print("⚙️ Applying recommendations...")
    policy = Policy(cwd)

    for ts, items in data.items():
        for item in items:
            print(f"- {item['filePath']}: {item['recommendation']}")
            file_path = item["filePath"]
            policy.enforce_file_write(file_path)
            
    project.log_execution(settings, "neuro audit run", True, "Audit applied")
