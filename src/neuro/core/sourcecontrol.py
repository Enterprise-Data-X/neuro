import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

console_print = print  # avoid rich dep in core layer

logger = logging.getLogger("neuro.sourcecontrol")


def _get_script_path(relative_path: str) -> str:
    """Locate a script in src/scripts/ relative to this package (dev layout)."""
    base = Path(__file__).parent.parent.parent / "scripts"
    return str(base / relative_path)


def clone_repository(repo_url: str, neuro_path: str) -> bool:
    """Clone a git repository into the neuro workspace."""
    repo_dir = os.path.join(neuro_path, "workspace", "tmp")

    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    os.makedirs(repo_dir)

    print(f"Cloning {repo_url} into {repo_dir}...")
    try:
        subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
        print("✅ Repository cloned")
        return True
    except FileNotFoundError:
        print("❌ git is not installed or not available in PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Git clone failed with exit code {e.returncode}.")
        return False


def pull_repo(uri: str, provider: str) -> None:
    """Pull skills/tools from a remote repository via provider-specific script."""
    providers = {
        "azuredevops": "azuredevops/install-skill-from-azuredevops.py",
        "github": "github/install-skill-from-github.py",
    }

    script_subpath = providers.get(provider.lower())
    if not script_subpath:
        logger.error("Unsupported provider requested: %s", provider)
        print(f"❌ Unsupported provider '{provider}'")
        return

    script_path = _get_script_path(script_subpath)
    if not os.path.exists(script_path):
        logger.error("Script not found: %s", script_path)
        print("❌ Internal script missing.")
        return

    try:
        logger.info("Executing %s pull script for URI: %s", provider, uri)
        result = subprocess.run(
            [sys.executable, script_path, "--url", uri],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug("Script output: %s", result.stdout)
        print(f"✅ Successfully pulled from {provider}")
    except subprocess.CalledProcessError as e:
        logger.error("Script failed (Exit %d): %s", e.returncode, e.stderr)
        print("❌ Script failed. See logs for details.")
