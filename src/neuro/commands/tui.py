"""
Interactive Neuro terminal.
"""

from __future__ import annotations

import logging
import os

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from neuro.commands import ensure_directories
from neuro.commands import init as init_mod
from neuro.commands import skills as skills_cmd
from neuro.commands import status as status_mod
from neuro.commands import update as update_mod
from neuro.services import neuro_chat_agent as agent_svc
from neuro.services import skill_manager as sm

console = Console()
logger = logging.getLogger("neuro.tui")

# Updated command structure
COMMANDS = [
    "/skills", "/skills list", "/skills add", "/skills remove", "/skills check",
    "/skills create", "/skills update",
    "/init", "/status", "/config",
    "/agent", "/agent update", "/agent refresh", "/agent clear", "/agent config",
    "/clear", "/help", "/exit",
]

# Map old logic to new subcommand structure
_SKILLS_SUB = {"list", "add", "remove", "check", "create"}

_completer = WordCompleter(COMMANDS, ignore_case=True)

_PT_STYLE = Style.from_dict({
    "prompt.name":  "#666666",
    "prompt.arrow": "#5fd7ff bold",
})

def _prompt_tokens() -> FormattedText:
    return FormattedText([
        ("class:prompt.name",  "neuro"),
        ("class:prompt.arrow", "  ❯  "),
    ])

def _ok(msg: str)   -> None: console.print(f"  [green]✔[/]  {msg}")
def _warn(msg: str) -> None: console.print(f"  [yellow]⚠[/]  [yellow]{msg}[/]")
def _err(msg: str)  -> None: console.print(f"  [red]✘[/]  [red]{msg}[/]")
def _hint(msg: str) -> None: console.print(f"  [dim]{msg}[/]")

def _welcome(agent) -> None:
    items = sm.list_items()
    skill_count = sum(1 for i in items if i.category == "skill")
    tool_count  = sum(1 for i in items if i.category == "tool")

    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="dim", min_width=14)
    grid.add_column(style="white")

    if agent.available:
        grid.add_row("AI Provider", f"[cyan]{agent.provider_name}[/]")
    else:
        grid.add_row("AI Provider", "[dim]unavailable[/]")
    grid.add_row("Skills", f"{skill_count} installed")
    grid.add_row("Tools",  f"{tool_count} installed")

    hint = "type naturally to chat  ·  [bold]/help[/] for commands"
    content = Group(
        Text.from_markup("[bold cyan]NEURO[/bold cyan]  [dim]·[/dim]  [white]AI Skill Manager[/white]"),
        Text(""),
        grid,
        Text(""),
        Text.from_markup(f"[dim]{hint}[/dim]"),
    )
    console.print()
    console.print(Panel(content, border_style="cyan", padding=(1, 3), expand=False))
    console.print()

def _help() -> None:
    def _section(title: str, rows: list[tuple[str, str]]) -> None:
        console.print(Rule(f"[dim] {title} [/]", style="cyan"))
        t = Table.grid(padding=(0, 3))
        t.add_column(style="bold cyan", min_width=30)
        t.add_column(style="white")
        for cmd, desc in rows:
            t.add_row(cmd, desc)
        console.print(t)
        console.print()

    console.print()
    _section("Skill Management", [
        ("/skills list",           "View installed skills and tools"),
        ("/skills add <path|url>", "Add a skill or tool"),
        ("/skills remove [name]",  "Remove a skill or tool"),
        ("/skills check [name]",   "Check for updates and view diff"),
        ("/skills create",         "Create a new skill with policy check"),
        ("/skills update",         "Re-install all skills from repository"),
    ])
    _section("Agent & AI", [
        ("/agent",                 "Show current selected agent/provider"),
        ("/agent update",          "Switch provider / model  (claude · ollama · codex)"),
        ("/agent refresh",         "Rebuild subagent context"),
        ("/agent clear",           "Clear conversation history"),
        ("/status",                "Show agent detection status"),
    ])
    _section("System", [
        ("/init",                  "Sync skills to installed agents"),
        ("/config [k v]",          "View or set global config values"),
        ("/clear",                 "Clear screen"),
        ("/help",                  "Show this help"),
        ("/exit",                  "Exit Neuro"),
    ])

def _show_config(args: list[str]) -> None:
    import json
    from pathlib import Path
    config_path = Path.home() / ".neuro" / "config.json"
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    except (json.JSONDecodeError, OSError) as exc:
        _err(f"Could not read config: {exc}")
        return

    if len(args) == 2:
        # /config key value  — simple top-level key set
        key, val = args
        cfg[key] = val
        config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        _ok(f"[cyan]{key}[/] = {val}")
        return

    if len(args) == 3 and args[0] == "agent":
        # /config agent key value
        _, key, val = args
        cfg.setdefault("agent", {})[key] = val
        config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        _ok(f"[cyan]agent.{key}[/] = {val}")
        return

    # Display mode
    agent_cfg = cfg.get("agent", {})
    repos     = cfg.get("templateRepository", [])

    console.print()
    console.print(Rule("[dim] ~/.neuro/config.json [/]", style="cyan"))
    console.print()

    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="dim", min_width=22)
    grid.add_column(style="white")
    grid.add_row("Provider", f"[cyan]{agent_cfg.get('provider', '—')}[/]")
    grid.add_row("Model",    agent_cfg.get("model", "—"))
    if agent_cfg.get("api_key"):
        grid.add_row("API Key", "[dim](set)[/]")
    grid.add_row("Role",     cfg.get("role", "—"))
    grid.add_row("Version",  cfg.get("version", "—"))
    for repo in repos:
        grid.add_row("Template Repo", f"[white]{repo.get('name', '—')}[/]")
        grid.add_row("  URL",         f"[dim]{repo.get('url', '—')}[/]")
        grid.add_row("  Path",        f"[dim]{repo.get('path', '—')}[/]")
    console.print(grid)
    console.print()
    _hint("/config agent model <value>   or   /config <key> <value>  to update")
    console.print()


