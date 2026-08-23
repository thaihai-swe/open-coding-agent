# Feature Specification

## Metadata
- Feature: `6-compact-memory`
- Profile: `Complex`
- Status: `Approved`
- Owner: adopter
- Requested artifact name: `6.compact-memory` (harness slug `6-compact-memory`)
- References (scoped, not global architecture): Session 08 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s08/

## Problem Statement
- Who is affected, what fails, and why now: A coding-agent CLI user working a long session accumulates file reads, shell output, and tool results in `QueryEngine.history`. That list is sent on every `complete()` and written to `.cda/.sessions/<id>.json`. There is no compression. A large `read_file` or many turns eventually trips the provider (`prompt_too_long`, HTTP 413 / context-length) or makes each turn slower and more expensive. Session 08 / s08 is the next roadmap slice: cheap structural compression first, then one LLM summary, plus a way for the human and the model to force compact.

## Outcome
- Observable result:
  1. Project settings live in `.cda/config.json` only. `.cda/ui-config.json` is no longer read. Missing keys use the locked defaults. Compaction knobs and `show_tool_results` share that file.
  2. Before every provider `complete()` in a turn (when `auto_compact` is true), the engine runs cheap layers in this order: L3 `tool_result_budget`, L1 `snip_compact`, L2 `micro_compact`. If history still exceeds `max_messages` **or** estimated character count exceeds `max_chars`, it runs L4 `compact_history`.
  3. L3 writes oversized tool-result bodies under `.cda/task_outputs/tool-results/` and leaves a `<persisted-output>` marker plus a preview in history.
  4. L1, when message count is above `max_messages`, keeps the first `keep_head` messages and a tail that fills the budget, inserts one user placeholder `[snipped N messages from conversation middle]`, and never splits an assistant `tool_calls` message from its following `tool` results.
  5. L2 keeps the newest `keep_recent_tool_results` tool results intact and replaces older tool-result bodies longer than 120 characters with `[Earlier tool result compacted. Re-run if needed.]`.
  6. L4 writes a full JSONL snapshot to `.cda/.transcripts/`, asks the provider for a summary using the compact prompt section, and replaces the older prefix with one user message whose content is wrapped in `<compacted-summary>...</compacted-summary>`, keeping a boundary-safe recent window of `keep_recent` messages.
  7. `/compact` (builtin, before skill expansion) and the LOW `compact` tool both force L4. A context-length / `prompt_too_long` provider error runs `reactive_compact` and retries at most `reactive_retries` times. L4 summarizer failures stop after `compact_fail_retries` consecutive failures without looping forever.
  8. Compacted `history` is saved to `.cda/.sessions/<id>.json`. The Feature 5 system message is still assembled on each `complete()` and is never stored in session JSON.
- Minimum useful release: US1–US6 (config cutover + cheap layers + L4 summary + invocation + reactive/circuit-breaker + prompt/transcript isolation).

## Scope
- In scope:
  - Hard cutover of project config to `.cda/config.json` (UI + compact knobs).
  - Four-layer pipeline + reactive compact, with locked defaults and per-key overrides.
  - Compaction boundary: never orphan `tool_calls` from following `tool` results.
  - Character-count estimate (sum of message `content` and serialized `tool_result` bodies). No third-party tokenizer.
  - Transcript snapshot under `.cda/.transcripts/` before L4 / reactive compact.
  - Persist path `.cda/task_outputs/tool-results/` inside process cwd.
  - Builtin `/compact` reserved before skill slash expansion.
  - LOW `compact` tool.
  - Compact prompt as markdown section `compact` (`src/prompts/compact.md` / `.cda/prompts/compact.md` / inline fallback).
  - Tests for each layer, config cutover, slash vs skill, tool, auto trigger, reactive retry, circuit breaker, boundary, session JSON, and Feature 1–5 regression.
