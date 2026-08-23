# Session extracts: 3-to-do-management

## Candidates

- [CANDIDATE] Planning tools persist a JSON array at `.cda/.todos/<session_id>.json`. Bare `invoke` uses session id `default`. `QueryEngine.turn` binds the engine session id via ContextVar and resets it in `finally`.
- [CANDIDATE] Planning tools run on the main thread in listed index order; other approved tools still use `ThreadPoolExecutor`. That is the REQ-013 on-disk sequential-apply rule — do not re-pool `create_task` / `claim_task` / `complete_task` / `cancel_task`.
- [CANDIDATE] The system planning message is prepended on every `complete()` and must not be appended to `history` or session JSON. The nag counter lives on the QueryEngine instance; `list_tasks` / `get_task` do not reset it.
- [CANDIDATE] Human Current Tasks is printed from `tool_result` for `PLANNING_BOARD_NAMES` using `format_board`. JSON mode keeps Feature 1 event types; no new board event.

## Post-Ship Sync

- MEM-01 [PROMOTE]: Planning public API is six LOW tools (`create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`). `todo_write` is unknown. Source: spec.md REQ-001, REQ-002; AC-001, AC-002.
- MEM-02 [PROMOTE]: Task board storage is `.cda/.todos/<session_id>.json`; session JSON stays messages-only. Source: spec.md REQ-004, REQ-005; AC-013, AC-015.

## Follow-Up

- Reopened tasks: none
- Deferred work: `corebase-specharness/project/architecture.md` still describes Feature 1 extra tools and no system prompt; update via `/context-memory` if requested.
- Next required action: `/harness-verify` artifact `3-to-do-management`.

## Triaged
