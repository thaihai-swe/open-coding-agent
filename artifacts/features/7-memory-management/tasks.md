# Tasks

## Metadata

- Feature/profile: `7-memory-management` / Complex
- Plan approved date: 2026-08-23

## Implementation Strategy

- Strategy: Incremental
- Reason: Slices follow a clean dependency sequence from pure data storage and prompt modules to engine orchestration and finally presentation/CLI wiring:
  1. `T-001`: Memory store and index builder (`src/tools/memory.py`), configuration resolution (`src/tools/config.py`), and system prompt catalog integration (`src/prompts/memory.md`, `src/tools/prompt.py`) with unit tests in `tests/tools_check.py`.
  2. `T-002`: QueryEngine integration (`src/application/query_engine.py`) and side-query transformers in `src/tools/memory.py`, adding pre-turn relevant memory retrieval, request-only `<relevant_memories>` injection, pre-compression snapshotting, post-turn extraction, threshold consolidation ("Dreaming"), and non-persisted session JSON isolation with integration tests in `tests/query_engine_check.py`.
  3. `T-003`: Presentation layer (`src/presentation/cli.py`) `/memory` slash command intercept before skill expansion, displaying memory entries and utilization stats, with CLI tests in `tests/cli_check.py` and full regression verification across all feature suites.
- No `[P]` markers.

## Task Contract

Each task includes ID, target paths from the plan module map, `Covers: AC-*`, `Depends on: T-NNN`, entry proof (failing test), and exit proof. Status is `Not Started` until `/spec-implement` runs `task-start`. No `[P]` markers.

## Tasks

### Phase 1: Setup / Foundational — Storage, Indexing, Config & Prompts (US1, US2, US3)

- Goal: Implement `src/tools/memory.py` for `.cda/memory/<slug>.md` frontmatter storage, index building (`.cda/memory/MEMORY.md`), and path traversal sanitization; update `src/tools/config.py` with `DEFAULT_MEMORY_CONFIG` and `resolve_memory_config()`; add bundled prompt `src/prompts/memory.md`; update `src/tools/prompt.py` to register `"memory"` prompt section and format `MEMORY.md` index catalog into `assemble_system_prompt()`; add unit tests in `tests/tools_check.py`.
- Entry proof: `python3 -c "import src.tools.memory"` fails with `ModuleNotFoundError`.
- Exit proof: `python3 tests/tools_check.py` exit 0 with all memory storage, frontmatter, index rebuild, slug sanitization, config loading, and system prompt memory catalog tests passing.

