import os
import shutil
import json
import subprocess
from datetime import datetime
from ..core import project
from ..core.sourcecontrol import clone_repository


def run(path: str):
    abs_path = os.path.abspath(path)
    neuro_path = os.path.join(abs_path, ".neuro")

    # recreate .neuro
    if os.path.exists(neuro_path):
        shutil.rmtree(neuro_path)

    os.makedirs(neuro_path)

    # create structure
    for folder in ["tools", "skills", "hooks", "workspace"]:
        os.makedirs(os.path.join(neuro_path, folder))

    settings = {
        "projectName": os.path.basename(abs_path),
        "projectPath": abs_path,
        "createdAt": datetime.utcnow().isoformat(),
        "permissions": {
            "allowUnsafeCommands": False,
            "allowedCommands": []
        }
    }

    with open(os.path.join(neuro_path, "settings.json"), "w") as f:
        json.dump(settings, f, indent=2)

    project.register_project(settings)

    repo_url = input("Organisation Repository Repository Url: ").strip()
    if repo_url:
        clone_repository(repo_url, neuro_path)
    else:
        print("No repository URL provided; skipping clone.")

    print("✅ Neuro initialized")

    project.log_execution(settings, "neuro init", True, "Project initialized")