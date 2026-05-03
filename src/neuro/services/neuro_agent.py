"""
Multi-provider conversational Neuro subagent.

Provider resolution order:
  1. ~/.neuro/config.json  →  agent.provider  (written by install.sh)
  2. NEURO_AGENT_PROVIDER  env var            (manual override)
  3. Auto-detect from available API keys

Supported providers (names match install.sh):
  claude   — ANTHROPIC_API_KEY  → Claude (via anthropic SDK)
  ollama   — local Ollama daemon → any pulled model
  codex    — OPENAI_API_KEY     → GPT-4o (via openai SDK)
  github   — GITHUB_TOKEN       → GitHub Models (OpenAI-compatible)

All provider packages are optional; neuro works without them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from neuro.services import skill_manager as sm

NEURO_HOME = Path.home() / ".neuro"

# provider name → (pip package, default model, display name)
# Keys match what install.sh writes into config.json["agent"]["provider"]
_PROVIDER_META: dict[str, tuple[str, str, str]] = {
    "claude":    ("anthropic", "claude-opus-4-7",  "Claude (Anthropic)"),
    "anthropic": ("anthropic", "claude-opus-4-7",  "Claude (Anthropic)"),   # env-var alias
    "ollama":    ("ollama",    "",                  "Ollama (Local)"),       # model from config
    "codex":     ("openai",    "gpt-4o",            "Codex (OpenAI)"),
    "openai":    ("openai",    "gpt-4o",            "ChatGPT (OpenAI)"),     # env-var alias
    "github":    ("openai",    "gpt-4o",            "GitHub Copilot / Models"),
}

_GITHUB_BASE_URL = "https://models.inference.ai.azure.com"


# ── system prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    items = sm.list_items()
    skills = [i for i in items if i.category == "skill"]
    tools  = [i for i in items if i.category == "tool"]

    skill_lines = "\n".join(
        f"  - {s.name}" + (f" (source: {s.source})" if s.source else "")
        for s in skills
    ) or "  (none)"

    tool_lines = "\n".join(
        f"  - {t.name}" + (f" (source: {t.source})" if t.source else "")
        for t in tools
    ) or "  (none)"

    config: dict = {}
    config_path = NEURO_HOME / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    init_assets: dict = config.get("init_assets", {})
    agent_lines = "\n".join(
        f"  - {agent}: {len(data.get('installed', []))} item(s) installed"
        for agent, data in init_assets.items()
        if not agent.startswith("_")
    ) or "  (no init manifest — run `neuro init`)"

    return f"""\
You are the Neuro subagent — an embedded assistant inside the Neuro CLI.

Neuro is a skill-management system that installs behavioral instruction files \
(skills and tools) into AI agent configuration directories (Claude Code, Cursor, \
GitHub Copilot, Gemini, Windsurf, etc.).

## Current Neuro Installation State

**Neuro home (~/.neuro/ exists):** {"yes" if NEURO_HOME.exists() else "no"}

**Installed skills:**
{skill_lines}

**Installed tools:**
{tool_lines}

**Agents synced via `neuro init`:**
{agent_lines}

## Your Role

Answer questions about the user's neuro installation in natural language. \
Help the user understand what is installed, what each skill does, how neuro \
works, how to troubleshoot issues, and what commands to run.

If asked to take an action (install, remove, etc.) remind the user they can \
use the TUI commands: /skills add, /skills remove, /skills list, /skills update, /init.

