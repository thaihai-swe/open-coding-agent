# Feature Specification

## Metadata
- Feature: `1-tool-and-execution`
- Profile: `Complex`
- Status: `Approved`
- Owner: adopter
- Requested artifact name: `1.tool-and-execution` (harness slug `1-tool-and-execution`)
- References (scoped, not global architecture): Session 02 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s02/

## Problem Statement
- Who is affected, what fails, and why now: A coding-agent CLI user needs Session 02 terminal + tool-dispatch behavior. Today a dispatch table exists and extra tools are registered, but file/search tools can operate outside the working directory, the ShareAI `glob` name is missing, a single model response’s tool list runs strictly serially, human prompts cannot contain newlines, assistant text is not Markdown, and live status/`tool_result` events are absent. Handler tests do not exist. This feature closes that Session 02 gap without removing later-session tools.

## Outcome
- Observable result: From `python3 -m src.cli`, a user can submit multiline prompts, see Markdown-rendered assistant text in human mode, observe live tool/status lines (or JSON events in `--json`), cancel with session preserved, and have the model use `bash`, `read_file`, `write_file`, `edit_file`, `glob` / `glob_search` (and already-registered extra tools) through one dispatch table. File/search tools refuse resolved paths outside cwd. All tool calls in one assistant message may run overlapping in time; transcript order matches the model’s listed order.
- Minimum useful release: US1–US4 (dispatch + alias + path bound + concurrent batch + live/JSON events + cancel preserve). US5–US6 complete the Session 02 terminal goal.

## Scope
- In scope:
  - Public dispatch for `bash`, `read_file`, `write_file`, `edit_file`, `glob_search`, and alias `glob`.
  - Unknown tool name → observable tool-error result; turn continues.
  - Workspace bound for `read_file`, `write_file`, `edit_file`, `glob_search`/`glob`, `grep_search` using resolved real paths.
  - Concurrent batch: every tool call listed in one assistant message may run overlapping; results appended in listed order; failures do not skip remaining calls in that batch.
  - Sequential approve/deny for tools that already require it, completed for that batch before overlapping execution starts. Denied calls do not execute.
  - Human multiline period-submit; empty first line still quits.
  - Human-mode Markdown for assistant `text` events only.
  - Additive JSON events: keep `text`, `tool`, `tool_denied`, `error`; add `status` and `tool_result`. JSON is never Markdown.
  - Live human-mode lines for tool start, tool result, and status.
  - Ctrl+C still preserves session (exit 130).
- Out of scope / non-goals:
  - Permission modes, deny-list expansion, AST command analysis (Session 03+).
  - Lifecycle hooks (Session 04).
  - Starting a tool before the provider stream for that assistant message finishes.
  - Persisting oversized tool results to disk.
  - Removing or hiding extra registered tools.
  - Workspace-jailing `bash` / `powershell` / `repl`.
  - High-contrast or screen-reader TTY themes (JSON mode is the machine-readable surface).
  - Image/PDF/notebook `read_file` formats from the long blueprint table.
  - Introducing pytest or third-party schema libraries as a requirement.
- Preserved behavior:
  - Extra tools remain registered; their contracts stay the same except the path bound on file/search tools and the `glob` alias.
  - Env/JSON provider config, missing-config exit `2`, `max_turns` default 8, session JSON redaction of `api_key`/`authorization` keys.
  - Existing unittest scripts remain the app proof style.

## User Stories & Journeys (Moderate/Complex)

