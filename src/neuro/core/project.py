import os
import json
from datetime import datetime

NEURO_GLOBAL = os.path.expanduser("~/.neuro/projects")


def is_initialized(project_path: str) -> bool:
    return os.path.exists(os.path.join(project_path, ".neuro/settings.json"))


def get_settings(project_path: str):
    path = os.path.join(project_path, ".neuro/settings.json")
    with open(path) as f:
        return json.load(f)


def ensure_global_registry():
    os.makedirs(NEURO_GLOBAL, exist_ok=True)


def register_project(settings: dict):
    ensure_global_registry()

    project_name = settings["projectName"]
    file_path = os.path.join(NEURO_GLOBAL, f"{project_name}.json")

    entry = {
        "projectPath": settings["projectPath"],
        "neuroPath": os.path.join(settings["projectPath"], ".neuro"),
        "createdDate": settings["createdAt"],
        "executionHistory": []
    }

    if os.path.exists(file_path):
        data = json.load(open(file_path))
    else:
        data = {"projectName": project_name, "entries": []}

    data["entries"].append(entry)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def log_execution(settings: dict, command: str, success: bool, summary: str):
    file_path = os.path.join(NEURO_GLOBAL, f"{settings['projectName']}.json")

    data = json.load(open(file_path))

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "command": command,
        "success": success,
        "summary": summary
    }

    data["entries"][-1]["executionHistory"].append(log_entry)

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)