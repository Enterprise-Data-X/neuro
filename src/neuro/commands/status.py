import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from neuro.commands.init import AGENT_MAP, NEURO_HOME

console = Console()


def _count_installed(agent_config: dict) -> tuple[int, int]:
    """Count installed skills and tools in the agent's global directories."""
    skills = tools = 0
    skills_dir = agent_config.get("skills_dir")
    if skills_dir and Path(skills_dir).exists():
        skills = sum(1 for _ in Path(skills_dir).iterdir())
    commands_dir = agent_config.get("commands_dir")
    if commands_dir and Path(commands_dir).exists():
        tools = sum(1 for _ in Path(commands_dir).iterdir())
    return skills, tools


def run() -> None:
    neuro_home = NEURO_HOME

    # Load init_assets written by `neuro init`
    config_path = neuro_home / "config.json"
    init_assets: dict = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            init_assets = data.get("init_assets", {})
        except (json.JSONDecodeError, OSError):
            pass

    table = Table(title="🧠 Neuro Agent Status", header_style="bold cyan")
    table.add_column("Agent", style="bold white", min_width=28)
    table.add_column("Status", justify="center", min_width=12)
    table.add_column("Instruction File", style="dim")
    table.add_column("Installed", justify="right", style="green")

    for agent_name, config in AGENT_MAP.items():
        detected, _ = config["detect"]()
        instr_file = Path(config["instruction_file"])
        instr_exists = instr_file.exists()

        agent_data = init_assets.get(agent_name, {})
        installed_count = len(agent_data.get("installed", []))
        error_count = len(agent_data.get("errors", []))

        if not detected:
            status_cell = Text("not detected", style="dim")
            installed_cell = "-"
        elif not agent_data:
            status_cell = Text("detected / not init'd", style="yellow")
            installed_cell = "-"
        elif error_count:
            status_cell = Text("⚠ partial", style="yellow")
            installed_cell = str(installed_count)
        else:
            status_cell = Text("✔ active", style="bold green")
            installed_cell = str(installed_count)

        instr_label = str(instr_file).replace(str(Path.home()), "~") if instr_exists else (
            f"[dim]{str(instr_file).replace(str(Path.home()), '~')} (missing)[/]"
        )

        table.add_row(agent_name, status_cell, instr_label, installed_cell)

    console.print()
    console.print(table)

    if not init_assets:
        console.print("\n[yellow]No init data found. Run [bold]neuro init[/] to install skills.[/]")
    console.print()
