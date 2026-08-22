# Architecture

> Ownership: `Adopter-owned`
> Status: Evidence-backed draft from Phase A (2026-04-08). Product identity confirmed: open-coding-agent REPL.

Describe this repository's application architecture here. Do not describe
CoreZero unless this repository itself is CoreZero. Keep operational watchouts
and cross-document pointers in `core-zero/memories/repo/project-knowledge-base.md`.

## System Snapshot

- Repository type: Brownfield Python coding-agent CLI
- Primary runtime(s): Python 3.13.13 locally (`enum.StrEnum` requires 3.11+)
- Main entrypoints: `python3 -m src.cli` (`src/cli.py` → `src/presentation/cli.py:run`); `python3 -m src` (`src/__main__.py`)
- Deployment shape: Local REPL process. No daemon, container, or hosted service.
- Confidence: High for implemented layers; `[UNKNOWN]` for intended production shape

## Top-Level Components

| Component | Responsibility | Key Paths | Notes |
| - | - | - | - |
| Presentation | CLI flags, REPL loop, authorize UX, event rendering | `src/presentation/cli.py`, `src/presentation/terminal_ui.py` | `--session`, `--json`, `--debug`; exit 0 / 2 / 130 |
| Application | Multi-turn complete → tool → persist loop | `src/application/query_engine.py` | Streams text events; injects `bypass_permissions=True` after HIGH approve |
| Domain | Immutable conversation types and `ProviderError` | `src/domain/models/`, `src/domain/errors.py` | Frozen dataclasses |
| Provider | OpenAI-compatible `/chat/completions` + SSE | `src/infrastructure/providers/openai.py` | Stdlib `urllib`; env overrides JSON |
| Session store | Persist history under `.sessions/<id>.json` | `src/infrastructure/session_store.py` | Redacts keys containing `api_key` / `authorization` |
| Tools | Register, validate, permission-check, invoke 14 tools | `src/tools/`, `src/tools/handlers/` | HIGH: `bash`, `powershell`, `repl`; MEDIUM: write/edit/fetch/config |
| Compatibility shims | Flat `src/*.py` re-exports | `src/{cli,terminal_ui,query_engine,provider,session,tools}.py` | Preserve import paths |

## Runtime Boundaries

- Boundary: Presentation → Application
  Owner: `src/presentation/cli.py`
  Crossing rule: CLI constructs `QueryEngine(provider, store, session_id, ui.authorize, ui.event)` and calls `turn(prompt)` only.

- Boundary: Application → Provider
  Owner: `src/application/query_engine.py`
  Crossing rule: `provider.complete(history, tool_schemas, stream=True)` is the only outbound model call. Failures wrap as `ProviderError`.

- Boundary: Application → Tools
  Owner: `QueryEngine._run_call`
  Crossing rule: HIGH/MEDIUM require `authorize()` first. Denial becomes a tool error, not a crash. LOW tools run without a prompt.

- Boundary: Application → Session store
  Owner: `QueryEngine._save`
  Crossing rule: Save after every user, assistant, and tool message, and on KeyboardInterrupt.

- Boundary: Config / secrets → Provider
  Owner: `OpenAIProvider.__init__`
  Crossing rule: constructor args > `OPENAI_*` env > `.secrets/config.json` (or `$CONFIG_FILE`). Missing any of base/key/model raises `ProviderError`.

## Safe Change Guidance

- High-risk areas: `permissions.py`, `query_engine.py` authorize/bypass path, `shell.py`, `execution.py`, `openai.py` secret load, `session_store.py` redaction, `.gitignore` secret ignore, `file_io.py` / `network.py`
- Required proof: the five `tests/*_check.py` scripts (18 tests) must stay green. Add a focused check when changing an untested handler.
- Do not treat `documents/BUILDING_A_CODING_AGENT.md` as current architecture. It is a roadmap; implemented surface is the stdlib REPL above.

## Architectural Decision Records (ADRs)

Record project architectural decisions in `core-zero/project/adr/` as
`NNNN-<slug>.md`. Append a matching entry to
`core-zero/memories/repo/adr-log.md` with status, reversibility, and a
one-line summary. Compare at least two options on depth, seam, blast
radius, and reversibility before accepting a lasting decision.
