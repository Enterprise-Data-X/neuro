import os
from typing import List


def load_rule_files(project_path: str) -> List[str]:
    rules_path = os.path.join(project_path, ".neuro/rules")

    if not os.path.exists(rules_path):
        return []

    files = []
    for f in os.listdir(rules_path):
        if f.endswith(".md"):
            files.append(os.path.join(rules_path, f))

    return files


def parse_rule_file(file_path: str) -> str:
    """
    Converts markdown rules into structured prompt instructions.
    Focuses on MUST / MUST NOT / SHOULD
    """
    lines = []
    with open(file_path, "r") as f:
        for line in f.readlines():
            line = line.strip()

            if not line:
                continue

            # Keep only enforceable lines
            if any(keyword in line for keyword in ["MUST", "MUST NOT", "SHOULD"]):
                lines.append(line)

    return "\n".join(lines)


def build_policy_prompt(project_path: str) -> str:
    rule_files = load_rule_files(project_path)

    fragments = []

    for file in rule_files:
        content = parse_rule_file(file)

        if content:
            fragments.append(f"# Rules from {os.path.basename(file)}\n{content}")

    return "\n\n".join(fragments)

def build_system_prompt(project_path: str) -> str:
    policy = build_policy_prompt(project_path)

    return f"""
You are Neuro AI Agent.

You MUST follow all rules below strictly.
You are NOT allowed to deviate.

{policy}

You act as a Translator, not a Creator.
"""