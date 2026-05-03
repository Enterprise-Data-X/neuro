import os
import json
import shutil
import platform
from datetime import datetime, timezone
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule

console = Console()

# ─── CONFIGURATION ───────────────────────────────────────────────────────────

NEURO_HOME = Path.home() / ".neuro"
BUNDLED_MD = Path(__file__).parent.parent / "NEURO.md"

_OS = platform.system()  # "Darwin" | "Linux" | "Windows"


# ─── AGENT DETECTION ─────────────────────────────────────────────────────────
#
# Each detector returns (is_installed: bool, detail: str).
# "detail" is surfaced in the CLI — the found path, or why detection failed.
#
# Detection strategy per agent:
#
#   Universal Agent  – ~/.agent/ directory exists
#   GitHub Copilot   – `copilot` binary in PATH  (npm install -g @github/copilot)
#                      OR legacy gh-copilot extension directory
#                      OR ~/.copilot/ config dir
#   Claude Code      – `claude` binary in PATH  OR  ~/.claude/ config dir exists
#   Gemini           – `gemini` binary in PATH  OR  ~/.gemini/ config dir exists
#   Cursor           – macOS: /Applications/Cursor.app
#                      Linux: `cursor` in PATH or ~/.config/Cursor
#                      Windows: %LOCALAPPDATA%\Programs\cursor\Cursor.exe
#                      Any OS: ~/.cursor/ settings dir
#   Windsurf         – macOS: /Applications/Windsurf.app
#                      Linux: `windsurf` in PATH or ~/.config/Windsurf
#                      Windows: %LOCALAPPDATA%\Programs\windsurf\Windsurf.exe
#                      Any OS: ~/.codeium/windsurf/ data dir
#   Continue.dev     – ~/.continue/ config dir exists

def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _app_exists_mac(app_name: str) -> Path | None:
    for base in (Path("/Applications"), Path.home() / "Applications"):
        p = base / f"{app_name}.app"
        if p.exists():
            return p
    return None


def _exe_exists_win(relative: str) -> Path | None:
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        p = Path(local_app) / "Programs" / relative
        if p.exists():
            return p
    return None


def _detect_universal_agent() -> tuple[bool, str]:
    d = Path.home() / ".agent"
    if d.exists():
        return True, str(d)
    return False, "~/.agent/ directory not found"


def _detect_copilot() -> tuple[bool, str]:
    p = _which("copilot")
    if p:
        return True, p
    if _which("gh"):
        for ext_dir in [
            Path.home() / ".config" / "gh" / "extensions" / "gh-copilot",
            Path.home() / "Library" / "Application Support" / "gh" / "extensions" / "gh-copilot",
            Path(os.environ.get("GH_DATA_DIR", "")) / "extensions" / "gh-copilot",
            Path.home() / ".local" / "share" / "gh" / "extensions" / "gh-copilot",
        ]:
            if ext_dir.exists():
                return True, f"gh-copilot extension → {ext_dir}"
    config_dir = Path.home() / ".copilot"
    if config_dir.exists():
        return True, f"config dir {config_dir}"
    return False, "`copilot` not in PATH; no gh-copilot extension or ~/.copilot/ found"


def _detect_claude_code() -> tuple[bool, str]:
    p = _which("claude")
    if p:
        return True, p
    config_dir = Path.home() / ".claude"
    if config_dir.exists():
        return True, f"config dir {config_dir}"
    return False, "`claude` not in PATH and ~/.claude/ not found"


def _detect_gemini() -> tuple[bool, str]:
    p = _which("gemini")
    if p:
        return True, p
    config_dir = Path.home() / ".gemini"
    if config_dir.exists():
        return True, f"config dir {config_dir}"
    return False, "`gemini` not in PATH and ~/.gemini/ not found"


