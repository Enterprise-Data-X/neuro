# Neuro — Architecture

## Overview

Neuro is structured in four layers. Each layer has a single responsibility and depends only on layers below it.

```
┌─────────────────────────────────────────────────────┐
│  CLI / TUI  (cli.py · commands/)                    │  User interface
├─────────────────────────────────────────────────────┤
│  Commands   (init · status · update · agent_update) │  Orchestration
├─────────────────────────────────────────────────────┤
│  Services   (agents · skill_manager · evaluator)    │  Business logic
├─────────────────────────────────────────────────────┤
│  Core       (policy · sourcecontrol · project)      │  Primitives
└─────────────────────────────────────────────────────┘
```

---

## Source Layout

```
src/neuro/
├── cli.py                    Entry point — Click command group
├── NEURO.md                  Global AI directive shipped with the package
│
├── commands/                 One module per CLI or TUI command
│   ├── init.py               Agent detection + skill installation
│   ├── status.py             Installation status display
│   ├── update.py             Template repo pull + skill refresh
│   ├── config.py             Config file read / write
│   ├── uninstall.py          4-step full removal
│   ├── agent_update.py       Interactive provider switcher
│   ├── tui.py                Prompt Toolkit interactive terminal
│   └── skills.py             TUI skill CRUD handlers
│
├── services/                 Stateless business logic
│   ├── base_agent.py         NeuroAgent interface + UnavailableAgent
│   ├── claude_agent.py       Claude CLI subprocess wrapper
│   ├── ollama_agent.py       Ollama daemon wrapper + auto-start
│   ├── codex_agent.py        OpenAI API streaming wrapper
│   ├── copilot_agent.py      GitHub Models API wrapper
│   ├── neuro_chat_agent.py   Multi-provider factory (create_agent)
│   ├── skill_loader.py       Load SKILL.md files from ~/.neuro/skills/
│   ├── skill_manager.py      Skill CRUD, source tracking
│   └── skill_evaluator.py    Local vs remote diff, update result
│
└── core/                     Low-level primitives
    ├── policy.py             Skill content validation rules
    ├── sourcecontrol.py      Git clone / pull helpers
    └── project.py            Project registry + execution log
```

---

## Agent Layer

### Interface

Every chat provider implements `NeuroAgent` from `services/base_agent.py`:

```
NeuroAgent
 ├── .available       → bool
 ├── .provider_name   → str
 ├── .chat(msg, on_token)
 ├── .trigger_login() → int   # exit code; only Claude overrides this
 ├── .clear_history()
 └── .refresh_context()
```

### Providers

| File | Class | Backend |
| :--- | :--- | :--- |
| `claude_agent.py` | `ClaudeAgent` | `claude --bare -p` subprocess |
| `ollama_agent.py` | `OllamaAgent` | `ollama.chat()` streaming |
| `codex_agent.py` | `CodexAgent` | OpenAI streaming completions |
| `copilot_agent.py` | `CopilotAgent` | OpenAI client → `models.inference.ai.azure.com` |

### Factory

`neuro_chat_agent.create_agent()` resolves the provider in this order:

```
1. Read ~/.neuro/config.json → agent.provider
2. If provider is set and found        → return configured agent
3. Auto-discovery fallback:
     claude binary in PATH             → ClaudeAgent
     ollama.list() reachable           → OllamaAgent
     OPENAI_API_KEY in env             → CodexAgent
     GITHUB_TOKEN in env               → CopilotAgent
4. None found                          → UnavailableAgent
```

For `ollama`, if the daemon is not running, `start_daemon()` spawns `ollama serve` in the background and polls for up to 5 s before giving up.

---

## Skill Installation Flow (`neuro init`)

```
neuro init
    │
    ├─ 1. bootstrap_neuro_home()
    │       Ensure ~/.neuro/{skills,tools}/
    │       Copy NEURO.md directive if missing
    │
    ├─ 2. For each entry in AGENT_MAP:
    │       detect()  ─────────────────────────┐
    │         not found → skip                 │
    │         found    → install_agent()       │
    │                       │                  │
    │               For each skill/tool in     │
    │               ~/.neuro/{skills,tools}/   │
    │                   _install_item()        │
    │                       │                  │
    │              ┌────────┴────────┐         │
    │         dir-based          file-based    │
    │         (symlink/copy       (append text │
    │          to skills_dir/     to instruction│
    │          commands_dir/)     file)         │
    │
    └─ 3. render_summary() + persist_to_config() + write_log_entry()
```

### AGENT_MAP entries

