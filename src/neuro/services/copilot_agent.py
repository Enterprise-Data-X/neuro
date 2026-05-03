"""
Copilot agent — GitHub Models API (OpenAI-compatible, GITHUB_TOKEN auth).
"""

from __future__ import annotations

from typing import Callable, Optional

from neuro.services.base_agent import NeuroAgent

try:
    from openai import OpenAI as _OpenAI
except ImportError:
    _OpenAI = None  # type: ignore[assignment]

_BASE_URL = "https://models.inference.ai.azure.com"


class CopilotAgent(NeuroAgent):
    def __init__(self, token: str, model: str = "openai/gpt-4o") -> None:
        self._client = _OpenAI(base_url=_BASE_URL, api_key=token)
        self._model  = model

    @property
    def provider_name(self) -> str:
        return f"GitHub Copilot ({self._model})"

    def chat(self, message: str, on_token: Optional[Callable[[str], None]] = None) -> str:
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": message}],
            stream=True,
        )
        parts: list[str] = []
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                parts.append(delta.content)
                if on_token:
                    on_token(delta.content)
        return "".join(parts)