def _detect_cursor() -> tuple[bool, str]:
    if _OS == "Darwin":
        app = _app_exists_mac("Cursor")
        if app:
            return True, str(app)
    elif _OS == "Linux":
        p = _which("cursor")
        if p:
            return True, p
        cfg = Path.home() / ".config" / "Cursor"
        if cfg.exists():
            return True, f"config dir {cfg}"
    elif _OS == "Windows":
        exe = _exe_exists_win("cursor\\Cursor.exe")
        if exe:
            return True, str(exe)
    cursor_home = Path.home() / ".cursor"
    if cursor_home.exists():
        return True, f"settings dir {cursor_home}"
    return False, "Cursor not found (checked PATH, app dirs, ~/.cursor/)"


def _detect_continue() -> tuple[bool, str]:
    continue_dir = Path.home() / ".continue"
    if continue_dir.exists():
        return True, f"config dir {continue_dir}"
    return False, "~/.continue/ not found"


# ─── AGENT MAP ───────────────────────────────────────────────────────────────
#
# Keys used by install_agent():
#
#   "detect"           – () -> (bool, str)
#   "instruction_file" – global markdown the agent reads for instructions
#   "skills_dir"       – where skill *directories* (containing SKILL.md) go,
#                        or None if the agent has no skills-directory concept
#   "commands_dir"     – where flat *.md command files go,
#                        or None if not applicable
#   "agents_dir"       – where sub-agent/tool files go, or None
#   "note"             – surfaced in the summary for user-visible caveats
#
# Claude Code distinction (verified May 2026 — code.claude.com/docs/en/skills):
#   ~/.claude/skills/<name>/SKILL.md  →  auto-invoked skills (directory-based)
#   ~/.claude/commands/<name>.md      →  manual /slash-commands (flat files)
#   Files in either location create the same /command interface, but skills
#   take precedence on name conflict and support auto-invocation + bundled files.

AGENT_MAP: dict[str, dict] = {
    "Universal Agent (.agent)": {
        "detect":           _detect_universal_agent,
        "instruction_file": Path.home() / ".agent" / "NEURO.md",
        "skills_dir":       Path.home() / ".agent" / "skills",
        "commands_dir":     None,
        "agents_dir":       Path.home() / ".agent" / "agents",
        "note":             None,
    },
    "GitHub Copilot": {
        "detect":           _detect_copilot,
        # Single global instruction file only — no skills/commands dirs.
        "instruction_file": Path.home() / ".copilot" / "copilot-instructions.md",
        "skills_dir":       None,
        "commands_dir":     None,
        "agents_dir":       None,
        "note": "Copilot reads a single global instruction file. "
                "Skills and tools are appended as sections inside it.",
    },
    "Claude Code": {
        "detect":           _detect_claude_code,
        # Skill directories (containing SKILL.md) → ~/.claude/skills/
        # Flat .md files                           → ~/.claude/commands/
        # Sub-agent .md files                      → ~/.claude/agents/
        "instruction_file": Path.home() / ".claude" / "CLAUDE.md",
        "skills_dir":       Path.home() / ".claude" / "skills",
        "commands_dir":     Path.home() / ".claude" / "commands",
        "agents_dir":       Path.home() / ".claude" / "agents",
        "note": "Skill directories → ~/.claude/skills/  |  "
                "Flat .md files → ~/.claude/commands/  |  "
                "Tools → ~/.claude/agents/",
    },
    "Continue.dev (Codex / OpenAI)": {
        "detect":           _detect_continue,
        # Skills/tools land in ~/.continue/prompts/ as .md files and are
        # available as slash-command prompts inside the Continue extension.
        "instruction_file": Path.home() / ".continue" / "config.yaml",
        "skills_dir":       Path.home() / ".continue" / "prompts",
        "commands_dir":     Path.home() / ".continue" / "prompts",
        "agents_dir":       None,
        "note": "Skills are installed as prompt files into ~/.continue/prompts/",
    },
}


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _symlink_or_copy(src: Path, dest: Path) -> tuple[str, str]:
    """Symlink dest → src; fall back to copy on OSError. Returns (action, name)."""
    if dest.exists() or dest.is_symlink():
        return "skip", dest.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(src.absolute(), dest.absolute())
        return "symlink", dest.name
    except OSError:
        try:
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
            return "copy", dest.name
        except Exception as exc:
            return "error", str(exc)


