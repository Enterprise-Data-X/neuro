from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

NEURO_HOME = Path.home() / ".neuro"


@dataclass
class SkillInfo:
    name: str
    path: Path
    category: Literal["skill", "tool"]
    source: str | None
    is_symlink: bool
    has_skill_md: bool


# ── config helpers ────────────────────────────────────────────────────────────

def _load_config() -> dict:
    p = NEURO_HOME / "config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(data: dict) -> None:
    p = NEURO_HOME / "config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── public API ────────────────────────────────────────────────────────────────

def list_items() -> list[SkillInfo]:
    """Return all skills and tools currently in ~/.neuro/."""
    config = _load_config()
    sources: dict = config.get("skill_sources", {})
    items: list[SkillInfo] = []

    for bucket in ("skills", "tools"):
        base = NEURO_HOME / bucket
        if not base.exists():
            continue
        for p in sorted(base.iterdir()):
            key = f"{bucket}/{p.name}"
            items.append(SkillInfo(
                name=p.name,
                path=p,
                category="skill" if bucket == "skills" else "tool",
                source=sources.get(key),
                is_symlink=p.is_symlink(),
                has_skill_md=p.is_dir() and (p / "SKILL.md").exists(),
            ))
    return items


def get_item(name: str) -> SkillInfo | None:
    for item in list_items():
        if item.name == name:
            return item
    return None


def record_source(bucket: str, name: str, source: str) -> None:
    config = _load_config()
    sources: dict = config.setdefault("skill_sources", {})
    sources[f"{bucket}/{name}"] = source
    _save_config(config)


def remove_item(bucket: str, name: str) -> tuple[bool, str]:
    target = NEURO_HOME / bucket / name
    if not target.exists() and not target.is_symlink():
        return False, f"'{name}' not found in {bucket}"
    try:
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    except OSError as e:
        return False, str(e)

    config = _load_config()
    sources: dict = config.get("skill_sources", {})
    sources.pop(f"{bucket}/{name}", None)
    config["skill_sources"] = sources
    _save_config(config)
    return True, f"Removed {bucket}/{name}"


def install_skill_content(name: str, content: str) -> Path:
    """Write content to ~/.neuro/skills/<name>/SKILL.md."""
    skill_dir = NEURO_HOME / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def install_from_local(src: Path, bucket: str) -> tuple[bool, str]:
    """Copy a local path into ~/.neuro/<bucket>/."""
    dest = NEURO_HOME / bucket / src.name
    if dest.exists():
        return False, f"'{src.name}' already exists in {bucket}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        return True, str(dest)
    except Exception as e:
        return False, str(e)


def install_from_git(url: str, skill_name: str | None = None) -> tuple[bool, str, str]:
    """
    Clone a git URL and install detected skill(s) to ~/.neuro/skills/.
    Returns (ok, installed_name, message).
    """
    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run(
                ["git", "clone", "--depth=1", "--quiet", url, tmp],
                check=True, capture_output=True, text=True, timeout=60,
            )
        except subprocess.CalledProcessError as e:
            return False, "", f"git clone failed: {e.stderr.strip() or 'unknown error'}"
        except subprocess.TimeoutExpired:
            return False, "", "git clone timed out (>60s)"

        tmp_path = Path(tmp)

        # Determine which directory to install
        if skill_name:
            candidates = [
                tmp_path / "skills" / skill_name,
                tmp_path / skill_name,
            ]
        else:
            # Find first directory containing SKILL.md
            candidates = [
                p for p in tmp_path.rglob("SKILL.md")
                if p.parent != tmp_path
            ]
            candidates = [p.parent for p in candidates] or [tmp_path]

        src = next((c for c in candidates if (c / "SKILL.md").exists()), None)
        if src is None:
            # Fallback: install whole repo as a skill named after the repo
            repo_name = url.rstrip("/").split("/")[-1].removesuffix(".git")
            src = tmp_path
            install_name = skill_name or repo_name
        else:
            install_name = skill_name or src.name

        dest = NEURO_HOME / "skills" / install_name
        if dest.exists():
            return False, install_name, f"'{install_name}' already exists in skills"
        try:
            shutil.copytree(src, dest)
        except Exception as e:
            return False, install_name, str(e)

    return True, install_name, str(dest)
