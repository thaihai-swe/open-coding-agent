# Feature Proposal

## Metadata
- Feature slug: `1-tool-and-execution`
- Profile: `Complex`
- Date / owner: 2026-08-22 / adopter

## Problem & Outcome
- Problem statement: The CLI already dispatches many tools and has JSON events plus Ctrl+C session save, but Session 02 is not met: file/search tools can escape the working directory, `glob` is not a public name, tool calls from one model response run only one-at-a-time, human input is single-line, assistant text is not Markdown, and live status/`tool_result` events are missing. `src/tools/` has no tests.
- Desired observable outcome: A user can drive the REPL through Session 02 tasks (read, write, edit, glob, multi-call) with workspace-bound file/search tools, overlapping execution of a response’s tool list, multiline period-submit, Markdown assistant text in human mode, additive JSON events, and session preserved on cancel. Extra tools stay registered.
- Non-goals: Permission-mode redesign (Session 03), lifecycle hooks (Session 04), starting tools before the model finishes streaming, persisting oversized tool results to disk, Pydantic/pytest, deleting extra tools, jailing `bash`, high-contrast TTY themes.

## Proposed Approach
- High-level architecture / public seams:
  - Tool registry remains the name→handler dispatch table. `glob` and `glob_search` are two public names for one glob operation.
  - File/search tools refuse work when the resolved real path is outside process cwd.
  - QueryEngine treats all tool calls in one assistant message as one concurrent batch; results are recorded in listed order. Tools that already require user approval are prompted sequentially for that batch before overlapping execution starts.
  - Terminal: period-submit multiline prompts; human-mode Markdown for assistant text only; live `status` / `tool` / `tool_result` lines; JSON mode stays raw and additive.
- Alternatives rejected and why (Design-it-Twice comparison):
  - Teaching-only s02 (no Markdown/multiline): rejected; adopter chose the full local Session 02 goal.
  - CC partition (only read/search concurrent): rejected; adopter set concurrency-safe set to **all** registered tools, so one assistant message is one concurrent batch.
  - Rename `glob_search` → `glob`: rejected; keep current name and add alias.
  - Lexical `..` jail without following symlinks: rejected; real-path escape must fail.
  - Abort batch or turn on first tool error: rejected; remaining calls still run; history stays listed order.
- Preserved behavior:
  - Extra tools stay registered with existing contracts except file/search path bound and `glob` alias.
  - Empty first prompt line still exits the REPL.
  - Missing provider config still exits `2`.
  - Ctrl+C still saves session and exits `130`.
  - MEDIUM/HIGH tools still require approve/deny.
  - `max_turns` default 8 still stops the loop.
  - Existing JSON event types `text`, `tool`, `tool_denied`, `error` remain valid.

## Risks & Dependencies
- Component dependencies: QueryEngine turn loop, tool registry/invoke, file_io/search handlers, TerminalUI, SessionStore, existing `tests/*_check.py`.
- Security or migration risks: All-tool concurrency can race overlapping writes/shell; path bound does not jail `bash`. Approval prompts stay sequential to avoid stdin races. `.secrets/` still not gitignored (out of this slice).
- Open questions (blocking only): none after two grilling rounds.

## Disposition
- Approval decision: `Approved`
- Next skill/action: `/spec-plan`
