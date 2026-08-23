# Architecture

> Ownership: `Adopter-owned`
> Status: Pre-filled from `/starter-init` archaeology (2026-08-22). Adopter: product is the coding-agent CLI.

This repository contains a local OpenAI-compatible **coding-agent CLI** under `src/`, plus an installed CoreBase SpecHarness kit under `corebase-specharness/` for spec-driven delivery. This document describes the **application** (`src/`), not the harness internals.

## System Snapshot

- Repository type: Brownfield local Python CLI (no package marker files; no CI)
- Primary runtime(s): Python 3.11+ (`StrEnum`); observed 3.13.13
- Main entrypoints: `python3 -m src.cli` (`src/presentation/cli.py` composition root); also `python3 -m src` via `src/__main__.py`
- Deployment shape: Local REPL. No production deploy config found.
- Confidence: High for `src/` layout and seams. `documents/BUILDING_A_CODING_AGENT.md` is adopter-declared out of scope.

## Top-Level Components

| Component | Responsibility | Key Paths | Notes |
| - | - | - | - |
| Presentation | Parse flags, REPL loop, human/JSON events, tool approval prompt | `src/presentation/cli.py`, `src/presentation/terminal_ui.py` | Flags: `--session`, `--json`, `--debug`. Missing config → exit 2. Ctrl+C saves session → exit 130 |
| Application | Turn loop, stream collect, tool loop (`max_turns=8`) | `src/application/query_engine.py` | After HIGH approval, injects `bypass_permissions=True` into `invoke` |
| Domain | Provider protocol and frozen message/tool models | `src/domain/` | Tests use structural fakes, not `OpenAIProvider` |
| Infrastructure: provider | HTTP `POST {api_base}/chat/completions` | `src/infrastructure/providers/openai.py` | Stdlib urllib; no request timeout |
| Infrastructure: sessions | Persist/redact transcripts | `src/infrastructure/session_store.py` | Default dir `.sessions/` |
| Tools | Registry + handlers (shell, files, search, network, repl, …) | `src/tools/` | Import of `src.tools` registers all handlers |
| App tests | stdlib unittest scripts | `tests/*_check.py` | No coverage of `src/tools/` handlers |
| Delivery kit | Spec harness, skills, context compiler | `corebase-specharness/`, `.agents/skills/` | Not the runtime agent |

## Runtime Boundaries

- Boundary: User terminal ↔ CLI
  Owner: `src/presentation/`
  Crossing rule: Interactive `input()` for prompts and HIGH/MEDIUM tool approval. JSON mode still uses the same authorize string on stdin.

- Boundary: QueryEngine ↔ Provider protocol
  Owner: `src/application/query_engine.py` / `src/domain/provider.py`
  Crossing rule: Only `complete(messages, tools, stream=...)`. Composition root hard-wires `OpenAIProvider`.

- Boundary: QueryEngine ↔ tools
  Owner: `src/tools/`
  Crossing rule: LOW tools skip UI approval. MEDIUM/HIGH require `TerminalUI.authorize`. `check_permission` additionally requires `bypass_permissions` for HIGH and blocks MEDIUM `file_path`/`key` substrings in `PROTECTED_PATHS`.

- Boundary: Process ↔ network
  Owner: `OpenAIProvider`, `web_fetch`
  Crossing rule: Provider URL is caller-configured. `web_fetch` uses `urlopen` with no host allowlist. `web_search` does not hit the network.

- Boundary: Process ↔ filesystem / shell
  Owner: file_io, search, shell, execution handlers
  Crossing rule: No workspace jail. `bash` is `subprocess.run(..., shell=True)`. `repl` is `exec` into `registry.repl_globals`.

## Safe Change Guidance

- High-risk areas: `src/tools/permissions.py`, `src/tools/handlers/shell.py`, `src/tools/handlers/execution.py`, `src/tools/handlers/file_io.py`, `src/tools/handlers/network.py`, `src/infrastructure/providers/openai.py` (secrets), `src/application/query_engine.py` (authorize + bypass), `.secrets/config.json`
- Required proof: Run documented `tests/*_check.py` (or `python3 -m unittest discover -s tests -p '*_check.py'`). Tool-handler changes currently have **no** dedicated tests — add checks before changing permission or execution behavior.

## Architectural Decision Records (ADRs)

Record lasting decisions via `/spec-adr`. Full write contract and ledger:
`corebase-specharness/memories/repo/adr-log.md`. Artifacts live in
`corebase-specharness/project/adr/NNNN-<slug>.md`.

No ADRs recorded as of 2026-08-22.
