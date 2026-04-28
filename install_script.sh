#!/bin/bash
set -e

# 1. Define Paths
NEURO_HOME="$HOME/.neuro"
INSTALL_SRC="$(pwd)"

echo
if ! command -v git >/dev/null 2>&1; then
  echo "❌ git is not installed or not available in PATH. Please install git and try again."
  exit 1
fi

while true; do
  read -p "Template Repository HTTPS Url or SSH: " TEMPLATE_REPO_URL
  TEMPLATE_REPO_URL="${TEMPLATE_REPO_URL%/}"

  if [ -z "$TEMPLATE_REPO_URL" ]; then
    echo "❌ No repository URL provided. Please enter a valid URL."
    continue
  fi

  TMP_CLONE_DIR="$(mktemp -d)"
  if git clone "$TEMPLATE_REPO_URL" "$TMP_CLONE_DIR" >/dev/null 2>&1; then
    echo "✅ Repository URL validated."
    repo_name="$(basename "$TEMPLATE_REPO_URL")"
    repo_name="${repo_name%.git}"
    repo_dir="$NEURO_HOME/.repo/$repo_name"
    break
  fi

  echo "❌ Invalid repository URL or clone failed. Please provide a valid HTTPS or SSH repository URL."
  rm -rf "$TMP_CLONE_DIR"
done

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
mkdir -p "$NEURO_HOME/skills"
mkdir -p "$NEURO_HOME/logs"
mkdir -p "$NEURO_HOME/hooks"
mkdir -p "$NEURO_HOME/tools"
mkdir -p "$NEURO_HOME/workspace"
mkdir -p "$NEURO_HOME/.repo"



# 3. Create default config.json with full command structure
if [ ! -f "$NEURO_HOME/config.json" ]; then
    echo "📝 Configuring default commands in config.json..."
    cat <<EOF > "$NEURO_HOME/config.json"
{
  "version": "1.0.0",
  "loglevel": "Info",
  "templateRepository": [
    {
      "url": "${TEMPLATE_REPO_URL}",
      "name": "${repo_name}",
      "path": "${repo_dir}"
    }
  ],
  "commands": [
    {
      "trigger": "/config",
      "type": "group",
      "description": "Manage neuro config",
      "options": [
        {
          "name": "list",
          "type": "module",
          "action": "neuro.commands.config.list"
        },
        {
          "name": "add",
          "type": "script",
          "action": "neuro.commands.config.add"
        },
        {
          "name": "remove",
          "type": "script",
          "action": "neuro.commands.config.remove"
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
      "trigger": "/tools",
      "type": "group",
      "description": "Manage neuro tools",
      "options": [
        {
          "name": "list",
          "type": "module",
          "action": "neuro.commands.tools.list"
        },
        {
          "name": "install",
          "type": "module",
          "action": "neuro.commands.tools.install"
        },
        {
          "name": "remove",
          "type": "module",
          "action": "neuro.commands.tools.remove"
        }
      ]
    },
    {
      "trigger": "/hooks",
      "type": "group",
      "description": "Get current hooks",
      "options": [
        {
          "name": "config",
          "type": "module",
          "action": "neuro.commands.hooks.config"
        },
        {
          "name": "add",
          "type": "module",
          "action": "neuro.commands.hooks.add"
        },
        {
          "name": "remove",
          "type": "module",
          "action": "neuro.commands.hooks.remove"
        }
      ]
    },
    {
      "trigger": "/logs",
      "type": "group",
      "description": "Manage logs for neuro agent",
      "options": [
        {
          "name": "add",
          "type": "module",
          "action": "neuro.commands.logs.add"
        },
        {
          "name": "list",
          "type": "module",
          "action": "neuro.commands.logs.list"
        },
        {
          "name": "remove",
          "type": "module",
          "action": "neuro.commands.logs.remove"
        }
      ]
    }
  ]
}
EOF
fi

if [ -n "$TEMPLATE_REPO_URL" ]; then
  echo "📥 Moving validated template repository into $repo_dir..."
  rm -rf "$repo_dir"
  mkdir -p "$(dirname "$repo_dir")"
  mv "$TMP_CLONE_DIR" "$repo_dir"
  echo "✅ Template repository moved to $repo_dir"
fi

# 5. Refresh the venv and symlink (as done before)
python3 -m venv "$NEURO_HOME/.venv"
"$NEURO_HOME/.venv/bin/pip" install --upgrade pip
"$NEURO_HOME/.venv/bin/pip" install -e "$INSTALL_SRC"
sudo ln -sf "$NEURO_HOME/.venv/bin/neuro" /usr/local/bin/neuro

echo "✅ Installation Complete."