def _append_to_instruction_file(dest: Path, content: str, section_header: str) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if dest.exists() else "w"
        with dest.open(mode, encoding="utf-8") as fh:
            fh.write(f"\n\n## {section_header}\n\n{content}")
        return True
    except Exception:
        return False


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _is_skill_dir(path: Path) -> bool:
    """A skill directory contains a SKILL.md file at its root."""
    return path.is_dir() and (path / "SKILL.md").exists()


# ─── BOOTSTRAP ───────────────────────────────────────────────────────────────

def bootstrap_neuro_home() -> None:
    """Seeds the global NEURO.md directive into ~/.neuro/skills/."""
    skills_dir = NEURO_HOME / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (NEURO_HOME / "tools").mkdir(parents=True, exist_ok=True)

    if BUNDLED_MD.exists():
        target_md = skills_dir / "NEURO.md"
        if not target_md.exists():
            shutil.copy2(BUNDLED_MD, target_md)
            console.print(f"  [dim]📡 System protocol bootstrapped → {target_md}[/]")


# ─── CORE INSTALL LOGIC ──────────────────────────────────────────────────────

def _install_item(
    item: Path,
    config: dict,
    category: str,          # "skill" | "tool"
    summary: dict,
    append_content: list,   # mutable list; text is accumulated here for file-based agents
) -> None:
    """
    Routes a single item from ~/.neuro/{skills,tools}/ to the correct
    destination inside the agent's global config, based on whether:

      • The agent has a dedicated directory (skills_dir / commands_dir / agents_dir)
      • The item is a skill directory (contains SKILL.md)  →  skills_dir
      • The item is a flat .md file                        →  commands_dir (if set) else skills_dir
      • The agent uses a single instruction file           →  append text content
    """
    label = f"{category}s/{item.name}"
    agent_name = summary.get("agent")
    
    # ── agents that use dedicated directories ─────────────────────────────────
    if config["skills_dir"] is not None or config["commands_dir"] is not None:

        # ROUTING LOGIC
        if agent_name == "Claude Code":
            # Override: Force everything to commands_dir if available
            dest_dir = config.get("commands_dir") or config["skills_dir"]
        elif _is_skill_dir(item):
            # Standard: Directory with SKILL.md goes to skills_dir
            dest_dir = config["skills_dir"]
        elif item.is_dir():
            # Plain directory -> tools/agents
            dest_dir = config.get("agents_dir") or config["skills_dir"]
        else:
            # Flat markdown file
            dest_dir = config.get("commands_dir") or config["skills_dir"]

        if dest_dir is None:
            summary["errors"].append(f"{label}: no destination directory available")
            return

        dest = dest_dir / item.name

        # Ensure we don't try to symlink a file into a non-existent dir
        action, result = _symlink_or_copy(item, dest)
        
        if action == "skip":
            summary["skipped"].append(item.name)
        elif action == "error":
            summary["errors"].append(f"{label} → {result}")
        else:
            summary["installed"].append((action, label))
            console.print(
                f"    [bold green]✔ {action.upper():8}[/] [white]{label}[/]"
                f"  [dim]→ {dest}[/]"
            )

    # ── agents that use a single instruction file (append mode) ──────────────
    else:
        if item.is_dir():
            # Recurse into the directory and append all .md files inside
            for sub in sorted(item.rglob("*.md")):
                text = _read_text(sub)
                if text.strip():
                    append_content.append(text)
                    sub_label = f"{category}s/{item.name}/{sub.relative_to(item)}"
                    summary["installed"].append(("appended", sub_label))
                    console.print(
                        f"    [bold cyan]✔ APPENDED [/] [white]{sub_label}[/]"
                        f"  [dim]→ {config['instruction_file']}[/]"
                    )
        elif item.suffix in {".md", ".txt"}:
            text = _read_text(item)
            if text.strip():
                append_content.append(text)
                summary["installed"].append(("appended", label))
                console.print(
                    f"    [bold cyan]✔ APPENDED [/] [white]{label}[/]"
                    f"  [dim]→ {config['instruction_file']}[/]"
                )


