#!/bin/bash
set -e

# 1. Define Paths
NEURO_HOME="$HOME/.neuro"
INSTALL_SRC="$(pwd)"

echo "🧹 Cleaning up previous installation..."

# Kill any running heartbeat processes associated with this user
pkill -f "neuro heartbeat" || true

# Remove the entire directory and the global symlink
rm -rf "$NEURO_HOME"
sudo rm -f /usr/local/bin/neuro

# Clear the shell's command hash cache
hash -r

echo "✨ Fresh environment ready. Starting installation..."

# 2. Create Directory Structure (Fresh)
mkdir -p "$NEURO_HOME/scripts"
mkdir -p "$NEURO_HOME/skills"
mkdir -p "$NEURO_HOME/agents"
mkdir -p "$NEURO_HOME/logs"


# 3. Copy your local scripts folder to ~/.neuro/scripts
# We use -r for recursive and delete existing to ensure a clean copy
if [ -d "$INSTALL_SRC/neuro/scripts" ]; then
    echo "📂 Copying scripts to $NEURO_HOME/scripts..."
    rm -rf "$NEURO_HOME/scripts"
    cp -r "$INSTALL_SRC/neuro/scripts" "$NEURO_HOME/scripts"
    # Ensure they are executable
    chmod -R +x "$NEURO_HOME/scripts"
else
    echo "⚠️ Warning: Source scripts folder not found at $INSTALL_SRC/neuro/scripts"
fi

# 4. Create default config.json with full command structure
if [ ! -f "$NEURO_HOME/config.json" ]; then
    echo "📝 Configuring default commands in config.json..."
    cat <<EOF > "$NEURO_HOME/config.json"
{
  "version": "1.0.0",
  "loglevel": "Info",
  "commands": [
    {
      "trigger": "/policies",
      "type": "group",
      "description": "Manage neuro policies",
      "options": [
        {
          "name": "list",
          "type": "module",
          "action": "neuro.commands.policies.list"
        },
        {
          "name": "add",
          "type": "script",
          "action": "neuro.commands.policies.add"
        },
        {
          "name": "remove",
          "type": "script",
          "action": "neuro.commands.policies.remove"
        }
      ]
    },
    {
      "trigger": "/skills",
      "type": "group",
      "description": "Manage neuro skills",
      "options": [
        {
          "name": "list",
          "type": "module",
          "action": "neuro.commands.skills.list_all"
        },
        {
          "name": "add",
          "type": "script",
          "action": "azuredevops/install-skill-from-azuredevops.py"
        },
        {
          "name": "remove",
          "type": "script",
          "action": "azuredevops/install-skill-from-azuredevops.py"
        },
        {
          "name": "apply",
          "type": "module",
          "action": "neuro.commands.skills.apply_skill"
        }
      ]
    },
    {
      "trigger": "/plugins",
      "type": "group",
      "description": "Manage neuro plugins",
      "options": [
        {
          "name": "list",
          "type": "module",
          "action": "neuro.commands.plugins.list"
        },
        {
          "name": "install",
          "type": "module",
          "action": "neuro.commands.plugins.install"
        },
        {
          "name": "remove",
          "type": "module",
          "action": "neuro.commands.plugins.remove"
        }
      ]
    },
    {
      "trigger": "/agent",
      "type": "group",
      "description": "Get current agent",
      "options": [
        {
          "name": "config",
          "type": "module",
          "action": "neuro.commands.agent.config"
        },
        {
          "name": "add",
          "type": "module",
          "action": "neuro.commands.agent.add"
        },
        {
          "name": "remove",
          "type": "module",
          "action": "neuro.commands.agent.remove"
        }
      ]
    },
    {
      "trigger": "/agents",
      "type": "group",
      "description": "Get current configured agents",
      "options": [
        {
          "name": "config",
          "type": "module",
          "action": "neuro.commands.agents.config"
        },
        {
          "name": "remove",
          "type": "module",
          "action": "neuro.commands.agents.remove"
        }
      ]
    },
    {
      "trigger": "/templates",
      "type": "group",
      "description": "Manage templates for neuro agent",
      "options": [
        {
          "name": "add",
          "type": "module",
          "action": "neuro.commands.templates.add"
        },
        {
          "name": "list",
          "type": "module",
          "action": "neuro.commands.templates.list"
        },
        {
          "name": "remove",
          "type": "module",
          "action": "neuro.commands.templates.remove"
        }
      ]
    }
  ]
}
EOF
fi
# 5. Refresh the venv and symlink (as done before)
python3 -m venv "$NEURO_HOME/.venv"
"$NEURO_HOME/.venv/bin/pip" install --upgrade pip
"$NEURO_HOME/.venv/bin/pip" install -e "$INSTALL_SRC"
sudo ln -sf "$NEURO_HOME/.venv/bin/neuro" /usr/local/bin/neuro

echo "✅ Installation Complete."