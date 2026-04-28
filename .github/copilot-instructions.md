Repository summary

- Package: neuro (src/)
- Entry point: neuro.cli:main (console script `neuro`)
- Workspace: Neuro assumes a local workspace at ~/.neuro for policies, skills, logs.

Build, test, and lint commands

- Install for development (editable):
  - python3 -m venv .venv && source .venv/bin/activate && pip install -e .
  - Or run the included installer: ./install_script.sh
- Run the CLI (TUI):
  - neuro start
- Tests: No tests or test runner configuration are included in this repository. If tests are added, standard commands apply:
  - Run full suite: pytest
  - Run a single test by keyword or node id: pytest -k <expr> or pytest path/to/test.py::test_name
- Linting: No lint configuration (flake8/ruff/black) is present. Use your preferred tooling if required (not enforced by repo).

High-level architecture (big picture)

- Purpose: Neuro is a governance layer that maps specs (Swagger/OpenAPI, JSON schema, or natural-language descriptions) into organization-approved templates via "skills" and policy checks.
- Runtime: CLI TUI (neuro start) that exposes hierarchical commands (/policy, /skills, /agent, /templates, /status, /help).
- Workspace layout (user-local): ~/.neuro holds policies/, skills/, scripts/, logs/ and config.json — this is the authoritative runtime data source.
- Components in repo:
  - src/neuro/: core package code (cli.py, commands, core services)
  - scripts/ and services/ referenced by skills live in the workspace at runtime and are registered with Neuro's commands registry.
- Generation flow: Input spec -> selected skill -> policy validation -> template mapping -> diff preview in TUI -> apply changes. Every generation embeds metadata (neuro-version, policy-hash) for traceability.

Key conventions and repo-specific patterns

- Package layout: Uses src/ layout with setuptools entry point defined in setup.py and pyproject.toml. The console script is `neuro` which maps to neuro.cli:main.
- Policy-first: Active policies live under ~/.neuro/policies. The agent MUST load these before producing code. AGENT.md defines strict refusal behavior if a requested change violates policy.
- Skills registry: Skills are treated as transformation scripts under ~/.neuro/skills (or skills/ in the workspace). Skills are referenced by `neuro` commands and may be external (git URL) per README.
- Traceability: Generated code must include a header referencing the policy-hash and neuro-version. Search for this pattern when validating generated code.
- No assumptions about CI hooks or tests: This repo focuses on runtime governance; CI/test/lint integrations are intentionally absent.
- Install path expectations: The installer links the CLI from a venv into /usr/local/bin/neuro (see install_script.sh).

Important docs for Copilot sessions

- Primary docs to consult in this repo:
  - README.md (overview & quick-start)
  - AGENT.md (agent protocol & constraints) — authoritative for behavior and refusal rules
  - install_script.sh (install process and default config.json contents)
  - VISION.md / GEMINI.md for strategic/contextual notes

What Copilot should prioritize when assisting

- Respect Policy-First constraints: Always check AGENT.md and ~/.neuro/policies (or example policy snippets in the repo) before generating or modifying code.
- Preserve templates and trace headers: Do not change template shapes or remove the policy-hash/neuro-version headers in generated files.
- Prefer small, surgical edits: Follow the repo's emphasis on reproducible, auditable transformations.
- When asked to add new features, recommend registering a skill and adding tests/CI rather than directly modifying templates used across the system.

MCP servers

If you'd like, configure MCP servers relevant to this repo (e.g., Playwright for UI testing). Would you like help setting any up?

Last notes

Created .github/copilot-instructions.md summarizing repo commands, architecture, and conventions. Ask for adjustments or coverage of any area you want expanded.