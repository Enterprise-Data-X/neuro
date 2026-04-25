from pathlib import Path


def execute(_: list[str], log_path: Path) -> str:
    log_path.write_text("")
    return "🧹 Logs cleared."
