#!/bin/bash
set -e

# ─── 1. Constants & Styling ──────────────────────────────────────────────────
NEURO_HOME="$HOME/.neuro"
INSTALL_SRC="$(pwd)"
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' 

echo -e "${BOLD}${CYAN}🧠 Neuro AI Framework: Developer & BA Setup${NC}"
echo -e "------------------------------------------------"

# ─── 2. Helper Functions ─────────────────────────────────────────────────────

sync_folder() {
  local SRC="$1"
  local DEST="$2"
  local LABEL="$3"
  if [ -d "$SRC" ]; then
    echo -e "  ${GREEN}🔄 Syncing $LABEL...${NC}"
    mkdir -p "$DEST"
    cp -r "$SRC/." "$DEST/"
  fi
}

# ─── 3. Reinstall Guard ──────────────────────────────────────────────────────

if [ -d "$NEURO_HOME" ]; then
  echo -e "${YELLOW}⚠️  Existing Neuro installation found at $NEURO_HOME.${NC}"
  while true; do
    read -p "   Reinstall? This will reset your config. [y/n]: " confirm
    case $confirm in
      [Yy]*) 
        sudo rm -f /usr/local/bin/neuro
        rm -rf "$NEURO_HOME"
        break ;;
      [Nn]*) echo "Installation aborted."; exit 0 ;;
      *) echo "Please answer y or n." ;;
    esac
  done
fi

mkdir -p "$NEURO_HOME"/{skills,hooks,tools,template}

# ─── 4. Dynamic Provider & Model Selection ───────────────────────────────────

echo -e "\n${BOLD}🤖 Step 1: Select AI Agent Type${NC}"
echo -e "   1) Claude Pro CLI  -> Best for Devs  (Claude Code subscription)"
echo -e "   2) Ollama (Local)  -> local agent    (runs offline, free)"
echo -e "   3) Codex           -> Cloud API      (OpenAI API key required)"
echo -e "   4) GitHub Copilot  -> GitHub Models  (GITHUB_TOKEN required)"

