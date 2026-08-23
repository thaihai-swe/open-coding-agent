# Feature Specification

## Metadata
- Feature: `3-to-do-management`
- Profile: `Complex`
- Status: `Approved`
- Owner: adopter
- Requested artifact name: `3.to-do-management` (harness slug `3-to-do-management`)
- References (scoped, not global architecture): Session 05 and Session 12 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s05/; https://learn.shareai.run/en/s12/

## Problem Statement
- Who is affected, what fails, and why now: A coding-agent CLI user (and the model driving the session) has no durable plan. `todo_write` is registered as a LOW planning tool but only echoes its argument list: nothing is stored, nothing is shown as a board, nothing is restored on `--session`, and nothing reminds the model after it stops updating tasks. Long multi-step turns lose the remaining work. Session 05/12 teaching references a planning subsystem; this feature must make a structured task board a live, persisted, observable part of the REPL without pulling in a dependency graph or a second `todo_write` API.

## Outcome
- Observable result: The model uses six LOW tools — `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task` — to maintain a per-session board of `{id, content, status}` items. The board is stored at `.cda/.todos/<session_id>.json`. Human mode prints a Current Tasks board after each successful mutation and after `list_tasks`. JSON mode uses existing `tool_result` with no new event type. `claim_task` moves `pending` → `in_progress`. `complete_task` moves `pending` or `in_progress` → `completed`. `cancel_task` removes the item. After three consecutive provider rounds with no successful planning mutation, a user-role nag `<reminder>Update your todos.</reminder>` is appended to history. Every provider `complete()` is prepended with a system message that tells the model to plan before executing and names the six tools; that system message is not saved in session JSON. `todo_write` is not registered.
- Minimum useful release: US1–US6 (CRUD lifecycle + persist/resume + board + nag + system message + `todo_write` removed).

## Scope
- In scope:
  - Six LOW planning tools: `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`.
  - Per-session persist at `.cda/.todos/<session_id>.json` (process cwd). Missing or invalid file = empty list.
  - Item shape `{id, content, status}` with `status` in `pending` / `in_progress` / `completed`. `cancel_task` deletes; `cancelled` is not a stored status.
  - State machine: create → `pending`; claim `pending` → `in_progress` only; complete `pending` or `in_progress` → `completed`; cancel any stored status → removed. Multiple `in_progress` items allowed. No `owner`, no `blockedBy`.
  - Human Current Tasks board after successful `create_task` / `claim_task` / `complete_task` / `cancel_task` / `list_tasks`.
  - JSON: existing `tool_result` only; no new event type.
  - Nag reminder after 3 provider rounds without a successful planning mutation.
  - Fixed system message prepended on every provider `complete()`, not stored in session JSON.
  - Unregister `todo_write`; no leftover handler or unused planning entry points for that name.
  - Proof tests for create/list/get/claim/complete/cancel, persist/resume/session isolation, illegal transitions, nag, system message, human board, and unknown `todo_write`.
- Out of scope / non-goals:
  - `blockedBy` / `blocks` dependency graph, cycle detection, `can_start` gating.
  - `owner`, claim locking, one-`in_progress`-at-a-time, Session 17 autonomous claiming.
  - One JSON file per task; cwd `.tasks/`; CC `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` names.
  - `todo_write`; `priority`; `activeForm`; `description`; stored `cancelled`.
  - Session 10 dynamic CLAUDE.md / instruction-file assembly.
  - Session 06 subagents; Session 04 hooks.
  - New JSON event types.
  - Storing the board on `.cda/.sessions/<id>.json`.
  - Permission-gate changes; planning tools are LOW and skip authorize.
- Preserved behavior:
  - Feature 1: workspace bound, `glob` alias, concurrent batch, listed-order results. Extra tools stay registered except `todo_write` is removed.
  - Feature 2: hard deny / project rules / numbered authorize for MEDIUM/HIGH; `.cda/` data root; session JSON remains `{"messages": [...]}` only; `.cda/` gitignored.
  - Env/JSON provider config, missing-config exit `2`, `max_turns` default 8, Ctrl+C exit `130`, `api_key`/`authorization` redaction.
  - Existing unittest `*_check.py` proof style.