def install_agent(agent_name: str, config: dict) -> dict:
    """
    Installs ~/.neuro/skills and ~/.neuro/tools into the agent's global
    config location.  Returns a summary dict.
    """
    summary: dict = {
        "agent":            agent_name,
        "instruction_file": config["instruction_file"],
        "installed":        [],
        "skipped":          [],
        "errors":           [],
        "note":             config.get("note"),
    }

    append_content: list[str] = []

    # ── skills ───────────────────────────────────────────────────────────────
    skills_src = NEURO_HOME / "skills"
    for item in sorted(skills_src.iterdir()) if skills_src.exists() else []:
        _install_item(item, config, "skill", summary, append_content)

    # ── tools ─────────────────────────────────────────────────────────────────
    tools_src = NEURO_HOME / "tools"
    for item in sorted(tools_src.iterdir()) if tools_src.exists() else []:
        _install_item(item, config, "tool", summary, append_content)

    # ── instruction file ──────────────────────────────────────────────────────
    instr_path = config["instruction_file"]

    if append_content:
        # File-based agents: dump everything into the instruction file
        ok = _append_to_instruction_file(
            instr_path,
            "\n\n".join(append_content),
            "Neuro Skills & Tools",
        )
        if ok:
            console.print(
                f"    [bold cyan]✔ WRITTEN  [/] instruction file  [dim]→ {instr_path}[/]"
            )
        else:
            summary["errors"].append(f"Could not write instruction file: {instr_path}")

    else:
        # Directory-based agents: symlink/copy NEURO.md as the instruction file
        neuro_md_src = NEURO_HOME / "skills" / "NEURO.md"
        if neuro_md_src.exists():
            instr_path.parent.mkdir(parents=True, exist_ok=True)
            action, result = _symlink_or_copy(neuro_md_src, instr_path)
            if action == "skip":
                console.print(
                    f"    [dim]⏭  instruction file already exists → {instr_path}[/]"
                )
                summary["skipped"].append(instr_path.name)
            elif action == "error":
                summary["errors"].append(f"instruction file: {result}")
            else:
                summary["installed"].append((action, instr_path.name))
                console.print(
                    f"    [bold green]✔ {action.upper():8}[/] [white]{instr_path.name}[/]"
                    f"  [dim]→ {instr_path}[/]"
                )

    return summary


# ─── SUMMARY RENDERER ────────────────────────────────────────────────────────

def render_summary(
    installed_summaries: list[dict],
    skipped_agents: list[tuple[str, str]],
) -> None:
    console.print()
    console.print(Rule("[bold white] INSTALLATION SUMMARY [/]", style="green"))

    total_installed = total_skipped = total_errors = 0

    for s in installed_summaries:
        console.print()
        console.print(Text(f" {s['agent']} ", style="bold reverse white"))
        console.print(f"  [dim]Instruction file:[/] {s['instruction_file']}")
        if s["note"]:
            console.print(f"  [yellow]ℹ  {s['note']}[/]")

        tbl = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
        tbl.add_column("Status", style="bold", width=14)
        tbl.add_column("File",   style="white")
        tbl.add_column("Action", style="dim")

        for action, fname in s["installed"]:
            colour = "green" if action != "appended" else "cyan"
            tbl.add_row(f"[{colour}]✔ {action.upper()}[/]", fname, "installed")
            total_installed += 1
        for fname in s["skipped"]:
            tbl.add_row("[dim]⏭  SKIP[/]", fname, "already exists")
            total_skipped += 1
        for msg in s["errors"]:
            tbl.add_row("[red]✘ ERROR[/]", msg, "")
            total_errors += 1
        if not any([s["installed"], s["skipped"], s["errors"]]):
            tbl.add_row("[dim]—[/]", "[dim]nothing to install[/]", "")

        console.print(tbl)

    if skipped_agents:
        console.print()
        console.print(Text(" Not detected — skipped ", style="bold reverse yellow"))
        skip_tbl = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
        skip_tbl.add_column("Agent",  style="white", width=28)
        skip_tbl.add_column("Reason", style="dim")
        for name, reason in skipped_agents:
            skip_tbl.add_row(name, reason)
        console.print(skip_tbl)

    console.print()
    console.print(Rule(style="green"))
    ok_colour = "green" if total_errors == 0 else "red"
    console.print(
        f"[bold {ok_colour}]  Files installed:[/] {total_installed}  "
        f"[dim]Files skipped:[/] {total_skipped}  "
        f"[{'red' if total_errors else 'dim'}]Errors:[/] {total_errors}  "
        f"[yellow]Agents not detected:[/] {len(skipped_agents)}"
    )
    console.print()


