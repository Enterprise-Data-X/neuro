import sys
import subprocess
import os
from neuro.heartbeat import start_heartbeat
from neuro.tui import start_tui

def main():
    # Get the command-line arguments
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Resolve the absolute path to the project root 
    # This ensures scripts like update_neuro.sh can be found even if the user is in ~/Documents
    package_dir = os.path.dirname(os.path.abspath(__file__)) # neuro/ directory
    project_root = os.path.dirname(package_dir)             # neuro-installer/ directory

    if cmd == "heartbeat":
        print("💓 Heartbeat started... (Ctrl+C to stop)")
        start_heartbeat()

    elif cmd == "update":
        update_script = os.path.join(project_root, 'update_neuro.sh')
        if os.path.exists(update_script):
            print(f"🚀 Running update from {update_script}...")
            # Use project_root as the working directory so the script can find its git context
            subprocess.run(['bash', update_script], cwd=project_root)
        else:
            print(f"❌ Error: Could not find update script at {update_script}", file=sys.stderr)

    elif cmd == "log-level":
        # Placeholder for your JSON update logic
        print("🔧 Log level configuration...")
        pass

    elif cmd == "start":
        print("🖥️ Starting Neuro TUI...")
        start_tui()

    else:
        print("Usage: neuro [heartbeat|update|log-level|start]")

if __name__ == "__main__":
    main()