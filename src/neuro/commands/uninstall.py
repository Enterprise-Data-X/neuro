"""
neuro uninstall

Three-step destructive cleanup:
  1. Remove every skill and tool that neuro init placed in agent config dirs
  2. Remove ~/.neuro/ entirely
  3. Remove /usr/local/bin/neuro (the CLI symlink, requires sudo)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from neuro.commands.init import AGENT_MAP, NEURO_HOME

console = Console()

_NEURO_BINARY = Path("/usr/local/bin/neuro")
_SECTION_MARKER = "\n\n## Neuro Skills & Tools"


# ── per-agent cleanup ─────────────────────────────────────────────────────────

def _is_file_based(agent_config: dict) -> bool:
    """File-based agents (Copilot, Gemini, Windsurf) have no skills_dir."""
    return agent_config["skills_dir"] is None and agent_config.get("commands_dir") is None


def _strip_neuro_section(path: Path) -> tuple[str, str]:
    """
    Remove '## Neuro Skills & Tools' and everything after it from a file.
    Returns (status, description).
    """
    if not path.exists():
        return "skip", f"{path} not found"
    try:
        content = path.read_text(encoding="utf-8")
        idx = content.find(_SECTION_MARKER)
        if idx == -1:
            return "skip", f"no Neuro section in {path}"
        path.write_text(content[:idx], encoding="utf-8")
        return "stripped", str(path)
    except OSError as e:
        return "error", str(e)


def _remove_path(p: Path) -> tuple[str, str]:
    if not p.exists() and not p.is_symlink():
        return "skip", f"{p} not found"
    try:
        if p.is_symlink() or p.is_file():
            p.unlink()
        else:
            shutil.rmtree(p)
        return "removed", str(p)
    except OSError as e:
        return "error", str(e)


def _cleanup_directory_agent(
    agent_config: dict,
    installed: list[str],
) -> list[tuple[str, str]]:
    """
    Remove every item that neuro init placed in this agent's directories.
    Also removes the instruction file if it's a symlink into ~/.neuro/.
    """
    results: list[tuple[str, str]] = []
    instr_path = Path(agent_config["instruction_file"])

    for label in installed:
        # The instruction file is stored by its basename (e.g. "CLAUDE.md")
        if label == instr_path.name:
            if instr_path.is_symlink():
                # Only unlink if it points into the neuro home; leave user files alone
                try:
                    target = instr_path.resolve(strict=False)
                    if str(NEURO_HOME) in str(target):
                        results.append(_remove_path(instr_path))
                    else:
                        results.append(("skip", f"{instr_path} (not a neuro symlink, leaving intact)"))
                except OSError:
                    results.append(_remove_path(instr_path))
            else:
                results.append(("skip", f"{instr_path} (not a symlink, leaving intact)"))
            continue

        # Map "category/name" → agent directory path
        parts = label.split("/", 1)
        if len(parts) != 2:
            continue
        category, name = parts

        dir_map = {
            "skills":   agent_config.get("skills_dir"),
            "commands": agent_config.get("commands_dir"),
            "tools":    agent_config.get("agents_dir"),
            "agents":   agent_config.get("agents_dir"),
        }
        base = dir_map.get(category)
        if base is None:
            results.append(("skip", f"{label} (agent has no {category} dir)"))
            continue

        results.append(_remove_path(Path(base) / name))

    return results


def _cleanup_file_agent(agent_config: dict) -> list[tuple[str, str]]:
    """Strip the Neuro section from a file-based agent's instruction file."""
    instr_path = Path(agent_config["instruction_file"])
    status, desc = _strip_neuro_section(instr_path)
    return [(status, desc)]


# ── display helpers ───────────────────────────────────────────────────────────

def _print_results(results: list[tuple[str, str]]) -> None:
    for status, desc in results:
        if status == "removed":
            console.print(f"    [bold green]✔ removed[/]  [dim]{desc}[/]")
        elif status == "stripped":
            console.print(f"    [bold cyan]✔ stripped[/] [dim]{desc}[/]")
        elif status == "skip":
            console.print(f"    [dim]⏭  skip    {desc}[/]")
        else:
            console.print(f"    [bold red]✘ error   {desc}[/]")


def _preview_table(init_assets: dict) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Agent", style="bold white", min_width=30)
    table.add_column("Items", style="dim")

    for agent, data in init_assets.items():
        if agent.startswith("_"):
            continue
        count = len(data.get("installed", []))
        table.add_row(agent, f"{count} installed item(s)")

    console.print(table)
    console.print()

    extras = [
        ("neuro  (pip package)",  "Python package removal"),
        (str(NEURO_HOME),         "entire directory"),
    ]
    if _NEURO_BINARY.exists() or _NEURO_BINARY.is_symlink():
        extras.append((str(_NEURO_BINARY), "CLI symlink — requires sudo"))

    for path, note in extras:
        console.print(f"  [white]{path}[/]  [dim]({note})[/]")


# ── entry point ───────────────────────────────────────────────────────────────

