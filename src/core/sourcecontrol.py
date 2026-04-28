import os
import shutil
import subprocess
import sys
from rich.console import Console
from neuro.logger import get_logger
from neuro.config import get_script_path

console = Console()
logger = get_logger("SourceControl")


def clone_repository(repo_url: str, neuro_path: str) -> bool:
    """
    Clone a git repository into the neuro workspace.

    Args:
        repo_url: The git repository URL to clone
        neuro_path: The path to the .neuro directory

    Returns:
        bool: True if cloning was successful, False otherwise
    """
    repo_dir = os.path.join(neuro_path, "workspace", "tmp")

    # Clean up existing directory if it exists
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    os.makedirs(repo_dir)

    print(f"Cloning {repo_url} into {repo_dir}...")
    try:
        subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
        print("✅ Repository cloned")
        return True
    except FileNotFoundError:
        print("❌ git is not installed or not available in PATH. Please install git and try again.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Git clone failed with exit code {e.returncode}.")
        return False


def pull_repo(uri: str, provider: str):
    """
    Optimized repo puller using a provider mapping and centralized logging.
    """
    providers = {
        "azuredevops": "azuredevops/install-skill-from-azuredevops.py",
        "github": "github/install-skill-from-github.py"
    }

    script_subpath = providers.get(provider.lower())

    if not script_subpath:
        logger.error(f"Unsupported provider requested: {provider}")
        console.print(f"[bold red]❌ Error:[/] Unsupported provider '{provider}'")
        return

    script_path = get_script_path(script_subpath)

    if os.path.exists(script_path):
        try:
            logger.info(f"Executing {provider} pull script for URI: {uri}")
            # Capture output so it doesn't mess up the TUI layout
            result = subprocess.run(
                [sys.executable, script_path, "--url", uri],
                check=True,
                capture_output=True,
                text=True
            )
            logger.debug(f"Script output: {result.stdout}")
            console.print(f"[bold green]✅ Successfully pulled from {provider}[/]")

        except subprocess.CalledProcessError as e:
            logger.error(f"Script failed (Exit {e.returncode}): {e.stderr}")
            console.print(f"[bold red]❌ Script failed.[/] See logs for details.")
    else:
        logger.error(f"Execution failed: Script not found at {script_path}")
        console.print(f"[bold red]❌ Error:[/] Internal script missing.")