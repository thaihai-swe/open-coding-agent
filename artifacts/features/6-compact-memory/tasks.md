# Tasks

## Metadata

- Feature/profile: `6-compact-memory` / Complex
- Plan approved date: 2026-08-23

## Implementation Strategy

- Strategy: Incremental
- Reason: Slices follow a clean dependency sequence from pure data transformation modules to engine orchestration and finally presentation/CLI wiring:
  1. `T-001`: Config loading (`src/tools/config.py`), compact prompt template (`src/prompts/compact.md`), and pure history compression layers L1, L2, L3 + boundary guards (`src/tools/compact.py`) with standalone unit tests in `tests/tools_check.py`.
  2. `T-002`: QueryEngine integration (`src/application/query_engine.py`) and `compact` tool registration (`src/tools/handlers/agent.py`), adding pre-complete pipeline, L4 summarization with JSONL transcript snapshotting, emergency reactive compaction, circuit breaker, and session JSON updates with integration tests in `tests/query_engine_check.py`.
  3. `T-003`: Presentation cutover (`src/presentation/cli.py`) to `.cda/config.json` and REPL `/compact` slash command intercept before skill expansion, with CLI tests in `tests/cli_check.py` and full regression verification across all feature suites.
- No `[P]` markers.

## Task Contract

Each task includes ID, target paths from the plan module map, `Covers: AC-*`, `Depends on: T-NNN`, entry proof (failing test), and exit proof. Status is `Not Started` until `/spec-implement` runs `task-start`. No `[P]` markers.

## Tasks

### Phase 1: Setup / Foundational — Config, Compact Prompt & Pure Compression Transformers (US1, US2, US6)

- Goal: Implement `src/tools/config.py` for `.cda/config.json` loading with defaults, `src/prompts/compact.md` default summarization prompt with `src/tools/prompt.py` `"compact"` section support, and pure compression functions in `src/tools/compact.py` (`estimate_history_chars`, `tool_result_budget` L3 disk persister under `.cda/task_outputs/tool-results/`, `snip_compact` L1 middle snip, `micro_compact` L2 placeholders, `find_safe_boundary`, and path traversal sanitization).
- Entry proof: `python3 -c "import src.tools.config; import src.tools.compact"` fails with `ModuleNotFoundError`.
- Exit proof: `python3 tests/tools_check.py` exit 0 with all config loading, L3 budget, L1 snip, L2 micro, boundary guard, and sanitization tests passing.

- [x] T-001 [US1] [US2] [US6] `src/tools/config.py`, `src/tools/compact.py`, `src/prompts/compact.md`, `src/tools/prompt.py`, `tests/tools_check.py` — implement `src/tools/config.py` (`load_config`, `resolve_compact_config`, `DEFAULT_CONFIG` with s08 defaults), `src/prompts/compact.md` bundled prompt template, `src/tools/prompt.py` `"compact"` section registration in `PROMPT_SECTIONS` and `FALLBACK_SECTIONS`, and `src/tools/compact.py` pure transformers (`estimate_history_chars`, `tool_result_budget` persisting large outputs >200KB to `.cda/task_outputs/tool-results/<call_id>.txt` with `<persisted-output>` preview, `snip_compact` trimming middle messages when >50 while protecting `assistant(tool_calls)` -> `tool(tool_result)` pairings with `[snipped N messages...]` placeholder, `micro_compact` replacing older tool results >120 chars with placeholders, `find_safe_boundary`, and filename traversal sanitization); add unit tests in `tests/tools_check.py`.
  - Covers: `AC-001`, `AC-002`, `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-011`, `AC-020`, `AC-024`
  - Depends on:
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:

### Phase 2: User Stories 3, 4, 5 & 6 — QueryEngine Pipeline, L4 Summarizer, Reactive Recovery & Compact Tool (US3, US4, US5, US6)

- Goal: Register LOW `compact` tool in `src/tools/handlers/agent.py`. Integrate 4-layer compaction pipeline in `src/application/query_engine.py`: pre-complete L3->L1->L2 execution when `auto_compact` is true; threshold trigger (`len > max_messages` or `chars > max_chars`) running L4 with pre-compaction transcript snapshot in `.cda/.transcripts/<session_id>-<timestamp>.jsonl`; provider summarization with `compact` prompt; replacing older history with `<compacted-summary>...</compacted-summary>` while retaining recent window; emergency `reactive_compact` on provider context overflow (`prompt_too_long`, `context length`, HTTP 413) with bounded retry (`reactive_retries=1`); circuit breaker capping consecutive summarizer failures at 3; status events emission; `compact` tool execution ending turn loop; session JSON persistence of compacted messages without system roles.
- Entry proof: `QueryEngine` has no context compaction or reactive compact logic; `tests/query_engine_check.py` has no L4 compaction tests.
- Exit proof: `python3 tests/query_engine_check.py` exit 0 with auto-compact, L4 summary, transcript snapshots, reactive retry, circuit breaker, compact tool, and session transcript isolation tests passing.
  Validation evidence: python3 tests/tools_check.py exit 0; 74 tests OK. Added src/tools/config.py, src/tools/compact.py, src/prompts/compact.md, compact prompt section. AC-001 defaults, AC-002 config override, AC-004 L3 persist, AC-005 L1 snip 50 with [snipped 11], AC-006 tool pair intact, AC-007 L2 placeholders, AC-008 noop, AC-011 safe boundary, AC-020 compact prompt override, AC-024 sanitized persist path.