while true; do
  read -p "   Selection (1-4): " p_choice
  case $p_choice in
    1)
      SELECTED_PROVIDER="claude"
      if ! command -v claude >/dev/null 2>&1; then
          echo -e "   ${YELLOW}📥 Installing Claude Code CLI via npm...${NC}"
          sudo npm install -g @anthropic-ai/claude-code
      fi
      echo -e "\n   ${BOLD}🎯 Step 2: Select Claude Model${NC}"
      echo "   1) claude-3-7-sonnet-latest"
      echo "   2) claude-4-opus-latest"
      while true; do
        read -p "   Select (1-2) [default 1]: " m_c
        m_c=${m_c:-1}
        [[ "$m_c" == "1" ]] && { SELECTED_MODEL="claude-3-7-sonnet-latest"; break; }
        [[ "$m_c" == "2" ]] && { SELECTED_MODEL="claude-4-opus-latest"; break; }
        echo "Invalid selection."
      done
      break ;;
    2)
      SELECTED_PROVIDER="ollama"
      if ! command -v ollama >/dev/null 2>&1; then
          echo -e "${RED}❌ Ollama not found. Install from ollama.com first.${NC}"
          exit 1
      fi
      echo -e "   ${CYAN}🔍 Fetching local Ollama models...${NC}"
      mapfile -t models < <(ollama list | awk 'NR>1 {print $1}')
      if [ ${#models[@]} -eq 0 ]; then
          echo -e "${RED}❌ No models found. Run 'ollama pull llama3' first.${NC}"
          exit 1
      fi
      for i in "${!models[@]}"; do echo "   $((i+1))) ${models[$i]}"; done
      while true; do
        read -p "   Select model (1-${#models[@]}): " m_idx
        if [[ "$m_idx" =~ ^[0-9]+$ ]] && [ "$m_idx" -ge 1 ] && [ "$m_idx" -le "${#models[@]}" ]; then
            SELECTED_MODEL="${models[$((m_idx-1))]}"
            break
        fi
        echo "Invalid number."
      done
      break ;;
    3)
      SELECTED_PROVIDER="codex"
      while true; do
        read -sp "   🔑 Enter Codex (OpenAI) API Key: " CODEX_API_KEY
        if [ -n "$CODEX_API_KEY" ]; then break; fi
        echo -e "\n${RED}   API Key cannot be empty.${NC}"
      done
      echo -e "\n   ${CYAN}🔍 Fetching live models from Codex...${NC}"
      
      # Use Python to validate key and fetch models
      FETCH_RESULT=$(python3 - <<EOF
import urllib.request, json, sys
try:
    req = urllib.request.Request("https://api.openai.com/v1/models")
    req.add_header("Authorization", "Bearer $CODEX_API_KEY")
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read())
        m_list = sorted([m['id'] for m in data['data'] if 'gpt' in m['id']])[:10]
        if not m_list: raise Exception("No GPT models")
        for i, name in enumerate(m_list): print(f"   {i+1}) {name}", file=sys.stderr)
        print("SUCCESS")
        print("\n".join(m_list))
except:
    print("FAILED")
EOF
)
      if [[ $(echo "$FETCH_RESULT" | head -n 1) == "FAILED" ]]; then
          echo -e "${RED}   Failed to fetch models. API key might be invalid.${NC}"
          SELECTED_MODEL="gpt-4o" # Safe fallback for Codex
      else
          mapfile -t c_models < <(echo "$FETCH_RESULT" | sed -n '2,$p')
          while true; do
            read -p "   Select number: " c_idx
            if [[ "$c_idx" =~ ^[0-9]+$ ]] && [ "$c_idx" -ge 1 ] && [ "$c_idx" -le "${#c_models[@]}" ]; then
                SELECTED_MODEL="${c_models[$((c_idx-1))]}"
                break
            fi
            echo "Invalid selection."
          done
      fi
      break ;;
    4)
      SELECTED_PROVIDER="copilot"
      if [ -z "$GITHUB_TOKEN" ]; then
        read -sp "   🔑 Enter GitHub Personal Access Token: " GITHUB_TOKEN
        echo
        if [ -z "$GITHUB_TOKEN" ]; then
          echo -e "${RED}❌ GitHub Token is required for Copilot.${NC}"
          exit 1
        fi
      else
        echo -e "   ${GREEN}✅ GITHUB_TOKEN found in environment.${NC}"
      fi
      echo -e "\n   ${BOLD}🎯 Step 2: Select GitHub Model${NC}"
      echo "   1) openai/gpt-4o"
      echo "   2) openai/gpt-4o-mini"
      echo "   3) meta/llama-3.3-70b-instruct"
      while true; do
        read -p "   Select (1-3) [default 1]: " m_c
        m_c=${m_c:-1}
        [[ "$m_c" == "1" ]] && { SELECTED_MODEL="openai/gpt-4o"; break; }
        [[ "$m_c" == "2" ]] && { SELECTED_MODEL="openai/gpt-4o-mini"; break; }
        [[ "$m_c" == "3" ]] && { SELECTED_MODEL="meta/llama-3.3-70b-instruct"; break; }
        echo "Invalid selection."
      done
      break ;;
    *) echo "Please enter 1, 2, 3, or 4." ;;
  esac
done

# ─── 5. Repository & Persona Sync ───────────────────────────────────────────

echo -e "\n${BOLD}🔗 Step 3: Skill Template Repository${NC}"
while true; do
  read -p "   Enter Template Repo URL (Git): " TEMPLATE_REPO_URL
  if [[ -z "$TEMPLATE_REPO_URL" ]]; then 
    echo "URL cannot be empty."
    continue 
  fi
  TMP_CLONE_DIR="$(mktemp -d)"
  if git clone "$TEMPLATE_REPO_URL" "$TMP_CLONE_DIR" --quiet; then
    repo_name="$(basename "$TEMPLATE_REPO_URL" .git)"
    repo_dir="$NEURO_HOME/template/$repo_name"
    mv "$TMP_CLONE_DIR" "$repo_dir"
    echo -e "   ${GREEN}✅ Repository Cloned.${NC}"
    break
  else
    echo -e "   ${RED}❌ Git clone failed. Check the URL and your credentials.${NC}"
    rm -rf "$TMP_CLONE_DIR"
  fi
done

# Sync assets
[[ -d "$repo_dir/_common" ]] && {
    sync_folder "$repo_dir/_common/skills" "$NEURO_HOME/skills" "common-skills"
    sync_folder "$repo_dir/_common/tools"  "$NEURO_HOME/tools"  "common-tools"
}

