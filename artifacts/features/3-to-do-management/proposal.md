# Feature Proposal

## Metadata
- Feature slug: `3-to-do-management`
- Profile: `Complex`
- Date / owner: 2026-08-23 / adopter

## Problem & Outcome
- Problem statement: The coding-agent CLI registers `todo_write`, but the handler only echoes the payload. There is no stored plan, no terminal board, no resume, and no reminder when the model stops updating tasks. Long turns drift because the plan is not a first-class object.
- Desired observable outcome: Six LOW planning tools create, list, get, claim, complete, and cancel items on a per-session board persisted at `.cda/.todos/<session_id>.json`. Human mode prints Current Tasks after mutations and `list_tasks`. JSON keeps existing `tool_result`. After three provider rounds with no successful mutation, a nag reminder is injected. Every provider `complete()` is prefixed with a system message that tells the model to plan before executing and names the six tools. `todo_write` is gone. Session JSON stays messages-only. No dependency graph.
- Non-goals: `blockedBy` / `blocks` / `owner` / claim locking / cycle detection; one-file-per-task `.tasks/`; CC `TaskCreate`/`TaskUpdate`/`TaskList`/`TaskGet` names; `todo_write`; `priority` / `activeForm` / `description`; Session 10 CLAUDE.md assembly; Session 06 subagents; Session 17 autonomous claiming; new JSON event types; storing the board on session JSON.

## Proposed Approach
- High-level architecture / public seams:
  - Planning tools are registered LOW names: `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`. They skip authorize. `todo_write` is unregistered and has no leftover handler.
  - Store: one JSON array per QueryEngine session id at process-cwd `.cda/.todos/<session_id>.json`. Missing or invalid file = empty list. `--session` restore loads that file. A different session id uses a different file.
  - Item: `{id, content, status}` with `status` in `pending` / `in_progress` / `completed`. `cancel_task` deletes the item (no stored `cancelled`).
  - Transitions: create → `pending`; claim `pending` → `in_progress` only; complete `pending` or `in_progress` → `completed`; cancel any status → removed. Illegal transition or unknown id: tool error, list unchanged.
  - QueryEngine prepends one system message on every `complete()` (not saved). After 3 rounds without a successful mutation, it appends a user nag to history (saved).
  - Terminal: human board after successful mutation and `list_tasks`. JSON: existing `tool_result` only.
- Alternatives rejected and why (Design-it-Twice comparison):
  - Teaching s05 `todo_write` only, in-process, replace-entire-list: rejected. Adopter chose the Session 12 five-tool names, persist under `.cda`, upsert/lifecycle tools, and then `cancel_task`.
  - Full teaching s12 (`.tasks/{id}.json`, `blockedBy`, `owner`, `claim` gated on dependencies): rejected. Adopter chose no graph, one JSON list per session, `content` not `subject`+`description`.
  - Keep `todo_write` plus the six tools on the same store: rejected. Adopter: remove it; no duplicated or dead planning code.
  - Persist the board on `.cda/.sessions/<id>.json`: rejected. Feature 2 locked session JSON as messages-only.
  - New JSON event type `todo`: rejected. Feature 1 event set stays; board is human-mode text; JSON uses `tool_result`.
  - Defer all prompt work to Session 10: rejected. Adopter locked a fixed system message prepended at every `complete()`.
- Preserved behavior:
  - Feature 1: workspace bound, glob alias, concurrent batch, listed-order results, extra tools stay registered **except** `todo_write` is removed.
  - Feature 2: permission gate, `.cda/` data root, session JSON messages-only, numbered authorize for MEDIUM/HIGH. Planning tools are LOW and do not prompt.
  - `max_turns` 8, missing-config exit 2, Ctrl+C exit 130, unittest `*_check.py`.

## Risks & Dependencies
- Component dependencies: tool registry / `invoke`, `QueryEngine.turn` (system message, nag, session id), TerminalUI human rendering, `.cda/.todos/`, existing `tests/*_check.py`.
- Security or migration risks: Planning tools are LOW and skip authorize; they only mutate a JSON list under `.cda/` (already gitignored). System message is a new prompt channel; Session 10 may replace it later. Removing `todo_write` changes the provider tool list (models that call the old name get unknown-tool).
- Open questions (blocking only): none.

## Disposition
- Approval decision: `Approved`
- Next skill/action: `/spec-plan`
