import json
import os
from logger import get_logger

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
