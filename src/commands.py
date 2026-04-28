import importlib
import subprocess
import sys
import os
from neuro.config import get_slash_commands, get_script_path

def handle_slash_command(user_input):
    parts = user_input.split()
    if not parts:
        return ""
        
    primary_trigger = parts[0]
    sub_command_name = parts[1] if len(parts) > 1 else None
    args = parts[2:] if len(parts) > 1 else []

    commands = get_slash_commands()
    cmd_config = next((c for c in commands if c["trigger"] == primary_trigger), None)

    if not cmd_config:
        return f"Unknown command: {primary_trigger}"

    # Handle Group Commands (Nested)
    if cmd_config.get("type") == "group":
        if not sub_command_name:
            available = ", ".join([opt["name"] for opt in cmd_config["options"]])
            return f"Usage: {primary_trigger} [{available}]"
            
        # Find the specific sub-option
        option = next((opt for opt in cmd_config["options"] if opt["name"] == sub_command_name), None)
        
        if not option:
            return f"Unknown sub-command '{sub_command_name}' for {primary_trigger}"
            
        return execute_action(option["type"], option["action"], args)

    # Handle Direct Commands (Standard)
    return execute_action(cmd_config["type"], cmd_config["action"], parts[1:])

def execute_action(action_type, action, args):
    """Helper to execute the actual logic based on type."""
    try:
        if action_type == "module":
            module_name, func_name = action.rsplit(".", 1)
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            return func(*args)

        elif action_type == "script":
            script_path = get_script_path(action)
            subprocess.run([sys.executable, script_path] + args, check=True)
            return f"Executed {action} successfully."

        elif action_type == "builtin":
            if action == "clear_screen":
                os.system('clear' if os.name == 'posix' else 'cls')
                return ""
    except Exception as e:
        return f"Execution Error: {str(e)}"