### User Story 1 - Dispatch core tools and glob alias (Priority: P1) 🎯 MVP
- Description: The model can call `bash`, `read_file`, `write_file`, `edit_file`, `glob_search`, and `glob`. Each name reaches the matching operation through one dispatch table. Extra tools stay callable.
- Why this priority: Session 02 teaching core; without dispatch the rest of the slice is unused.
- Independent Test: Invoke each core name (and `glob`) against a temp workspace with a fake provider; extra tool names still resolve.
- Acceptance Scenarios:
  1. Given a registered dispatch table, When the model calls `read_file` / `write_file` / `edit_file` / `bash` / `glob_search` with valid in-cwd arguments, Then the matching operation runs and a tool result is appended to history.
  2. Given `glob_search` exists, When the model calls `glob` with the same arguments, Then the glob operation runs with the same observable result shape as `glob_search`.
  3. Given extra tools are registered, When the model calls `grep_search` (or another extra name), Then dispatch still finds it.
  4. Given an unknown tool name, When that call is executed, Then history records a tool-error result and the turn does not crash.

### User Story 2 - Workspace-bound file and search tools (Priority: P1) 🎯 MVP
- Description: File and search tools refuse to read, write, edit, or return paths whose resolved real location is outside the process working directory.
- Why this priority: ShareAI s02 path safety for file tools; adopter extended it to search tools.
- Independent Test: From a temp cwd, invoke file/search tools with `..`, symlink-escape, and in-cwd paths.
- Acceptance Scenarios:
  1. Given cwd is a temp project, When `read_file` / `write_file` / `edit_file` / `glob_search` / `glob` / `grep_search` is given a path whose resolved real path is outside cwd, Then the tool returns an error result, no file outside cwd is created or modified, and no outside content is returned.
  2. Given a symlink inside cwd that points outside cwd, When a file/search tool follows that path, Then it is refused the same way.
  3. Given an in-cwd path, When the same tools are used, Then they operate as today (read/write/edit/match).
  4. Given `bash` with a command that could leave cwd, When it is approved, Then this slice does not add a path jail for `bash`.

### User Story 3 - Concurrent tool batch (Priority: P1) 🎯 MVP
- Description: All tool calls in one assistant message may run overlapping in time. History and events preserve the original listed order. One failure does not skip the rest of the batch. The next provider call waits until the batch finishes.
- Why this priority: Adopter chose CC-style batches with concurrency-safe set = all tools.
- Independent Test: Fake provider returns two or more tool calls in one message; observe completion overlap is allowed, history order is listed order, both results present on mixed success/failure.
- Acceptance Scenarios:
  1. Given one assistant message with N>1 tool calls, When the engine executes them, Then each call is executed (unless denied at authorize), and tool results appear in history in the same order as the calls were listed.
  2. Given one call in that list fails, When the batch finishes, Then the other calls still have results (success or error); none are silently dropped.
  3. Given tools that require approve/deny, When they appear in the list, Then prompts happen sequentially in listed order before overlapping execution of that batch; denied calls emit `tool_denied` and do not run.
  4. Given the batch is in progress, When the engine would start the next provider completion, Then it does not start until every call in the batch has a result.

### User Story 4 - Live terminal events, JSON, cancel (Priority: P1) 🎯 MVP
- Description: Human mode shows live tool/status/result lines. JSON mode emits structured events without Markdown. Cancel still saves the session.
- Why this priority: Session 02 terminal observability; JSON already exists and must stay a contract.
- Independent Test: TerminalUI event tests; CLI KeyboardInterrupt still 130 with session file present.
- Acceptance Scenarios:
  1. Given human mode, When a tool starts and finishes, Then the user sees a tool-start line and a tool-result line (plain text, not Markdown).
  2. Given a batch or long operation, When execution is underway, Then at least one `status` line/event is emitted.
  3. Given `--json`, When the same turn runs, Then stdout/event stream includes JSON objects with `type` in `text`, `tool`, `tool_denied`, `error`, `status`, `tool_result` as applicable, and no event payload is Markdown-rendered.
  4. Given an in-progress REPL, When the user cancels (KeyboardInterrupt), Then the session is saved and the process exits 130.