Do not invent skills or agents that are not listed above."""


# ── config resolution ─────────────────────────────────────────────────────────

def _read_agent_config() -> tuple[str | None, str | None]:
    """
    Read (provider, model) from ~/.neuro/config.json.

    install.sh writes:
      { "agent": { "provider": "claude|ollama|codex", "model": "<model>" }, ... }
    """
    config_path = NEURO_HOME / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            agent_cfg = data.get("agent", {})
            if isinstance(agent_cfg, dict):
                provider = (agent_cfg.get("provider") or "").lower() or None
                model    = agent_cfg.get("model") or None
                if provider:
                    return provider, model
        except (json.JSONDecodeError, OSError):
            pass
    return None, None


def _resolve_provider_and_model() -> tuple[str | None, str | None]:
    """
    Return (provider, model).  Model may be None (caller falls back to default).
    """
    # 1. config.json written by install.sh
    provider, model = _read_agent_config()
    if provider:
        return provider, model

    # 2. explicit env override
    env_provider = os.environ.get("NEURO_AGENT_PROVIDER", "").lower() or None
    if env_provider:
        return env_provider, None

    # 3. auto-detect from available keys
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude", None
    if os.environ.get("OPENAI_API_KEY"):
        return "codex", None
    if os.environ.get("GITHUB_TOKEN"):
        return "github", None

    return None, None


# ── null agent ────────────────────────────────────────────────────────────────

class _NullAgent:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    @property
    def available(self) -> bool:
        return False

    @property
    def provider_name(self) -> str:
        return "unavailable"

    def chat(self, message: str, on_token: Callable[[str], None] | None = None) -> str:
        return f"[Neuro subagent unavailable: {self._reason}]"

    def clear_history(self) -> None:
        pass

    def refresh_context(self) -> None:
        pass


# ── Anthropic / Claude ────────────────────────────────────────────────────────

class _AnthropicAgent:
    def __init__(self, client, model: str) -> None:
        self._client = client
        self._model  = model
        self._system = _build_system_prompt()
        self._history: list[dict] = []

    @property
    def available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return f"Claude ({self._model})"

    def clear_history(self) -> None:
        self._history = []

    def refresh_context(self) -> None:
        self._system = _build_system_prompt()

    def chat(self, message: str, on_token: Callable[[str], None] | None = None) -> str:
        self._history.append({"role": "user", "content": message})
        collected: list[str] = []

        with self._client.messages.stream(
            model=self._model,
            max_tokens=2048,
            system=[{
                "type": "text",
                "text": self._system,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=self._history,
        ) as stream:
            for text in stream.text_stream:
                collected.append(text)
                if on_token:
                    on_token(text)

        reply = "".join(collected)
        self._history.append({"role": "assistant", "content": reply})
        return reply


# ── Ollama (local) ────────────────────────────────────────────────────────────

class _OllamaAgent:
    def __init__(self, client, model: str) -> None:
        self._client = client
        self._model  = model
        self._system = _build_system_prompt()
        self._history: list[dict] = []

    @property
    def available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return f"Ollama ({self._model})"

    def clear_history(self) -> None:
        self._history = []

    def refresh_context(self) -> None:
        self._system = _build_system_prompt()

    def chat(self, message: str, on_token: Callable[[str], None] | None = None) -> str:
        self._history.append({"role": "user", "content": message})
        messages = [
            {"role": "system", "content": self._system},
            *self._history,
        ]
        collected: list[str] = []

        stream = self._client.chat(
            model=self._model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            token = chunk["message"]["content"]
            if token:
                collected.append(token)
                if on_token:
                    on_token(token)

        reply = "".join(collected)
        self._history.append({"role": "assistant", "content": reply})
        return reply


# ── OpenAI / Codex / GitHub Models ───────────────────────────────────────────

class _OpenAIAgent:
    def __init__(self, client, model: str, display_name: str) -> None:
        self._client  = client
        self._model   = model
        self._display = display_name
        self._system  = _build_system_prompt()
        self._history: list[dict] = []

    @property
    def available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return self._display

    def clear_history(self) -> None:
        self._history = []

    def refresh_context(self) -> None:
        self._system = _build_system_prompt()

    def chat(self, message: str, on_token: Callable[[str], None] | None = None) -> str:
        self._history.append({"role": "user", "content": message})
        messages = [{"role": "system", "content": self._system}, *self._history]
        collected: list[str] = []

        stream = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=2048,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                collected.append(delta.content)
                if on_token:
                    on_token(delta.content)

        reply = "".join(collected)
        self._history.append({"role": "assistant", "content": reply})
        return reply


# ── factory ───────────────────────────────────────────────────────────────────

def create_agent() -> _AnthropicAgent | _OllamaAgent | _OpenAIAgent | _NullAgent:
    provider, config_model = _resolve_provider_and_model()

    if provider is None:
        return _NullAgent(
            "no provider configured — run install.sh or set "
            "ANTHROPIC_API_KEY / OPENAI_API_KEY / GITHUB_TOKEN"
        )

    if provider not in _PROVIDER_META:
        return _NullAgent(
            f"unknown provider '{provider}' — valid: claude, ollama, codex, openai, github"
        )

    package, default_model, display = _PROVIDER_META[provider]
    model = config_model or default_model

    try:
        # ── Claude / Anthropic ──────────────────────────────────────────────
        if provider in ("claude", "anthropic"):
            import anthropic  # type: ignore[import]
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                return _NullAgent("ANTHROPIC_API_KEY is not set")
            return _AnthropicAgent(anthropic.Anthropic(api_key=api_key), model)

        # ── Ollama (local) ──────────────────────────────────────────────────
        if provider == "ollama":
            import ollama as ollama_mod  # type: ignore[import]
            if not model:
                return _NullAgent(
                    "Ollama model not configured — set agent.model in config.json "
                    "or re-run install.sh"
                )
            # Quick connectivity check
            try:
                ollama_mod.list()
            except Exception as exc:
                return _NullAgent(f"Ollama daemon unreachable: {exc}")
            return _OllamaAgent(ollama_mod, model)

        # ── Codex / OpenAI / GitHub Models ─────────────────────────────────
        import openai as openai_mod  # type: ignore[import]

        if provider == "github":
            token = os.environ.get("GITHUB_TOKEN", "")
            if not token:
                return _NullAgent("GITHUB_TOKEN is not set")
            client = openai_mod.OpenAI(api_key=token, base_url=_GITHUB_BASE_URL)
        else:  # codex / openai
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                return _NullAgent("OPENAI_API_KEY is not set")
            client = openai_mod.OpenAI(api_key=api_key)

        return _OpenAIAgent(client, model, display)

    except ImportError:
        return _NullAgent(f"install the `{package}` package: pip install {package}")
    except Exception as exc:
        return _NullAgent(str(exc))