| Agent | Detection | Skills destination | Note |
| :--- | :--- | :--- | :--- |
| Universal Agent | `~/.agent/` exists | `~/.agent/skills/` | Symlink |
| GitHub Copilot | `copilot` binary / `~/.copilot/` | `~/.copilot/copilot-instructions.md` | Appended |
| Claude Code | `claude` binary / `~/.claude/` | `~/.claude/skills/` + `commands/` | Symlink |
| Continue.dev | `~/.continue/` exists | `~/.continue/prompts/` | Symlink |

---

## Skill Vault Layers

The template repository is cloned to `~/.neuro/template/<repo-name>/` and its contents are merged into `~/.neuro/` in three passes:

```
_common/skills  → ~/.neuro/skills/   (all users)
_common/tools   → ~/.neuro/tools/

_persona/<role>/skills → ~/.neuro/skills/  (role-specific overlay)
_persona/<role>/tools  → ~/.neuro/tools/

_agents/<provider>/skills → ~/.neuro/skills/  (provider-specific overlay)
_agents/<provider>/tools  → ~/.neuro/tools/
```

Later passes override earlier ones. `neuro update` re-runs this merge from `git pull --ff-only` output.

---

## Configuration File

`~/.neuro/config.json` is the single source of truth for runtime state.

```jsonc
{
  "version": "1.0.0",
  "agent": {
    "provider": "claude",      // active chat provider
    "model": "claude-opus-4-7",
    "api_key": "..."           // optional; codex / copilot only
  },
  "templateRepository": [
    {
      "url": "git@github.com:org/vault.git",
      "name": "vault",
      "path": "/home/user/.neuro/template/vault"
    }
  ],
  "role": "backend",
  "init_assets": {             // written by neuro init
    "Claude Code": {
      "installed": ["skills/my-skill", "commands/my-cmd.md"],
      "skipped": [],
      "errors": []
    },
    "_agents_not_detected": ["Cursor"]
  }
}
```

Writers: `install.sh`, `agent_update.py`, `init.py`, `update.py`  
Readers: `neuro_chat_agent.py`, `tui.py`, `status.py`, `uninstall.py`

---

## TUI Architecture

```
tui.run()
  │
  ├─ _get_configured_provider()  ─┐  reads config before blocking
  │                                │  shows "Checking Ollama…" if needed
  ├─ agent_svc.create_agent()   ◄─┘
  │
  ├─ PromptSession (prompt_toolkit)
  │     WordCompleter on COMMANDS list
  │     styled prompt: "neuro  ❯  "
  │
  └─ event loop
        /skills   → skills_cmd.handle()
        /agent    → inline handlers (update / refresh / clear)
        /status   → status_mod.run()
        /config   → _show_config()
        /init     → handle_slash_command("/init")
        /help     → _help()
        /clear    → os.system("clear")
        /exit     → break
        <text>    → _stream_agent_reply(agent, text)
                         → agent.chat(on_token=…)
                         → RuntimeError (login) → _run_claude_login()
                                                 → retry on success
```

---

## Policy Engine

`core/policy.py` validates skill content before installation:

- Blocks forbidden shell commands (`rm -rf /`, `curl … | bash`, etc.)
- Blocks hardcoded secrets patterns (tokens, passwords, private keys)
- Validates directive structure (must have a title, must not exceed size limits)
- Returns a list of violation strings — the TUI displays these and requires confirmation before installing a flagged skill

---

## Logging

Two log destinations:

| Path | Format | Written by |
| :--- | :--- | :--- |
| `~/.neuro/logs/neuro-log.json` | JSON object keyed by ISO-8601 timestamp | `init.py` |
| `~/.neuro/log/update-<ts>.log` | Plain text per-run log | `update.py` |

---

## Data Flow Summary

```
install.sh
  └─ write config.json  ─────────────────────────────────────┐
                                                              │
neuro init                                                    │
  └─ read config.json ◄──────────────────────────────────────┤
  └─ detect agents                                            │
  └─ symlink ~/.neuro/skills/ → agent dirs                   │
  └─ write init_assets → config.json  ───────────────────────┤
                                                              │
neuro update                                                  │
  └─ git pull template repo                                   │
  └─ copy skills → ~/.neuro/skills/  ───────────────────────►│
                                                              │
neuro (TUI)                                                   │
  └─ read config.json ◄──────────────────────────────────────┘
  └─ create_agent()
  └─ stream chat  → ClaudeAgent / OllamaAgent / CodexAgent / CopilotAgent
```