## User Stories & Journeys (Moderate/Complex)

### User Story 1 - Create, list, and get persisted tasks (Priority: P1) 🎯 MVP
- Description: The model creates a task with non-empty `content`. An `id` is assigned if omitted. The item is `pending`. `list_tasks` returns every item for this session. `get_task` returns one item by `id`. The list is written to `.cda/.todos/<session_id>.json` before the tool result is returned.
- Why this priority: Without create/list/get and a file, there is no planning subsystem.
- Independent Test: `invoke` / `QueryEngine.turn` create then list/get; read `.cda/.todos/<session_id>.json` in a temp cwd.
- Acceptance Scenarios:
  1. Given an empty board, When `create_task` is called with `content="Write tests"` and no `id`, Then the result includes a non-empty `id`, `content="Write tests"`, `status="pending"`, and that object is in `.cda/.todos/<session_id>.json`.
  2. Given that item, When `list_tasks` is called, Then the result is a list containing that item and authorize is not called.
  3. Given that item’s `id`, When `get_task` is called with that `id`, Then the result is that item.
  4. Given an unknown `id`, When `get_task` is called, Then the result is a tool error and the file is unchanged.

### User Story 2 - Claim, complete, and cancel (Priority: P1) 🎯 MVP
- Description: `claim_task` starts a pending item. `complete_task` finishes a pending or in-progress item. `cancel_task` removes an item in any stored status. Illegal transitions and unknown ids error without mutating the list.
- Why this priority: Session 12 teaching lifecycle without the graph; cancel is the adopter-chosen delete path.
- Independent Test: `invoke` the three mutators against a temp board file; assert file contents and error cases.
- Acceptance Scenarios:
  1. Given a `pending` item, When `claim_task` is called with its `id`, Then `status` is `in_progress` on disk.
  2. Given a `pending` or `in_progress` item, When `complete_task` is called with its `id`, Then `status` is `completed` on disk and the item remains on the board.
  3. Given an item in any stored status, When `cancel_task` is called with its `id`, Then the item is absent from the list and from the file.
  4. Given an `in_progress` or `completed` item, When `claim_task` is called, Then the result is a tool error and the list is unchanged.
  5. Given a `completed` item, When `complete_task` is called, Then the result is a tool error and the list is unchanged.
  6. Given an unknown `id`, When `claim_task` / `complete_task` / `cancel_task` is called, Then the result is a tool error and the list is unchanged.

### User Story 3 - Resume and session isolation (Priority: P1) 🎯 MVP
- Description: A new QueryEngine with the same session id in the same cwd sees the same board. A different session id has its own file and an empty board unless it created items. Session JSON has no task-board fields. A missing or invalid todos file is an empty board (the process does not crash).
- Why this priority: Adopter required persist under `.cda` keyed by session id; Feature 2 forbids board fields on session JSON.
- Independent Test: Two engines, same and different session ids; corrupt JSON file; inspect session JSON keys.
- Acceptance Scenarios:
  1. Given `.cda/.todos/<id>.json` with one item, When a new QueryEngine with that session id `list_tasks`, Then it returns that item and authorize is not called.
  2. Given that file, When a QueryEngine with a different session id `list_tasks`, Then it returns an empty list and does not read or write the first session’s file except by its own mutations.
  3. Given a later turn that only appends messages, When the session is saved, Then `.cda/.sessions/<id>.json` still has no task-board fields and the todos file is unchanged except by planning mutations.
  4. Given a missing todos file, When `list_tasks` runs, Then the result is an empty list.
  5. Given a todos file that is not a JSON array of valid items, When `list_tasks` runs, Then the result is an empty list and the process does not crash.