- Out of scope / non-goals:
  - Session 09 persistent memory (`MEMORY.md`, `.memory/`, promotion, dreaming).
  - A tool that retrieves `.cda/.transcripts/` snapshots.
  - Tokenizers or tiktoken.
  - Parent-directory or home-directory persist / transcript paths.
  - Changing Feature 5 section order or instruction-file discovery.
  - Changing permission-gate enforcement or planning nag rules.
  - Reading `.cda/ui-config.json` after this feature.
- Preserved behavior:
  - Feature 1: workspace bound, concurrent batch, human/JSON events (`text`, `tool`, `tool_denied`, `error`, `status`, `tool_result`).
  - Feature 2: hard deny, project rules, numbered authorize.
  - Feature 3: six planning tools, `.cda/.todos/`, 3-round nag, messages-only session JSON (compaction may rewrite `messages` contents; it must not add sibling keys).
  - Feature 4: skill scan, `load_skill`, `/<skill-name>` expansion. `/compact` is reserved and is not treated as a skill name.
  - Feature 5: dynamic system prompt, markdown section overrides, system role never persisted.

## User Stories & Journeys (Moderate/Complex)

### User Story 1 - Unified project config (Priority: P1) 🎯 MVP
- Description: The CLI reads `.cda/config.json` for `show_tool_results` and compact settings. Missing file or missing keys use defaults. `.cda/ui-config.json` is ignored even if it exists.
- Why this priority: Adopter required one config file and a hard cutover; every other story reads these knobs.
- Independent Test: Temp cwd with only `ui-config.json`, only `config.json`, and neither; assert load results.
- Acceptance Scenarios:
  1. Given no `.cda/config.json`, When settings are loaded, Then defaults apply (`show_tool_results` true; compact defaults below).
  2. Given `.cda/config.json` sets `show_tool_results` false and `compact.max_messages` 10, When settings are loaded, Then those values are used and other compact keys stay at defaults.
  3. Given only `.cda/ui-config.json` with `show_tool_results` false and no `config.json`, When settings are loaded, Then `show_tool_results` is still the default true (old file ignored).

### User Story 2 - Cheap layers L3 then L1 then L2 (Priority: P1) 🎯 MVP
- Description: Before `complete()`, when auto compact is on, the engine persists oversized last-batch tool results, then snips a too-long middle, then placeholders old tool results. No provider call is made for these three layers.
- Why this priority: s08 “cheap first”; L4 must not see 500KB tool dumps if L3 can persist them.
- Independent Test: Pure functions on constructed `ChatMessage` lists; assert disk files, placeholders, and pair integrity.
- Acceptance Scenarios:
  1. Given last-batch tool results whose combined UTF-8 byte length exceeds `tool_result_max_bytes`, When L3 runs, Then the largest results are written under `.cda/task_outputs/tool-results/` and history keeps a `<persisted-output>` marker plus at most `persist_preview_chars` of body until the batch is at or under the budget.
  2. Given `len(history) > max_messages`, When L1 runs, Then the result length is `keep_head + 1 + tail` (tail = `max_messages - keep_head`), the placeholder is a user message `[snipped N messages from conversation middle]`, and no assistant `tool_calls` message is separated from its following tool results.
  3. Given more than `keep_recent_tool_results` tool messages and older ones longer than 120 characters, When L2 runs, Then those older bodies become `[Earlier tool result compacted. Re-run if needed.]` and the newest `keep_recent_tool_results` tool bodies are unchanged.
  4. Given history at or under every cheap threshold, When the pre-processors run, Then history is unchanged.

