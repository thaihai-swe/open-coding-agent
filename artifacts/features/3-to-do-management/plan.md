# Implementation Plan

## Metadata
- Feature/profile: `3-to-do-management` / Complex
- Spec approved date: 2026-08-23
- Status: Draft
- Heuristics applied: `LH-001` (machine-verifiable proof commands on every seam), `LH-002` (failing tests before planning-path behavior changes)

## Lightweight Design

Brownfield change_request. `todo_write` is a stub echo. Replace it with six LOW planning tools whose board is a JSON array at `.cda/.todos/<session_id>.json`, a human Current Tasks print, a 3-round nag, and a system message prepended on every provider `complete()`.

- Approach and affected modules: add `src/tools/task_board.py` (persist + state machine + session bind + board text); rewrite `src/tools/handlers/planning.py` (six tools, no `todo_write`); bind session / prepend system / nag / serialize planning invokes in `QueryEngine`; print the board from `tool_result` in `TerminalUI`. No new orchestrator type, no domain Task entity, no session-JSON board fields, no new dependency.
- First useful slice and proof: task_board + six tools + `todo_write` gone (`AC-001`–`AC-012`, `AC-016`). Then QueryEngine session bind, persist/resume, system message, nag (`AC-013`–`AC-015`, `AC-017`–`AC-021`, `AC-025`). Then human board / JSON (`AC-022`–`AC-024`, `AC-026`).
- Key constraints or risks: planning mutations in one assistant message must apply in listed order (Feature 1 pool would race the JSON file). Bare `invoke` uses session id `default`. System message is not saved. Gates deferred — proof is the unittest scripts named in the spec.

## Technical Context

- Language/Version: Python 3.11+ (`StrEnum`, `contextvars`). Observed 3.13.13.
- Primary Dependencies: stdlib only (`json`, `pathlib`, `uuid`, `contextvars`, `unittest`). No new packages.
- Storage/Data: process-cwd `.cda/.todos/<session_id>.json` — JSON array of `{id, content, status}`. Missing or invalid file = empty list. Session transcripts stay `{"messages": [...]}` under `.cda/.sessions/`.
- Target Platform: local CLI (`python3 -m src.cli`).
- Performance Goals: none beyond Feature 1. Todos file is re-read per planning call (source of truth; no cache). Planning tools run on the main thread; other approved tools still overlap.
- Key Constraints: stdlib-first; extra tools stay except `todo_write` is removed; Feature 2 permission gate unchanged; planning tools are LOW; `max_turns` default 8; live-path only (no unused `todo_write` handler).

## Constraints
- Non-goals: `blockedBy` / `blocks` / `owner` / claim lock / cycle detection; one-file-per-task `.tasks/`; CC `TaskCreate` names; `todo_write`; `priority` / `activeForm` / `description`; Session 10 CLAUDE.md assembly; Session 06 subagents; Session 17 claiming; new JSON event types; board fields on session JSON.
- Security/trust boundaries: planning tools only mutate a gitignored JSON list under `.cda/`. They skip authorize and are not on the deny list. System message is a new prompt channel sent to the configured provider only.
- Preserved behavior: Feature 1 workspace bound, `glob` alias, concurrent batch for non-planning tools, listed-order results, sibling isolation; Feature 2 hard deny / project rules / numbered authorize; extra tools stay registered except `todo_write`; JSON types `text`, `tool`, `tool_denied`, `error`, `status`, `tool_result`; session redaction; missing-config exit 2; Ctrl+C exit 130.
- Explicit out of scope: `TaskStore` injectable path, `PlanningRouter` type, in-memory board cache, file locks, dual-write cwd `.todos/` / `.tasks/`, pytest.

## Approach

Stay inside the current layers. Presentation does not import handlers. Handlers do not import QueryEngine. Domain models stay frozen dataclasses. SessionStore stays transcript-only.

### Interfaces / data flow