### User Story 4 - Human board and JSON tool_result (Priority: P1) 🎯 MVP
- Description: After a successful planning mutation or `list_tasks`, human mode prints a Current Tasks board. JSON mode emits the existing `tool_result` event whose content includes the tool’s result (item or list). No new event type is added.
- Why this priority: The user must see the plan; Feature 1 JSON consumers must not break.
- Independent Test: TerminalUI / QueryEngine events in human vs `--json`.
- Acceptance Scenarios:
  1. Given human mode, When `create_task` / `claim_task` / `complete_task` / `cancel_task` / `list_tasks` succeeds, Then output includes a line `## Current Tasks` and one line per remaining item showing that item’s status marker, `id`, and `content`.
  2. Given an empty board and human mode, When `list_tasks` succeeds, Then output includes `## Current Tasks` and no item lines.
  3. Given `--json`, When the same calls succeed, Then events include `type=tool_result` for that call and do not include a new event type for the board.
  4. Given human mode, When `get_task` succeeds, Then a `tool_result` is shown and a full-board reprint is not required.

### User Story 5 - Nag reminder and system message (Priority: P1) 🎯 MVP
- Description: Every provider `complete()` receives a first message with `role=system` whose content tells the model to plan before executing and names the six planning tools. That system message is not stored in session JSON. After three consecutive provider rounds in the turn loop with no successful `create_task` / `claim_task` / `complete_task` / `cancel_task`, a user message `<reminder>Update your todos.</reminder>` is appended to history before the next `complete()`. A successful planning mutation resets the counter. `list_tasks` and `get_task` do not reset it. Injecting the nag also resets the counter.
- Why this priority: Session 05 nag plus adopter-locked system message; these are the loop-level observables.
- Independent Test: Fake provider records `complete()` history; assert first message; drive three no-mutation rounds then inspect the fourth history.
- Acceptance Scenarios:
  1. Given any `QueryEngine.turn`, When `complete()` is called, Then `history[0].role` is `system` and its content includes `plan before executing` and the six tool names `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`.
  2. Given that turn saves the session, When `.cda/.sessions/<id>.json` is loaded, Then it has no system-role message from this feature.
  3. Given three consecutive `complete()` rounds whose tool batches contain no successful planning mutation, When the fourth `complete()` is about to run, Then history includes a user message whose content is exactly `<reminder>Update your todos.</reminder>`.
  4. Given a successful `create_task` (or claim/complete/cancel) in a round, When later rounds are counted, Then the nag counter is 0 after that round.
  5. Given three rounds of only `list_tasks` or `get_task` or text-only replies, When the fourth `complete()` runs, Then the nag was injected (reads do not reset the counter).

### User Story 6 - `todo_write` removed; errors stay isolated (Priority: P1) 🎯 MVP
- Description: `todo_write` is not a registered tool. Calling it is the same unknown-tool path as any other missing name. Empty `content`, duplicate `id` on create, and missing required arguments are tool errors and do not mutate the board. A failed planning call does not skip siblings in the same assistant message.
- Why this priority: Adopter required no duplicated or dead planning code; Feature 1 sibling isolation stays.
- Independent Test: `registry.get("todo_write")`; `invoke("todo_write", ...)`; mixed batch with one bad `create_task` and one good sibling.
- Acceptance Scenarios:
  1. Given the live registry, When `todo_write` is looked up or invoked, Then it is unknown (`invoke` returns unknown-tool error) and provider tool schemas do not include `todo_write`.
  2. Given `create_task` with empty or missing `content`, When it returns, Then it is a tool error and `.cda/.todos/<session_id>.json` is unchanged (still missing or previous items only).
  3. Given an existing id, When `create_task` is called with that same `id`, Then it is a tool error and the existing item is unchanged.
  4. Given one assistant message listing a failing `create_task` then a `list_tasks`, When the batch finishes, Then `list_tasks` still has a result (empty or prior items) and history order is listed order.

