# Project Knowledge Base

## Index

- System Reference Documents — links to architecture.md and core-policies.md
- Repository Overview — coding-agent CLI plus installed CoreZero kit
- Key Architectural Boundaries — layers, shims, config, tools
- Common Installation & Bootstrap Watchouts — missing example config, secrets ignore, blueprint drift
- Feature Lifecycle Handoff Patterns — first feature through spec-research
- Preserved Behavior Baseline — invariants that must not change
- Ubiquitous Domain Jargon — terms used in code

## System Reference Documents

- Architecture Boundary Map: Refer to `core-zero/project/architecture.md` for static system snapshots, components, and runtime boundaries. Do not duplicate structural maps here.
- Brownfield map: `core-zero/memories/repo/brownfield/brownfield-map.md`
- Rules & Mandates: Refer to `core-zero/memories/repo/core-policies.md` for normative CC-* mandates.

## Repository Overview

- This repository's product is a local OpenAI-compatible coding-agent REPL implemented in stdlib Python under `src/`.
- CoreZero is installed as the delivery harness (`core-zero/`, `.agents/skills/`). It is not the product.
- Application layers: `src/presentation/`, `src/application/`, `src/domain/`, `src/infrastructure/`, `src/tools/`.
- Flat `src/*.py` files are compatibility shims that re-export the layered packages.
- Tests live in `tests/*_check.py` (unittest, 18 cases).
- Operator docs: `documents/how-to-run.md`. Roadmap (not implemented): `documents/BUILDING_A_CODING_AGENT.md`.
- No root `README.md`, `CONTRIBUTING.md`, `pyproject.toml`, or `requirements.txt`.
- No CI, linter, or formatter config observed.

## Key Architectural Boundaries

Refer to `core-zero/project/architecture.md` for static component paths. This section is operational.

### 1. Product vs harness
Do not describe or change CoreZero kit internals when the request is about the coding agent. Do not treat kit seed memory as product truth.

### 2. Blueprint vs code
`documents/BUILDING_A_CODING_AGENT.md` describes slash commands, MCP, bootstrap_graph, Pydantic, pytest, and turn budgets. None of those exist in `src/`. Implement against code + tests + how-to-run.

### 3. Config cascade
Constructor args > `OPENAI_API_BASE` / `OPENAI_API_KEY` / `OPENAI_MODEL` > `.secrets/config.json` (or `$CONFIG_FILE`). Missing any of base/key/model → `ProviderError`; CLI exits `2`.

### 4. Tool risk gate
HIGH/MEDIUM tools prompt `TerminalUI.authorize`. Denial records `tool_denied` and continues the turn. After HIGH approve, `QueryEngine` calls `invoke(..., bypass_permissions=True)`.

### 5. Session persistence
`SessionStore` writes `.sessions/<id>.json` after every history mutation and on Ctrl+C. Redaction drops dict keys whose names contain `api_key` or `authorization` only.

## Common Installation & Bootstrap Watchouts

- `documents/how-to-run.md` says `cp documents/config.example.json .secrets/config.json`. That example file is missing.
- Same doc previously claimed `.secrets/` was ignored while the rule was commented out. Phase B uncommented `.secrets/` in `.gitignore`. Live `.secrets/config.json` exists at mode `0644` and must not be printed or committed.
- `cli_check` prints the missing-config Error line to stderr on purpose.
- Tool handlers have no dedicated tests. A green suite does not prove shell/file/network safety.
- First brownfield feature should go through `/spec-research` unless the change is isolated and already mapped.

## Feature Lifecycle Handoff Patterns

- First behavior-changing feature: `/spec-research` (brownfield), then `/spec-requirements`.
- Isolated, already-mapped changes may enter `/spec-requirements` directly after citing this knowledge base and the brownfield map.
- Enter and leave skills with `skill-enter` / `skill-exit`. `status-set` is the only writer of `- Phase:` in `status.md`.

## Preserved Behavior Baseline

These are current observable contracts. Do not change them unless a spec explicitly says so.

1. Missing provider configuration is an actionable `ProviderError`; `run([])` exits `2` and prints the set-env-or-config message (`tests/cli_check.py`, `tests/provider_check.py`).
2. Environment variables override JSON config keys; constructor args override environment (`tests/provider_check.py`).
3. Provider HTTP errors become `ProviderError` and must not include the API key string (`tests/provider_check.py`).
4. HIGH/MEDIUM denial emits `tool_denied` and a tool result error `"Tool execution denied by user."` without dropping the session (`tests/query_engine_check.py`).
5. Session JSON must not persist keys named like `api_key` / `authorization`; KeyboardInterrupt saves and exits `130` (`src/infrastructure/session_store.py`, `src/presentation/cli.py`).
6. CLI flags `--session`, `--json`, `--debug` keep their current argparse contract (`tests/cli_check.py`, `tests/terminal_ui_check.py`).

## Ubiquitous Domain Jargon

| Term | Meaning in this repo |
| - | - |
| QueryEngine | Application loop in `src/application/query_engine.py` |
| OpenAIProvider | Stdlib HTTP/SSE client; not the official OpenAI SDK |
| SessionStore | `.sessions/<id>.json` persistence |
| authorize | Interactive approve/deny callback for HIGH/MEDIUM tools |
| bypass_permissions | Kwarg that skips the HIGH gate in `check_permission` |
| ProviderError | Domain error for config and provider HTTP/JSON failures |
| tool_denied | UI/event type when the user denies a tool |
| Risk | HIGH / MEDIUM / LOW enum on each registered tool |
| shim | Flat `src/*.py` re-export, not a second implementation |
