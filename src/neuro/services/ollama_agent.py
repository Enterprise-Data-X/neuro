"""
Ollama agent — local LLM daemon via the `ollama` Python package.
Also provides start_daemon() to auto-start `ollama serve` if not running.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Callable, Optional

from neuro.services.base_agent import NeuroAgent

try:
    import ollama as _ollama_mod
except ImportError:
    _ollama_mod = None  # type: ignore[assignment]


def start_daemon() -> bool:
    """
    Start `ollama serve` in the background and wait up to 5 s for the
    daemon to become reachable.  Returns True if it comes up.
    """
    if _ollama_mod is None or not shutil.which("ollama"):
        return False
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    for _ in range(5):
        time.sleep(1)
        try:
            _ollama_mod.list()
            return True
        except Exception:
            pass
    return False


class OllamaAgent(NeuroAgent):
    def __init__(self, model: str) -> None:
        self._model = model

    @property
    def provider_name(self) -> str:
        return f"Ollama ({self._model})"

    def chat(self, message: str, on_token: Optional[Callable[[str], None]] = None) -> str:
        messages: list[dict] = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.append({"role": "user", "content": message})
        stream = _ollama_mod.chat(
            model=self._model,
            messages=messages,
            stream=True,
        )
        parts: list[str] = []
        for chunk in stream:
            token = chunk["message"]["content"]
            if token:
                parts.append(token)
                if on_token:
                    on_token(token)
        return "".join(parts)
