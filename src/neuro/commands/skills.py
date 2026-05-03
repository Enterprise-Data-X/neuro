"""
TUI command handlers for skill and tool management.

Commands:
  /list              — show all installed skills and tools
  /add <path|url>    — add a skill from a local path or git URL
  /remove <name>     — remove a skill or tool
  /update [name]     — check for updates; show diff and prompt to apply
  /create            — guided wizard to create a new skill with policy check
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from neuro.core.policy import validate_skill_content
from neuro.services import skill_manager as sm
from neuro.services import skill_evaluator as se


# ── notification primitives ───────────────────────────────────────────────────

def _ok(console: Console, msg: str)   -> None: console.print(f"  [green]✔[/]  {msg}")
def _warn(console: Console, msg: str) -> None: console.print(f"  [yellow]⚠[/]  [yellow]{msg}[/]")
def _err(console: Console, msg: str)  -> None: console.print(f"  [red]✘[/]  [red]{msg}[/]")
def _hint(console: Console, msg: str) -> None: console.print(f"  [dim]{msg}[/]")

def _section(console: Console, title: str) -> None:
    console.print(Rule(f"[dim] {title} [/]", style="cyan"))
    console.print()


# ── input helpers ─────────────────────────────────────────────────────────────

def _prompt(session: PromptSession, text: str, default: str = "") -> str:
    with patch_stdout():
        raw = session.prompt(text)
    return raw.strip() if raw else default


def _confirm(session: PromptSession, console: Console, question: str) -> bool:
    answer = _prompt(session, f"  [dim]{question}[/dim] [dim][y/N][/dim] ")
    return answer.lower() in ("y", "yes")


def _multiline(session: PromptSession, console: Console, label: str) -> str:
    _hint(console, f"{label}  [italic](blank line to finish)[/]")
    lines: list[str] = []
    while True:
        line = _prompt(session, "    > ")
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


# ── /list ─────────────────────────────────────────────────────────────────────

def _cmd_list(console: Console) -> None:
    items = sm.list_items()

    if not items:
        console.print()
        _warn(console, "No skills or tools installed in ~/.neuro/")
        _hint(console, "Run [bold]/add <path>[/] to add one, or [bold]/create[/] to build a new skill.")
        console.print()
        return

    t = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        show_lines=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column("Name",   style="bold white", min_width=22)
    t.add_column("Type",   min_width=6)
    t.add_column("Kind",   min_width=8, style="dim")
    t.add_column("Source", style="dim")

    for item in items:
        kind = "symlink" if item.is_symlink else ("dir" if item.path.is_dir() else "file")
        cat_style = "cyan" if item.category == "skill" else "magenta"
        source_label = item.source or "—"
        t.add_row(
            item.name,
            Text(item.category, style=cat_style),
            Text(kind),
            source_label,
        )

    skills = sum(1 for i in items if i.category == "skill")
    tools  = sum(1 for i in items if i.category == "tool")

    console.print()
    console.print(t)
    console.print()
    _hint(console, f"{skills} skill(s)  ·  {tools} tool(s)")
    console.print()


# ── /add ──────────────────────────────────────────────────────────────────────

def _cmd_add(args: list[str], session: PromptSession, console: Console) -> None:
    source = " ".join(args) if args else _prompt(session, "  Path or git URL:  ")
    if not source:
        _warn(console, "No source provided.")
        return

    is_url = source.startswith(("http://", "https://", "git@", "ssh://"))

    bucket_raw = _prompt(session, "  Category — skill or tool? [skill]:  ", default="skill")
    bucket = "tools" if bucket_raw.lower() in ("tool", "tools") else "skills"

    console.print()

    if is_url:
        _hint(console, f"Cloning [bold]{source}[/] …")
        ok, name, msg = sm.install_from_git(source, skill_name=None)
        if ok:
            sm.record_source(bucket, name, source)
            _ok(console, f"Installed [bold white]{name}[/]  [dim]→ {msg}[/]")
        else:
            _err(console, msg)
    else:
        src = Path(source).expanduser().resolve()
        if not src.exists():
            _err(console, f"Path not found: {src}")
            return
        ok, msg = sm.install_from_local(src, bucket)
        if ok:
            _ok(console, f"Installed [bold white]{src.name}[/]  [dim]→ {msg}[/]")
        else:
            _err(console, msg)

    console.print()


# ── /remove ───────────────────────────────────────────────────────────────────

def _cmd_remove(args: list[str], session: PromptSession, console: Console) -> None:
    items = sm.list_items()
    if not items:
        _warn(console, "Nothing installed to remove.")
        return

    if args:
        name   = args[0]
        target = next((i for i in items if i.name == name), None)
        if target is None:
            _err(console, f"'{name}' not found.")
            return
    else:
        console.print()
        t = Table.grid(padding=(0, 2))
        t.add_column(style="dim", min_width=4)
        t.add_column(style="bold white", min_width=22)
        t.add_column()
        for idx, item in enumerate(items, 1):
            cat = Text(item.category, style="cyan" if item.category == "skill" else "magenta")
            t.add_row(f"{idx}.", item.name, cat)
        console.print(t)
        console.print()

        choice = _prompt(session, "  Name or number to remove (blank to cancel):  ")
        if not choice:
            _hint(console, "Cancelled.")
            return

        if choice.isdigit():
            idx = int(choice) - 1
            if not (0 <= idx < len(items)):
                _err(console, "Invalid number.")
                return
            target = items[idx]
        else:
            target = next((i for i in items if i.name == choice), None)
            if target is None:
                _err(console, f"'{choice}' not found.")
                return

    console.print()
    if not _confirm(
        session, console,
        f"Remove {target.category} '[bold white]{target.name}[/bold white]'?"
    ):
        _hint(console, "Cancelled.")
        console.print()
        return

    ok, msg = sm.remove_item(f"{target.category}s", target.name)
    console.print()
    if ok:
        _ok(console, f"Removed [bold white]{target.name}[/]")
    else:
        _err(console, msg)
    console.print()


# ── /update ───────────────────────────────────────────────────────────────────

def _cmd_update(args: list[str], session: PromptSession, console: Console) -> None:
    items = sm.list_items()

    if args:
        name   = args[0]
        target = next((i for i in items if i.name == name), None)
        if target is None:
            _err(console, f"Skill '{name}' not found.")
            return
        candidates = [target]
    else:
        candidates = [i for i in items if i.source]
        if not candidates:
            _warn(console, "No skills have a recorded source URL.")
            _hint(console, "Add skills with [bold]/add <git-url>[/] to enable update checking.")
            return

    console.print()
    _section(console, "Update Check")

    updated = 0
    for item in candidates:
        console.print(f"  [dim]Checking[/]  [bold white]{item.name}[/] …")
        result = se.evaluate(item)

        if result.error:
            _warn(console, f"Skipped: {result.error}")
            console.print()
            continue

        if not result.has_update:
            _ok(console, f"[bold white]{item.name}[/]  [dim]up to date[/]")
            console.print()
            continue

        console.print()
        console.print(f"  [bold yellow]↑[/]  Update available for [bold white]{item.name}[/]")
        console.print()

        if result.diff:
            console.print(Syntax(result.diff, "diff", theme="ansi_dark", line_numbers=False))
            console.print()

        if _confirm(session, console, f"Apply update to '{item.name}'?"):
            ok, msg = se.apply_update(result)
            if ok:
                _ok(console, f"Updated [bold white]{item.name}[/]  [dim]→ {msg}[/]")
                updated += 1
            else:
                _err(console, f"Update failed: {msg}")
        else:
            _hint(console, "Skipped.")

        console.print()

    console.print(Rule(style="cyan"))
    console.print()
    _hint(console, f"Updates applied: {updated} of {len(candidates)} evaluated.")
    console.print()


# ── /create ───────────────────────────────────────────────────────────────────

_SKILL_TEMPLATE = """\
# Skill: {name}