```
TerminalUI.prompt  →  QueryEngine.turn(prompt)
                         bind_session(engine.session_id)
                         while turns:
                           if rounds_without_mutation >= 3:
                             append user "<reminder>Update your todos.</reminder>"
                             reset counter; save
                           Provider.complete([system_msg] + history, schemas)
                             system_msg NOT appended to history / session JSON
                           if no tool_calls: increment counter; return
                           _run_batch:
                             Feature 2 gate walk (hard deny → rules → authorize)
                             LOW planning tools skip authorize
                             emit status + tool events (listed order)
                             planning tools: invoke sequentially by listed index (main thread)
                             other approved: ThreadPoolExecutor (Feature 1)
                             emit tool_result + history (listed order); save
                           if any successful create/claim/complete/cancel: counter = 0
                           else: increment counter
                         finally: reset session bind

invoke(name, **kwargs)  →  validate_args → check_permission → handler
  handler → task_board.* using current_session_id()  (default "default")
```

`ChatMessage.role` already accepts `"system"`. `OpenAIProvider._message_payload` already forwards `role`. No provider change.

### Public seams (test surface)

| Seam | Observes | ACs |
| --- | --- | --- |
| `src.tools.invoke` / `registry` | six LOW tools registered; `todo_write` unknown; create/list/get/claim/complete/cancel; empty content; duplicate id; unknown id; illegal transitions; missing/invalid file = `[]`; writes `.cda/.todos/default.json` | AC-001–AC-012, AC-016 |
| `QueryEngine.turn` | session file `.cda/.todos/<id>.json`; other session isolated; no authorize; system message first on `complete()`; system not in session JSON; nag after 3 non-mutation rounds; reads do not reset nag; sibling isolation | AC-013–AC-015, AC-017–AC-021, AC-025 |
| `TerminalUI.event` | human board `## Current Tasks` + markers; empty board has no item lines; JSON has no new event type | AC-022–AC-024 |
| repository `.gitignore` + cwd paths | `.cda/` ignore; create writes `.cda/.todos/` not cwd `.todos/` or `.tasks/` | AC-026 |

Do not add mock seams. FakeProvider already records `complete(history, ...)`. Persist tests `os.chdir` into a temp cwd so the public path is what production uses (no injectable `todos_path`).

### Key decisions

1. **`src/tools/task_board.py` functions (chosen)**  
   Mirror `permission_rules.py`: cwd-relative path, no class, no cache, no path injection.

   | Name | Behavior |
   | --- | --- |
   | `PLANNING_TOOL_NAMES` | frozenset of the six names |
   | `PLANNING_MUTATION_NAMES` | `create_task`, `claim_task`, `complete_task`, `cancel_task` |
   | `PLANNING_BOARD_NAMES` | mutations + `list_tasks` (`get_task` excluded) |
   | `SYSTEM_MESSAGE` | one string containing `plan before executing` and the six tool names |
   | `bind_session(session_id)` / `current_session_id()` | `contextvars.ContextVar` default `"default"` |
   | `load_tasks()` / `save_tasks(items)` | `.cda/.todos/<id>.json`; missing/unreadable/non-array/invalid items → `[]`; `mkdir` on save; indent=2 |
   | `create_task(content, id=None)` | non-empty stripped `content`; assign `uuid.uuid4().hex` if `id` omitted; duplicate or blank `id` → `ValueError`; append `pending`; return `{id, content, status, tasks}` |
   | `list_tasks()` | return the list |
   | `get_task(id)` | item or `ValueError` |
   | `claim_task(id)` | `pending` → `in_progress` only; else `ValueError`; return item + `tasks` |
   | `complete_task(id)` | `pending` or `in_progress` → `completed`; else `ValueError`; return item + `tasks` |
   | `cancel_task(id)` | remove; unknown → `ValueError`; return `{id, tasks}` (remaining list) |
   | `format_board(items)` | first line `## Current Tasks`; each item `  {marker} {id} {content}` with `[ ]` / `[>]` / `[x]` |

   Valid item: `id` non-empty str, `content` non-empty str, `status` in `TODO_STATUSES`. Invalid entries dropped on load (empty board if none remain). `ponytail:` no file lock — QueryEngine runs these tools on the main thread.

   Deletion test: skip-invalid + state machine + cwd path + board text is enough complexity to keep out of `_run_batch` and out of six copy-pasted handlers. A `TaskBoard` class would only hold the cwd path — collapse to module functions (same reason as `permission_rules.py`).