# ─── PERSISTENCE ─────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Current UTC time as a compact ISO-8601 string, e.g. '2026-05-03T14:22:01Z'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def persist_to_config(
    installed_summaries: list[dict],
    skipped_agents: list[tuple[str, str]],
) -> None:
    """
    Merges the init results into ~/.neuro/config.json under the key
    "init_assets".  The attribute holds every skill and tool that was
    installed or skipped, keyed by agent name.

    Structure written / merged:
    {
      ...existing config keys...,
      "init_assets": {
        "Claude Code": {
          "installed": ["skills/my-skill", "commands/my-cmd.md"],
          "skipped":   ["CLAUDE.md"],
          "errors":    []
        },
        "GitHub Copilot": { ... },
        ...
        "_agents_not_detected": ["Cursor", "Windsurf"]
      }
    }

    Existing entries for an agent are replaced; all other config keys are
    preserved untouched.
    """
    config_path = NEURO_HOME / "config.json"

    # Load existing config (or start fresh if the file is absent / corrupt)
    config: dict = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config = {}

    init_assets: dict = config.get("init_assets", {})

    # Write per-agent results
    for s in installed_summaries:
        init_assets[s["agent"]] = {
            "installed": [fname for _, fname in s["installed"]],
            "skipped":   s["skipped"],
            "errors":    s["errors"],
        }

    # Record agents that were not detected on this machine
    init_assets["_agents_not_detected"] = [name for name, _ in skipped_agents]

    config["init_assets"] = init_assets

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        console.print(
            f"  [dim]💾 config.json updated → {config_path}[/]"
        )
    except OSError as exc:
        console.print(f"  [red]✘ Could not update config.json: {exc}[/]")


