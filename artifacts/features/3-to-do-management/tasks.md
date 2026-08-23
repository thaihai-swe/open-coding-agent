# Tasks

## Metadata

- Feature/profile: `3-to-do-management` / Complex
- Plan approved date: 2026-08-23

## Implementation Strategy

- Strategy: Incremental
- Reason: Shared files (`task_board.py`, `planning.py`, `query_engine.py`, `tools_check.py`, `query_engine_check.py`) make fake parallelism unsafe. Follow the plan’s four tracer slices: board + six tools → engine bind / persist / sequential batch / system / nag → human board → regression. No `[P]` markers.

## Task Contract

Each task includes ID, target paths from the plan module map, `Covers: AC-*`, `Depends on: T-NNN`, entry proof (failing test), and exit proof. Status is `Not Started` until `/spec-implement` runs `task-start`. No `[P]` markers: later tasks edit the same modules.

## Tasks

### Phase 1: Setup / Foundational — P1 board + six tools (US1, US2, US6)

- Goal: Six LOW planning tools persist `{id, content, status}` at `.cda/.todos/default.json` via bare `invoke`. `todo_write` is unknown. Missing or invalid file is `[]`. Claim / complete / cancel follow the locked state machine.
- Entry proof: `python3 tests/tools_check.py` still registers `todo_write` and has no create/list/get/claim/complete/cancel persist cases (or they fail).
- Exit proof: `python3 tests/tools_check.py` exit 0.

- [x] T-001 [US1] `src/tools/task_board.py`, `src/tools/handlers/planning.py`, `tests/tools_check.py` — add `task_board` (ContextVar default `"default"`, `load_tasks`/`save_tasks`, `create_task`/`list_tasks`/`get_task`, name sets, `SYSTEM_MESSAGE`, `format_board`); rewrite `planning.py` to register six LOW tools and delete `todo_write`; tests `chdir` a temp cwd; `registry.get` of the six names is LOW Planning and `todo_write` is `None`; `invoke("todo_write", todos=[])` is unknown-tool; `create_task(content="Write tests")` returns non-empty `id`, that content, `pending`, plus `tasks`; writes `.cda/.todos/default.json`; `list_tasks` returns that item; `get_task` returns that item; empty or omitted `content` is a tool error and writes nothing; missing file and `{not: "an array"}` `list_tasks` return `[]` without crash; extra Feature 1 tools stay registered; keep `TODO_STATUSES` live in `types.py`
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-011`, `AC-016`
  - Depends on:
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:
  Validation evidence: python3 tests/tools_check.py exit 0; 28 tests OK. AC-001 six LOW Planning tools registered, todo_write None and absent from list_schemas; AC-002 invoke todo_write Unknown tool; AC-003 create_task Write tests persists pending to .cda/.todos/default.json with id+tasks; AC-004 list_tasks/get_task return that item; AC-011 empty/omitted/blank content error and no file; AC-016 missing and non-array file list_tasks []; grep_search still registered.


- [x] T-002 [US2] `src/tools/task_board.py`, `src/tools/handlers/planning.py`, `tests/tools_check.py` — `claim_task` only `pending` → `in_progress`; `complete_task` `pending` or `in_progress` → `completed` (item stays); `cancel_task` removes any stored status; unknown `id` on get/claim/complete/cancel is a tool error and the file is unchanged; claim of `in_progress`/`completed` and complete of `completed` error without mutate; two claims both stay `in_progress`; duplicate `id` on `create_task` errors and leaves the original; mutators return the item (cancel: `{id}`) plus `tasks`
  - Covers: `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-012`
  - Depends on: `T-001`
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:

### Phase 2: User Stories 3, 5, 6 — Engine bind / persist / system / nag (Priority: P1) 🎯 MVP

- Goal: `QueryEngine.turn` binds the engine session id, applies planning tools in listed order on the main thread, skips authorize, prepends the system message without saving it, and injects the 3-round nag. A new engine with the same session id sees the same board.
- Entry proof: `python3 tests/query_engine_check.py` lacks session-todos / system-message / nag / sequential-planning cases (or they fail).
- Exit proof: `python3 tests/query_engine_check.py` exit 0.
  Validation evidence: python3 tests/tools_check.py exit 0; 35 tests OK. AC-005 unknown id get/claim/complete/cancel error and file unchanged; AC-006 claim pending->in_progress then complete stays completed on disk; AC-007 complete pending without claim; AC-008 illegal claim/complete error without mutate; AC-009 two claims both in_progress; AC-010 cancel removes pending and completed; AC-012 duplicate create id error original unchanged.


- [x] T-003 [US3] `src/application/query_engine.py`, `tests/query_engine_check.py` — `turn` `bind_session(self.session_id)` and reset in `finally`; `_run_batch` invokes `PLANNING_TOOL_NAMES` sequentially on the main thread in listed index order, other approved tools still use `ThreadPoolExecutor`; return `(hard_denied, mutated)`; FakeProvider `create_task` with session `s1` writes `.cda/.todos/s1.json` not `default.json` and not cwd `.todos/` / `.tasks/`; new engine same id `list_tasks` returns that item; session `s2` gets `[]` and does not change `s1`’s file; session JSON stays messages-only (no task-board fields); authorize is not called; failing empty-content `create_task` then `list_tasks` in one assistant message keeps listed-order history and the list result
  - Covers: `AC-003`, `AC-013`, `AC-014`, `AC-015`, `AC-017`, `AC-025`, `AC-026`
  - Depends on: `T-002`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:
  Validation evidence: python3 tests/query_engine_check.py exit 0; 36 tests OK. AC-003/AC-026 create_task session s1 writes .cda/.todos/s1.json not default.json or cwd .todos/.tasks/; AC-013 new engine same id list_tasks returns item; AC-014 s2 empty s1 unchanged; AC-015 session JSON keys only messages; AC-017 authorize not called; AC-025 failing create then list_tasks listed order; two creates in one batch both persist a then b. tools_check.py 35 OK.


- [x] T-004 [US5] `src/application/query_engine.py`, `tests/query_engine_check.py` — prepend `ChatMessage("system", SYSTEM_MESSAGE)` on every `complete()` via `_with_system`; do not append it to `self.history` or session JSON; `self._rounds_without_planning` starts at 0; before `complete()`, if `>= 3` append user `<reminder>Update your todos.</reminder>`, reset, `_save()`; after text-only increment; after batch reset on `mutated` else increment; `list_tasks`/`get_task`/failed planning/non-planning do not reset; three text-only rounds inject the nag on the fourth `complete()`; a successful `create_task` resets so two later text-only rounds do not nag yet; three rounds of only `list_tasks`/`get_task` still nag
  - Covers: `AC-015`, `AC-018`, `AC-019`, `AC-020`, `AC-021`
  - Depends on: `T-003`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:

### Phase 3: User Story 4 — Human board and JSON (Priority: P1) 🎯 MVP

- Goal: Human mode prints `## Current Tasks` after successful board-named `tool_result`. JSON mode keeps the Feature 1 event types.
- Entry proof: `python3 tests/terminal_ui_check.py` does not print a Current Tasks board (or the new cases fail).
- Exit proof: `python3 tests/terminal_ui_check.py` exit 0.
  Validation evidence: python3 tests/query_engine_check.py exit 0; 40 tests OK. AC-018 complete() history[0] role=system includes plan before executing and six tool names; AC-015 session JSON messages-only with no system role; AC-019 fourth text-only complete receives user <reminder>Update your todos.</reminder>; AC-020 create_task resets so two later text rounds have no nag; AC-021 three list/get rounds nag on fourth complete. tools_check.py 35 OK.