2. **Session id via ContextVar, not a tool argument (chosen)**  
   QueryEngine.turn: `token = bind_session(self.session_id)` at entry; `reset` in `finally`. Bare `invoke` sees default `"default"` (REQ-004). The model never passes `session_id`.

   Deletion test: adding `session_id` to every planning schema leaks an engine concern into the provider tool list. A constructor-injected store is a hypothetical seam (one adapter).

3. **Planning tools sequential on the main thread (chosen)**  
   Feature 1 pool stays for non-planning approved calls. In `_run_batch`, after the Feature 2 gate walk and after emitting `status`/`tool` events:

   - Partition approved calls: name in `PLANNING_TOOL_NAMES` vs others.
   - Invoke planning calls in listed-index order on the main thread (`_invoke_call`).
   - Invoke the rest with `ThreadPoolExecutor` as today.
   - Emit `tool_result` + history in listed order (unchanged).

   This is the REQ-013 on-disk sequential-apply rule. `list_tasks` / `get_task` in the same batch are not required to observe sibling mutations (they still use the bound session id because they also run on the main thread, after earlier listed planning calls).

   `_run_batch` returns `(hard_denied, mutated)` where `mutated` is true iff any planning mutation result has `is_error` false. The one caller (`turn`) updates the nag counter. Do not add a router type.

4. **Nag counter on the QueryEngine instance (chosen)**  
   `self._rounds_without_planning = 0` (not persisted). Before each `complete()`: if `>= 3`, append `ChatMessage("user", "<reminder>Update your todos.</reminder>")`, reset to 0, `_save()`. After a text-only reply: increment and return. After a batch: reset on `mutated` else increment. `list_tasks` / `get_task` / failed mutations / non-planning tools do not reset. Counter survives across `turn()` calls on the same engine (so three text-only user turns can trigger the nag on the fourth). Resume of a new engine starts at 0.

5. **System message prepended, not stored (chosen)**  
   Helper `_with_system(history) -> list[ChatMessage]`: `[ChatMessage("system", SYSTEM_MESSAGE), *history]`. Pass that list to `complete()`. Do not append to `self.history`. Proof: FakeProvider.calls[0][0]; session JSON has no `role=system`.

6. **Human board from `tool_result`, no new event (chosen)**  
   Mutators return `tasks` (full list) plus the item fields. `list_tasks` returns the list. `get_task` returns only the item.

   `TerminalUI.event`: JSON mode unchanged (dump the event). Human mode: existing `[tool_result]` line when `show_tool_results`. Additionally, when `name in PLANNING_BOARD_NAMES` and not `is_error`, print `format_board(...)` even if tool results are hidden (the board is the user-visible plan, not a debug dump). Extract the list from `content["result"]` (invoke wrap) or from `content` if tests pass a list directly.

   Presentation imports `format_board` and `PLANNING_BOARD_NAMES` from `task_board` (same layering as `wildcard_label` from `permission_rules`). It does not import handlers and does not read the todos file (no session id in the UI).

7. **`todo_write` removed (chosen)**  
   `planning.py` registers only the six tools. Delete the `todo_write` function. Keep `TODO_STATUSES` in `types.py` (live, consumed by `task_board`). `invoke("todo_write", ...)` stays on the existing unknown-tool path. Provider schemas come from `registry.list_schemas()` so the name disappears from `complete()` tools automatically.

### Module map

