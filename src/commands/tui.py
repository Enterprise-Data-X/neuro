
import os
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import patch_stdout

from neuro.commands import ensure_directories, handle_slash_command
from neuro.logger import get_logger
from neuro.core.sourcecontrol import pull_repo

console = Console()
logger = get_logger("TUI")

COMMANDS = ["/status", "/clear", "/bash", "/config", "/skill", "/agent", "/help", "/exit"]
neuro_completer = WordCompleter(COMMANDS, ignore_case=True)


def display_welcome():
    """Display a colorful welcome banner."""
    console.print()
    console.print(Panel("🧠 [bold bright_red]NEURO DIGITAL AI CONSOLE[/bold bright_red]", expand=False, border_style="bright_red"))
    console.print("[dim bright_red]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim bright_red]")
    console.print("[bold green]✓[/bold green] [bright_red]Autocomplete enabled for:[/bright_red] [yellow]/config, /skill, /agent[/yellow]")
    console.print("[bold green]✓[/bold green] [bright_red]Type[/bright_red] [yellow]/help[/yellow] [bright_red]or[/bright_red] [yellow]/exit[/yellow] [bright_red]to quit[/bright_red]")
    console.print("[dim bright_red]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim bright_red]\n")


def format_response(response: str) -> str:
    """Format command responses with colors."""
    if "✅" in response or "✓" in response:
        return f"[bold green]{response}[/bold green]"
    elif "❌" in response or "Error" in response:
        return f"[bold red]{response}[/bold red]"
    elif "⚠️" in response:
        return f"[bold yellow]{response}[/bold yellow]"
    elif "🧠" in response:
        return f"[bold bright_red]{response}[/bold bright_red]"
    elif "⚙️" in response:
        return f"[bold bright_red]{response}[/bold bright_red]"
    return f"[white]{response}[/white]"


def run():
    """Main TUI loop with enhanced visuals."""
    session = PromptSession(completer=neuro_completer)
    
    os.system('clear' if os.name == 'posix' else 'cls')
    display_welcome()
    
    logger.info("Neuro TUI session started.")

    try:
        while True:
            with patch_stdout():
                user_input = session.prompt("🧠 neuro ➜ ").strip()

            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "/exit"]:
                logger.info(f"exit via command: {user_input}")
                break

            if user_input.startswith("/"):
                logger.debug(f"Executing command: {user_input}")
                
                # handle_slash_command now looks up logic in config.json
                response = handle_slash_command(user_input)
                
                if response:
                    console.print(f"[bold bright_red]SYSTEM:[/] {response}")
                    logger.info(f"command: '{user_input}', response: {response}")
            else:
                # Handle standard natural language or logs
                logger.info(f"USER:{user_input}")
                # You can add LLM processing here later
                console.print(f"[dim]Neuro received:[/] {user_input}")

    except KeyboardInterrupt:
        logger.warning("Session interrupted via KeyboardInterrupt (Ctrl+C).")
    except Exception as e:
        logger.exception(f"Fatal error in TUI loop: {e}")
        console.print(f"[bold bright_red]💥 A fatal error occurred:[/] {e}")
    finally:
        console.print("[bold bright_red]\n👋 Neuro session ended.[/]")
        logger.info("TUI session closed.")


if __name__ == "__main__":
    ensure_directories()
    start_tui()