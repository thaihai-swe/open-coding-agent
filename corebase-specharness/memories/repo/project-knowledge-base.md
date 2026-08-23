# Project Knowledge Base

Durable descriptive knowledge for this repository. Managed via `/starter-init` and `/context-memory`.

## Preserved Behavior Baseline

<!-- Identify at least 3 critical behaviors that must never break during feature delivery or refactoring. Pre-filled during /starter-init archaeology. -->
- Missing provider configuration (no env vars and no readable config file) must fail loudly: CLI `run()` returns exit code `2` with an actionable `ProviderError` (`tests/cli_check.py`, `src/presentation/cli.py`).
- Environment variables `OPENAI_API_BASE` / `OPENAI_API_KEY` / `OPENAI_MODEL` override JSON config values (`tests/provider_check.py`).
- HIGH and MEDIUM tools require `authorize()`; deny must not execute the handler and must record a tool result error (`tests/query_engine_check.py`).
- Session JSON round-trip must not persist `OPENAI_API_KEY` (or similarly named) fields (`tests/session_check.py`, `SessionStore._redact`).
- KeyboardInterrupt during the REPL must save the session and exit `130` (`src/presentation/cli.py`).
- QueryEngine stops after `max_turns` (default 8) with `termination_reason="max_turns_reached"` (`tests/query_engine_check.py`).

## Operational Watchouts & Gotchas

<!-- Document known race conditions, tricky environment quirks, flaky external services, or performance hotspots discovered over time. -->
- `documents/how-to-run.md` instructs `cp documents/config.example.json .secrets/config.json`, but `documents/config.example.json` does not exist.
- `.secrets/` is not listed in `.gitignore`; `.sessions/` is. Do not commit real keys.
- `documents/BUILDING_A_CODING_AGENT.md` is out of scope (adopter, 2026-08-22). Do not use it as architecture or product contract.
- Verification gates and security policy are `[DEFERRED]`. Advisory/no-gate `verify` cannot authorize `Done` without `--verification-override`.
- `src/tools.py` is shadowed by package `src/tools/`; imports resolve to the package.
- `web_search` is a stub (`example.com`), not a live search client.
- Harness `init` will keep reporting unknown "repository stack" until a `pyproject.toml`, `requirements.txt`, or `setup.py` exists.
- `.mypy_cache/` exists locally; there is no checked-in mypy/ruff/pytest config or CI workflow.
- Manifest/README refer to a `skills/` tree; this workspace keeps skills under `.agents/skills/`.

## System Pointers

- Architecture & Components: See `corebase-specharness/project/architecture.md`.
- Tech Stack & Dependencies: See `corebase-specharness/project/tech-stack.md`.
- Project Constraints & Compliance: See `corebase-specharness/project/project-constraints.md`.
- Domain Vocabulary: See `corebase-specharness/project/glossary.md` and `corebase-specharness/memories/domain/`.
- Normative Policies: See `corebase-specharness/memories/repo/core-policies.md`.
- Architecture Decisions: See `corebase-specharness/memories/repo/adr-log.md`.
