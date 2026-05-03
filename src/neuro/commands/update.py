"""
neuro update

For each templateRepository entry in ~/.neuro/config.json:
  1. Pull latest (git pull if cached, git clone if fresh)
  2. Detect all skill directories in the repo
  3. Compare with currently installed skills
  4. Re-install every skill, overriding existing copies
  5. Report skills present in old install but absent from new repo
  6. Write a timestamped log to ~/.neuro/log/update-<timestamp>.log
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from neuro.services import skill_manager as sm

console = Console()

NEURO_HOME  = Path.home() / ".neuro"
_LOG_DIR    = NEURO_HOME / "log"
_REPO_CACHE = NEURO_HOME / ".repo"


# ── config ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    p = NEURO_HOME / "config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


# ── git helpers ───────────────────────────────────────────────────────────────

def _pull_or_clone(url: str, local_path: Path) -> tuple[bool, str]:
    """git pull if repo exists locally, otherwise git clone."""
    if local_path.exists() and (local_path / ".git").exists():
        result = subprocess.run(
            ["git", "-C", str(local_path), "pull", "--quiet", "--ff-only"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return True, "pulled latest"
        return False, result.stderr.strip() or "git pull failed"
    else:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--quiet", url, str(local_path)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return True, "cloned fresh"
        return False, result.stderr.strip() or "git clone failed"


# ── repo introspection ────────────────────────────────────────────────────────

def _find_skills_in_repo(repo_path: Path) -> dict[str, Path]:
    """
    Return {skill_name: source_dir} for every skill directory in the repo.

    Looks in two places (both are combined):
      - <repo>/skills/<name>/   (most common layout)
      - <repo>/<name>/SKILL.md  (top-level skill dirs)
    """
    found: dict[str, Path] = {}

    skills_sub = repo_path / "skills"
    if skills_sub.is_dir():
        for d in sorted(skills_sub.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                found[d.name] = d

    for d in sorted(repo_path.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and d.name != "skills":
            if (d / "SKILL.md").exists() and d.name not in found:
                found[d.name] = d

    return found


# ── skill installation ────────────────────────────────────────────────────────

def _install_skill(name: str, src: Path) -> tuple[str, str]:
    """
    Copy skill directory into ~/.neuro/skills/, overriding if already there.
    Returns ("installed"|"updated"|"error", detail).
    """
    dest = NEURO_HOME / "skills" / name
    existed = dest.exists()
    try:
        if dest.exists():
            if dest.is_symlink():
                dest.unlink()
            else:
                shutil.rmtree(dest)
        shutil.copytree(src, dest)
        return ("updated" if existed else "installed"), str(dest)
    except Exception as exc:
        return "error", str(exc)


# ── notification helpers ──────────────────────────────────────────────────────

def _ok(msg: str)   -> None: console.print(f"  [green]✔[/]  {msg}")
def _warn(msg: str) -> None: console.print(f"  [yellow]⚠[/]  [yellow]{msg}[/]")
def _err(msg: str)  -> None: console.print(f"  [red]✘[/]  [red]{msg}[/]")
def _hint(msg: str) -> None: console.print(f"  [dim]{msg}[/]")
def _section(title: str) -> None:
    console.print(Rule(f"[dim] {title} [/]", style="cyan"))
    console.print()


# ── log writer ────────────────────────────────────────────────────────────────

def _write_log(
    timestamp: str,
    repo_entries: list[dict],
) -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _LOG_DIR / f"update-{timestamp}.log"

    lines: list[str] = [
        "Neuro Update Log",
        f"Timestamp : {timestamp}",
        "=" * 64,
    ]

    for entry in repo_entries:
        lines += [
            "",
            f"Repository : {entry['url']}",
            f"Local path : {entry['path']}",
            f"Git        : {entry['git_msg']}",
            "",
        ]

        if not entry["git_ok"]:
            lines.append(f"  ERROR: {entry['git_msg']}")
            continue

        for name, status, detail in entry["results"]:
            marker = "✔" if status in ("installed", "updated") else "✘"
            lines.append(f"  {marker}  [{status:<10}]  {name:<36}  {detail}")

        if entry["removed"]:
            lines += ["", "  Skills no longer present in repository:"]
            for name in entry["removed"]:
                lines.append(f"    -  {name}")

        n_ok  = sum(1 for _, s, _ in entry["results"] if s in ("installed", "updated"))
        n_err = sum(1 for _, s, _ in entry["results"] if s == "error")
        lines += [
            "",
            f"  Installed/updated: {n_ok}  |  Errors: {n_err}  "
            f"|  Removed from repo: {len(entry['removed'])}",
        ]

    lines += ["", "=" * 64]
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


# ── update engine ─────────────────────────────────────────────────────────────

def _process_repo(repo: dict) -> dict:
    """
    Process one templateRepository entry.
    Returns a report dict consumed by both the display layer and the log writer.
    """
    url        = repo.get("url", "")
    name       = repo.get("name", url.split("/")[-1].removesuffix(".git"))
    local_path = Path(repo.get("path") or str(_REPO_CACHE / name))

    report = {
        "url":     url,
        "name":    name,
        "path":    str(local_path),
        "git_ok":  False,
        "git_msg": "",
        "results": [],   # list of (skill_name, status, detail)
        "removed": [],   # skills installed locally but absent from new repo
    }

    # Step 1 — pull / clone
    git_ok, git_msg = _pull_or_clone(url, local_path)
    report["git_ok"]  = git_ok
    report["git_msg"] = git_msg
    if not git_ok:
        return report

    # Step 2 — find skills in repo
    new_skills = _find_skills_in_repo(local_path)

    # Current skills in ~/.neuro/skills/
    old_names = {i.name for i in sm.list_items() if i.category == "skill"}

    # Skills that exist locally but are gone from the new repo version
    report["removed"] = sorted(old_names - set(new_skills))

    # Step 3 — install / override every skill in the repo
    for skill_name, src_path in sorted(new_skills.items()):
        status, detail = _install_skill(skill_name, src_path)
        report["results"].append((skill_name, status, detail))

    return report


# ── display helpers ───────────────────────────────────────────────────────────

def _display_report(report: dict) -> None:
    console.print(f"  [bold white]{report['name']}[/]  [dim]{report['url']}[/]")
    console.print()

    if not report["git_ok"]:
        _err(f"Git failed: {report['git_msg']}")
        console.print()
        return

    _hint(f"git: {report['git_msg']}  ·  local: {report['path']}")
    console.print()

    # Results table
    t = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        show_lines=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column("Skill",  style="bold white", min_width=30)
    t.add_column("Status", min_width=10)

    for skill_name, status, _ in report["results"]:
        if status == "installed":
            status_text = "[green]installed[/]"
        elif status == "updated":
            status_text = "[cyan]updated[/]"
        else:
            status_text = "[red]error[/]"
        t.add_row(skill_name, status_text)

    console.print(t)
    console.print()

    # Removed skills
    if report["removed"]:
        console.print(
            f"  [yellow]⚠[/]  [yellow]{len(report['removed'])} skill(s) no longer in this "
            "repository version:[/]"
        )
        for name in report["removed"]:
            console.print(f"     [dim]•  {name}[/]  [dim](still installed locally — run /remove to delete)[/]")
        console.print()

    n_ok  = sum(1 for _, s, _ in report["results"] if s in ("installed", "updated"))
    n_err = sum(1 for _, s, _ in report["results"] if s == "error")
    _hint(
        f"installed/updated: {n_ok}  ·  errors: {n_err}"
        + (f"  ·  removed from repo: {len(report['removed'])}" if report["removed"] else "")
    )
    console.print()


# ── entry point ───────────────────────────────────────────────────────────────

def run(confirm_fn: Callable[[str], bool] | None = None) -> None:
    """
    Run the full template-repository update flow.

    confirm_fn — optional callable(question: str) -> bool for non-default confirmation.
                 Defaults to asking via input() on stdout.
    """
    config = _load_config()
    repos: list[dict] = config.get("templateRepository", [])

    if not repos:
        console.print()
        _err("No templateRepository configured in ~/.neuro/config.json")
        _hint(
            "Add one with:  neuro config templateRepository "
            '[{"url":"<git-url>","name":"<name>","path":"~/.neuro/.repo/<name>"}]'
        )
        console.print()
        return

    # ── preview ───────────────────────────────────────────────────────────────
    console.print()
    _section("Neuro Update")

    console.print("  [bold]Repositories to update:[/]")
    console.print()
    for r in repos:
        console.print(f"  [cyan]·[/]  [bold white]{r.get('name', '?')}[/]  [dim]{r.get('url', '')}[/]")
    console.print()

    # ── confirm ───────────────────────────────────────────────────────────────
    if confirm_fn:
        if not confirm_fn("Pull latest and re-install all skills?"):
            _hint("Cancelled.")
            console.print()
            return
    else:
        console.print("[dim]Pull latest and re-install all skills? Type [bold]yes[/] to confirm:[/]")
        console.print()
        try:
            answer = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            _hint("Cancelled.")
            console.print()
            return
        if answer.lower() != "yes":
            _hint("Cancelled.")
            console.print()
            return

    console.print()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # ── process each repo ────────────────────────────────────────────────────
    all_reports: list[dict] = []
    for repo in repos:
        _section(f"Repository: {repo.get('name', repo.get('url', ''))}")
        report = _process_repo(repo)
        _display_report(report)
        all_reports.append(report)

    # ── write log ─────────────────────────────────────────────────────────────
    log_path = _write_log(timestamp, all_reports)

    console.print(Rule(style="cyan"))
    console.print()
    _ok(f"Update complete.  Log saved to [dim]{log_path}[/]")
    _hint("Run [bold]neuro init[/] to sync updated skills to your agents.")
    console.print()
