import json
from pathlib import Path
from typing import Any, Dict


def _load_config(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except Exception:
            return {}
    return {}


def _handle_agent_subcommands(args: list[str], config_path: Path) -> str:
    """Handle subcommands for /agent."""
    if not args:
        return "🧠 Agent Options: /agent list (show AI configs), /agent add api-key <key> (add API key)"

    if args[0].lower() == "list":
        config = _load_config(config_path)
        ai_configs = {k: v for k, v in config.items() if "api" in k.lower() or "key" in k.lower()}
        if ai_configs:
            return f"🧠 Available AI Configurations: {json.dumps(ai_configs, indent=2)}"
        return "🧠 No AI configurations found in local environment."

    return None  # Not handled by subcommands


def execute(args: list[str], config_path: Path) -> str:
    # Try subcommand handling first
    subcommand_result = _handle_agent_subcommands(args, config_path)
    if subcommand_result is not None:
        return subcommand_result

    # Fallback to original logic
    if len(args) >= 2 and args[0].lower() == "add" and args[1].lower() == "api-key":
        return "✅ API key command received. Add storage logic here."

    return "🧠 Agent Status: Idle. (Waiting for LLM API connection...)"
