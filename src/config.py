import json
import os
from neuro.logger import get_logger

logger = get_logger("config")
# Base directory
NEURO_HOME = os.path.expanduser("~/.neuro")

# Sub-paths
SCRIPTS_DIR = os.path.join(NEURO_HOME, "scripts")
SKILLS_DIR = os.path.join(NEURO_HOME, "skills")
LOGS_DIR = os.path.join(NEURO_HOME, "logs")
CONFIG_PATH = os.path.join(NEURO_HOME, "config.json")


def load_neuro_config():
    if not os.path.exists(CONFIG_PATH):
        logger.error("config.json not found")
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def get_slash_commands():
    try:
        config = load_neuro_config()
        return config.get("commands", [])
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback to an empty list so the TUI can at least open
        return []

# Helper for the TUI to run a script
def get_script_path(sub_path: str) -> str:
    """
    Combines the base scripts directory with a specific sub-path.
    Input: 'azuredevops/install-skill-from-azuredevops.py'
    Output: '/home/mpaik/.neuro/scripts/azuredevops/install-skill-from-azuredevops.py'
    """
    return os.path.join(SCRIPTS_DIR, sub_path)
