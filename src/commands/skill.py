def execute(args: list[str]) -> str:
    if not args:
        return "🛠️ Available Skills: [monitor, backup, deploy]. Use '/skill <name>' to run."

    skill_name = args[0].lower()
    return f"🛠️ Skill '{skill_name}' is not configured yet."
