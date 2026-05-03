import os
import re
from typing import Dict, List

# ── standalone content validator (used during skill creation) ─────────────────

_FORBIDDEN_SHELL: list[str] = [
    r"rm\s+-[rf]{1,2}\b",
    r"\bsudo\b",
    r"chmod\s+777",
    r"curl\b[^|]*\|\s*bash",
    r"wget\b[^|]*\|\s*bash",
    r"eval\s*\$\(",
]

_SENSITIVE_DATA: list[str] = [
    r"\.env\b",
    r"\bsecrets?\b",
    r"\bcredentials?\b",
    r"private[-_]?key",
    r"-----BEGIN\s+\w+\s+PRIVATE KEY-----",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"password\s*=\s*\S",
    r"api[_-]key\s*=\s*\S",
]


def validate_skill_content(name: str, content: str) -> list[str]:
    """
    Check a skill name + content against Neuro policy rules.
    Returns a list of violation messages; empty list means clean.
    """
    issues: list[str] = []

    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,48}$", name):
        issues.append(
            f"Skill name '{name}' is invalid — use letters, digits, hyphens, "
            "underscores, start with a letter or digit, max 49 chars."
        )

    if not content.strip():
        issues.append("Content is empty.")
        return issues

    if len(content.split()) < 10:
        issues.append(
            "Content is too short (< 10 words). Provide a meaningful description and behavior."
        )

    for pattern in _FORBIDDEN_SHELL:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Forbidden shell pattern detected: `{pattern}`")

    for pattern in _SENSITIVE_DATA:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Sensitive data reference detected: `{pattern}`")

    return issues


# ── class-based policy (file/command enforcement) ─────────────────────────────

class Policy:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.rules_path = os.path.join(project_path, ".neuro/rules")
        self.constraints = {
            "must": [],
            "must_not": [],
            "should": []
        }

        self._load()

    # -----------------------------
    # Load + Parse Rules
    # -----------------------------
    def _load(self):
        if not os.path.exists(self.rules_path):
            return

        for file in os.listdir(self.rules_path):
            if file.endswith(".md"):
                self._parse_file(os.path.join(self.rules_path, file))

    def _parse_file(self, file_path: str):
        with open(file_path, "r") as f:
            for line in f.readlines():
                line = line.strip()

                if not line:
                    continue

                if "MUST NOT" in line:
                    self.constraints["must_not"].append(line)

                elif "MUST" in line:
                    self.constraints["must"].append(line)

                elif "SHOULD" in line:
                    self.constraints["should"].append(line)

    # -----------------------------
    # Public API
    # -----------------------------
    def summary(self) -> Dict[str, List[str]]:
        return self.constraints

    # -----------------------------
    # Enforcement Methods
    # -----------------------------
    def can_modify_file(self, file_path: str) -> bool:
        """
        Prevent restricted file access
        """
        restricted_patterns = [
            r"\.env",
            r"secrets?",
            r"config/production"
        ]

        for pattern in restricted_patterns:
            if re.search(pattern, file_path):
                return False

        return True

    def can_delete_file(self, file_path: str) -> bool:
        """
        Block destructive operations unless explicitly allowed
        """
        critical_paths = [
            "main.py",
            "app/",
            "core/"
        ]

        for cp in critical_paths:
            if cp in file_path:
                return False

        return True

    def validate_command(self, command: str) -> bool:
        """
        Control shell execution
        """
        forbidden = [
            "rm -rf",
            "sudo",
            "chmod 777"
        ]

        for f in forbidden:
            if f in command:
                return False

        return True

    # -----------------------------
    # Enforcement Wrapper
    # -----------------------------
    def enforce_file_write(self, file_path: str):
        if not self.can_modify_file(file_path):
            raise PermissionError(f"Modification not allowed: {file_path}")

    def enforce_file_delete(self, file_path: str):
        if not self.can_delete_file(file_path):
            raise PermissionError(f"Deletion not allowed: {file_path}")

    def enforce_command(self, command: str):
        if not self.validate_command(command):
            raise PermissionError(f"Command not allowed: {command}")