## Requirements (Moderate/Complex)
- `REQ-001`: Six LOW planning tools are registered: `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`. They skip authorize. Priority: Must. Validation: registry, `QueryEngine.turn`. Linked story: US1, US2, US6.
- `REQ-002`: `todo_write` is not registered. No handler, schema, or other live entry point remains for that name. Unknown-tool behavior matches any other missing name. Priority: Must. Linked story: US6.
- `REQ-003`: Each stored item is an object with string `id`, non-empty string `content`, and `status` in exactly `{pending, in_progress, completed}`. No `priority`, `activeForm`, `description`, `owner`, `blockedBy`, or stored `cancelled`. Priority: Must. Linked story: US1, US2.
- `REQ-004`: The board for session id S is the JSON array at process-cwd `.cda/.todos/S.json`. On `QueryEngine.turn`, S is the engine’s session id. Bare `invoke` of a planning tool uses S=`default` when no turn is in progress. Missing file or non-array / invalid contents = empty list (no crash). A successful mutation writes the full array (creating `.cda/.todos/` if needed) before the tool result is returned. Priority: Must. Linked story: US1, US3.
- `REQ-005`: Session files stay `{"messages": [...]}` only under `.cda/.sessions/`. They must not contain task-board fields. The nag user message may appear in `messages` because it is history. The system message must not. Priority: Must. Linked story: US3, US5.
- `REQ-006`: `create_task` requires `content` (non-empty string). Optional `id` if omitted is assigned a unique non-empty string in this session’s list. Optional `id` if provided and already present is a tool error. New items are `pending`. Priority: Must. Linked story: US1, US6.
- `REQ-007`: `list_tasks` takes no required arguments and returns this session’s list (possibly empty). Priority: Must. Linked story: US1.
- `REQ-008`: `get_task` requires `id`. Known id returns that item. Unknown id is a tool error; list unchanged. Priority: Must. Linked story: US1.
- `REQ-009`: `claim_task` requires `id`. Only `pending` → `in_progress`. Any other stored status or unknown id is a tool error; list unchanged. Multiple items may be `in_progress`. Priority: Must. Linked story: US2.
- `REQ-010`: `complete_task` requires `id`. `pending` or `in_progress` → `completed`. `completed` or unknown id is a tool error; list unchanged. Completed items stay on the board. Priority: Must. Linked story: US2.
- `REQ-011`: `cancel_task` requires `id`. Any stored status removes that item from the list and file. Unknown id is a tool error; list unchanged. Priority: Must. Linked story: US2.
- `REQ-012`: There is no `blockedBy` / `blocks` check and no `owner`. Claim and complete are not dependency-gated. Priority: Must. Linked story: US2.
- `REQ-013`: After a batch, the on-disk list equals sequential application of successful planning mutations in listed order. A failed or denied sibling does not skip remaining listed calls. `list_tasks` / `get_task` in the same batch are not required to observe sibling mutations. Priority: Must. Linked story: US6.
- `REQ-014`: Human mode, after a successful `create_task`, `claim_task`, `complete_task`, `cancel_task`, or `list_tasks`, prints a board whose first line is `## Current Tasks`. Each remaining item is one line containing a status marker, the `id`, and the `content`. Markers: pending `[ ]`, in_progress `[>]`, completed `[x]`. Empty board prints the heading and no item lines. `get_task` does not have to reprint the full board. Priority: Must. Linked story: US4.
- `REQ-015`: JSON mode does not add an event type. Planning tool outcomes use existing `tool` / `tool_result` events. Board text is not required in JSON. Priority: Must. Linked story: US4.
- `REQ-016`: On every provider `complete()`, the engine prepends one `role=system` message (not stored in session JSON) whose content includes the phrase `plan before executing` and the six tool names in REQ-001. Priority: Must. Linked story: US5.
- `REQ-017`: Count provider rounds in the turn loop. A round with at least one successful `create_task` / `claim_task` / `complete_task` / `cancel_task` resets the count to 0. `list_tasks`, `get_task`, text-only replies, failed planning calls, and non-planning tools do not reset it. When the count is 3 before the next `complete()`, append a user message whose content is exactly `<reminder>Update your todos.</reminder>` and reset the count to 0. Priority: Must. Linked story: US5.
- `REQ-018`: Planning tools do not consult project permission rules and do not call authorize. Hard deny lists do not apply to these tools. Priority: Must. Linked story: US1, US6.
- `REQ-019`: `.cda/` remains gitignored (covers `.todos`). The CLI does not write cwd `.todos/` or `.tasks/` outside `.cda/`. Priority: Must. Linked story: US3.

