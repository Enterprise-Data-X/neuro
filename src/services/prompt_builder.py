from neuro.services.policy_mapper import build_system_prompt
from neuro.services.skill_loader import build_skill_prompt


def build_full_prompt(project_path: str, skill_name: str, user_input: str) -> str:
    system = build_system_prompt(project_path)
    skill = build_skill_prompt(skill_name)

    return f"""
{system}

{skill}

# User Request
{user_input}
"""