- [x] T-005 [US4] `src/presentation/terminal_ui.py`, `tests/terminal_ui_check.py` — on human `tool_result` with `name in PLANNING_BOARD_NAMES` and not `is_error`, print `format_board(...)` even if `show_tool_results` is hidden; extract the list from `content["result"]` (invoke wrap) or `content` if a list; pending line contains `[ ]`, `t1`, `Write tests` under `## Current Tasks`; empty board prints the heading and no `[ ]`/`[>]`/`[x]` item lines; `get_task` does not reprint the full board; JSON `create_task` success emits `type=tool_result` and no type outside `text` / `tool` / `tool_denied` / `error` / `status` / `tool_result`
  - Covers: `AC-022`, `AC-023`, `AC-024`
  - Depends on: `T-004`
  - Status: Done
  - Proof: `python3 tests/terminal_ui_check.py`
  - Evidence:

### Phase 4: Polish — regression pack

- Goal: Full unittest surface still green after the planning-board slices. `.cda/` stays gitignored.
- Entry proof: prior tasks Done.
- Exit proof: compile + discover exit 0.
  Validation evidence: python3 tests/terminal_ui_check.py exit 0; 24 tests OK. AC-022 list_tasks human output has ## Current Tasks plus [ ] t1 Write tests even when show_tool_results is hidden; AC-023 empty board heading with no [ ]/[>]/[x]; AC-024 JSON create_task is type=tool_result with no ## Current Tasks and no new event type; get_task does not reprint the board.


- [x] T-006 `src/`, `tests/` — run the full app check pack; confirm `.gitignore` contains `.cda/`; fix only regressions caused by this feature
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-013`, `AC-014`, `AC-015`, `AC-016`, `AC-017`, `AC-018`, `AC-019`, `AC-020`, `AC-021`, `AC-022`, `AC-023`, `AC-024`, `AC-025`, `AC-026`
  - Depends on: `T-005`
  - Status: Done
  - Proof: `python3 -m compileall -q src` && `python3 -m unittest discover -s tests -p '*_check.py'`
  - Evidence:

## Traceability

| ID | Tasks |
| --- | --- |
| REQ-001 | T-001, T-003 |
| REQ-002 | T-001 |
| REQ-003 | T-001, T-002 |
| REQ-004 | T-001, T-003 |
| REQ-005 | T-003, T-004 |
| REQ-006 | T-001, T-002 |
| REQ-007 | T-001 |
| REQ-008 | T-001, T-002 |
| REQ-009 | T-002 |
| REQ-010 | T-002 |
| REQ-011 | T-002 |
| REQ-012 | T-002 |
| REQ-013 | T-003 |
| REQ-014 | T-005 |
| REQ-015 | T-005 |
| REQ-016 | T-004 |
| REQ-017 | T-004 |
| REQ-018 | T-003 |
| REQ-019 | T-003, T-006 |
| AC-001, AC-002, AC-004, AC-011, AC-016 | T-001, T-006 |
| AC-003 | T-001, T-003, T-006 |
| AC-005–AC-010, AC-012 | T-002, T-006 |
| AC-013, AC-014, AC-017, AC-025 | T-003, T-006 |
| AC-015 | T-003, T-004, T-006 |
| AC-018–AC-021 | T-004, T-006 |
| AC-022–AC-024 | T-005, T-006 |
| AC-026 | T-003, T-006 |

## Resume Notes

- Next recommended task: `T-001`
- First ready (no unfinished deps): `T-001`
- Implement with `/spec-implement`; `task-start --task T-001` before coding.
- Gates remain deferred; task Proof commands are not closeout.
  Validation evidence: python3 -m compileall -q src exit 0; python3 -m unittest discover -s tests -p '*_check.py' exit 0; 127 tests OK. AC-026 .gitignore contains .cda/. No regressions to fix.