## Acceptance Criteria
- `AC-001`: Given `registry.get("create_task")` (and the other five names), When inspected, Then each is registered LOW Planning (or equivalent LOW risk) and `registry.get("todo_write")` is `None`. Provider schemas from the engine do not include `todo_write`. Covers REQ-001, REQ-002. Proof: `python3 tests/tools_check.py`.
- `AC-002`: Given `invoke("todo_write", todos=[])`, When it returns, Then `status` is `error` and the error names an unknown tool. Covers REQ-002. Proof: `python3 tests/tools_check.py`.
- `AC-003`: Given a temp cwd and `QueryEngine` session id `s1`, When the model calls `create_task` with `content="Write tests"` and no `id`, Then the tool result has non-empty `id`, `content="Write tests"`, `status="pending"`, and `.cda/.todos/s1.json` is a JSON array containing that object. Bare `invoke("create_task", content="Write tests")` with no turn in progress writes `.cda/.todos/default.json` instead. Covers REQ-003, REQ-004, REQ-006. Proof: `python3 tests/query_engine_check.py` and `python3 tests/tools_check.py`.
- `AC-004`: Given that item on `default` or `s1`, When `list_tasks` runs for the same session id, Then the result is a list containing it. When `get_task` runs with that `id`, Then the result is that item. Covers REQ-007, REQ-008. Proof: `python3 tests/tools_check.py`.
- `AC-005`: Given an unknown `id`, When `get_task` / `claim_task` / `complete_task` / `cancel_task` runs, Then each is a tool error and the session’s todos file is unchanged. Covers REQ-008, REQ-009, REQ-010, REQ-011. Proof: `python3 tests/tools_check.py`.
- `AC-006`: Given a `pending` item, When `claim_task` runs, Then disk `status` is `in_progress`. When `complete_task` then runs, Then disk `status` is `completed` and the item is still in the array. Covers REQ-009, REQ-010. Proof: `python3 tests/tools_check.py`.
- `AC-007`: Given a `pending` item, When `complete_task` runs without claim, Then disk `status` is `completed`. Covers REQ-010. Proof: `python3 tests/tools_check.py`.
- `AC-008`: Given an `in_progress` item, When `claim_task` runs, Then it is a tool error and `status` stays `in_progress`. Given a `completed` item, When `complete_task` or `claim_task` runs, Then it is a tool error and the item is unchanged. Covers REQ-009, REQ-010. Proof: `python3 tests/tools_check.py`.
- `AC-009`: Given two `pending` items, When both are `claim_task`’d, Then both are `in_progress` (no single-active lock). Covers REQ-009, REQ-012. Proof: `python3 tests/tools_check.py`.
- `AC-010`: Given an item in `pending` or `completed`, When `cancel_task` runs with its `id`, Then the item is absent from `.cda/.todos/s1.json`. Covers REQ-011. Proof: `python3 tests/tools_check.py`.
- `AC-011`: Given `create_task` with `content=""` or omitted `content`, When it returns, Then it is a tool error and no new item is written. Covers REQ-006. Proof: `python3 tests/tools_check.py`.
- `AC-012`: Given an existing `id`, When `create_task` is called with that `id` and new `content`, Then it is a tool error and the original item is unchanged. Covers REQ-006. Proof: `python3 tests/tools_check.py`.
- `AC-013`: Given `.cda/.todos/s1.json` with one item, When a new `QueryEngine` with session id `s1` in that cwd runs `list_tasks`, Then it returns that item. Covers REQ-004. Proof: `python3 tests/query_engine_check.py`.
- `AC-014`: Given that file, When a `QueryEngine` with session id `s2` runs `list_tasks`, Then it returns `[]` and `.cda/.todos/s1.json` is unchanged. Covers REQ-004. Proof: `python3 tests/query_engine_check.py`.
- `AC-015`: Given a saved session after `create_task`, When `.cda/.sessions/<id>.json` is loaded, Then top-level keys do not include a task-board field (only `messages` as today) and no message has `role=system`. Covers REQ-005, REQ-016. Proof: `python3 tests/session_check.py` or `python3 tests/query_engine_check.py`.
- `AC-016`: Given no todos file, When `list_tasks` runs, Then the result is `[]`. Given a file whose contents are `{not: "an array"}`, When `list_tasks` runs, Then the result is `[]` and the process does not crash. Covers REQ-004. Proof: `python3 tests/tools_check.py`.
- `AC-017`: Given `QueryEngine.turn` with one `create_task` and an authorize recorder, When the turn finishes, Then authorize was not called and a tool result is present. Covers REQ-001, REQ-018. Proof: `python3 tests/query_engine_check.py`.
- `AC-018`: Given a FakeProvider, When `turn` calls `complete()`, Then the first history message has `role="system"` and content includes `plan before executing` and `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`. Covers REQ-016. Proof: `python3 tests/query_engine_check.py`.
- `AC-019`: Given three consecutive rounds that only return assistant text (no planning mutation), When the fourth `complete()` is invoked, Then the history passed in includes a user message with content exactly `<reminder>Update your todos.</reminder>`. Covers REQ-017. Proof: `python3 tests/query_engine_check.py`.
- `AC-020`: Given a round whose batch includes a successful `create_task`, When the next two rounds are text-only, Then the third following `complete()` does not yet include a new nag from that window (counter reset). Covers REQ-017. Proof: `python3 tests/query_engine_check.py`.
- `AC-021`: Given three consecutive rounds whose only tools are `list_tasks` or `get_task`, When the fourth `complete()` is invoked, Then the nag user message is present. Covers REQ-017. Proof: `python3 tests/query_engine_check.py`.
- `AC-022`: Given human-mode UI, When `list_tasks` succeeds on a board with one pending item `id=t1` `content=Write tests`, Then output contains `## Current Tasks` and a line containing `[ ]`, `t1`, and `Write tests`. Covers REQ-014. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-023`: Given human-mode UI, When the same board is empty, Then `list_tasks` output contains `## Current Tasks` and does not contain `[ ]`, `[>]`, or `[x]` item lines. Covers REQ-014. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-024`: Given `--json` / `json_mode`, When `create_task` succeeds, Then events include `type=tool_result` and do not include a type other than the Feature 1 set (`text`, `tool`, `tool_denied`, `error`, `status`, `tool_result`). Covers REQ-015. Proof: `python3 tests/query_engine_check.py` or `python3 tests/terminal_ui_check.py`.
- `AC-025`: Given one assistant message listing a failing `create_task` (empty content) then `list_tasks`, When the batch finishes, Then history has the error result then the list result, in that order. Covers REQ-013, REQ-006. Proof: `python3 tests/query_engine_check.py`.
- `AC-026`: Given `.gitignore` at the repository root, When it is read, Then it contains a `.cda/` ignore entry (so `.cda/.todos/` is ignored). After a successful `create_task` in a temp cwd, When paths are inspected, Then `.cda/.todos/<id>.json` exists and cwd `.todos/` and cwd `.tasks/` do not. Covers REQ-019. Proof: `python3 tests/cli_check.py` and `python3 tests/query_engine_check.py`.

