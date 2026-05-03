"""
neuro agent update  /  TUI: /agent update

Interactive AI provider switcher.  Mirrors the provider-selection flow from
install.sh so all required prerequisites are installed consistently.

Flow:
  1. Show current agent configuration from ~/.neuro/config.json
  2. Present provider menu  (claude / ollama / codex / copilot)
  3. Provider-specific setup:
       claude  → check / install Claude Code CLI, select model
       ollama  → check daemon reachability, list + select model
       codex   → prompt for API key, fetch + select model
       copilot → prompt for GITHUB_TOKEN, select GitHub model
  4. pip install the provider SDK into the neuro venv
  5. Write updated  agent.provider / agent.model (/ agent.api_key) to config.json
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.rule import Rule
from rich.table import Table

NEURO_HOME = Path.home() / ".neuro"

# Mirrors install.sh option list
_PROVIDERS: list[tuple[str, str, str]] = [
    ("claude",  "Claude Pro CLI",   "Best for BAs  (requires Claude Code subscription)"),
    ("ollama",  "Ollama (Local)",   "Best for Devs  (runs offline, free)"),
    ("codex",   "Codex / OpenAI",   "Cloud GPT API  (requires OpenAI API key)"),
    ("copilot", "GitHub Copilot",   "GitHub Models API  (requires GITHUB_TOKEN)"),
]

_CLAUDE_MODELS = [
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-3-7-sonnet-latest",
    "claude-4-opus-latest",
]

_COPILOT_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "meta/llama-3.3-70b-instruct",
    "mistral-ai/mistral-large-2407",
]


# ── console helpers ───────────────────────────────────────────────────────────

def _make_console() -> Console:
    return Console()


def _ok(c: Console, msg: str)   -> None: c.print(f"  [green]✔[/]  {msg}")
def _warn(c: Console, msg: str) -> None: c.print(f"  [yellow]⚠[/]  [yellow]{msg}[/]")
def _err(c: Console, msg: str)  -> None: c.print(f"  [red]✘[/]  [red]{msg}[/]")
def _hint(c: Console, msg: str) -> None: c.print(f"  [dim]{msg}[/]")

def _section(c: Console, title: str) -> None:
    c.print(Rule(f"[dim] {title} [/]", style="cyan"))
    c.print()


# ── input helpers (CLI vs TUI) ────────────────────────────────────────────────

def _prompt(session, text: str, default: str = "", password: bool = False) -> str:
    """Unified prompt — uses session.prompt() in TUI, input() in CLI."""
    if session is not None:
        from prompt_toolkit.patch_stdout import patch_stdout
        from prompt_toolkit import prompt as pt_prompt
        with patch_stdout():
            raw = session.prompt(f"  {text}  ", is_password=password)
        return (raw or "").strip() or default
    else:
        import getpass
        fn = getpass.getpass if password else input
        try:
            return fn(f"  {text}  ").strip() or default
        except (EOFError, KeyboardInterrupt):
            return default


def _confirm(session, c: Console, question: str) -> bool:
    answer = _prompt(session, f"{question} [y/N]:", default="n")
    return answer.lower() in ("y", "yes")


def _select_index(
    session,
    c: Console,
    options: list[str],
    label: str = "Selection",
) -> int | None:
    """Show numbered list, return 0-based index or None if cancelled."""
    for i, opt in enumerate(options, 1):
        c.print(f"   [dim]{i})[/]  {opt}")
    c.print()
    while True:
        raw = _prompt(session, f"{label} (1–{len(options)}, blank to cancel):")
        if not raw:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        _err(c, f"Enter a number between 1 and {len(options)}.")


# ── config helpers ────────────────────────────────────────────────────────────

def _load_config() -> dict:
    p = NEURO_HOME / "config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_agent_config(provider: str, model: str, api_key: str | None = None) -> None:
    config = _load_config()
    agent_cfg: dict = config.setdefault("agent", {})
    agent_cfg["provider"] = provider
    agent_cfg["model"]    = model
    if api_key is not None:
        agent_cfg["api_key"] = api_key
    elif "api_key" in agent_cfg and provider != "codex":
        del agent_cfg["api_key"]   # remove stale key when switching away
    p = NEURO_HOME / "config.json"
    p.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


# ── pip / npm install helpers ─────────────────────────────────────────────────

def _venv_pip() -> str:
    """Return the pip from the neuro venv if it exists, else the current pip."""
    candidate = NEURO_HOME / ".venv" / "bin" / "pip"
    return str(candidate) if candidate.exists() else sys.executable.replace("python3", "pip3").replace("python", "pip")


def _pip_install(c: Console, package: str) -> bool:
    _hint(c, f"Installing Python package: [bold]{package}[/] …")
    result = subprocess.run(
        [_venv_pip(), "install", package, "--quiet"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        _ok(c, f"{package} installed.")
        return True
    _err(c, f"pip install {package} failed:\n{result.stderr.strip()}")
    return False


def _npm_install_claude(c: Console, session) -> bool:
    """Install @anthropic-ai/claude-code globally via npm (requires sudo)."""
    _warn(c, "Claude Code CLI not found in PATH.")
    if not _confirm(session, c, "Install via npm? (sudo npm install -g @anthropic-ai/claude-code)"):
        return False
    c.print()
    _hint(c, "Running npm install — you may be asked for your sudo password.")
    result = subprocess.run(
        ["sudo", "npm", "install", "-g", "@anthropic-ai/claude-code"],
        text=True,
    )
    if result.returncode == 0:
        _ok(c, "Claude Code CLI installed.")
        return True
    _err(c, "npm install failed.  Install manually: sudo npm install -g @anthropic-ai/claude-code")
    return False


# ── per-provider setup ────────────────────────────────────────────────────────

def _setup_claude(session, c: Console) -> tuple[str, str] | None:
    """Returns (provider, model) or None if cancelled/failed."""
    _section(c, "Claude Setup")

    # 1. Check / install CLI
    claude_bin = shutil.which("claude")
    if claude_bin:
        _ok(c, f"Claude Code CLI found at [dim]{claude_bin}[/]")
    else:
        if not _npm_install_claude(c, session):
            return None
        claude_bin = shutil.which("claude")
        if not claude_bin:
            _err(c, "Claude CLI still not found after install.  Add npm bin dir to PATH and retry.")
            return None

    # 2. Model selection
    c.print()
    c.print("  [bold]Select Claude model:[/]")
    c.print()
    idx = _select_index(session, c, _CLAUDE_MODELS, "Model")
    if idx is None:
        return None
    model = _CLAUDE_MODELS[idx]

    # 3. SDK
    _pip_install(c, "anthropic")

    return "claude", model


def _setup_ollama(session, c: Console) -> tuple[str, str] | None:
    """Returns (provider, model) or None if cancelled/failed."""
    _section(c, "Ollama Setup")

    # 1. Binary check
    if not shutil.which("ollama"):
        _err(c, "Ollama binary not found.  Install from [link]https://ollama.com[/link] first.")
        return None

    # 2. Daemon check + model list
    try:
        import subprocess as sp
        result = sp.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [l.split()[0] for l in result.stdout.splitlines() if l and not l.startswith("NAME")]
        models = [l for l in lines if l]
    except Exception as exc:
        _err(c, f"Could not reach Ollama daemon: {exc}")
        _hint(c, "Start Ollama with: ollama serve")
        return None

    if not models:
        _err(c, "No models found.  Pull one first:  ollama pull llama3")
        return None

    _ok(c, f"{len(models)} model(s) available locally.")
    c.print()
    c.print("  [bold]Select model:[/]")
    c.print()
    idx = _select_index(session, c, models, "Model")
    if idx is None:
        return None

    # 3. SDK
    _pip_install(c, "ollama")

    return "ollama", models[idx]


def _setup_codex(session, c: Console) -> tuple[str, str, str] | None:
    """Returns (provider, model, api_key) or None if cancelled/failed."""
    _section(c, "Codex / OpenAI Setup")

    # 1. API key
    existing_key = _load_config().get("agent", {}).get("api_key") or ""
    if existing_key:
        _hint(c, "Existing API key found in config.")
        keep = _confirm(session, c, "Keep existing key?")
        api_key = existing_key if keep else ""
    else:
        api_key = ""

    if not api_key:
        api_key = _prompt(session, "Enter OpenAI API key:", password=True)
        if not api_key:
            _warn(c, "API key required for Codex.")
            return None

    # 2. Fetch models
    c.print()
    _hint(c, "Fetching available GPT models …")
    models = _fetch_openai_models(api_key)
    if not models:
        _warn(c, "Could not fetch model list — using built-in defaults.")
        models = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]

    c.print()
    c.print("  [bold]Select model:[/]")
    c.print()
    idx = _select_index(session, c, models, "Model")
    if idx is None:
        return None

    # 3. SDK
    _pip_install(c, "openai")

    return "codex", models[idx], api_key


def _setup_copilot(session, c: Console) -> tuple[str, str, str] | None:
    """Returns (provider, model, github_token) or None if cancelled/failed."""
    _section(c, "GitHub Copilot Setup")

    existing_key = _load_config().get("agent", {}).get("api_key") or os.environ.get("GITHUB_TOKEN", "")
    if existing_key:
        _hint(c, "Existing GitHub token found in config.")
        keep = _confirm(session, c, "Keep existing token?")
        token = existing_key if keep else ""
    else:
        token = ""

    if not token:
        token = _prompt(session, "Enter GitHub Personal Access Token:", password=True)
        if not token:
            _warn(c, "GitHub Token is required for Copilot.")
            return None

    c.print()
    c.print("  [bold]Select GitHub model:[/]")
    c.print()
    idx = _select_index(session, c, _COPILOT_MODELS, "Model")
    if idx is None:
        return None

    _pip_install(c, "openai")

    return "copilot", _COPILOT_MODELS[idx], token


def _fetch_openai_models(api_key: str) -> list[str]:
    try:
        import urllib.request
        req = urllib.request.Request("https://api.openai.com/v1/models")
        req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            names = sorted(m["id"] for m in data["data"] if "gpt" in m["id"])
            return names[:12]
    except Exception:
        return []


# ── main entry point ──────────────────────────────────────────────────────────

def run(*, session=None, console: Console | None = None) -> bool:
    """
    Interactive agent switcher.

    session — prompt_toolkit PromptSession when called from TUI; None for CLI.
    console — rich Console; a new one is created if not provided.
    Returns True if the agent was updated, False if cancelled or failed.
    """
    c = console or _make_console()

    c.print()
    _section(c, "Agent Update")

    # ── show current config ───────────────────────────────────────────────────
    config    = _load_config()
    agent_cfg = config.get("agent", {})
    cur_provider = agent_cfg.get("provider", "—")
    cur_model    = agent_cfg.get("model",    "—")

    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="dim", min_width=14)
    grid.add_column(style="white")
    grid.add_row("Provider", f"[cyan]{cur_provider}[/]")
    grid.add_row("Model",    cur_model)
    c.print("  [bold]Current configuration:[/]")
    c.print()
    c.print(grid)
    c.print()

    # ── provider menu ─────────────────────────────────────────────────────────
    c.print("  [bold]Select new AI provider:[/]")
    c.print()
    option_labels = [f"[bold white]{p}[/]  [dim]— {desc}[/]" for p, _, desc in _PROVIDERS]
    idx = _select_index(session, c, option_labels, "Provider")
    if idx is None:
        _hint(c, "Cancelled.")
        c.print()
        return False

    chosen_key, chosen_name, _ = _PROVIDERS[idx]
    c.print()

    # ── provider-specific setup ───────────────────────────────────────────────
    result = None

    if chosen_key == "claude":
        setup = _setup_claude(session, c)
        if setup:
            provider, model = setup
            result = (provider, model, None)

    elif chosen_key == "ollama":
        setup = _setup_ollama(session, c)
        if setup:
            provider, model = setup
            result = (provider, model, None)

    elif chosen_key == "codex":
        setup = _setup_codex(session, c)
        if setup:
            provider, model, api_key = setup
            result = (provider, model, api_key)

    elif chosen_key == "copilot":
        setup = _setup_copilot(session, c)
        if setup:
            provider, model, api_key = setup
            result = (provider, model, api_key)

    if result is None:
        _warn(c, "Agent update cancelled or setup failed.")
        c.print()
        return False

    provider, model, api_key = result

    # ── persist to config.json ────────────────────────────────────────────────
    _save_agent_config(provider, model, api_key)

    c.print()
    c.print(Rule(style="cyan"))
    c.print()
    _ok(c, f"Agent updated  →  [cyan]{provider}[/]  [dim]({model})[/]")
    _hint(c, "Config saved to ~/.neuro/config.json")
    c.print()
    return True