### User Story 3 - LLM compact and transcript (Priority: P1) 🎯 MVP
- Description: When cheap layers are not enough, or the user/model forces compact, the engine writes a JSONL transcript of the current history, asks the provider for a summary with the compact prompt, and replaces the older prefix with one `<compacted-summary>` user message plus a boundary-safe recent window of `keep_recent` messages.
- Why this priority: This is the Session 08 goal: summarization that keeps recent work.
- Independent Test: FakeProvider returns a known summary; inspect history, transcript file, and session JSON.
- Acceptance Scenarios:
  1. Given history whose estimated characters exceed `max_chars` after cheap layers, When the next `complete()` is about to run, Then a `.cda/.transcripts/<session_id>-*.jsonl` file exists with one JSON object per pre-compact message, and `history` is `[summary_user] + recent_window`.
  2. Given the summary text `SUM-BODY`, When L4 finishes, Then the first remaining message is `role=user` and its content contains `<compacted-summary>` and `SUM-BODY` and `</compacted-summary>`.
  3. Given the cut would land between an assistant `tool_calls` message and its tool results, When the window is chosen, Then those messages stay together entirely in the discarded prefix or entirely in the kept tail.
  4. Given L4 runs, When `.cda/.sessions/<id>.json` is loaded, Then it is still `{"messages": [...]}` with the compacted list and no `role=system` message.

### User Story 4 - /compact, compact tool, and auto (Priority: P1) 🎯 MVP
- Description: The human types `/compact` and the model can call `compact`. Auto compact runs the pipeline when thresholds are crossed. `/compact` is not a skill name.
- Why this priority: Adopter required all three invocation surfaces.
- Independent Test: CLI slash test; FakeProvider + `compact` tool call; threshold test with `auto_compact` false vs true.
- Acceptance Scenarios:
  1. Given a session with more than `keep_recent` messages, When the REPL input is `/compact`, Then L4 runs, no skill expansion occurs, and `QueryEngine.turn` is not called with the literal `/compact`.
  2. Given a cataloged skill named something other than `compact`, When the user types `/<skill-name>`, Then Feature 4 expansion still occurs.
  3. Given the model emits a `compact` tool call, When the batch runs, Then L4 runs, the tool result content indicates compaction succeeded, and the current turn ends after that batch (no further `complete()` on the pre-compact history).
  4. Given `auto_compact` is false and history is over `max_chars`, When a normal turn runs, Then L4 does not run unless `/compact` or the `compact` tool is used. Cheap layers still run only when `auto_compact` is true.
  5. Given `auto_compact` is true and history is over `max_messages` or `max_chars` after cheap layers, When the next `complete()` is prepared, Then L4 runs.

### User Story 5 - Reactive compact and circuit breaker (Priority: P1) 🎯 MVP
- Description: If `complete()` fails with a context-length / `prompt_too_long` provider error, the engine writes a transcript, runs `reactive_compact` (summary + last-five-message tail, boundary-safe), and retries at most `reactive_retries` times. If the L4 summarizer itself fails, it retries up to `compact_fail_retries` then stops and leaves history unsummarized (cheap layers already applied stay).
- Why this priority: s08 emergency path; without a breaker a failing summarizer loops.
- Independent Test: FakeProvider raises a recognizable overflow once then succeeds; FakeProvider always fails summarizer.
- Acceptance Scenarios:
  1. Given `complete()` raises a provider error whose text includes `prompt_too_long` or `context length` or HTTP 413, When `reactive_retries` is 1, Then reactive compact runs once and `complete()` is tried again with the compacted history.
  2. Given reactive compact already used its retry budget, When `complete()` still overflows, Then the error is surfaced and the engine does not loop.
  3. Given the L4 summarizer `complete()` fails three times (`compact_fail_retries=3`), When auto or manual L4 is attempted, Then no fourth summarizer call is made and history is not replaced with a partial summary.

### User Story 6 - Compact prompt and freshness (Priority: P1) 🎯 MVP
- Description: The summarizer instruction is the `compact` prompt section (override → bundled → fallback). Compaction status is visible via existing `status` events. Feature 5 assembly is unchanged.
- Why this priority: Matches the markdown-prompt contract from Feature 5; operators can change summary instructions without editing Python.
- Independent Test: Override file changes summarizer system/user instruction; FakeProvider records the compact request.
- Acceptance Scenarios:
  1. Given `.cda/prompts/compact.md` contains `OVERRIDE-COMPACT-PROMPT`, When L4 runs, Then that string appears in the summarizer request messages.
  2. Given no override, When L4 runs, Then the bundled `src/prompts/compact.md` text (or the inline fallback if the bundled file is missing) appears in the summarizer request.
  3. Given compaction starts, When events are collected, Then a `status` event is emitted whose message mentions compact (no new required event `type`).
  4. Given any turn after this feature, When `complete()` runs, Then the first message is still the Feature 5 assembled system prompt and it is not written to session JSON.