## Success Criteria (Measurable Outcomes)
- `SC-001`: In one REPL session the model can create three steps, claim or complete them, cancel one, and the user sees Current Tasks update without an authorize prompt.
- `SC-002`: Restarting the CLI with `--session <id>` in the same cwd shows the same board via `list_tasks`; a different `--session` starts empty.
- `SC-003`: After three planning-free provider rounds, the next model call’s history contains `<reminder>Update your todos.</reminder>`, and every model call in the session was prefixed with a system planning message that is not in the session file.
- `SC-004`: `todo_write` is unknown; disconnecting `.cda/.todos/` read/write from the six tools makes AC-003 or AC-013 fail (no unused task tables).
- `SC-005`: `--json` consumers still parse the Feature 1 event types; the board does not require a new type.

## Constraints and Risk
- Constraints:
  - App remains Python 3.11+ stdlib-first; no pytest requirement. Linked ACs: AC-001–AC-026.
  - NFR-001 Planning tools are LOW and skip authorize. Linked ACs: AC-017.
  - NFR-002 No dead planning code: `todo_write` is unregistered; `.cda/.todos/<id>.json` is read and written by the live tools. Linked ACs: AC-001, AC-002, AC-003, AC-013.
  - NFR-003 JSON event types stay the Feature 1 set. Linked ACs: AC-024.
  - NFR-004 Session JSON stays messages-only; system message is not persisted; nag may persist as a user message. Linked ACs: AC-015, AC-018, AC-019.
  - NFR-005 Feature 1 concurrent batch and sibling isolation; Feature 2 permission gate and `.cda/` root unchanged except adding `.todos`. Linked ACs: AC-017, AC-025, AC-026.
  - NFR-006 Human board is ASCII markers `[ ]` / `[>]` / `[x]` plus `## Current Tasks`. Linked ACs: AC-022, AC-023.
  - Verification gates remain `[DEFERRED]`; proof commands are the unittest scripts on each AC.