- [x] T-001 [US1] [US2] [US3] `src/tools/memory.py`, `src/tools/config.py`, `src/prompts/memory.md`, `src/tools/prompt.py`, `tests/tools_check.py` — implement `src/tools/memory.py` (`Memory` dataclass, `parse_memory_frontmatter`, `sanitize_slug`, `write_memory_file`, `read_memory_file`, `list_memory_files`, `read_memory_index`, `rebuild_memory_index`), `src/tools/config.py` (`DEFAULT_MEMORY_CONFIG`, `resolve_memory_config`, update `DEFAULT_CONFIG` and `ensure_default_config`), `src/prompts/memory.md` bundled prompt template, and `src/tools/prompt.py` (`"memory"` section in `PROMPT_SECTIONS` and `FALLBACK_SECTIONS`, format `MEMORY.md` catalog into `assemble_system_prompt`); add unit tests in `tests/tools_check.py`.
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-006`, `AC-007`, `AC-008`
  - Depends on:
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:

### Phase 2: User Stories 2, 4 & 5 — Relevance Selection, Request Injection, Post-Turn Extract & Consolidation (US2, US4, US5)

- Goal: Implement `select_relevant_memories` (LLM side-query + keyword fallback), `format_relevant_memories`, `extract_memories` (dialogue snapshot extraction), and `consolidate_memories` (periodic deduplication at threshold) in `src/tools/memory.py`. Update `src/application/query_engine.py` to prefetch relevant memories at the start of each user turn and inject `<relevant_memories>` into outgoing provider request messages copy without modifying `engine.history` or session JSON; capture pre-compression snapshot before L1-L4 compaction layers; trigger `extract_memories` and `consolidate_memories` on natural turn completion; ensure all side-queries use `tools=[]`, fail gracefully, and respect config flags (`memory.enabled`, `auto_extract`, `auto_consolidate`).
- Entry proof: `QueryEngine` has no memory selection, extraction, or consolidation logic; `tests/query_engine_check.py` has no persistent memory tests.
- Exit proof: `python3 tests/query_engine_check.py` exit 0 with relevance selection, keyword fallback, request-only injection, pre-compression snapshotting, post-turn extraction, threshold consolidation, error swallowing, and tool-less side-query tests passing.
  Validation evidence: python3 tests/tools_check.py exit 0; 84 tests OK. Implemented src/tools/memory.py, src/tools/config.py memory block, src/prompts/memory.md, and assemble_system_prompt integration. Covers AC-001, AC-002, AC-003, AC-004, AC-006, AC-007, AC-008.


- [x] T-002 [US2] [US4] [US5] `src/tools/memory.py`, `src/application/query_engine.py`, `tests/query_engine_check.py` — implement `select_relevant_memories`, `format_relevant_memories`, `extract_memories`, and `consolidate_memories` in `src/tools/memory.py`; update `QueryEngine` in `src/application/query_engine.py` to prefetch relevant memories at the start of a user turn, inject `<relevant_memories>` into outgoing request messages without modifying `self.history`, snapshot pre-compression messages, run post-turn extraction on turn completion, and trigger consolidation when memory file count meets or exceeds `consolidate_threshold`; ensure side-query calls are tool-less, non-blocking to the main turn on error, and respect `memory.enabled`, `auto_extract`, and `auto_consolidate`; add tests in `tests/query_engine_check.py`.
  - Covers: `AC-005`, `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-013`, `AC-014`, `AC-015`, `AC-018`, `AC-019`
  - Depends on: `T-001`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:

### Phase 3: User Stories 6 & Full Regression — CLI /memory Slash Command & Regression (US6)

- Goal: In `src/presentation/cli.py`, intercept `/memory` in the REPL loop before `expand_slash_prompt()`: read memory files via `list_memory_files()`, format summary list (`- [type] name: description`, count vs threshold), and emit status events without calling `engine.turn()`. Add CLI tests in `tests/cli_check.py`. Verify full regression suite and Python compilation across all features.
- Entry proof: `src/presentation/cli.py` does not intercept `/memory` and attempts to treat `/memory` as a skill.
- Exit proof: `python3 -m compileall -q src` exit 0 and `python3 -m unittest discover -s tests -p '*_check.py'` exit 0.
  Validation evidence: python3 tests/query_engine_check.py exit 0; 67 tests OK. Request-only relevant injection, extract from pre-compact snapshot, consolidate at threshold, tool-less side queries. Covers AC-005, AC-009–AC-015, AC-018, AC-019.


- [x] T-003 [US6] `src/presentation/cli.py`, `tests/cli_check.py` — intercept `/memory` in the REPL loop in `src/presentation/cli.py` before skill expansion to format and emit memory entries and file count statistics via status events without calling `engine.turn("/memory")` or reporting unknown skill; update `tests/cli_check.py`; verify full test suite passes and Python compilation succeeds.
  - Covers: `AC-016`, `AC-017`, `AC-020`
  - Depends on: `T-002`
  - Status: Done
  - Proof: `python3 -m compileall -q src` && `python3 -m unittest discover -s tests -p '*_check.py'`
  - Evidence:

## Traceability

| ID | Tasks |
| --- | --- |
| REQ-001 | T-001 |
| REQ-002 | T-001 |
| REQ-003 | T-001 |
| REQ-004 | T-002, T-003 |
| REQ-005 | T-001 |
| REQ-006 | T-001 |
| REQ-007 | T-002 |
| REQ-008 | T-002 |
| REQ-009 | T-002 |
| REQ-010 | T-002 |
| REQ-011 | T-003 |
| REQ-012 | T-002 |
| REQ-013 | T-003 |
| AC-001 | T-001 |
| AC-002 | T-001 |
| AC-003 | T-001 |
| AC-004 | T-001 |
| AC-005 | T-002 |
| AC-006 | T-001 |
| AC-007 | T-001 |
| AC-008 | T-001 |
| AC-009 | T-002 |
| AC-010 | T-002 |
| AC-011 | T-002 |
| AC-012 | T-002 |
| AC-013 | T-002 |
| AC-014 | T-002 |
| AC-015 | T-002 |
| AC-016 | T-003 |
| AC-017 | T-003 |
| AC-018 | T-002 |
| AC-019 | T-002 |
| AC-020 | T-003 |

## Resume Notes

- Next recommended task: `T-001`
- First ready (no unfinished deps): `T-001`
- Implement with `/spec-implement`; `task-start --task T-001` before coding.
- Gates remain deferred; task Proof commands are not closeout.
  Validation evidence: python3 -m compileall -q src exit 0; python3 -m unittest discover -s tests -p '*_check.py' exit 0; 212 tests passing. CLI /memory slash command intercepted before skills, status event formatting, skill preservation, AC-016, AC-017, AC-020.

