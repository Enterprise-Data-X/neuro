import os
import shutil
import json
from pathlib import Path
from datetime import datetime
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# --- CONFIGURATION ---
NEURO_HOME = Path.home() / ".neuro"
PROJECT_ROOT = Path.cwd()
BUNDLED_MD = Path(__file__).parent.parent / "NEURO.md"

AGENT_MAP = {
    "Universal Agent (.agent)": {"local": ".agent/skills", "global": Path.home() / ".agent/skills", "root": ".agent"},
    "GitHub Copilot": {"local": ".github/skills", "global": Path.home() / ".copilot/skills", "root": ".github"},
    "Claude Code": {"local": ".claude/skills", "global": Path.home() / ".claude/agents", "root": ".claude"},
    "Gemini Code Assist": {"local": ".gemini/skills", "global": Path.home() / ".gemini/skills", "root": ".gemini"},
    "Cursor": {"local": ".cursor/rules", "global": Path.home() / ".cursor/rules", "root": ".cursor"},
    "Windsurf": {"local": ".windsurf/memories", "global": Path.home() / ".windsurf/global_memories", "root": ".windsurf"}
}

def bootstrap_neuro_home():
    """Seeds the global NEURO.md directive into ~/.neuro."""
    skills_dir = NEURO_HOME / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (NEURO_HOME / "tools").mkdir(parents=True, exist_ok=True)

    if BUNDLED_MD.exists():
        target_md = skills_dir / "NEURO.md"
        if not target_md.exists():
            shutil.copy2(BUNDLED_MD, target_md)
            console.print(f"[dim]📡 System protocol bootstrapped to {target_md}[/]")

def install_to_path(source_neuro, target_dir, agent_name):
    """Links files and prints specific success messages for each."""
    installed_items = []
    for category in ["skills", "tools"]:
        src_cat = source_neuro / category
        if not src_cat.exists(): continue
        
        dest_cat = target_dir / category
        dest_cat.mkdir(parents=True, exist_ok=True)
    
        for item in src_cat.iterdir():
            link_name = dest_cat / item.name
            if not link_name.exists():
                try:
                    os.symlink(item.absolute(), link_name.absolute())
                    # Displaying specific installation success
                    console.print(f"  [bold green]➜ INSTALLED {category.upper()}:[/] [white]{item.name}[/]")
                    installed_items.append(item.name)
                except OSError:
                    shutil.copytree(item, link_name) if item.is_dir() else shutil.copy2(item, link_name)
                    console.print(f"  [bold yellow]➜ COPIED {category.upper()}:[/] [white]{item.name}[/] [dim](Symlink failed)[/]")
                    installed_items.append(item.name)
    return len(installed_items)

def run(force=False):
    bootstrap_neuro_home()

    scope = questionary.select(
        "Where would you like to apply Neuro behaviours?",
        choices=[
            {"name": "Project Level (Current folder only)", "value": "local"},
            {"name": "Global Level (All projects for this user)", "value": "global"}
        ]
    ).ask()

    if not scope: return

    selected = questionary.checkbox(f"Select agents for {scope} alignment:", choices=list(AGENT_MAP.keys())).ask()
    if not selected: return

    installed_count = 0

    for agent in selected:
        config = AGENT_MAP[agent]
        
        if scope == "global":
            console.print(f"\n[bold blue]🌍 GLOBAL ALIGNMENT:[/] [reverse]{agent}[/]")
            install_to_path(NEURO_HOME, config["global"], agent)
            installed_count += 1
        else:
            root_folder = PROJECT_ROOT / config["root"]
            
            # --- HIGH VISIBILITY ERROR/ADVICE BLOCK ---
            if not root_folder.exists() and not force:
                error_text = Text()
                error_text.append(f"\n⚠️  CANNOT INSTALL SKILLS OR TOOLS FOR: {agent}\n", style="bold white on red")
                error_text.append(f"\nReason: ", style="bold")
                error_text.append(f"Directory '{config['root']}/' is missing from project root.\n", style="cyan")
                error_text.append("\n[Action Required]", style="bold underline")
                error_text.append(f"\nRun: neuro init --force", style="bold green")
                error_text.append(f" OR mkdir {config['root']}", style="bold green")
                
                console.print(Panel(error_text, border_style="red", padding=(1, 2)))
                continue
            
            if force and not root_folder.exists():
                console.print(f"\n🚀 [bold]FORCE MODE:[/] Creating [cyan]{config['root']}/[/]...")
                root_folder.mkdir(parents=True, exist_ok=True)

            console.print(f"\n[bold magenta]📦 PROJECT ALIGNMENT:[/] [reverse]{agent}[/]")
            if install_to_path(NEURO_HOME, PROJECT_ROOT / config["local"], agent) > 0:
                installed_count += 1
            else:
                console.print(f"  [dim italic]No skills or tools found in {NEURO_HOME}[/]")

    console.print(f"\n[bold reverse green] COMPLETED [/] [bold green]Aligned {installed_count} agent system(s).[/]\n")