## Requirements (Moderate/Complex)
- `REQ-001`: Project config is read only from `.cda/config.json`. `.cda/ui-config.json` is ignored. Missing file or keys use defaults. Priority: Must. Validation: `cli_check.py`, compact unit tests. Linked story: US1.
- `REQ-002`: Default compact settings are `auto_compact=true`, `max_messages=50`, `max_chars=80000`, `keep_head=3`, `keep_recent=4`, `keep_recent_tool_results=3`, `tool_result_max_bytes=200000`, `persist_preview_chars=2000`, `reactive_retries=1`, `compact_fail_retries=3`. `show_tool_results` default remains true. Priority: Must. Validation: config loader tests. Linked story: US1.
- `REQ-003`: When `auto_compact` is true, before each provider `complete()` in the turn loop, run L3 then L1 then L2. If `len(history) > max_messages` or estimated characters `> max_chars` after those layers, run L4. Priority: Must. Validation: `query_engine_check.py`. Linked story: US2, US3, US4.
- `REQ-004`: Estimated characters equal the sum, over history messages, of `len(content or "")` plus the UTF-8 length of JSON-serialized `tool_result.content` when present. No tokenizer library. Priority: Must. Validation: compact unit tests. Linked story: US3.
- `REQ-005`: L3 inspects tool results in the last history message that carries them (the most recent tool batch). If their combined UTF-8 bytes exceed `tool_result_max_bytes`, persist largest-first to `.cda/task_outputs/tool-results/<call_id>` under process cwd until under budget. History body becomes a marker containing `<persisted-output>` and a preview of at most `persist_preview_chars` characters. Path traversal out of that directory is refused. Priority: Must. Validation: compact unit tests. Linked story: US2.
- `REQ-006`: L1 when `len(history) > max_messages` keeps `history[:keep_head]`, one user placeholder `[snipped N messages from conversation middle]` (`N` = number removed), and a tail of `max_messages - keep_head` messages, after sliding both cuts so a `tool_calls` assistant and its following tool results are not split. If already `<= max_messages`, no-op. Priority: Must. Validation: compact unit tests. Linked story: US2.
- `REQ-007`: L2 replaces tool-result bodies older than the newest `keep_recent_tool_results` tool messages, when body length `> 120`, with exactly `[Earlier tool result compacted. Re-run if needed.]`. Newer ones unchanged. Priority: Must. Validation: compact unit tests. Linked story: US2.
- `REQ-008`: L4 writes `.cda/.transcripts/<session_id>-<utc-timestamp>.jsonl` with one JSON object per current history message (redaction rules of SessionStore still apply: drop keys whose names contain `api_key` or `authorization`), then requests a provider summary using the `compact` prompt section and the older prefix as source, then sets `history` to `[ChatMessage("user", "<compacted-summary>\\n" + summary + "\\n</compacted-summary>")] + recent_window`. `recent_window` is the last `keep_recent` messages after a safe-boundary slide. Empty model summary is a failure, not a wipe. Priority: Must. Validation: `query_engine_check.py`. Linked story: US3.
- `REQ-009`: `/compact` is a builtin REPL command handled before Feature 4 skill expansion. It forces L4 on the current engine history (if longer than the keep window) and does not call `turn("/compact")`. Unknown `/name` that is not `/compact` stays Feature 4 behavior. Priority: Must. Validation: `cli_check.py`. Linked story: US4.
- `REQ-010`: Register LOW Agent tool `compact` with no required arguments. On successful invoke from the turn loop, run L4, return a non-error result whose text includes `Compacted`, and end the current turn after that batch. Unknown other tools unchanged. Priority: Must. Validation: `query_engine_check.py`, `tools_check.py`. Linked story: US4.
- `REQ-011`: When `auto_compact` is false, L3/L1/L2/L4 do not run on the automatic pre-`complete()` path. `/compact` and the `compact` tool still run L4. Priority: Must. Validation: `query_engine_check.py`. Linked story: US4.
- `REQ-012`: If `complete()` (non-summarizer) raises `ProviderError` whose message contains `prompt_too_long`, `context length`, or `HTTP 413`, run `reactive_compact`: transcript snapshot, summarizer, then `[summary_user] + last 5 messages` after safe-boundary slide, and retry `complete()` at most `reactive_retries` times. After the budget, propagate the error. Priority: Must. Validation: `query_engine_check.py`. Linked story: US5.
- `REQ-013`: L4/reactive summarizer failures increment a consecutive-failure counter. After `compact_fail_retries` consecutive failures, stop calling the summarizer for that attempt; do not replace history with a summary; do not loop. A successful summary resets the counter. Priority: Must. Validation: `query_engine_check.py`. Linked story: US5.
- `REQ-014`: Compact prompt resolution uses `load_prompt_section("compact")` (override `.cda/prompts/compact.md`, then `src/prompts/compact.md`, then inline fallback). The summarizer `complete()` must not register tools. Priority: Must. Validation: `tools_check.py`. Linked story: US6.
- `REQ-015`: Compaction emits `status` events (start/complete or equivalent message containing `compact`). No change to Feature 5 system-prompt assembly. Session JSON remains `{"messages": [...]}` without system roles. Priority: Must. Validation: `query_engine_check.py`. Linked story: US3, US6.
- `REQ-016`: `src/` remains Python 3.11+ stdlib only. Feature 1–5 public behavior is unchanged except the config path cutover and reserved `/compact`. Priority: Must. Validation: full `*_check.py` suite. Linked story: US1–US6.