| Path | Public seam | Responsibility | Depends on | Split / co-locate |
| --- | --- | --- | --- | --- |
| `src/tools/types.py` | `TODO_STATUSES` | Status set only | none | Already exists; keep live |
| `src/tools/task_board.py` **new** | load/save/CRUD, `bind_session`, `format_board`, name sets, `SYSTEM_MESSAGE` | Per-session JSON board + state machine | `types.TODO_STATUSES`, stdlib | Split from QueryEngine (disk + invariants) and from UI (text) |
| `src/tools/handlers/planning.py` | six `Tool` registrations | Thin handlers → `task_board`; no `todo_write` | `registry`, `task_board` | Co-locate tool schemas with the other handler modules |
| `src/tools/__init__.py` | `invoke` | Unchanged validate → check_permission → handler | `permissions` | Do not take `session_id` kwargs |
| `src/application/query_engine.py` | `QueryEngine.turn` | Bind session; prepend system; nag; serialize planning invokes | `task_board`, `invoke` | Keep as methods, not a planner type |
| `src/presentation/terminal_ui.py` | `event` | Print board on successful board-named `tool_result` | `task_board.format_board` | Same pattern as `wildcard_label` |
| `src/domain/models/chat_message.py` | `role: str` | Unchanged; `"system"` already legal | none | Do not add a SystemMessage type |
| `src/infrastructure/providers/openai.py` | `_message_payload` | Unchanged role forward | none | No touch unless a proof fails |
| `src/infrastructure/session_store.py` | `save`/`load` | Transcripts only | none | No todos fields |
| `tests/tools_check.py` | `invoke` / registry | AC-001–AC-012, AC-016; chdir | `invoke` | Extend |
| `tests/query_engine_check.py` | `QueryEngine.turn` | AC-013–AC-015, AC-017–AC-021, AC-025, AC-026 path; FakeProvider history | FakeProvider | Extend; chdir for `.cda/.todos/` |
| `tests/terminal_ui_check.py` | `TerminalUI.event` | AC-022–AC-024 | scripted output | Extend |
| `tests/cli_check.py` | `.gitignore` | AC-026 ignore line | read repo `.gitignore` | Existing Feature 2 assertion; keep |

Dependency direction (unchanged, inward):

```
presentation → application → tools / domain / infrastructure
task_board.py → types + stdlib (no QueryEngine, no UI)
planning.py handlers → task_board
QueryEngine → task_board.bind_session / name sets / SYSTEM_MESSAGE + invoke
TerminalUI → task_board.format_board + PLANNING_BOARD_NAMES
task_board ↛ invoke
handlers ↛ QueryEngine
```

### Non-functional considerations

- NFR-001 LOW skip authorize: planning tools never enter the MEDIUM/HIGH walk. Proof AC-017.
- NFR-002 no dead planning code: `todo_write` unregistered; `.cda/.todos/` read/written by `task_board` functions that the six handlers and tests call. Proof AC-001, AC-002, AC-003, AC-013.
- NFR-003 JSON event types unchanged. Proof AC-024.
- NFR-004 session JSON messages-only; system not persisted; nag may persist as user. Proof AC-015, AC-018, AC-019.
- NFR-005 Feature 1 pool for non-planning tools; Feature 2 gate unchanged; `.cda/` root gains `.todos`. Proof AC-017, AC-025, AC-026.
- NFR-006 ASCII board markers. Proof AC-022, AC-023.

## Alternatives Considered

| Option | Depth / seam / blast radius | Chosen? | Why rejected or kept |
| --- | --- | --- | --- |
| `task_board.py` functions + ContextVar session | One persist/state-machine module; handlers stay thin | Yes | Same shape as `permission_rules.py`; tests chdir + `invoke` |
| QueryEngine owns the list; handlers no-ops | All logic in the turn loop | No | Bare `invoke` would not persist (AC-003); deletion test fails — complexity would still live somewhere |
| `session_id` argument on every planning tool | Model-visible | No | Spec: engine session id / `default`; pollutes the tool schema |
| `TaskBoard(path)` class | Test-injected path | No | Hypothetical seam; one adapter |
| Keep Feature 1 pool for planning tools + file lock | Overlap | No | REQ-013 is listed-order apply, not last-writer-wins; a lock still races two `create_task`s |
| In-memory board + write on turn end | Fewer reads | No | File is source of truth; sibling mutations in one batch must land before the next listed planning call |
| New JSON event `todo` | Explicit board event | No | Spec forbids a new type; Feature 1 `tool_result` is enough |
| Print board via `status` event | Reuse `status` | No | Human line would be `[status] ## Current Tasks`; AC-022 wants the heading itself; JSON would grow a status payload |
| Persist nag counter / system message in session JSON | Survive process exit | No | Spec: system not saved; nag is history only when injected |
| Keep `todo_write` as upsert alias | Compat | No | Adopter: remove duplicate/dead planning code |
| Domain `Task` dataclass | Invariant locality | No | Spec and JSON are dicts; `permission_rules` already uses dicts; a type with one adapter is a wrapper |
| `/spec-adr` for ContextVar vs kwarg | Hard-to-reverse platform choice | No | Both stdlib; reversible in one milestone. Revisit via `/spec-adr` only if a second board backend appears |