PERSONA_DIR="$repo_dir/_persona"
SELECTED_ROLE="default"
if [ -d "$PERSONA_DIR" ]; then
    echo -e "\n${BOLD}👥 Step 4: Choose your Role Persona${NC}"
    roles=($(ls -d "$PERSONA_DIR"/*/ 2>/dev/null | xargs -I{} basename {}))
    if [ ${#roles[@]} -gt 0 ]; then
        for i in "${!roles[@]}"; do echo "   $((i+1))) ${roles[$i]}"; done
        while true; do
            read -p "   Selection (1-${#roles[@]}): " r_idx
            if [[ "$r_idx" =~ ^[0-9]+$ ]] && [ "$r_idx" -ge 1 ] && [ "$r_idx" -le "${#roles[@]}" ]; then
                SELECTED_ROLE="${roles[$((r_idx-1))]}"
                sync_folder "$PERSONA_DIR/$SELECTED_ROLE/skills" "$NEURO_HOME/skills" "role-skills"
                sync_folder "$PERSONA_DIR/$SELECTED_ROLE/tools"  "$NEURO_HOME/tools"  "role-tools"
                break
            fi
            echo "Invalid selection."
        done
    fi
fi

# ─── 5b. Agent-specific Skills ───────────────────────────────────────────────
# Template repos may ship provider-specific skills under _agents/<provider>/.
# e.g.  _agents/claude/skills/   _agents/ollama/skills/

AGENT_SKILL_DIR="$repo_dir/_agents/$SELECTED_PROVIDER"
if [ -d "$AGENT_SKILL_DIR" ]; then
    echo -e "\n${BOLD}🎯 Step 5: Syncing ${SELECTED_PROVIDER}-specific skills & tools${NC}"
    sync_folder "$AGENT_SKILL_DIR/skills" "$NEURO_HOME/skills" "${SELECTED_PROVIDER}-skills"
    sync_folder "$AGENT_SKILL_DIR/tools"  "$NEURO_HOME/tools"  "${SELECTED_PROVIDER}-tools"
else
    echo -e "  ${CYAN}ℹ  No provider-specific assets for '${SELECTED_PROVIDER}' in this template.${NC}"
fi

# ─── 6. Finalizing Configuration ─────────────────────────────────────────────

python3 - <<PYEOF
import json, os

# Determine api_key to persist (codex/copilot only)
provider  = "${SELECTED_PROVIDER}"
api_key   = ""
if provider == "codex":
    api_key = os.environ.get("CODEX_API_KEY", "")
elif provider == "copilot":
    api_key = "${GITHUB_TOKEN}"

agent_cfg = {"provider": provider, "model": "${SELECTED_MODEL}"}
if api_key:
    agent_cfg["api_key"] = api_key

config = {
    "version": "1.0.0",
    "agent": agent_cfg,
    "templateRepository": [
        {"url": "${TEMPLATE_REPO_URL}", "name": "${repo_name}", "path": "${repo_dir}"}
    ],
    "role": "${SELECTED_ROLE}",
}
with open("${NEURO_HOME}/config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    f.write("\n")
PYEOF

echo -e "\n${BOLD}📦 Installing Neuro Python Environment...${NC}"
python3 -m venv "$NEURO_HOME/.venv"
"$NEURO_HOME/.venv/bin/pip" install --upgrade pip --quiet
"$NEURO_HOME/.venv/bin/pip" install "$INSTALL_SRC" --quiet

# Install provider-specific python SDK
echo -e "  ${CYAN}📦 Installing AI provider SDK...${NC}"
case "$SELECTED_PROVIDER" in
  claude)    "$NEURO_HOME/.venv/bin/pip" install anthropic --quiet ;;
  ollama)    "$NEURO_HOME/.venv/bin/pip" install ollama    --quiet ;;
  codex)     "$NEURO_HOME/.venv/bin/pip" install openai    --quiet ;;
  copilot)   "$NEURO_HOME/.venv/bin/pip" install openai    --quiet ;;
esac

echo -e "${BOLD}🔗 Creating global 'neuro' command...${NC}"
sudo ln -sf "$NEURO_HOME/.venv/bin/neuro" /usr/local/bin/neuro

echo -e "\n${GREEN}${BOLD}✅ INSTALLATION SUCCESSFUL!${NC}"
echo -e "🚀 Type ${BOLD}'neuro'${NC} to start using ${CYAN}$SELECTED_PROVIDER ($SELECTED_MODEL)${NC}."