_LOGIN_KEYWORDS = ("not logged in", "claude login", "login", "unauthorized")


def _run_claude_login(agent) -> bool:
    """Launch `claude login` interactively. Returns True if it exits 0."""
    console.print()
    _hint("Launching [bold]claude login[/bold] — follow the prompts in your browser…")
    console.print()
    rc = agent.trigger_login()
    console.print()
    if rc == 0:
        _ok("Logged in successfully.")
        return True
    _err("Login failed or was cancelled. Try running [bold]claude login[/bold] manually.")
    return False


def _stream_agent_reply(agent, message: str) -> None:
    console.print()
    console.print(Rule("[dim] neuro [/]", style="cyan"))
    console.print()

    def _do_stream() -> None:
        agent.chat(message, on_token=lambda t: console.print(t, end="", highlight=False))

    # try:
    #     _do_stream()
    # except RuntimeError as exc:
    #     if any(kw in str(exc).lower() for kw in _LOGIN_KEYWORDS):
    #         _warn("Claude CLI is not logged in.")
    try:
        _do_stream()
    except RuntimeError as exc:
        if any(kw in str(exc).lower() for kw in _LOGIN_KEYWORDS):
            # Check if they have an API key they could use
            if not os.environ.get("ANTHROPIC_API_KEY"):
                _warn("Claude is not logged in. TIP: Set ANTHROPIC_API_KEY to skip this.")
            if _run_claude_login(agent):
                _hint("Retrying your message…")
                console.print()
                try:
                    _do_stream()
                except Exception as retry_exc:
                    _err(f"Agent error: {retry_exc}")
        else:
            _err(f"Agent error: {exc}")
    except Exception as exc:
        _err(f"Agent error: {exc}")

    console.print("\n")
    console.print(Rule(style="cyan"))
    console.print()

def _get_configured_provider() -> str:
    import json
    from pathlib import Path
    try:
        cfg = json.loads((Path.home() / ".neuro" / "config.json").read_text(encoding="utf-8"))
        return (cfg.get("agent") or {}).get("provider", "").lower()
    except Exception:
        return ""


def run() -> None:
    ensure_directories()
    session = PromptSession(completer=_completer, style=_PT_STYLE)

    # Ollama may need a moment to start — show feedback before the 5-s wait
    if _get_configured_provider() == "ollama":
        console.print()
        console.print("  [cyan]⟳[/]  Checking Ollama daemon…")

    agent = agent_svc.create_agent()

    os.system("clear" if os.name == "posix" else "cls")
    _welcome(agent)

    try:
        while True:
            with patch_stdout():
                raw = session.prompt(_prompt_tokens)
            user_input = raw.strip() if raw else ""

            if not user_input: continue
            if user_input.lower() in ("exit", "quit", "/exit"): break

            if user_input == "/clear":
                os.system("clear" if os.name == "posix" else "cls")
                continue

            if user_input == "/help":
                _help()
                continue

            if user_input.startswith("/"):
                parts = user_input.split()
                cmd = parts[0].lower()
                args = parts[1:]

                # --- NEW /skills SUB-MENU LOGIC ---
                if cmd == "/skills":
                    sub = args[0].lower() if args else "list"
                    sub_args = args[1:]
                    
                    if sub == "update":
                        def _confirm(q): return session.prompt(f"{q} [y/N]: ").lower() == "y"
                        update_mod.run(confirm_fn=_confirm)
                    elif sub in _SKILLS_SUB:
                        skills_cmd.handle(f"/{sub}", sub_args, session, console, agent=agent)
                    else:
                        _hint("Usage: /skills [list|add|remove|check|create|update]")
                    continue

                # --- /agent SUB-MENU ---
                if cmd == "/agent":
                    sub = args[0].lower() if args else "status"

                    if sub == "update":
                        from neuro.commands import agent_update as au
                        updated = au.run(session=session, console=console)
                        if updated:
                            agent = agent_svc.create_agent()
                            _ok(f"Now using: [cyan]{agent.provider_name}[/]")

                    elif sub == "refresh":
                        agent.refresh_context()
                        _ok("Context refreshed.")

                    elif sub == "clear":
                        agent.clear_history()
                        _ok("History cleared.")

                    elif sub in ("status", "info", ""):
                        if agent.available:
                            _ok(f"Active Provider: [cyan]{agent.provider_name}[/]")
                        else:
                            _warn("No active AI provider.  Run [bold]/agent update[/] to configure one.")

                    else:
                        _hint("Usage:  /agent [update|refresh|clear]")

                    continue

                if cmd == "/init":
                    init_mod.run()
                    continue

                if cmd == "/status":
                    status_mod.run()
                    continue

                if cmd == "/config":
                    _show_config(args)
                    continue

                # Fallback for unrecognised slash commands
                _warn(f"Unknown command: {cmd}  — type [bold]/help[/] for available commands")
            
            else:
                if agent.available:
                    _stream_agent_reply(agent, user_input)
                else:
                    _err("Agent unavailable. Configure your API key using [bold]/agent config[/]")

    except KeyboardInterrupt:
        pass
    finally:
        console.print("\n[dim]Neuro session ended.[/]\n")

if __name__ == "__main__":
    run()