def write_log_entry(
    installed_summaries: list[dict],
    skipped_agents: list[tuple[str, str]],
    overall_status: str,          # "success" | "partial" | "failure"
) -> None:
    """
    Appends one entry to ~/.neuro/logs/neuro-log.json.

    The file is a JSON object whose keys are ISO-8601 UTC timestamps.
    Each value is a log-entry object describing what `neuro init` did.

    {
      "2026-05-03T14:22:01Z": {
        "command":        "neuro init",
        "status":         "success",
        "agents_processed": 3,
        "agents_skipped":   2,
        "agents": {
          "Claude Code": {
            "status":    "success",
            "installed": ["skills/my-skill", "commands/my-cmd.md"],
            "skipped":   [],
            "errors":    []
          },
          ...
        },
        "agents_not_detected": ["Cursor", "Windsurf"]
      },
      ...
    }
    """
    log_path = NEURO_HOME / "logs" / "neuro-log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing log file (create empty dict if absent or corrupt)
    log: dict = {}
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log = {}

    # Build agent-level entries
    agents_detail: dict = {}
    for s in installed_summaries:
        has_errors = len(s["errors"]) > 0
        agent_status = "failure" if has_errors and not s["installed"] else (
            "partial" if has_errors else "success"
        )
        agents_detail[s["agent"]] = {
            "status":    agent_status,
            "installed": [fname for _, fname in s["installed"]],
            "skipped":   s["skipped"],
            "errors":    s["errors"],
        }

    # Write new timestamped entry — use a unique key even on sub-second collisions
    timestamp = _now_iso()
    # Guard against the (unlikely) case of two runs in the same second
    unique_key = timestamp
    counter = 1
    while unique_key in log:
        unique_key = f"{timestamp}#{counter}"
        counter += 1

    log[unique_key] = {
        "command":            "neuro init",
        "status":             overall_status,
        "agents_processed":   len(installed_summaries),
        "agents_skipped":     len(skipped_agents),
        "agents":             agents_detail,
        "agents_not_detected": [name for name, _ in skipped_agents],
    }

    try:
        log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        console.print(
            f"  [dim]📋 log entry written  → {log_path}[/]"
        )
    except OSError as exc:
        console.print(f"  [red]✘ Could not write log entry: {exc}[/]")


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def run(force: bool = False) -> None:
    """
    `neuro init`

    Probes each known AI agent for installation evidence, then installs
    ~/.neuro/skills and ~/.neuro/tools into that agent's global config
    location.  Agents that are not installed on this machine are silently
    skipped and reported in the final summary.
    """
    console.print()
    console.print(
        Panel(
            "[bold white]neuro init[/]  —  Aligning AI agents with Neuro behaviours\n"
            "[dim]Applies [bold]~/.neuro/skills[/] and [bold]~/.neuro/tools[/] "
            "only to agents detected on this machine.[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )

    # ── Step 1: bootstrap ~/.neuro ───────────────────────────────────────────
    console.print("[bold blue]Step 1/3[/] Bootstrapping Neuro home (~/.neuro)…")
    bootstrap_neuro_home()

    skills_count = (
        sum(1 for _ in (NEURO_HOME / "skills").iterdir())
        if (NEURO_HOME / "skills").exists() else 0
    )
    tools_count = (
        sum(1 for _ in (NEURO_HOME / "tools").iterdir())
        if (NEURO_HOME / "tools").exists() else 0
    )
    console.print(
        f"  [dim]Found [bold]{skills_count}[/] skill(s) and "
        f"[bold]{tools_count}[/] tool(s) in ~/.neuro[/]"
    )

    if skills_count + tools_count == 0:
        console.print(
            "\n[yellow]  ⚠  No skills or tools found in ~/.neuro. "
            "Run [bold]`neuro install`[/] first to populate your Neuro home.[/]"
        )
        return

    # ── Step 2: detect agents → install only those present ───────────────────
    console.print()
    console.print("[bold blue]Step 2/3[/] Detecting installed agents…\n")

    summaries:      list[dict]            = []
    skipped_agents: list[tuple[str, str]] = []

    for agent_name, config in AGENT_MAP.items():
        is_installed, detail = config["detect"]()

        if not is_installed:
            console.print(
                f"  [dim]⏭  {agent_name:<28}[/] [red]not detected[/]  [dim]{detail}[/]"
            )
            skipped_agents.append((agent_name, detail))
            continue

        console.print(
            f"  [bold green]✔[/]  [bold]{agent_name}[/]  [dim]{detail}[/]\n"
            f"       [dim]→ installing into[/] [cyan]{config['instruction_file'].parent}[/]"
        )
        summary = install_agent(agent_name, config)
        summaries.append(summary)
        console.print()

    # ── Step 3: summary + persistence ────────────────────────────────────────
    console.print("[bold blue]Step 3/3[/] Generating summary…")
    render_summary(summaries, skipped_agents)

    # Derive overall status from all agent results
    all_errors   = [e for s in summaries for e in s["errors"]]
    all_installed = [i for s in summaries for i in s["installed"]]
    if not summaries:
        overall_status = "failure"          # nothing was processed at all
    elif all_errors and not all_installed:
        overall_status = "failure"          # every action failed
    elif all_errors:
        overall_status = "partial"          # some succeeded, some failed
    else:
        overall_status = "success"

    console.print("[bold blue]Persisting results…[/]")
    persist_to_config(summaries, skipped_agents)
    write_log_entry(summaries, skipped_agents, overall_status)
    console.print()