"""
Codex agent — OpenAI API (gpt-* models) via the `openai` Python package.
"""

from __future__ import annotations

from typing import Callable, Optional

from neuro.services.base_agent import NeuroAgent

try:
    from openai import OpenAI as _OpenAI
except ImportError:
    _OpenAI = None  # type: ignore[assignment]


class CodexAgent(NeuroAgent):
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._client = _OpenAI(api_key=api_key)
        self._model  = model

    @property
    def provider_name(self) -> str:
        return f"Codex ({self._model})"

    def chat(self, message: str, on_token: Optional[Callable[[str], None]] = None) -> str:
        messages: list[dict] = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.append({"role": "user", "content": message})
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
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