## Description
{description}

## Behavior
{behavior}

## Constraints
{constraints}

---
_created: {timestamp} | source: local_
"""


def _cmd_create(session: PromptSession, console: Console) -> None:
    console.print()
    _section(console, "Create Skill")

    name = _prompt(session, "  Skill name (e.g. my-skill):  ")
    if not name:
        _hint(console, "Cancelled.")
        return

    existing = sm.get_item(name)
    if existing:
        _warn(console, f"A skill named '[bold white]{name}[/bold white]' already exists.")
        console.print()
        if not _confirm(session, console, "Overwrite it?"):
            _hint(console, "Cancelled.")
            console.print()
            return

    description = _prompt(session, "  Short description (one line):  ")

    console.print()
    behavior = _multiline(session, console, "Behavior instructions — what should the AI do with this skill?")

    console.print()
    constraints_raw = _multiline(session, console, "Constraints or restrictions (optional):")
    constraints = constraints_raw.strip() or "None"

    # Build content
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = _SKILL_TEMPLATE.format(
        name=name,
        description=description,
        behavior=behavior or "(no behavior specified)",
        constraints=constraints,
        timestamp=timestamp,
    )

    # Policy check
    console.print()
    _section(console, "Policy Check")

    issues = validate_skill_content(name, content)
    if issues:
        _err(console, f"{len(issues)} policy violation(s) found:")
        for issue in issues:
            console.print(f"    [dim red]•[/]  [red]{issue}[/]")
        console.print()
        if not _confirm(session, console, "Install anyway (not recommended)?"):
            _hint(console, "Skill not installed. Fix the issues and try /create again.")
            console.print()
            return
    else:
        _ok(console, "All policy checks passed.")

    # Preview
    console.print()
    _section(console, "Preview")
    console.print(Syntax(content, "markdown", theme="ansi_dark", word_wrap=True))
    console.print()

    if not _confirm(session, console, f"Install skill '[bold white]{name}[/bold white]' to ~/.neuro/skills/?"):
        _hint(console, "Cancelled.")
        console.print()
        return

    skill_file = sm.install_skill_content(name, content)
    console.print()
    _ok(console, f"Skill installed  [dim]→ {skill_file}[/]")
    _hint(console, "Run [bold]/init[/] to sync this skill to your installed agents.")
    console.print()


# ── dispatcher ────────────────────────────────────────────────────────────────

def handle(cmd: str, args: list[str], session: PromptSession, console: Console) -> None:
    if cmd == "/list":
        _cmd_list(console)
    elif cmd == "/add":
        _cmd_add(args, session, console)
    elif cmd == "/remove":
        _cmd_remove(args, session, console)
    elif cmd == "/check":
        _cmd_update(args, session, console)
    elif cmd == "/create":
        _cmd_create(session, console)
    else:
        _warn(console, f"Unknown skill command: {cmd}")
