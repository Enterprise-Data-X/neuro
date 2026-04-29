# 🧠 Neuro CLI

> **Persona-Driven AI Alignment for Organisations.**

Neuro is a professional orchestration layer that synchronises AI agent behaviours across an entire organisation. It ensures that every developer’s AI—whether in Cursor, Claude, or Copilot—operates with the same high-standard skills, tools, and hooks defined by their specific role (**Persona**).

---

## 🚀 Installation & Setup

Neuro follows a "Source of Truth" model. During installation, the CLI links your machine to your organisation’s central configuration repository to establish a unified base.

### 1. Run the Installer
```bash
sudo ./install.sh
```

### 2. Connect Your Skill Vault
The installer will prompt you for a **Skills Repository URL**. 
*   **Template:** Use the [Neuro-Template](https://github.com) as your base.
*   **Initial Sync:** The CLI clones this repository into `~/.neuro/`, instantly downloading all `_common` and `_persona` configurations.

### 3. Persona Selection
After the sync, you will be prompted to select your **Persona** (e.g., Architect, Frontend, DevOps).
*   **Result:** Neuro configures your local instance to prioritise skills from `_persona/<selected>` while maintaining the global guardrails from `_common`.

---

## 🛠 How It Works

### The Multi-Layer Architecture
Neuro organises your organisation's collective intelligence into a hierarchy that prevents "Agent Drift":

*   **`_common/`**: Universal rules, security guardrails, and base coding standards applied to **every** seat in the organisation.
*   **`_persona/`**: Role-specific expertise. A "Lead Architect" persona might include system design skills, while a "Security" persona includes vulnerability scanning tools.
*   **`hooks/`**: Automated scripts that trigger during agent actions to ensure compliance.

### Project Initialization
When you run `neuro init` in a repository:
1.  **Agent Discovery:** Neuro detects which agents are present (Cursor, Claude, Copilot, etc.).
2.  **Smart Symlinking:** It maps your persona-filtered vault (`~/.neuro`) directly into the project's local agent folders.
3.  **Instant Alignment:** Your AI immediately adopts the directives, hooks, and tools assigned to your organisational role.

---

## 📂 Repository Structure
To maintain compatibility, your skills repository must follow this standard:

```text
Neuro-Vault/
├── _common/           # Universal skills/tools for all users
│   ├── skills/        # Global .md directives
│   └── tools/         # Global MCP / scripts
├── _persona/          # Role-based directories
│   ├── {role/team}/     # specific role or team specific vault, can be defined for usecase
│       ├── skills/        # Persona-specific .md directives
│       └── tools/         # Persona-specific MCP / scripts
└── hooks/             # Global pre-flight scripts
```
```text
EXAMPLE
Neuro-Vault/
├── _common/           # Universal skills/tools for all users
│   ├── skills/        # Global .md directives
│   └── tools/         # Global MCP / scripts
├── _persona/          # Role-based directories
│   ├── architect/     # Architect-specific vault
│       ├── skills/        # Persona-specific .md directives
│       └── tools/         # Persona-specific MCP / scripts
│   ├── frontend/      # Frontend-specific vault
│       ├── skills/        # Persona-specific .md directives
│       └── tools/         # Persona-specific MCP / scripts
│   ├── backend/      # Frontend-specific vault
│       ├── skills/        # Persona-specific .md directives
│       └── tools/         # Persona-specific MCP / scripts
│   └── security/      # Security-specific vault
│       ├── skills/        # Persona-specific .md directives
│       └── tools/         # Persona-specific MCP / scripts
└── hooks/             # Global pre-flight scripts
```

---

## 💻 Commands


| Command | Description |
| :--- | :--- |
| `neuro init` | Align local AI agents with your selected persona. |
| `neuro status` | View active links and verify current persona alignment. |
| `neuro init --force` | Force-create agent folders if they don't exist yet. |

---

**Standardise the intent. Scale the expertise. Build with Neuro.**
