import os
from typing import Dict

GLOBAL_SKILLS = os.path.expanduser("~/.neuro/skills")


def list_skills() -> Dict[str, str]:
    """
    Returns:
    {
      "skill_name": "/full/path/to/SKILL.md"
    }
    """
    skills = {}

    if not os.path.exists(GLOBAL_SKILLS):
        return skills

    for folder in os.listdir(GLOBAL_SKILLS):
        skill_path = os.path.join(GLOBAL_SKILLS, folder)

        if not os.path.isdir(skill_path):
            continue

        skill_file = os.path.join(skill_path, "SKILL.md")

        if os.path.exists(skill_file):
            skills[folder] = skill_file

    return skills


def load_skill(skill_name: str) -> str:
    skills = list_skills()

    if skill_name not in skills:
        raise ValueError(f"Skill '{skill_name}' not found")

    with open(skills[skill_name], "r") as f:
        return f.read()
    

def build_skill_prompt(skill_name: str) -> str:
    content = load_skill(skill_name)

    return f"""
# Skill: {skill_name}

{content}
"""