No `/spec-adr` this slice: six-tool API, `.cda/.todos/<session_id>.json`, no graph, and `todo_write` removal are locked in `spec.md`. Remaining choices are Ponytail stdlib vs extra types.

## Complexity Tracking

| Violation / Shortcut | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| New `task_board.py` | State machine, skip-invalid load, cwd path, board text, session bind | Inlining into QueryEngine hides a second persistence contract next to the turn loop; six handlers would copy it |
| ContextVar for session id | Turn path vs bare `invoke` (`default`) | Tool-arg `session_id` leaks engine state into the model schema |
| Planning tools skipped by `ThreadPoolExecutor` | REQ-013 listed-order disk apply | Feature 1 overlap would race two mutations on one JSON file |
| Nag counter on the engine instance | REQ-017 spans batches and later `turn()` calls | A function-local counter would reset every user prompt and never fire on text-only turns |
| `ponytail:` no file lock, no cache | Main-thread planning + tiny N | Lock is unused if we already serialize; cache would hide user edits of the JSON file |
| System message built in QueryEngine from `SYSTEM_MESSAGE` | Every `complete()` must see it; history must not | Putting it in SessionStore would persist it (forbidden) |

Technical risk of session bind + sequential planning + nag is specified in REQ-004 / REQ-013 / REQ-016 / REQ-017, not unverified — no halt to `/spec-research`.

## Delivery

Ordered milestone roadmap (tracer slices; each leaves unittest proof).

1. **P1 board + six tools** — `task_board.py`; rewrite `planning.py`; delete `todo_write`. Covers AC-001–AC-012, AC-016. Proof: `python3 tests/tools_check.py`.
2. **P1 engine bind / persist / system / nag** — `bind_session` in `turn`; sequential planning invokes; `_with_system`; nag counter. Covers AC-013–AC-015, AC-017–AC-021, AC-025, AC-026 write path. Proof: `python3 tests/query_engine_check.py`.
3. **P1 human board** — `TerminalUI.event` prints `format_board` for `PLANNING_BOARD_NAMES`. Covers AC-022–AC-024. Proof: `python3 tests/terminal_ui_check.py`.
4. **Regression pack** — `python3 -m compileall -q src` and `python3 -m unittest discover -s tests -p '*_check.py'` (includes AC-026 `.gitignore` in `tests/cli_check.py`).

Rollback or migration: revert the listed files. No schema migration. No `todo_write` compat shim.

Open risks:

- Models that still call `todo_write` get unknown-tool. Mitigation: system message names the six tools; accepted by adopter.
- Fixed system message is a prompt channel Session 10 may replace. Mitigation: content is a locked observable; CLAUDE.md assembly stays out of scope.
- Teaching nag is not in Claude Code source. Mitigation: exact reminder string is in the spec.
- `corebase-specharness/project/architecture.md` still describes Feature 1 extra tools and no system prompt. Out of this skill; update via `/context-memory` if requested.
- `save_tasks` IO errors abort the call (handler raise → invoke error). Same as today’s session save.
- Verification gates still deferred; these commands are proof, not closeout.

Next step: execute `/spec-tasks` to build the executable task graph.
