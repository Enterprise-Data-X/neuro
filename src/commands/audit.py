import os
from ..core import project
from ..services import audit_engine


def run():
    cwd = os.getcwd()

    if not project.is_initialized(cwd):
        print("❌ Neuro is not initialized. Run `neuro init` first.")
        return

    settings = project.get_settings(cwd)

    audit_file, result = audit_engine.run_audit(cwd)

    print(f"✅ Audit generated: {audit_file}")

    project.log_execution(settings, "neuro audit", True, "Audit completed")