### User Story 5 - Multiline period-submit (Priority: P2)
- Description: Human-mode prompts may contain newlines. A line that is only `.` submits. EOF submits accumulated text. An empty first line still quits.
- Why this priority: Completes Session 02 terminal input; not required to prove dispatch.
- Independent Test: TerminalUI.prompt with a scripted line sequence.
- Acceptance Scenarios:
  1. Given human mode, When the user enters `line1`, then `line2`, then `.`, Then the engine receives `line1\nline2` (period line omitted).
  2. Given human mode, When the first line is empty, Then the REPL exits as it does today (no turn).
  3. Given human mode with at least one non-empty line accumulated, When input hits EOF, Then the accumulated text is submitted.
  4. Given `--json` mode, When prompting, Then the same submit rules apply (JSON affects output events, not prompt assembly).

### User Story 6 - Markdown assistant text (Priority: P2)
- Description: In human mode, assistant `text` events render as Markdown. Tool, status, and error lines stay plain. JSON never Markdown-renders.
- Why this priority: Local Session 02 renderer goal; isolated from dispatch.
- Independent Test: Feed a `text` event containing a Markdown heading or emphasis; human output shows rendered structure; JSON output contains the original string.
- Acceptance Scenarios:
  1. Given human mode, When an assistant `text` event contains Markdown (for example a heading or bold span), Then the printed output is Markdown-rendered, not the raw markers alone.
  2. Given human mode, When a `tool`, `tool_result`, `status`, or `error` event is emitted, Then that line is plain text.
  3. Given JSON mode, When a `text` event contains Markdown source, Then the JSON `content` is the original string.

## Requirements (Moderate/Complex)
- `REQ-001`: Dispatch table maps each public tool name to one operation; adding a name must not require changing the turn loop. Rationale: ShareAI s02 “add a tool, add one handler”. Priority: Must. Validation: `invoke` / registry public seam. Linked story: US1.
- `REQ-002`: `glob` and `glob_search` are public names for the same glob operation; both appear in the tool list offered to the provider. Priority: Must. Validation: schemas + invoke. Linked story: US1.
- `REQ-003`: Unknown tool names yield a tool-error result and do not abort the process. Priority: Must. Validation: QueryEngine.turn. Linked story: US1.
- `REQ-004`: Extra registered tools remain available. Priority: Must. Validation: registry membership. Linked story: US1.
- `REQ-005`: `read_file`, `write_file`, `edit_file`, `glob_search`/`glob`, `grep_search` refuse resolved real paths outside process cwd; no outside read or write. Priority: Must. Validation: handler/invoke. Linked story: US2.
- `REQ-006`: `bash` is not workspace-jailed by this feature. Priority: Must. Validation: spec + no new bash path error for cwd escape. Linked story: US2.
- `REQ-007`: All tool calls listed in one assistant message form one concurrent batch and may run overlapping. Priority: Must. Validation: QueryEngine.turn. Linked story: US3.
- `REQ-008`: Batch results (including errors) are recorded in the original listed order. Priority: Must. Linked ACs: AC-009. Linked story: US3.
- `REQ-009`: A failed call does not skip remaining calls in that batch. Priority: Must. Linked story: US3.
- `REQ-010`: Authorize prompts for tools that already require approval are sequential in listed order and finish before overlapping execution of that batch; deny means that call does not run. Priority: Must. Linked story: US3.
- `REQ-011`: The next provider completion for the turn starts only after the current batch has a result for every listed call. Priority: Must. Linked story: US3.
- `REQ-012`: Human mode emits live tool-start, tool-result, and status lines. Priority: Must. Linked story: US4.
- `REQ-013`: JSON mode keeps `text`, `tool`, `tool_denied`, `error` and adds `status` and `tool_result`; payloads are not Markdown-rendered. Priority: Must. Linked story: US4, US6.
- `REQ-014`: KeyboardInterrupt saves session and exits 130. Priority: Must. Linked story: US4.
- `REQ-015`: Human multiline submit is a solo `.` line; empty first line quits; EOF submits accumulated text. Priority: Must. Linked story: US5.
- `REQ-016`: Human mode Markdown-renders assistant `text` only. Priority: Must. Linked story: US6.

