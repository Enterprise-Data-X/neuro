import json
from pathlib import Path

import click
from neuro.commands import init, status, tui, uninstall, update


@click.group()
def main():
    """Neuro CLI: Manage AI Agent skills and tools."""
    pass


@main.command()
@click.option('--force', is_flag=True, help='Force create directories')
def init_cmd(force):
    """Initialise Neuro skills for agents."""
    init.run(force=force)


@main.command()
def status_cmd():
    """Check active agent links."""
    status.run()


@main.command()
def update_cmd():
    """Pull latest templateRepository and re-install all skills."""
    update.run()


@main.command("config")
@click.argument("args", nargs=-1)
def config_cmd(args):
    """View or update ~/.neuro/config.json.  Usage: neuro config [agent model <val>]"""
    from rich.console import Console
    from rich.rule import Rule
    from rich.table import Table
    c = Console()
    config_path = Path.home() / ".neuro" / "config.json"

    def _load():
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(cfg):
        config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    if len(args) == 2:
        key, val = args
        cfg = _load(); cfg[key] = val; _save(cfg)
        c.print(f"  [green]✔[/]  [cyan]{key}[/] = {val}")
        return
    if len(args) == 3 and args[0] == "agent":
        _, key, val = args
        cfg = _load(); cfg.setdefault("agent", {})[key] = val; _save(cfg)
        c.print(f"  [green]✔[/]  [cyan]agent.{key}[/] = {val}")
        return

    cfg = _load()
    agent_cfg = cfg.get("agent", {})
    repos     = cfg.get("templateRepository", [])
    c.print()
    c.print(Rule("[dim] ~/.neuro/config.json [/]", style="cyan"))
    c.print()
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
    c.print(grid)
    c.print()


@main.command()
def tui_cmd():
    """Launch the interactive Neuro terminal."""
    tui.run()


@main.command()
def uninstall_cmd():
    """Remove all neuro assets and uninstall neuro from this machine."""
    uninstall.run()


# ── agent subcommand group ────────────────────────────────────────────────────

@main.group()
def agent():
    """Manage the active AI agent provider."""
    pass


@agent.command("update")
def agent_update_cmd():
    """Switch AI provider and model (claude / ollama / codex)."""
    from neuro.commands import agent_update as au
    au.run()


@agent.command("status")
def agent_status_cmd():
    """Show the currently configured AI provider."""
    from neuro.services.neuro_chat_agent import create_agent
    a = create_agent()
    from rich.console import Console
    c = Console()
    c.print()
    if a.available:
        c.print(f"  [green]✔[/]  [cyan]{a.provider_name}[/]  [dim](active)[/]")
    else:
        c.print(f"  [yellow]⚠[/]  [yellow]{a.chat('')}[/]")
    c.print()


if __name__ == "__main__":
    main()
