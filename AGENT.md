# Neuro Agent

This document describes the AI chat agent embedded in the Neuro TUI — what it is, how it is configured, how each provider works, and how to extend or troubleshoot it.

---

## What is the Neuro Agent?

When you type a free-form message in the Neuro TUI (anything that is not a `/command`), it is sent to your configured **AI provider** and the response is streamed back in real time. The provider is selected during `install.sh` or changed at any time with `/agent update`.

The agent is a lightweight wrapper — it does not maintain a persistent conversation history by default, but it loads your installed skills as context so the AI operates within your organisation's persona.

---

## Supported Providers

### Claude (CLI)

Uses the `claude --bare -p` subprocess. Requires a Claude Code subscription and the `claude` binary in `PATH`.

```
Provider key:  claude
Binary:        claude   (npm install -g @anthropic-ai/claude-code)
Model format:  claude-opus-4-7 / claude-sonnet-4-6 / …
Auth:          claude login   (browser OAuth)
```

**Login flow:** If the Claude CLI is not authenticated, the TUI detects the error and automatically launches `claude login` for you. After successful login, your original message is retried.

### Ollama (Local)

Uses the `ollama` Python package against a locally running `ollama serve` daemon.

```
Provider key:  ollama
Binary:        ollama   (https://ollama.com)
Model format:  llama3 / mistral / codellama / …
Auth:          none (local)
```

**Auto-start:** If the daemon is not running when the TUI starts, Neuro will attempt to launch `ollama serve` in the background and wait up to 5 s for it to come up before opening the TUI.

### Codex / OpenAI

Uses the `openai` Python package with the OpenAI API.

```
Provider key:  codex
API endpoint:  https://api.openai.com/v1
Model format:  gpt-4o / gpt-4o-mini / gpt-4-turbo / …
Auth:          OPENAI_API_KEY env var  or  agent.api_key in config.json
```

### GitHub Copilot

Uses the `openai` Python package pointed at the GitHub Models inference endpoint, authenticated with a GitHub Personal Access Token.

```
Provider key:  copilot
API endpoint:  https://models.inference.ai.azure.com
Model format:  openai/gpt-4o / openai/gpt-4o-mini / meta/llama-3.3-70b-instruct / …
Auth:          GITHUB_TOKEN env var  or  agent.api_key in config.json
```

---

## Switching Providers

### From the TUI

```
/agent update
```

Walks you through provider selection, prerequisite checks, and model selection. Saves the result to `~/.neuro/config.json` and immediately activates the new provider for the current session.

### From the terminal

```bash
neuro agent update
```

Same interactive flow, usable outside the TUI.

### Manual edit

Edit `~/.neuro/config.json` directly:

```json
{
  "agent": {
    "provider": "ollama",
    "model": "llama3"
  }
}
```

Then restart the TUI.

---

## Configuration Reference

`~/.neuro/config.json` → `agent` object:

| Key | Required | Description |
| :--- | :--- | :--- |
| `provider` | Yes | One of `claude` · `ollama` · `codex` · `copilot` |
| `model` | Recommended | Model identifier for the chosen provider |
| `api_key` | codex / copilot | API key or token (can also be set via env var) |

---

## Provider Auto-Discovery

If `config.json` has no provider set, Neuro falls back to auto-discovery in this order:

1. `claude` binary found in `PATH` → Claude
2. `ollama.list()` reachable → Ollama
3. `OPENAI_API_KEY` in environment → Codex
4. `GITHUB_TOKEN` in environment → GitHub Copilot
5. None found → agent unavailable (run `/agent update`)

---

## Agent Interface (for developers)

Every provider implements `NeuroAgent` from `src/neuro/services/base_agent.py`:

```python
class NeuroAgent:
    available: bool          # False if provider cannot be initialised
    provider_name: str       # Display string, e.g. "Ollama (llama3)"

    def chat(message, on_token=None) -> str
    def trigger_login() -> int   # exit code; Claude only
    def clear_history() -> None
    def refresh_context() -> None
```

To add a new provider:

1. Create `src/neuro/services/<name>_agent.py` with a class that extends `NeuroAgent`
2. Add a `if provider == "<name>":` block in `neuro_chat_agent.create_agent()`
3. Add the provider to `_PROVIDERS` in `commands/agent_update.py`
4. Add the provider to `install.sh` option list

---

## TUI Chat Commands

| In-session command | Effect |
| :--- | :--- |
| `/agent` | Show current provider name |
| `/agent update` | Interactive provider / model switcher |
| `/agent refresh` | Re-load installed skills into context |
| `/agent clear` | Clear conversation history |
| Any other text | Sent to the active AI provider |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| :--- | :--- | :--- |
| "Agent unavailable" at startup | No provider configured | Run `/agent update` |
| Claude: "not logged in" error | Claude CLI not authenticated | TUI auto-launches `claude login` |
| Ollama: TUI hangs for ~5 s at start | Daemon not running, auto-start attempted | Wait; or run `ollama serve` manually first |
| Ollama: "model not found" | Model not pulled locally | `ollama pull <model>` |
| Codex / Copilot: auth error | API key missing or invalid | Run `/agent update` to re-enter the key |
| Chat sends but no response | Model overloaded or network issue | Wait and retry; check provider status page |