## Acceptance Criteria
- `AC-001`: Given no `.cda/config.json`, When config is loaded, Then `show_tool_results` is true and compact defaults match REQ-002. Covers REQ-001, REQ-002. Proof: `python3 tests/tools_check.py` or dedicated config tests in that module.
- `AC-002`: Given `.cda/config.json` `{"show_tool_results": false, "compact": {"max_messages": 10}}`, When loaded, Then `show_tool_results` is false, `max_messages` is 10, and `max_chars` is 80000. Covers REQ-001, REQ-002. Proof: `python3 tests/tools_check.py`.
- `AC-003`: Given only `.cda/ui-config.json` `{"show_tool_results": false}` and no `config.json`, When the CLI resolves show-tool-results without CLI flags, Then the value is true. Covers REQ-001. Proof: `python3 tests/cli_check.py`.
- `AC-004`: Given a last tool batch whose serialized bodies exceed `tool_result_max_bytes`, When L3 runs, Then at least one file exists under `.cda/task_outputs/tool-results/`, the corresponding history body contains `<persisted-output>`, and remaining in-history preview length is `<= persist_preview_chars`. Covers REQ-005. Proof: `python3 tests/tools_check.py`.
- `AC-005`: Given 60 messages and `max_messages=50`, `keep_head=3`, When L1 runs, Then result length is 50, a user placeholder matches `[snipped 11 messages from conversation middle]` (or `N` equal to messages removed), and the first 3 messages are the original first 3 after any boundary slide of the head cut. Covers REQ-006. Proof: `python3 tests/tools_check.py`.
- `AC-006`: Given an assistant message with `tool_calls` immediately followed by its tool results, When an L1 cut would fall between them, Then those messages are all kept or all snipped together. Covers REQ-006. Proof: `python3 tests/tools_check.py`.
- `AC-007`: Given 5 tool messages with bodies of 200 characters and `keep_recent_tool_results=3`, When L2 runs, Then the oldest 2 tool bodies equal `[Earlier tool result compacted. Re-run if needed.]` and the newest 3 are unchanged. Covers REQ-007. Proof: `python3 tests/tools_check.py`.
- `AC-008`: Given history under all cheap thresholds, When L3/L1/L2 run, Then the message list equals the input. Covers REQ-006, REQ-007. Proof: `python3 tests/tools_check.py`.
- `AC-009`: Given estimated characters above `max_chars` after cheap layers and `auto_compact` true, When `QueryEngine.turn` next calls `complete()` for the user turn (not the summarizer), Then a `.cda/.transcripts/<session>-*.jsonl` exists, history[0] is user `<compacted-summary>…`, and the summarizer `complete()` was invoked with empty tools. Covers REQ-003, REQ-004, REQ-008, REQ-014. Proof: `python3 tests/query_engine_check.py`.
- `AC-010`: Given FakeProvider summarizer content `SUM-BODY`, When L4 finishes, Then `history[0].content` contains `<compacted-summary>`, `SUM-BODY`, and `</compacted-summary>`. Covers REQ-008. Proof: `python3 tests/query_engine_check.py`.
- `AC-011`: Given a would-be keep window that starts on a tool result whose previous message has `tool_calls`, When L4 chooses the window, Then the window start moves so the pair is not split. Covers REQ-008. Proof: `python3 tests/tools_check.py`.
- `AC-012`: Given L4 completed, When session JSON is loaded, Then top-level keys are only `messages`, no message has `role=system`, and `messages` equals the compacted history encoding. Covers REQ-008, REQ-015. Proof: `python3 tests/query_engine_check.py`.
- `AC-013`: Given REPL input `/compact` with history longer than `keep_recent`, When `run()` handles it, Then L4 ran, `turn` was not called with `/compact`, and no `Unknown skill: /compact` error is emitted. Covers REQ-009. Proof: `python3 tests/cli_check.py`.
- `AC-014`: Given a skill `code-review`, When REPL input is `/code-review`, Then Feature 4 expansion still occurs. Covers REQ-009, REQ-016. Proof: `python3 tests/cli_check.py`.
- `AC-015`: Given a FakeProvider assistant message whose only tool call is `compact`, When `turn` runs, Then L4 runs, the tool result is not an error and contains `Compacted`, and no additional user-turn `complete()` happens on the pre-compact history after that batch. Covers REQ-010. Proof: `python3 tests/query_engine_check.py`.
- `AC-016`: Given `auto_compact` false and history over `max_chars`, When a text-only turn runs, Then L4 is not invoked. Covers REQ-011. Proof: `python3 tests/query_engine_check.py`.
- `AC-017`: Given `complete()` raises `ProviderError("HTTP 413 prompt_too_long")` once then succeeds, When `reactive_retries` is 1, Then reactive compact runs once and the turn completes. Covers REQ-012. Proof: `python3 tests/query_engine_check.py`.
- `AC-018`: Given overflow on every `complete()` after reactive budget is exhausted, When the turn runs, Then `ProviderError` propagates and summarizer/reactive is not retried beyond `reactive_retries`. Covers REQ-012. Proof: `python3 tests/query_engine_check.py`.
- `AC-019`: Given the summarizer `complete()` fails three times, When L4 is attempted, Then exactly three summarizer calls occur and history still contains the pre-L4 messages (cheap-layer edits may remain). Covers REQ-013. Proof: `python3 tests/query_engine_check.py`.
- `AC-020`: Given `.cda/prompts/compact.md` body `OVERRIDE-COMPACT-PROMPT`, When L4 summarizer is called, Then that body appears in the summarizer messages. Covers REQ-014. Proof: `python3 tests/query_engine_check.py`.
- `AC-021`: Given L4 or cheap auto compact runs, When events are collected, Then at least one event has `type=status` and a message containing `compact` (case-insensitive). Covers REQ-015. Proof: `python3 tests/query_engine_check.py`.
- `AC-022`: Given Feature 5 assembly, When `complete()` is called after this feature, Then the first message is `role=system` with identity / `Working directory:` / planning string / `Skills available:`, and session JSON has no system role. Covers REQ-015, REQ-016. Proof: `python3 tests/query_engine_check.py`.
- `AC-023`: Given existing Feature 1–5 suites plus new tests, When `python3 -m unittest discover -s tests -p '*_check.py'` runs, Then all tests pass. Covers REQ-016. Proof: `python3 -m unittest discover -s tests -p '*_check.py'`.
- `AC-024`: Given L3 persist directory, When a tool call id contains `..` or a path separator, Then the persist file is written only as a sanitized name inside `.cda/task_outputs/tool-results/` and not outside process cwd. Covers REQ-005. Proof: `python3 tests/tools_check.py`.