## Acceptance Criteria
- `AC-001`: Given a temp cwd with `hello.txt`, When `invoke("read_file", file_path="hello.txt")` (or QueryEngine.turn with that tool call) runs, Then the result contains the file’s text and is not an error. Covers REQ-001 / US1. Proof: `python3 tests/tools_check.py` (new) and existing `python3 tests/query_engine_check.py`.
- `AC-002`: Given the same cwd, When the model/tool name is `glob` and when it is `glob_search` with the same pattern, Then both succeed and return the same match set for that pattern. Covers REQ-002. Proof: `python3 tests/tools_check.py`.
- `AC-003`: Given the provider tool list for a turn, When it is inspected, Then it contains both names `glob` and `glob_search`. Covers REQ-002. Proof: `python3 tests/tools_check.py`.
- `AC-004`: Given a tool call name that is not registered, When QueryEngine executes that call, Then history includes a tool result with an error, process exit is not used, and a later assistant completion in the same turn can still run. Covers REQ-003. Proof: `python3 tests/query_engine_check.py`.
- `AC-005`: Given current extra tools, When the registry is listed, Then names beyond the Session 02 five (at least `grep_search`) are still present and `invoke` resolves them. Covers REQ-004. Proof: `python3 tests/tools_check.py`.
- `AC-006`: Given cwd `P`, When `write_file` / `read_file` / `edit_file` / `glob_search` / `glob` / `grep_search` is invoked with a path whose resolved real path is outside `P` (including `..` and a symlink inside `P` that points outside `P`), Then the result is an error, no file outside `P` is created or changed, and no outside file contents are returned. Covers REQ-005. Proof: `python3 tests/tools_check.py`.
- `AC-007`: Given an in-cwd relative path, When those file/search tools run, Then they succeed as they do for valid in-cwd paths today. Covers REQ-005. Proof: `python3 tests/tools_check.py`.
- `AC-008`: Given an approved `bash` call whose command references a path outside cwd, When this feature’s tests run, Then there is no new workspace-bound rejection from the bash tool itself. Covers REQ-006. Proof: `python3 tests/tools_check.py`.
- `AC-009`: Given one assistant message with two tool calls A then B, When the batch completes, Then history has A’s result then B’s result in that order even if B finishes first. Covers REQ-007, REQ-008. Proof: `python3 tests/query_engine_check.py`.
- `AC-010`: Given one assistant message with two calls where the first handler fails, When the batch completes, Then the second call still has a result in history. Covers REQ-009. Proof: `python3 tests/query_engine_check.py`.
- `AC-011`: Given a MEDIUM or HIGH tool in the list, When authorize returns false for that call, Then `tool_denied` is emitted, that handler does not run, and other listed calls still receive results. Covers REQ-010. Proof: `python3 tests/query_engine_check.py`.
- `AC-012`: Given authorize returns true for required tools, When prompts are issued, Then they occur one after another in listed order before overlapping execution of that batch begins. Covers REQ-010. Proof: `python3 tests/query_engine_check.py`.
- `AC-013`: Given a batch of two calls, When QueryEngine would request the next provider completion, Then that completion is not requested until both calls have results. Covers REQ-011. Proof: `python3 tests/query_engine_check.py`.
- `AC-014`: Given human mode (json_mode false), When a tool runs, Then events include tool-start and tool-result as distinct observable events, printed as plain lines. Covers REQ-012. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-015`: Given a tool batch starts, When execution is underway, Then a `status` event is emitted at least once. Covers REQ-012. Proof: `python3 tests/terminal_ui_check.py` and `python3 tests/query_engine_check.py`.
- `AC-016`: Given json_mode true, When text, tool start, deny, error, status, and tool result occur, Then each is a JSON object with `type` equal to `text` | `tool` | `tool_denied` | `error` | `status` | `tool_result` respectively, and string fields are not Markdown-rendered. Covers REQ-013. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-017`: Given an active REPL with a created session, When KeyboardInterrupt is raised during the prompt loop, Then exit code is 130 and the session file exists. Covers REQ-014. Proof: `python3 tests/cli_check.py`.
- `AC-018`: Given human prompt input lines `hello`, `world`, `.`, When `TerminalUI.prompt` returns, Then the value is `hello\nworld`. Covers REQ-015. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-019`: Given the first prompt line is `""`, When `prompt` returns, Then the value is empty (REPL exit). Covers REQ-015. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-020`: Given accumulated non-empty lines and then EOF, When `prompt` returns, Then it returns the accumulated text without requiring a `.` line. Covers REQ-015. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-021`: Given human mode and a `text` event whose content is `# Title` or contains `**bold**`, When `TerminalUI.event` prints it, Then the output is Markdown-rendered (raw `#`/`**` markers are not the sole formatting). Covers REQ-016. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-022`: Given human mode, When `tool` / `tool_result` / `status` / `error` events print, Then those lines are not Markdown-rendered. Covers REQ-016. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-023`: Given json_mode and a `text` event with Markdown source, When printed, Then JSON `content` equals the original source string. Covers REQ-013, REQ-016. Proof: `python3 tests/terminal_ui_check.py`.

