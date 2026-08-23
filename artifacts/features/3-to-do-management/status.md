# Feature Status: 3-to-do-management

- Phase: Implementing
- Delivery profile: Complex
- Status: Active
- Active task: None
- Next step: /harness-verify

## Progress
- [x] Research/spec complete
- [x] Spec approved
- [x] Plan/tasks complete (Moderate/Complex only)
- [x] Plan approved
- [ ] Implementation complete
- [ ] Validation complete

## Intake
- Input type: `change_request`
- One-line restatement: Replace stub `todo_write` with six persisted planning tools, a per-session board under `.cda/.todos/`, a 3-round nag, and a fixed system message.
- Artifact name requested: `3.to-do-management` (harness slug: `3-to-do-management`)
- Why now: User invoked `/spec-requirements` with Session 05 (and Session 12 as the chosen public API) as references only. Scoped override of the starter-init “blueprint out of scope” decision for this feature only.
- Analysis: `analysis.md` absent. User skipped `/spec-research`.
- ADR conflict: none (empty log).
- Domain packs: none matched beyond default project files.

## Facts (not decisions)
- `todo_write` is already registered: category Planning, risk LOW, required arg `todos` (list). Handler validates each item `status` is in `{pending, in_progress, completed}` and returns the same list. No process-level store, no terminal board, no reminder, no tests.
- `TODO_STATUSES` in `src/tools/types.py` is `{pending, in_progress, completed}`. Schema does not require `id`, `content`, or `priority`.
- `invoke("todo_write", todos=...)` wraps the handler return as `{status: success, result: <list>}` or `{status: error, error: ...}` on invalid status.
- QueryEngine has no system prompt. `complete(history, tool schemas)` only. No reminder injection. Tool schemas include `todo_write` via the registry.
- Session files are `{"messages": [...]}` under `.cda/.sessions/`. Feature 2 locked: no extra fields on session JSON.
- Feature 1: extra tools stay registered; concurrent batch; listed-order results. This feature explicitly removes `todo_write` as a duplicate planning surface.
- Feature 2: hard deny / project rules / numbered authorize. New planning tools are LOW and skip the ask path.
- Teaching s05: one `todo_write`, in-process list, board print, nag after 3 rounds. Teaching s12: five tools, `.tasks/{id}.json`, `blockedBy`, `claim`/`owner`. Blueprint Session 12 names `TaskCreate` / `TaskUpdate` / `TaskStop`.
- `skill-enter` expected `skills/_shared/status-template.md`; this tree keeps the template at `.agents/skills/_shared/status-template.md`. Status was seeded from that template so the envelope could set `Specifying`.

## Blockers / Decisions
- Blocker:
- Locked decision: Product is the coding-agent CLI (`src/`). Session 05 and Session 12 pages are in-scope references for this feature only, not a global architecture contract.
- Locked decision: Public API is six LOW tools: `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`. `todo_write` is unregistered; no leftover handler or dead planning code.
- Locked decision: No `blockedBy` / `blocks` graph. No `owner`. No claim lock. Multiple items may be `in_progress`.
- Locked decision: One JSON list per session at `.cda/.todos/<session_id>.json`. Session JSON stays messages-only. Resume of that session id restores the board. Other session ids have their own files.
- Locked decision: Item fields are `id` (string), `content` (non-empty string), `status` in `pending` / `in_progress` / `completed`. No `priority`, `activeForm`, `description`, `owner`, or `blockedBy`. `cancelled` is not stored; `cancel_task` removes the item.
- Locked decision: `create_task(content, id?)` creates `pending` (assigns `id` if omitted; duplicate id is an error). `claim_task`: `pending` → `in_progress` only. `complete_task`: `pending` or `in_progress` → `completed`. `cancel_task`: any status, removes. Unknown id or illegal transition is a tool error; list unchanged.
- Locked decision: Teaching nag — after 3 consecutive provider rounds with no successful planning mutation, inject user message `<reminder>Update your todos.</reminder>` and reset the counter. Successful `create_task` / `claim_task` / `complete_task` / `cancel_task` also resets it. `list_tasks` / `get_task` do not.
- Locked decision: Human mode prints a Current Tasks board after each successful planning mutation and after `list_tasks`. JSON uses existing `tool_result`. No new event type.
- Locked decision: Fixed system message prepended at every provider `complete()` (plan before executing + the six tool names). Not stored in session JSON. Not Session 10 CLAUDE.md assembly.

## Blocked Recovery
- Reason:
- Owner:
- Evidence:
- Next review at:
- Recommended handoff: `/spec-plan`
