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


def _skill_description(path: Path) -> str:
    """Read the `description:` field from a skill file's YAML frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                for line in text[3:end].splitlines():
                    if line.startswith("description:"):
                        return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def build_system_prompt() -> str:
    """
    Build the Neuro-aware system prompt injected into every TUI chat call.
    Loads NEURO.md + installed skills/tools list + active role from config.
    """
    config   = _load_config()
    role     = config.get("role", "")
    provider = (config.get("agent") or {}).get("provider", "")

    skills_dir = NEURO_HOME / "skills"
    tools_dir  = NEURO_HOME / "tools"

    skill_lines: list[str] = []
    if skills_dir.exists():
        for f in sorted(skills_dir.glob("*.md")):
            desc = _skill_description(f)
            skill_lines.append(f"  • {f.stem}" + (f" — {desc}" if desc else ""))

    tool_lines: list[str] = []
    if tools_dir.exists():
        for f in sorted(tools_dir.iterdir()):
            tool_lines.append(f"  • {f.name}")

    neuro_md = ""
    neuro_md_path = skills_dir / "NEURO.md"
    if neuro_md_path.exists():
        try:
            neuro_md = neuro_md_path.read_text(encoding="utf-8")
        except OSError:
            pass

    parts: list[str] = [
        "You are the Neuro Agent — an AI assistant embedded in the Neuro CLI.",
        "Neuro is an organisational AI alignment framework that synchronises agent behaviour,",
        "persona, and tooling standards across development teams.",
        "",
        "Your purpose is to help users manage and understand their Neuro environment.",
        "This includes: installed skills and tools, AI provider configuration, persona alignment,",
        "the skill vault, and any question covered by NEURO.md.",
        "",
        "If a user's question falls outside the Neuro scope (general coding, unrelated topics),",
        "politely guide them back:",
        "  'I'm the Neuro Agent — I'm best placed to help with your Neuro environment.",
        "   For general questions, use your AI assistant outside of the Neuro TUI.'",
        "",
    ]

    if role:
        parts += [f"Active persona: {role}", ""]
    if provider:
        parts += [f"AI provider: {provider}", ""]

    if skill_lines:
        parts += ["Installed skills:"] + skill_lines + [""]
    else:
        parts += ["No skills installed yet — advise user to run `neuro init`.", ""]

    if tool_lines:
        parts += ["Installed tools:"] + tool_lines + [""]

    if neuro_md:
        parts += ["---", "", neuro_md]

    return "\n".join(parts)


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

    agent = _build_agent(provider, model, api_key)
    if agent.available:
        agent.set_context(build_system_prompt())
    return agent


def _build_agent(provider: str, model: str, api_key: str) -> NeuroAgent:
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
