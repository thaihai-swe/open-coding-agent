# Tasks

## Metadata

- Feature/profile: `1-tool-and-execution` / Complex
- Plan approved date: 2026-08-22

## Implementation Strategy

- Strategy: Incremental
- Reason: Shared files (`search.py`, `tests/tools_check.py`, `query_engine.py`, `terminal_ui.py`) make fake parallelism unsafe. Follow the plan’s five tracer slices: tools → batch → events/cancel → multiline/Markdown → regression.

## Task Contract

Each task includes ID, target paths from the plan module map, `Covers: AC-*`, `Depends on: T-NNN`, entry proof (failing test), and exit proof. Status is `Not Started` until `/spec-implement` runs `task-start`. No `[P]` markers: later tasks edit the same modules.

## Tasks

### Phase 1: Setup / Foundational — P1 tools (US1, US2)

- Goal: Public dispatch for core names, `glob` alias, extra tools still registered, workspace-bound file/search tools, bash not jailed.
- Entry proof: `python3 tests/tools_check.py` is missing or failing.
- Exit proof: `python3 tests/tools_check.py` exit 0 and `python3 tests/query_engine_check.py` still exit 0.

- [x] T-001 [US1] `src/tools/handlers/search.py`, `tests/tools_check.py` — add failing `tools_check` then register `glob` as the same handler as `glob_search`; prove in-cwd `read_file`/`write_file`/`edit_file`/`bash`/`glob_search`/`glob` and extra `grep_search` via `invoke` / `registry.list_schemas`
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-005`
  - Depends on:
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:
  Validation evidence: python3 tests/tools_check.py 6/6 OK; python3 tests/query_engine_check.py 5/5 OK; glob registered as glob_search alias; AC-001/002/003/005. verify: phase-check/artifact-check/traceability/gate-runner pass; review-provider skipped; gates deferred.


- [x] T-002 [US2] `src/tools/workspace.py`, `src/tools/handlers/file_io.py`, `src/tools/handlers/search.py`, `tests/tools_check.py` — add `bound_path`; handlers refuse resolved real paths outside cwd (including symlink escape) before IO; filter glob/grep matches; do not jail `bash`
  - Covers: `AC-006`, `AC-007`, `AC-008`
  - Depends on: `T-001`
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:

### Phase 2: User Story 3 — Concurrent batch (Priority: P1) 🎯 MVP

- Goal: One assistant message’s tool list may overlap; history order is listed order; failures do not skip siblings; next provider complete waits; sequential authorize then execute.
- Entry proof: `python3 tests/query_engine_check.py` lacks batch-order / deny-batch cases (or they fail).
- Exit proof: `python3 tests/query_engine_check.py` exit 0.
  Validation evidence: python3 tests/tools_check.py 10/10 OK; query_engine_check 5/5 OK; bound_path refuses .. and symlink escape; bash still reads outside file; AC-006/007/008.


- [x] T-003 [US3] `src/application/query_engine.py`, `tests/query_engine_check.py` — replace serial `_run_call` loop with `_run_batch` using `ThreadPoolExecutor`; unknown tool → error result; mixed success/failure still records every result; listed-order history even if B finishes first; next `complete` only after the batch
  - Covers: `AC-004`, `AC-009`, `AC-010`, `AC-013`
  - Depends on: `T-002`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:
  Validation evidence: python3 tests/query_engine_check.py 9/9 OK; unknown tool error continues; overlap B-before-A with listed-order history; mixed failure keeps sibling; next complete sees both tool results. AC-004/009/010/013.


- [x] T-004 [US3] `src/application/query_engine.py`, `tests/query_engine_check.py` — sequential MEDIUM/HIGH authorize in listed order before overlap; deny emits `tool_denied` and does not invoke; other calls still get results; emit `status` then `tool` starts on the main thread, then `tool_result` in listed order after `wait=True`
  - Covers: `AC-011`, `AC-012`, `AC-015`
  - Depends on: `T-003`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:

### Phase 3: User Story 4 — Live events, JSON, cancel (Priority: P1) 🎯 MVP

- Goal: Human-mode plain tool/status/result lines; JSON additive types; KeyboardInterrupt still 130 with session file.
- Entry proof: `python3 tests/terminal_ui_check.py` does not cover `status`/`tool_result`; `python3 tests/cli_check.py` does not cover exit 130.
- Exit proof: `python3 tests/terminal_ui_check.py` and `python3 tests/cli_check.py` exit 0.
  Validation evidence: python3 tests/query_engine_check.py 12/12 OK; deny skips handler and keeps sibling; authorize listed order before any run; status then tool then tool_result. AC-011/012/015.


- [x] T-005 [US4] `src/presentation/terminal_ui.py`, `tests/terminal_ui_check.py` — print plain `tool` / `tool_result` / `status` / `error` lines; JSON mode emits `text` | `tool` | `tool_denied` | `error` | `status` | `tool_result` without Markdown rendering
  - Covers: `AC-014`, `AC-016`
  - Depends on: `T-004`
  - Status: Done
  - Proof: `python3 tests/terminal_ui_check.py`
  - Evidence:
  Validation evidence: python3 tests/terminal_ui_check.py 5/5 OK; human prints [tool]/[status]/[tool_result]/Error; JSON types text|tool|tool_denied|error|status|tool_result with raw content. AC-014/016.


- [x] T-006 [US4] `src/presentation/cli.py`, `tests/cli_check.py` — KeyboardInterrupt during the REPL saves the session and returns 130 (change `cli.py` only if the new test fails)
  - Covers: `AC-017`
  - Depends on: `T-003`
  - Status: Done
  - Proof: `python3 tests/cli_check.py`
  - Evidence:

### Phase 4: User Stories 5–6 — Multiline and Markdown (Priority: P2)

- Goal: Period-submit multiline prompts; human Markdown on assistant `text` only.
- Entry proof: `python3 tests/terminal_ui_check.py` fails AC-018–AC-023 cases.
- Exit proof: `python3 tests/terminal_ui_check.py` exit 0.
  Validation evidence: python3 tests/cli_check.py 4/4 OK; KeyboardInterrupt during prompt returns 130 and writes session JSON; cli.py unchanged (path already existed). AC-017.


- [x] T-007 [US5] `src/presentation/terminal_ui.py`, `tests/terminal_ui_check.py` — `prompt` accumulates lines; first empty line returns `""`; solo `.` submits joined text; EOF submits accumulation
  - Covers: `AC-018`, `AC-019`, `AC-020`
  - Depends on: `T-005`
  - Status: Done
  - Proof: `python3 tests/terminal_ui_check.py`
  - Evidence:
  Validation evidence: python3 tests/terminal_ui_check.py 9/9 OK; period-submit hello\nworld; empty first line quits; EOF submits accumulation; json_mode same. AC-018/019/020.


- [x] T-008 [US6] `src/presentation/terminal_ui.py`, `tests/terminal_ui_check.py` — private `_render_markdown` on human `text` only (ATX heading + `**bold**`); tool/status/error/`tool_result` stay plain; JSON `content` stays source
  - Covers: `AC-021`, `AC-022`, `AC-023`
  - Depends on: `T-007`
  - Status: Done
  - Proof: `python3 tests/terminal_ui_check.py`
  - Evidence:

### Phase 5: Polish — regression pack

- Goal: Full unittest surface still green after the Session 02 slices.
- Entry proof: prior tasks Done.
- Exit proof: compile + discover exit 0.
  Validation evidence: python3 tests/terminal_ui_check.py 12/12 OK; human text renders ATX/bold; tool/status/error/tool_result keep markers; JSON content is source. AC-021/022/023.


- [x] T-009 `src/`, `tests/` — run the full app check pack; fix only regressions caused by this feature
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-013`, `AC-014`, `AC-015`, `AC-016`, `AC-017`, `AC-018`, `AC-019`, `AC-020`, `AC-021`, `AC-022`, `AC-023`
  - Depends on: `T-006`, `T-008`
  - Status: Done
  - Proof: `python3 -m compileall -q src` && `python3 -m unittest discover -s tests -p '*_check.py'`
  - Evidence:

