# Tasks

## Metadata

- Feature/profile: `5-system-prompt` / Complex
- Plan approved date: 2026-08-23

## Implementation Strategy

- Strategy: Incremental
- Reason: Slices follow an expand-contract sequence across shared boundaries (`src/tools/prompt.py`, `src/tools/skills.py`, `src/application/query_engine.py`). First, implement pure prompt assembly, instruction discovery, capping, dedup, and formatting in `src/tools/prompt.py` with standalone unit tests. Next, connect QueryEngine and delegate `skills.build_system_message` to the new assembler. Finally, update existing test assertions expecting the legacy 2-part string and verify full regression suite across all features. No `[P]` markers.

## Task Contract

Each task includes ID, target paths from the plan module map, `Covers: AC-*`, `Depends on: T-NNN`, entry proof (failing test), and exit proof. Status is `Not Started` until `/spec-implement` runs `task-start`. No `[P]` markers.

## Tasks

### Phase 1: Setup / Foundational — Prompt Assembler & Instruction Discovery (US2, US3, US4, US5)

- Goal: Implement `src/tools/prompt.py` with `discover_instructions` (reading cwd `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`, 4000/12000 character limits, SHA-256 dedup, unreadable error tolerance), `format_security_section`, `format_tools_section`, and `assemble_system_prompt` (joining identity, workspace, planning, security, tools, skills catalog, and instructions).
- Entry proof: `python3 -c "import src.tools.prompt"` fails (module not found).
- Exit proof: `python3 tests/tools_check.py` exit 0 with all instruction discovery, character capping, dedup, tools list, security text, and assembly order tests passing.

- [x] T-001 [US2] [US3] [US4] [US5] `src/tools/prompt.py`, `tests/tools_check.py` — add `src/tools/prompt.py` with pure stdlib `discover_instructions` (reads cwd `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` in order; skips missing/unreadable without raising; dedups identical content via SHA-256; caps per-file at 4000 chars and total file text at 12000 chars; marks truncated text with `TRUNCATED`), `format_security_section` (mentions workspace bound, hard-deny / deny-list, protected paths/keys, MEDIUM/HIGH approval; excludes rules.json tokens), `format_tools_section` (lists registered tools as `- <name>: <description>`, no schema dump), and `assemble_system_prompt` (assembles identity, workspace with resolved cwd, Feature 3 planning text, security, tools, Feature 4 skill catalog, and on-demand instructions joined by `\n\n`); add unit tests in `tests/tools_check.py`.
  - Covers: `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-016`, `AC-017`
  - Depends on:
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:

### Phase 2: User Story 1 & 6 — QueryEngine Integration & Skill Delegation (US1, US6)

- Goal: Update `src/application/query_engine.py` `_with_system` to invoke `prompt.assemble_system_prompt()` dynamically on every `complete()`. Update `src/tools/skills.py` `build_system_message` to delegate to `assemble_system_prompt`. Verify system prompt is never stored in session JSON transcripts, changes to `AGENTS.md` or skills mid-session appear on next turn, and `.cda/.permission_rules/rules.json` tokens are not in the prompt.
- Entry proof: `QueryEngine._with_system` calls legacy `skills.build_system_message` without workspace/security/tools/instructions sections.
- Exit proof: `python3 tests/query_engine_check.py` exit 0 with dynamic assembled prompt, empty catalog fallback, mid-session file updates, and session transcript isolation tests passing.
  Validation evidence: python3 tests/tools_check.py passed 58 tests. Implemented src/tools/prompt.py covering AC-004 through AC-011, AC-016, AC-017.


- [x] T-002 [US1] [US6] `src/application/query_engine.py`, `src/tools/skills.py`, `tests/query_engine_check.py` — update `QueryEngine._with_system` to call `prompt.assemble_system_prompt()`; update `skills.build_system_message` to delegate to `assemble_system_prompt`; add/update unit tests in `tests/query_engine_check.py` verifying `complete()` receives full assembled prompt (identity, workspace, planning string, security text, tools list, skill catalog, instructions), empty catalog produces `(no skills found)`, mid-session `AGENTS.md` and skill creation appear on next prompt without restart, permission rules file tokens are not in prompt, and `.cda/.sessions/<id>.json` contains no system role messages.
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-012`, `AC-013`, `AC-014`
  - Depends on: `T-001`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:

### Phase 3: Polish — Full Regression & Assert Migration

- Goal: Migrate existing test assertions across `tests/` that strictly checked `first.content.startswith(SYSTEM_MESSAGE)` to verify the planning sentence is present within the assembled system prompt. Verify 100% test suite pass and Python compile.
- Entry proof: prior tasks completed; legacy tests run cleanly.
- Exit proof: `python3 -m compileall -q src` exit 0 and `python3 -m unittest discover -s tests -p '*_check.py'` exit 0.
  Validation evidence: QueryEngine._with_system now calls assemble_system_prompt(); skills.build_system_message delegates. T-002 tests: AC-001 assembled prompt order, AC-002 empty catalog, AC-003 no system in session JSON, AC-012 UNIQUE-RULE-TOKEN absent, AC-013 AGENTS.md freshness, AC-014 skill freshness. python3 tests/query_engine_check.py TestPlanningEngine T-002 slice: 6 tests OK.


- [x] T-003 `src/`, `tests/` — adjust legacy test assertions in `tests/query_engine_check.py` and `tests/tools_check.py` that asserted `startswith(SYSTEM_MESSAGE)` to assert `assertIn(SYSTEM_MESSAGE, ...)` or check section contents; verify all tools, permissions, task planning, skills, and CLI tests pass without regression.
  - Covers: `AC-015`
  - Depends on: `T-002`
  - Status: Done
  - Proof: `python3 -m compileall -q src` && `python3 -m unittest discover -s tests -p '*_check.py'`
  - Evidence:

## Traceability

| ID | Tasks |
| --- | --- |
| REQ-001 | T-002 |
| REQ-002 | T-001, T-002 |
| REQ-003 | T-001, T-002 |
| REQ-004 | T-001, T-002 |
| REQ-005 | T-001, T-002, T-003 |
| REQ-006 | T-001, T-002 |
| REQ-007 | T-001, T-002 |
| REQ-008 | T-001, T-002 |
| REQ-009 | T-001 |
| REQ-010 | T-001 |
| REQ-011 | T-001 |
| REQ-012 | T-001, T-002 |
| REQ-013 | T-001, T-002 |
| REQ-014 | T-001, T-002, T-003 |
| REQ-015 | T-002, T-003 |
| AC-001 | T-002 |
| AC-002 | T-002 |
| AC-003 | T-002 |
| AC-004 | T-001 |
| AC-005 | T-001 |
| AC-006 | T-001 |
| AC-007 | T-001 |
| AC-008 | T-001 |
| AC-009 | T-001 |
| AC-010 | T-001 |
| AC-011 | T-001 |
| AC-012 | T-002 |
| AC-013 | T-002 |
| AC-014 | T-002 |
| AC-015 | T-003 |
| AC-016 | T-001 |
| AC-017 | T-001 |

## Resume Notes

- Next recommended task: `T-001`
- First ready (no unfinished deps): `T-001`
- Implement with `/spec-implement`; `task-start --task T-001` before coding.
- Gates remain deferred; task Proof commands are not closeout.
  Validation evidence: python3 -m compileall -q src exit 0; python3 -m unittest discover -s tests -p '*_check.py' exit 0; 159 tests OK. Migrated startswith(SYSTEM_MESSAGE) to assertIn. Isolated TestQueryEngine denied-tool cwd from leftover project rules.json. AC-015 covered.

