from __future__ import annotations

from pathlib import Path
from typing import Callable

from . import config, init

BASE_DIR = Path.home() / ".neuro"
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "log" / "neuro.log"

COMMAND_HANDLERS: dict[str, Callable[..., str]] = {
    "/init": init.run,
    "/config": config.execute
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

    if cmd == "/init":
        return handler(args, CONFIG_PATH)
    if cmd == "/config":
        return handler(args, LOG_PATH)
    return handler(args)
