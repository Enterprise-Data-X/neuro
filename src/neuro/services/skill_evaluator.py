from __future__ import annotations

import difflib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from neuro.services.skill_manager import SkillInfo


@dataclass
class UpdateResult:
    skill: SkillInfo
    has_update: bool
    diff: str
    remote_content: str
    error: str | None = None


# ── helpers ───────────────────────────────────────────────────────────────────

def _local_content(info: SkillInfo) -> str:
    try:
        if info.has_skill_md:
            return (info.path / "SKILL.md").read_text(encoding="utf-8")
        if info.path.is_file():
            return info.path.read_text(encoding="utf-8")
    except OSError:
        pass
    return ""


def _fetch_remote(url: str, skill_name: str) -> tuple[str | None, str | None]:
    """Clone url into a temp dir and return content of the skill's SKILL.md."""
    tmp = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", url, tmp],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return None, f"git clone failed: {result.stderr.strip() or 'exit ' + str(result.returncode)}"
    except subprocess.TimeoutExpired:
        return None, "git clone timed out (>60s)"
    except FileNotFoundError:
        return None, "git not found in PATH"

    tmp_path = Path(tmp)
    for candidate in [
        tmp_path / "skills" / skill_name / "SKILL.md",
        tmp_path / skill_name / "SKILL.md",
        tmp_path / "SKILL.md",
    ]:
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8"), None
            except OSError as e:
                return None, str(e)

    return None, f"SKILL.md not found in remote for '{skill_name}'"


def _make_diff(local: str, remote: str, skill_name: str) -> str:
    return "".join(difflib.unified_diff(
        local.splitlines(keepends=True),
        remote.splitlines(keepends=True),
        fromfile=f"local/{skill_name}/SKILL.md",
        tofile=f"remote/{skill_name}/SKILL.md",
    ))


# ── public API ────────────────────────────────────────────────────────────────

def evaluate(info: SkillInfo) -> UpdateResult:
    """Compare local skill against its recorded remote source."""
    if not info.source:
        return UpdateResult(info, False, "", "", "No source URL recorded — cannot check for updates")

    local = _local_content(info)
    remote, err = _fetch_remote(info.source, info.name)

    if err:
        return UpdateResult(info, False, "", "", err)

    if local == remote:
        return UpdateResult(info, False, "", remote)

    return UpdateResult(
        skill=info,
        has_update=True,
        diff=_make_diff(local, remote, info.name),
        remote_content=remote,
    )


def evaluate_all(items: list[SkillInfo]) -> list[UpdateResult]:
    """Evaluate every item that has a recorded source URL."""
    return [evaluate(item) for item in items if item.source]


def apply_update(result: UpdateResult) -> tuple[bool, str]:
    """Write remote content back to the local SKILL.md."""
    info = result.skill
    if info.has_skill_md:
        target = info.path / "SKILL.md"
    elif info.path.is_file():
        target = info.path
    else:
        return False, f"Cannot resolve target path for '{info.name}'"
    try:
        target.write_text(result.remote_content, encoding="utf-8")
        return True, str(target)
    except OSError as e:
        return False, str(e)