- [x] T-002 [US3] [US4] [US5] [US6] `src/application/query_engine.py`, `src/tools/handlers/agent.py`, `src/tools/registry.py`, `tests/query_engine_check.py` — register LOW `compact` tool in `src/tools/handlers/agent.py`; update `QueryEngine` to integrate the 4-layer compaction pipeline (`tool_result_budget` -> `snip_compact` -> `micro_compact` -> `compact_history` if over thresholds) before `provider.complete()`; implement `compact_history` writing `.cda/.transcripts/<session_id>-<utc_timestamp>.jsonl` with API key redaction, querying provider for summary using `load_prompt_section("compact")` without tools, and setting `history` to `[ChatMessage("user", "<compacted-summary>\n" + summary + "\n</compacted-summary>")] + recent_window` (boundary safe); implement emergency `reactive_compact` catching `ProviderError` with `prompt_too_long` / `context length` / HTTP 413 and retrying once; implement circuit breaker capping consecutive summarizer failures at 3; emit status events on compaction; handle `compact` tool invocation to trigger compaction and stop turn loop; ensure session JSON contains only compacted `messages` with no system roles; add tests in `tests/query_engine_check.py`.
  - Covers: `AC-009`, `AC-010`, `AC-012`, `AC-015`, `AC-016`, `AC-017`, `AC-018`, `AC-019`, `AC-020`, `AC-021`, `AC-022`
  - Depends on: `T-001`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:

### Phase 3: User Stories 1, 4 & 6 — CLI /compact Slash Command, Config Cutover & Full Regression (US1, US4, US6)

- Goal: Update `src/presentation/cli.py` to use `src/tools/config.py` (cutting over from `.cda/ui-config.json` to `.cda/config.json`, ignoring old file). Add REPL intercept for `/compact` before skill expansion to trigger manual compaction on the active engine session. Update existing test suites in `tests/cli_check.py` and `tests/terminal_ui_check.py` to use `.cda/config.json`. Verify full regression suite and Python compilation across all features.
- Entry proof: `src/presentation/cli.py` reads `_UI_CONFIG_PATH = Path(".cda/ui-config.json")` and delegates all slash commands to `expand_slash_prompt()`.
- Exit proof: `python3 -m compileall -q src` exit 0 and `python3 -m unittest discover -s tests -p '*_check.py'` exit 0.
  Validation evidence: python3 tests/query_engine_check.py exit 0; 57 tests OK. QueryEngine L3-L1-L2-L4 pipeline, compact tool, reactive compact, circuit breaker, transcript snapshots. AC-009 auto-chars, AC-010 summary wrap, AC-012 session JSON, AC-015 compact tool, AC-016 auto_compact false, AC-017 reactive recover, AC-018 retry budget, AC-019 circuit breaker, AC-020 compact prompt override, AC-021 status events.


- [x] T-003 [US1] [US4] [US6] `src/presentation/cli.py`, `tests/cli_check.py`, `tests/terminal_ui_check.py` — update `src/presentation/cli.py` to load settings from `src.tools.config` `.cda/config.json` and ignore `.cda/ui-config.json`; intercept `/compact` in the REPL loop before `expand_slash_prompt` to trigger manual compaction on `engine` and notify user without calling `engine.turn("/compact")` or reporting unknown skill; update `tests/cli_check.py` and `tests/terminal_ui_check.py` to use `.cda/config.json`; verify all unit test suites pass and Python compilation succeeds.
  - Covers: `AC-003`, `AC-013`, `AC-014`, `AC-023`
  - Depends on: `T-002`
  - Status: Done
  - Proof: `python3 -m compileall -q src` && `python3 -m unittest discover -s tests -p '*_check.py'`
  - Evidence:

## Traceability

| ID | Tasks |
| --- | --- |
| REQ-001 | T-001, T-003 |
| REQ-002 | T-001 |
| REQ-003 | T-002 |
| REQ-004 | T-001, T-002 |
| REQ-005 | T-001 |
| REQ-006 | T-001 |
| REQ-007 | T-001 |
| REQ-008 | T-002 |
| REQ-009 | T-003 |
| REQ-010 | T-002 |
| REQ-011 | T-002 |
| REQ-012 | T-002 |
| REQ-013 | T-002 |
| REQ-014 | T-001, T-002 |
| REQ-015 | T-002 |
| REQ-016 | T-003 |
| AC-001 | T-001 |
| AC-002 | T-001 |
| AC-003 | T-003 |
| AC-004 | T-001 |
| AC-005 | T-001 |
| AC-006 | T-001 |
| AC-007 | T-001 |
| AC-008 | T-001 |
| AC-009 | T-002 |
| AC-010 | T-002 |
| AC-011 | T-001 |
| AC-012 | T-002 |
| AC-013 | T-003 |
| AC-014 | T-003 |
| AC-015 | T-002 |
| AC-016 | T-002 |
| AC-017 | T-002 |
| AC-018 | T-002 |
| AC-019 | T-002 |
| AC-020 | T-001, T-002 |
| AC-021 | T-002 |
| AC-022 | T-002 |
| AC-023 | T-003 |
| AC-024 | T-001 |

## Resume Notes

- Next recommended task: `T-001`
- First ready (no unfinished deps): `T-001`
- Implement with `/spec-implement`; `task-start --task T-001` before coding.
- Gates remain deferred; task Proof commands are not closeout.
  Validation evidence: python3 -m compileall -q src exit 0; python3 -m unittest discover -s tests -p '*_check.py' exit 0; 187 tests OK. CLI /compact intercepted before skills; .cda/config.json hard cutover; ui-config.json ignored. AC-003, AC-013, AC-014, AC-023.

