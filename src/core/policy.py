import os
import re
from typing import Dict, List


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