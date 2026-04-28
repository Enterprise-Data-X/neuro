import logging
import json
import os

def get_logger(name):
    base_dir = os.path.expanduser("~/.neuro")
    log_dir = os.path.join(base_dir, "log")
    config_path = os.path.join(base_dir, "config.json")
    
    # Ensure directories exist (Senior dev safety)
    os.makedirs(log_dir, exist_ok=True)

    # Load config with fallback defaults
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {"severity": "INFO"}

    level_name = config.get("severity", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    
    log_file = os.path.join(log_dir, "neuro.log")
    
    # Use log handlers to avoid duplicate logs in long-running processes
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
