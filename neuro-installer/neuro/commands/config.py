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


def _save_config(config_path: Path, config: Dict[str, Any]) -> None:
    config_path.write_text(json.dumps(config, indent=4))


def init_config(config_path: Path) -> Dict[str, Any]:
    """Initialize an existing config file with a logging setting."""
    config = _load_config(config_path)
    if "logging" not in config or not isinstance(config["logging"], bool):
        config["logging"] = False
        _save_config(config_path, config)
    return config


def add_parameter(config_path: Path, key: str, value: Any) -> Dict[str, Any]:
    """Load the JSON config file and update a key with the given value.
    Returns a JSON-like dictionary indicating whether the key was updated or created.
    """
    config = _load_config(config_path)
    existed = key in config
    config[key] = value
    _save_config(config_path, config)

    return {
        "flag": "updated" if existed else "new",
        "key": key,
        "value": value
    }


def execute(args: list[str], config_path: Path) -> str:
    if config_path.exists():
        init_config(config_path)

    if not args:
        config = _load_config(config_path)
        return f"⚙️ Current Config: {json.dumps(config, indent=2)}"

    if len(args) == 2:
        key, val = args
        result = add_parameter(config_path, key, val)
        return f"{result['flag'].upper()}: {result['key']} -> {result['value']}"

    return "⚠️ Usage: /config [key value]"