def run() -> None:
    console.print()
    console.print(Panel(
        "[bold red]neuro uninstall[/bold red]\n\n"
        "[dim]Step 1[/dim]  Remove all neuro-managed skills and tools from AI agent configs\n"
        "[dim]Step 2[/dim]  Run [bold]pip uninstall neuro[/bold] (removes the Python package)\n"
        "[dim]Step 3[/dim]  Delete [bold]~/.neuro/[/bold] (your neuro home)\n"
        "[dim]Step 4[/dim]  Remove [bold]/usr/local/bin/neuro[/bold] (CLI binary)",
        border_style="red",
        padding=(1, 2),
    ))
    console.print()

    # Load install manifest from config
    config: dict = {}
    config_path = NEURO_HOME / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    init_assets: dict = config.get("init_assets", {})

    # Preview
    console.print("[bold]What will be removed:[/]")
    console.print()
    if init_assets:
        _preview_table(init_assets)
    else:
        console.print("  [dim]No install manifest found — agent cleanup will be skipped.[/]")
        console.print(f"  [white]{NEURO_HOME}[/]  [dim](entire directory)[/]")
        if _NEURO_BINARY.exists() or _NEURO_BINARY.is_symlink():
            console.print(f"  [white]{_NEURO_BINARY}[/]  [dim](CLI symlink — requires sudo)[/]")
    console.print()

    # Explicit confirmation — must type "yes"
    console.print("[bold red]⚠  This is irreversible.[/]  Type [bold]yes[/] to confirm, or anything else to cancel:")
    console.print()
    try:
        answer = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[dim]Cancelled.[/]")
        return

    if answer.lower() != "yes":
        console.print("\n[dim]Uninstall cancelled.[/]")
        return

    console.print()

    # ── Step 1: agent cleanup ────────────────────────────────────────────────
    console.print(Rule("[bold white] Step 1/3 — Agent directories [/]", style="red"))
    console.print()

    if not init_assets:
        console.print("  [dim]No install manifest — skipping agent cleanup.[/]")
    else:
        for agent_name, data in init_assets.items():
            if agent_name.startswith("_"):
                continue

            agent_config = AGENT_MAP.get(agent_name)
            if agent_config is None:
                console.print(f"  [yellow]⚠ Unknown agent '{agent_name}' — skipping[/]")
                continue

            installed: list[str] = data.get("installed", [])
            console.print(f"  [bold]{agent_name}[/]")

            if not installed:
                console.print("    [dim]Nothing recorded — skipping[/]")
            elif _is_file_based(agent_config):
                results = _cleanup_file_agent(agent_config)
                _print_results(results)
            else:
                results = _cleanup_directory_agent(agent_config, installed)
                _print_results(results)

            console.print()

    # ── Step 2: pip uninstall ────────────────────────────────────────────────
    console.print(Rule("[bold white] Step 2/4 — pip uninstall neuro [/]", style="red"))
    console.print()

    pip_cmd = [sys.executable, "-m", "pip", "uninstall", "neuro", "-y"]
    try:
        result = subprocess.run(pip_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            console.print("  [bold green]✔ uninstalled[/]  neuro Python package")
        else:
            err = (result.stderr or result.stdout).strip()
            if "not installed" in err.lower():
                console.print("  [dim]neuro package not found in current environment — skipping.[/]")
            else:
                console.print(f"  [bold red]✘ pip uninstall failed:[/] {err}")
                console.print(f"  [dim]Remove manually:[/]  pip uninstall neuro")
    except Exception as e:
        console.print(f"  [bold red]✘ Could not run pip:[/] {e}")

    console.print()

    # ── Step 3: remove ~/.neuro/ ─────────────────────────────────────────────
    console.print(Rule("[bold white] Step 3/4 — Remove ~/.neuro/ [/]", style="red"))
    console.print()

    if NEURO_HOME.exists():
        try:
            shutil.rmtree(NEURO_HOME)
            console.print(f"  [bold green]✔ removed[/]  {NEURO_HOME}")
        except OSError as e:
            console.print(f"  [bold red]✘ Could not remove {NEURO_HOME}:[/] {e}")
    else:
        console.print(f"  [dim]{NEURO_HOME} does not exist — skipping.[/]")

    console.print()

    # ── Step 4: remove CLI binary ─────────────────────────────────────────────
    console.print(Rule("[bold white] Step 4/4 — Remove CLI binary [/]", style="red"))
    console.print()

    if _NEURO_BINARY.exists() or _NEURO_BINARY.is_symlink():
        try:
            result = subprocess.run(
                ["sudo", "rm", "-f", str(_NEURO_BINARY)],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                console.print(f"  [bold green]✔ removed[/]  {_NEURO_BINARY}")
            else:
                err = result.stderr.strip()
                console.print(f"  [bold red]✘ sudo rm failed:[/] {err or 'unknown error'}")
                console.print(f"  [dim]Remove manually:[/]  sudo rm {_NEURO_BINARY}")
        except FileNotFoundError:
            console.print(f"  [yellow]⚠ sudo not found — remove manually:[/]  sudo rm {_NEURO_BINARY}")
    else:
        console.print(f"  [dim]{_NEURO_BINARY} not found — skipping.[/]")

    console.print()
    console.print(Rule(style="red"))
    console.print()
    console.print("[bold green]✔ Neuro has been uninstalled.[/]")
    console.print()
