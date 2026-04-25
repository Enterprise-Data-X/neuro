from __future__ import annotations

from pathlib import Path
from typing import Callable

from . import agent, bash, clear, config, skill, status

BASE_DIR = Path.home() / ".neuro"
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "log" / "neuro.log"

COMMAND_HANDLERS: dict[str, Callable[..., str]] = {
    "/config": config.execute,
    "/skill": skill.execute,
    "/agent": agent.execute,
    "/status": status.execute,
    "/clear": clear.execute,
    "/bash": bash.execute,
}


def ensure_directories() -> None:
    BASE_DIR.joinpath("log").mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text("{}")


def handle_slash_command(user_input: str) -> str:
    parts = user_input.split()
    if not parts:
        return "⚠️ Empty command."

    cmd = parts[0].lower()
    args = parts[1:]
    handler = COMMAND_HANDLERS.get(cmd)
    if handler is None:
        return f"❓ Unknown command: {cmd}"

    if cmd == "/config":
        return handler(args, CONFIG_PATH)
    if cmd == "/agent":
        return handler(args, CONFIG_PATH)
    if cmd == "/clear":
        return handler(args, LOG_PATH)
    return handler(args)