## Success Criteria (Measurable Outcomes)
- `SC-001`: A session that would exceed `max_messages` or `max_chars` continues: the next `complete()` succeeds with a shorter history that still includes a summary of prior work and the recent turns.
- `SC-002`: A user can type `/compact` or the model can call `compact` and see history replaced by `<compacted-summary>` plus the recent window, with a JSONL transcript left on disk.
- `SC-003`: Oversized tool results do not remain in history above `tool_result_max_bytes`; their full text is on disk under `.cda/task_outputs/tool-results/`.
- `SC-004`: A failing summarizer cannot loop; overflow after reactive budget surfaces as `ProviderError`.
- `SC-005`: Zero third-party dependencies added to `src/`. `.cda/ui-config.json` is no longer a runtime input.

## Constraints and Risk
- Constraints:
  - NFR-001 Stdlib-only `src/` (Python 3.11+). Linked ACs: AC-023.
  - NFR-002 Session JSON remains `{"messages": [...]}` with no system role. Linked ACs: AC-012, AC-022.
  - NFR-003 Persist and transcript paths stay under process cwd `.cda/`. Linked ACs: AC-004, AC-009, AC-024.
  - NFR-004 Compaction cannot split tool_call / tool_result pairs. Linked ACs: AC-006, AC-011.
  - NFR-005 Summarizer and reactive retries are bounded. Linked ACs: AC-018, AC-019.
  - NFR-006 Config hard cutover to `.cda/config.json`. Linked ACs: AC-001, AC-003.
