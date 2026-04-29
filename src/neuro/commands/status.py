from pathlib import Path
from rich.console import Console
from rich.table import Table

NEURO_HOME = Path.home() / ".neuro"
PROJECT_ROOT = Path.cwd()
AGENT_PATHS = {
    "GitHub Copilot": ".github/skills",
    "Claude Code": ".claude/skills",
    "Gemini Code Assist": ".gemini/skills",
    "Cursor": ".cursor/rules",
    "Windsurf": ".windsurf/memories",
}

def run():
    console = Console()
    table = Table(title="🧠 Neuro Agent Status", header_style="bold cyan")
    table.add_column("Agent")
    table.add_column("Status", justify="center")
    table.add_column("Linked Skills/Tools", style="green")

    found = False
    for agent, rel_path in AGENT_PATHS.items():
        target = PROJECT_ROOT / rel_path
        links = []
        if target.exists():
            found = True
            for cat in ["skills", "tools"]:
                p = target / cat
                if p.exists():
                    links.extend([f"{cat}/{i.name}" for i in p.iterdir() if i.is_symlink()])
            
            status = "✅ ACTIVE" if links else "🟡 EMPTY"
            table.add_row(agent, status, ", ".join(links) if links else "No neuro links")
        else:
            table.add_row(agent, "❌ INACTIVE", "-")

    console.print(table) if found else console.print("[yellow]No agents found. Run 'neuro init'[/]")