## Success Criteria (Measurable Outcomes)
- `SC-001`: The four ShareAI s02 try-it tasks (read a file and summarize, create then re-read a file, find files by pattern, read two files then write a summary) can be completed in one REPL session without path-escape success and without renaming `glob_search`.
- `SC-002`: A user can paste a two-line prompt and submit with a `.` line; assistant Markdown is readable in human mode; `--json` consumers parse event types without stripping markup.
- `SC-003`: Cancel during a session does not lose already-saved turns (session file present, exit 130).

## Constraints and Risk
- Constraints:
  - App remains Python 3.11+ stdlib-first; no requirement to add pytest. Linked ACs: AC-001–AC-023.
  - Security policy is still `[DEFERRED]` at repo level; this feature still must implement the locked cwd real-path bound. Linked ACs: AC-006, AC-007.
  - Verification gates are `[DEFERRED]`; proof commands are the unittest scripts named on each AC. Closeout cannot be `Done` without later gate confirmation or override.
  - NFR-001 workspace bound: Linked ACs AC-006, AC-007.
  - NFR-002 listed-order results under concurrency: Linked ACs AC-009, AC-010, AC-013.
  - NFR-003 session durability on cancel: Linked ACs AC-017.
  - NFR-004 JSON is machine-readable, not Markdown: Linked ACs AC-016, AC-023.
  - NFR-005 Markdown only on human assistant text: Linked ACs AC-021, AC-022.
- Dependencies/touchpoints: `QueryEngine.turn`, tool registry/`invoke`, file_io and search handlers, `TerminalUI`, `run()` REPL loop, `SessionStore`, existing `tests/*_check.py`.
- Risks and mitigations:
  - All-tool concurrency can race overlapping writes and shells. Mitigation: sequential authorize; results ordered after completion; document race as accepted for this slice.
  - `bash` can still escape cwd. Mitigation: explicit non-goal; Session 03 territory.
  - Markdown renderer quality is subjective. Mitigation: AC-021 only requires observable rendering of heading or emphasis, not a specific library.
- Open questions (blocking only): none.

## Decisions
- Locked decisions:
  - Full local Session 02 goal (dispatch + path bound + concurrent batches + multiline + Markdown + live status + JSON + cancel-preserves-session).
  - Extra tools stay registered.
  - File and search tools workspace-bound via resolved real path; symlink escape refused.
  - `glob_search` remains; `glob` is an alias also advertised to the provider.
  - Concurrency-safe set = all registered tools; one assistant message = one concurrent batch.
  - Failed call does not skip the rest of the batch; history order = listed order.
  - Multiline submit = solo `.` line; empty first line quits; EOF submits accumulated text.
  - Human Markdown on assistant `text` only; JSON additive `status` + `tool_result`.
  - Authorize stays sequential before overlapping execute (derived from preserved MEDIUM/HIGH prompts + concurrent batch).
- Related `ADR-*`: none.
