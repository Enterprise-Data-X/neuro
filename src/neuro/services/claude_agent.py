"""
Claude agent — wraps the `claude` CLI binary (Claude Code subscription).
"""

from __future__ import annotations

import subprocess
from typing import Callable, Optional

from neuro.services.base_agent import NeuroAgent

_LOGIN_KEYWORDS = ("not logged in", "log in", "login", "unauthorized", "authentication")


class ClaudeAgent(NeuroAgent):
    def __init__(self, bin_path: str, model: str = "") -> None:
        self._bin   = bin_path
        self._model = model

    @property
    def provider_name(self) -> str:
        return f"Claude ({self._model})" if self._model else "Claude (CLI)"

    def trigger_login(self) -> int:
        try:
            return subprocess.run([self._bin, "login"]).returncode
        except Exception:
            return 1

    def chat(self, message: str, on_token: Optional[Callable[[str], None]] = None) -> str:
        full_message = f"{self._system_prompt}\n\n---\n\n{message}" if self._system_prompt else message
        cmd = [self._bin, "--bare", "-p", full_message]
        if self._model:
            cmd += ["--model", self._model]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        parts: list[str] = []
        for line in iter(process.stdout.readline, ""):
            parts.append(line)
            if on_token:
                on_token(line)
        process.wait()
        if process.returncode != 0:
            stderr_out = process.stderr.read().strip()
            combined   = (stderr_out + " " + "".join(parts)).lower()
            if any(kw in combined for kw in _LOGIN_KEYWORDS):
                raise RuntimeError(
                    "Claude CLI is not logged in.\n"
                    "  Run [bold]claude login[/bold] in your terminal, then try again."
                )
            raise RuntimeError(stderr_out or f"claude exited with code {process.returncode}")
        return "".join(parts)
