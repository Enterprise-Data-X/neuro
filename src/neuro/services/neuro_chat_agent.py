"""
Neuro chat agent factory.

Resolution order:
  1. ~/.neuro/config.json  →  agent.provider + agent.model
  2. Auto-discovery fallback: claude binary → ollama daemon → OPENAI_API_KEY → GITHUB_TOKEN

Supported providers:  claude · ollama · codex · copilot
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from neuro.services.base_agent import NeuroAgent, UnavailableAgent
from neuro.services.claude_agent import ClaudeAgent
from neuro.services.codex_agent import CodexAgent
from neuro.services.copilot_agent import CopilotAgent
from neuro.services.ollama_agent import OllamaAgent, start_daemon

try:
    import ollama as _ollama_mod
except ImportError:
    _ollama_mod = None  # type: ignore[assignment]

try:
    from openai import OpenAI as _OpenAI
except ImportError:
    _OpenAI = None  # type: ignore[assignment]

NEURO_HOME = Path.home() / ".neuro"


def _load_config() -> dict:
    p = NEURO_HOME / "config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def create_agent() -> NeuroAgent:
    """
    Build a NeuroAgent from config.json, falling back to auto-discovery.
    Re-call after `neuro agent update` to pick up a new provider.
    """
    config    = _load_config()
    agent_cfg = config.get("agent", {}) if isinstance(config.get("agent"), dict) else {}
    provider  = (agent_cfg.get("provider") or "").lower()
    model     = agent_cfg.get("model") or ""
    api_key   = agent_cfg.get("api_key") or ""

    # ── config-driven ─────────────────────────────────────────────────────────

    if provider == "claude":
        bin_path = shutil.which("claude")
        if bin_path:
            return ClaudeAgent(bin_path, model)
        return UnavailableAgent(
            "Claude CLI not found — run `neuro agent update` to (re)install"
        )

    if provider == "ollama":
        if _ollama_mod is None:
            return UnavailableAgent("ollama package not installed — run: pip install ollama")
        try:
            _ollama_mod.list()
        except Exception:
            if not start_daemon():
                return UnavailableAgent(
                    "Ollama daemon is not running and could not be started automatically.  "
                    "Run [bold]ollama serve[/bold] in a separate terminal, then restart Neuro."
                )
        return OllamaAgent(model or "llama3")

    if provider == "codex":
        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return UnavailableAgent("OpenAI API key not set — run `neuro agent update`")
        if _OpenAI is None:
            return UnavailableAgent("openai package not installed — run: pip install openai")
        return CodexAgent(key, model or "gpt-4o")

    if provider == "copilot":
        token = api_key or os.environ.get("GITHUB_TOKEN", "")
        if not token:
            return UnavailableAgent("GITHUB_TOKEN not set — run `neuro agent update`")
        if _OpenAI is None:
            return UnavailableAgent("openai package not installed — run: pip install openai")
        return CopilotAgent(token, model or "openai/gpt-4o")

    # ── auto-discovery fallback (no config / unknown provider) ───────────────

    claude_bin = shutil.which("claude")
    if claude_bin:
        return ClaudeAgent(claude_bin, model)

    if _ollama_mod is not None:
        try:
            _ollama_mod.list()
            return OllamaAgent(model or "llama3")
        except Exception:
            pass

    openai_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if _OpenAI is not None and openai_key:
        return CodexAgent(openai_key, model or "gpt-4o")

    github_token = os.environ.get("GITHUB_TOKEN", "")
    if _OpenAI is not None and github_token:
        return CopilotAgent(github_token, "openai/gpt-4o")

    return UnavailableAgent(
        "No AI provider configured — run `neuro agent update` to set one up"
    )
