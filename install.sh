#!/bin/bash
set -e

# ─── Helper Functions ────────────────────────────────────────────────────────

sync_folder() {
  local SRC="$1"
  local DEST="$2"
  local LABEL="$3"

  if [ -d "$SRC" ]; then
    echo "  🔄 Copying $LABEL..."
    mkdir -p "$DEST"
    cp -r "$SRC/." "$DEST/"
    echo "  ✅ $LABEL synced."
  else
    echo "  ⏭️  No $LABEL folder found, skipping."
  fi
}

sync_common() {
  local REPO_DIR="$1"
  local NEURO_HOME="$2"
  local COMMON_DIR="$REPO_DIR/_common"

  if [ ! -d "$COMMON_DIR" ]; then
    echo "❌ _common directory not found at $COMMON_DIR"
    exit 1
  fi

  echo "📦 Syncing _common assets into neuro home..."

  sync_folder "$COMMON_DIR/skills" "$NEURO_HOME/skills" "skills"
  sync_folder "$COMMON_DIR/tools"  "$NEURO_HOME/tools"  "tools"
  sync_folder "$COMMON_DIR/hooks"  "$NEURO_HOME/hooks"  "hooks"

  echo "✅ _common sync complete."
}

sync_persona() {
  local REPO_DIR="$1"
  local NEURO_HOME="$2"
  local PERSONA_DIR="$REPO_DIR/_persona"

  if [ ! -d "$PERSONA_DIR" ]; then
    echo "⚠️  No _persona folder found in repository, skipping persona sync."
    return
  fi

  # List available roles from folder names
  local available_roles
  available_roles=$(ls -d "$PERSONA_DIR"/*/  2>/dev/null | xargs -I{} basename {} | tr '\n' ', ' | sed 's/,$//')

  if [ -z "$available_roles" ]; then
    echo "⚠️  No roles found inside _persona, skipping persona sync."
    return
  fi

  echo ""
  echo "👥 Persona Selection"
  echo "   The '_persona' folder contains role/team-specific assets such as skills, tools,"
  echo "   and hooks. Each subfolder represents a distinct role or team (e.g. 'developer',"
  echo "   'devops', 'analyst'). Selecting a persona will copy its assets into your neuro home."
  echo ""
  echo "   Available roles: $available_roles"
  echo ""

  local max_attempts=3
  local attempt=0
  local role=""

  while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt + 1))

    read -p "   Enter your role/team name: " role
    role="${role// /_}"  # normalise spaces to underscores

    if [ -z "$role" ]; then
      echo "  ❌ No input provided. Please enter a role name."
    elif [ -d "$PERSONA_DIR/$role" ]; then
      echo "  ✅ Persona '$role' found."
      break
    else
      remaining=$((max_attempts - attempt))
      if [ $remaining -gt 0 ]; then
        echo "  ❌ Role '$role' not found. $remaining attempt(s) remaining."
        echo "     Available roles: $available_roles"
      else
        echo "  ❌ Role '$role' not found. No attempts remaining, skipping persona sync."
        return
      fi
    fi

    role=""
  done

  if [ -z "$role" ]; then
    return
  fi

  echo "📦 Syncing persona '$role' assets into neuro home..."

  sync_folder "$PERSONA_DIR/$role/skills" "$NEURO_HOME/skills" "skills"
  sync_folder "$PERSONA_DIR/$role/tools"  "$NEURO_HOME/tools"  "tools"
  sync_folder "$PERSONA_DIR/$role/hooks"  "$NEURO_HOME/hooks"  "hooks"

  echo "✅ Persona '$role' sync complete."
}

# ─── 1. Define Paths ─────────────────────────────────────────────────────────

NEURO_HOME="$HOME/.neuro"
INSTALL_SRC="$(pwd)"

echo
if ! command -v git >/dev/null 2>&1; then
  echo "❌ git is not installed or not available in PATH. Please install git and try again."
  exit 1
fi

# ─── 2. Validate Repository ──────────────────────────────────────────────────

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

# ─── 3. Clean Up Previous Installation ───────────────────────────────────────

echo "🧹 Cleaning up previous installation..."

pkill -f "neuro heartbeat" || true
rm -rf "$NEURO_HOME"
sudo rm -f /usr/local/bin/neuro
hash -r

echo "✨ Fresh environment ready. Starting installation..."

# ─── 4. Create Directory Structure ───────────────────────────────────────────

mkdir -p "$NEURO_HOME/skills"
mkdir -p "$NEURO_HOME/hooks"
mkdir -p "$NEURO_HOME/tools"
# mkdir -p "$NEURO_HOME/workspace"
mkdir -p "$NEURO_HOME/.repo"
# ─── 5. Create config.json ───────────────────────────────────────────────────

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
  ]
}
EOF
fi

# ─── 6. Move Repository & Validate Structure ─────────────────────────────────

if [ -n "$TEMPLATE_REPO_URL" ]; then
  echo "📥 Moving validated template repository into $repo_dir..."
  rm -rf "$repo_dir"
  mkdir -p "$(dirname "$repo_dir")"
  mv "$TMP_CLONE_DIR" "$repo_dir"
  echo "✅ Template repository moved to $repo_dir"

  if [ ! -d "$repo_dir/_common" ]; then
    echo "❌ Required folder '_common' not found in the repository."
    echo "   Please ensure your template repository contains a '_common' folder and try again."
    rm -rf "$repo_dir"
    exit 1
  fi

  if [ ! -d "$repo_dir/_persona" ]; then
    echo "⚠️  Warning: Optional folder '_persona' was not found in the repository."
  fi

  echo "✅ Repository structure validated."

  # Sync _common assets into neuro home
  sync_common "$repo_dir" "$NEURO_HOME"

  # Sync _persona assets into neuro home
  sync_persona "$repo_dir" "$NEURO_HOME"
fi

# ─── 7. Install Python Package & Global CLI ──────────────────────────────────

python3 -m venv "$NEURO_HOME/.venv"
"$NEURO_HOME/.venv/bin/pip" install --upgrade pip
"$NEURO_HOME/.venv/bin/pip" install -e "$INSTALL_SRC"
sudo ln -sf "$NEURO_HOME/.venv/bin/neuro" /usr/local/bin/neuro
hash -r


sudo rm -rf $NEURO_HOME/.repo

echo "✅ Installation Complete."