- Dependencies/touchpoints: tool registry / `invoke`, `QueryEngine.turn` (system message, nag, session id), TerminalUI human vs JSON rendering, `.cda/.todos/`, Feature 1 extra-tool list, existing `tests/*_check.py`. SessionStore stays transcript-only.
- Risks and mitigations:
  - Removing `todo_write` breaks any prompt or model habit that calls that name. Mitigation: unknown-tool error is the existing path; system message names the six tools.
  - A fixed system message is a new prompt channel that Session 10 may replace. Mitigation: content is a locked observable; assembly from CLAUDE.md stays out of scope.
  - Teaching nag is not in Claude Code source. Mitigation: adopter locked the 3-round teaching nag; ACs pin the exact reminder string.
  - Concurrent overlapping planning mutations could race. Mitigation: REQ-013 requires listed-order apply for the on-disk list after the batch.
  - Invalid todos file treated as empty can hide user edits. Mitigation: same pattern as Feature 2 invalid rules file; process must not crash.
- Open questions (blocking only): none.

## Decisions
- Locked decisions:
  - Session 05 and Session 12 sources are in-scope references for this feature only.
  - Six LOW tools: `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`. `todo_write` removed; no duplicate or dead planning code.
  - No dependency graph, no `owner`, no claim lock, multiple `in_progress` allowed.
  - Persist one JSON list per session at `.cda/.todos/<session_id>.json`. Session JSON messages-only.
  - Fields: `id`, `content`, `status` in `pending` / `in_progress` / `completed`. No `priority` / `activeForm` / `description`. Cancel removes.
  - `complete_task` allowed from `pending` or `in_progress`. `claim_task` only from `pending`.
  - Teaching nag after 3 rounds without a successful planning mutation; exact reminder string.
  - Human board; JSON `tool_result`; no new event type.
  - Fixed system message prepended at every `complete()`; not saved.
- Related `ADR-*`: none.