- Dependencies/touchpoints: `QueryEngine.turn` / `_with_system`, `SessionStore`, `expand_slash_prompt` / CLI loop, `load_prompt_section`, tool registry, `TerminalUI` events, `tests/cli_check.py`, `tests/query_engine_check.py`, `tests/tools_check.py`.
- Risks and mitigations:
  - Risk: L4 summarizer `complete()` itself is huge and overflows. Mitigation: cheap layers run first; reactive path exists; circuit breaker stops loops.
  - Risk: Hard cutover drops an existing `.cda/ui-config.json`. Mitigation: documented; default `show_tool_results` is already true, matching the checked-in file.
  - Risk: `/compact` collides with a future skill named `compact`. Mitigation: builtin wins; spec forbids treating `/compact` as a skill.
  - Risk: Character estimate ≠ tokens. Mitigation: accepted; dual trigger with message count; reactive compact on real overflow.
- Open questions (blocking only): none.

## Decisions
- Locked decisions:
  - Session 08 / s08 is an in-scope reference for this feature only, not a global architecture contract.
  - Full four-layer pipeline + reactive compact (not a focused L4-only MVP).
  - Invocation: builtin `/compact` + LOW `compact` tool + auto when `auto_compact` is true.
  - Auto trigger: message count **or** character estimate.
  - Keep window after L4: last `keep_recent` messages (default 4), boundary-safe; reactive tail default 5 messages.
  - Config: `.cda/config.json` only; ignore `.cda/ui-config.json`.
  - Defaults: s08-aligned values in REQ-002.
  - L3 persist: `.cda/task_outputs/tool-results/`.
  - Pre-L4 transcript: `.cda/.transcripts/<session>-<ts>.jsonl`. No retrieval tool.
  - Compact prompt: markdown section `compact`.
  - Status events for progress; do not require a new event `type`.
  - Out: Session 09 memory, tokenizers, reading `ui-config.json`.
- Related `ADR-*`: none.