## Traceability

| ID | Tasks |
| --- | --- |
| REQ-001 | T-001 |
| REQ-002 | T-001 |
| REQ-003 | T-003 |
| REQ-004 | T-001 |
| REQ-005 | T-002 |
| REQ-006 | T-002 |
| REQ-007 | T-003 |
| REQ-008 | T-003 |
| REQ-009 | T-003 |
| REQ-010 | T-004 |
| REQ-011 | T-003 |
| REQ-012 | T-005 |
| REQ-013 | T-005, T-008 |
| REQ-014 | T-006 |
| REQ-015 | T-007 |
| REQ-016 | T-008 |
| AC-001–AC-005 | T-001, T-009 |
| AC-006–AC-008 | T-002, T-009 |
| AC-004, AC-009, AC-010, AC-013 | T-003, T-009 |
| AC-011, AC-012, AC-015 | T-004, T-009 |
| AC-014, AC-016 | T-005, T-009 |
| AC-017 | T-006, T-009 |
| AC-018–AC-020 | T-007, T-009 |
| AC-021–AC-023 | T-008, T-009 |

## Resume Notes

- Next recommended task: `T-001`
- First ready (no unfinished deps): `T-001`
- Implement with `/spec-implement`; `task-start --task T-001` before coding.
- Gates remain deferred; task Proof commands are not closeout.
  Validation evidence: python3 -m compileall -q src OK; python3 -m unittest discover -s tests -p '*_check.py' 47/47 OK. No regressions to fix.

