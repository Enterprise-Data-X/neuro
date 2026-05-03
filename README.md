# Neuro

> **Persona-Driven AI Alignment for Organisations.**

Neuro is a professional orchestration layer that synchronises AI agent behaviours across an entire organisation. It ensures that every developer's AI — whether in Cursor, Claude Code, or Copilot — operates with the same high-standard skills, tools, and persona defined by their specific role.

---

## Quick Start

```bash
# 1. Run the installer
sudo ./install.sh

# 2. Select your AI provider (Claude · Ollama · Codex · GitHub Copilot)
# 3. Connect your team's Skill Vault (Git repository URL)
# 4. Choose your role persona (architect · frontend · backend · security · …)

# Launch the interactive TUI
neuro
```

---

## Installation

### Requirements

| Requirement | Notes |
| :--- | :--- |
| Python 3.10+ | Used for the neuro package |
| Git | For cloning skill repositories |
| Node.js / npm | Only for Claude provider (`@anthropic-ai/claude-code`) |
| `sudo` access | For linking `/usr/local/bin/neuro` |

### Run the Installer

```bash
sudo ./install.sh
```

The installer guides you through:

1. **AI Provider** — choose which model powers your TUI chat
2. **Skill Vault** — clone your organisation's template repository. (Sample Github : https://github.com/Enterprise-Data-X/Neuro-Template)
    
3. **Persona** — select your role (filters which skills are installed)
4. **Python environment** — creates `~/.neuro/.venv` and installs all dependencies

### Providers

| Option | Provider | Requirements |
| :--- | :--- | :--- |
| 1 | Claude (CLI) | Claude Code subscription + `claude` binary |
| 2 | Ollama (local) | `ollama` installed and running |
| 3 | Codex / OpenAI | OpenAI API key |
| 4 | GitHub Copilot | `GITHUB_TOKEN` with model access |

---

## CLI Commands

### Core

| Command | Description |
| :--- | :--- |
| `neuro` | Launch the interactive TUI |
| `neuro init` | Detect installed agents and sync all skills/tools |
| `neuro status` | Show which agents are detected and what is installed |
| `neuro update` | Pull latest skills from the template repository |
| `neuro config` | View `~/.neuro/config.json` |
| `neuro config agent model <value>` | Update a config value |
| `neuro uninstall` | Remove all Neuro assets and the CLI binary |

### Agent Management

| Command | Description |
| :--- | :--- |
| `neuro agent update` | Interactively switch AI provider or model |
| `neuro agent status` | Show the currently active provider |

---

## TUI Commands

Launch the TUI with `neuro`, then use these slash commands:

| Command | Description |
| :--- | :--- |
| `/skills list` | View installed skills and tools |
| `/skills add <path\|url>` | Install a skill from a local path or Git URL |
| `/skills remove [name]` | Remove an installed skill |
| `/skills check [name]` | Check for updates and preview the diff |
| `/skills create` | Create a new skill (with policy validation) |
| `/skills update` | Re-install all skills from the template repository |
| `/agent` | Show the current AI provider |
| `/agent update` | Switch provider or model interactively |
| `/agent refresh` | Rebuild the agent context |
| `/agent clear` | Clear conversation history |
| `/init` | Run `neuro init` from within the TUI |
| `/status` | Show agent detection status |
| `/config [key value]` | View or update config values |
| `/clear` | Clear the screen |
| `/help` | Show this command list |
| `/exit` | Exit Neuro |

Any text that is not a slash command is sent to your configured AI provider as a chat message.

---

## Skill Vault Structure

Your organisation's template repository must follow this layout:

```
Neuro-Vault/
├── _common/                # Applied to every user
│   ├── skills/             # Universal .md skill directives
│   └── tools/              # Universal MCP / tool definitions
├── _persona/               # Role-based layers
│   ├── architect/
│   │   ├── skills/
│   │   └── tools/
│   ├── frontend/
│   ├── backend/
│   └── security/
└── _agents/                # Provider-specific skills
    ├── claude/
    │   └── skills/
    ├── ollama/
    └── copilot/
```

Layers are applied in order: `_common` → `_persona/<role>` → `_agents/<provider>`.

---

## Configuration

All settings are stored in `~/.neuro/config.json`:

```json
{
  "version": "1.0.0",
  "agent": {
    "provider": "claude",
    "model": "claude-opus-4-7"
  },
  "templateRepository": [
    {
      "url": "git@github.com:your-org/neuro-vault.git",
      "name": "neuro-vault",
      "path": "/home/user/.neuro/template/neuro-vault"
    }
  ],
  "role": "backend"
}
```

| Key | Description |
| :--- | :--- |
| `agent.provider` | Active chat provider (`claude` · `ollama` · `codex` · `copilot`) |
| `agent.model` | Model identifier passed to the provider |
| `agent.api_key` | Stored API key (codex / copilot) |
| `templateRepository` | One or more cloned skill vault repositories |
| `role` | Persona applied during `neuro init` |

---

## Uninstall

```bash
neuro uninstall
```

Removes all agent-installed skills, runs `pip uninstall neuro`, deletes `~/.neuro/`, and removes `/usr/local/bin/neuro`. Requires typing `yes` to confirm.

---

*Standardise the intent. Scale the expertise. Build with Neuro.*
