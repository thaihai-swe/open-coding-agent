# Feature Specification

## Metadata
- Feature: `1-the-agent-loop`
- Profile: `Complex`
- Status: `Approved`
- Owner: open-coding-agent team
- Artifact slug note: requested `1.the-agent-loop`; harness requires lowercase hyphenated slug, so artifacts live under `1-the-agent-loop`.

## Problem Statement
- Who is affected, what fails, and why now: Operators of the local coding-agent REPL already have a working OpenAI-compatible loop, but the loop is bound to a concrete provider type, has no documented provider-neutral contract, and will follow tool calls forever. Session 01 of the product roadmap (`documents/BUILDING_A_CODING_AGENT.md`, ShareAI s01) requires a provider-neutral chat/tool-calling interface, one OpenAI-compatible implementation, and a minimal REPL that sends messages, executes tool calls, and appends results to history — with a finite turn bound.

## Outcome
- Observable result: An operator can start `python3 -m src.cli`, send a prompt, see streamed or completed assistant text, have requested tools run (or denied) with results appended to history, and have the turn stop when the model is done or when `max_turns` is reached.
- Minimum useful release: Protocol + OpenAI-compatible provider + QueryEngine turn loop with history persistence, `max_turns` default 8, and existing CLI/session contracts preserved.

## Scope
- In scope:
  - A provider-neutral chat and tool-calling contract that any implementation can satisfy structurally.
  - One OpenAI-compatible provider that posts to `{api_base}/chat/completions` with messages, tools, and optional streaming.
  - A minimal REPL turn: append user message → complete → if tool calls, authorize/execute, append tool results, complete again → stop when no tool calls or `max_turns` reached.
  - Persist history after each user, assistant, and tool message, and on interrupt.
  - Surface a termination reason (`completed` vs `max_turns_reached`) on the turn result.
  - Keep existing config cascade, missing-config exit `2`, and Ctrl+C exit `130`.
- Out of scope / non-goals:
  - Additional provider adapters (Anthropic native, Ollama-specific, Azure extras).
  - Slash commands, command graph, MCP, sub-agents, compaction, dreaming, hooks, permission-mode overhaul (s02–s20).
  - Changing the 14 registered tools' handler behavior except as needed to keep the loop contract.
  - Live-network e2e against a paid provider as a required gate.
- Preserved behavior:
  - Missing provider config → `ProviderError`; CLI `run([])` exits `2` with the set-env-or-config message.
  - Constructor args > `OPENAI_*` env > JSON config.
  - Provider HTTP errors become `ProviderError` and must not include the API key string.
  - HIGH/MEDIUM denial emits `tool_denied` and tool error `"Tool execution denied by user."` without aborting the session.
  - Session JSON redacts dict keys containing `api_key` / `authorization`.
  - KeyboardInterrupt saves and exits `130`.
  - CLI flags `--session`, `--json`, `--debug` keep current argparse meaning.

## User Stories & Journeys

### User Story 1 - Send a prompt and get a text reply (Priority: P1) 🎯 MVP
- Description: An operator starts the REPL with valid provider config, types a prompt, and receives assistant text. The user and assistant messages are appended to in-memory history and persisted.
- Why this priority: Without a working complete-and-stop path there is no agent.
- Independent Test: Fake or mocked provider returns a text-only `ProviderResponse`. Assert history length 2 and a `text` event; no tool events.
- Acceptance Scenarios:
  1. Given a configured provider that returns assistant text and no tool calls, When the operator submits a prompt, Then the engine appends user then assistant messages, emits `text`, persists history, and stops with termination reason `completed`.

### User Story 2 - Execute tool calls and continue the loop (Priority: P1) 🎯 MVP
- Description: When the model requests tools, the engine executes each call (after authorize for HIGH/MEDIUM), appends a tool-role result, and calls the provider again with the updated history until the model returns no tool calls.
- Why this priority: This is the s01 loop kernel: model decides, harness executes, result feeds back.
- Independent Test: Fake provider returns a `read_file` tool call then a final text message. Assert 4 history messages (user, assistant+tools, tool, assistant) and a `tool` event.
- Acceptance Scenarios:
  1. Given an approved LOW or authorized tool call, When the engine runs the turn, Then a tool result is appended with the matching call id and the next complete sees that history.
  2. Given a HIGH/MEDIUM tool the user denies, When the engine runs the turn, Then history gets an error tool result `"Tool execution denied by user."`, a `tool_denied` event is emitted, and the loop continues (does not crash).

### User Story 3 - Bound the loop with max_turns (Priority: P1) 🎯 MVP
- Description: A turn that keeps requesting tools stops after `max_turns` provider completions (default 8) and reports `max_turns_reached` instead of looping forever.
- Why this priority: Adopter chose formal turn limits; unbounded loops burn budget.
- Independent Test: Fake provider always returns a tool call. Engine constructed with `max_turns=2`. Assert the turn returns with `max_turns_reached` and does not request a third completion.
- Acceptance Scenarios:
  1. Given `max_turns=N` and a provider that always requests tools, When a turn runs, Then the provider is called at most N times and the result termination reason is `max_turns_reached`.
  2. Given a turn that finishes in fewer than N completions, When it stops because there are no tool calls, Then the termination reason is `completed`.

### User Story 4 - Provider-neutral complete contract (Priority: P1) 🎯 MVP
- Description: The engine talks only to a documented provider contract (messages + tool schemas + stream flag → response or stream deltas). A fake provider that matches the contract can drive the loop without `OpenAIProvider`.
- Why this priority: Roadmap s01 and adopter decision: formalize the protocol so later adapters plug in.
- Independent Test: Existing `FakeProvider` in `tests/query_engine_check.py` (or equivalent) type-checks / runs against the contract; engine constructor accepts it.
- Acceptance Scenarios:
  1. Given any object that implements `complete(messages, tools, stream=False)`, When QueryEngine is constructed with it, Then turns run without requiring the OpenAI class.
  2. Given the OpenAI-compatible implementation, When `complete` is called with `stream=False` or `stream=True`, Then it maps `/chat/completions` JSON or SSE into `ProviderResponse` / `StreamDelta` without exposing the API key in errors.

### User Story 5 - Operator starts and resumes a REPL session (Priority: P2)
- Description: `python3 -m src.cli` creates a session, prints the session id, and loops on `> `. `--session <id>` reloads persisted history. Empty/EOF exits 0. Missing config exits 2. Ctrl+C saves and exits 130.
- Why this priority: Required to use the loop, but already largely implemented; this story locks the contract.
- Independent Test: `tests/cli_check.py` and `tests/session_check.py` plus any new max_turns/protocol tests stay green.
- Acceptance Scenarios:
  1. Given no config, When `run([])` is invoked, Then exit code is 2 and stderr contains the set-env-or-config message.
  2. Given a valid session file, When `--session <id>` is used, Then history is loaded before the first prompt.

## Requirements

- `REQ-001`: The system SHALL expose a provider-neutral complete contract: input is ordered chat messages plus tool schemas and a stream flag; output is either a single assistant response or an iterable of stream deltas that can be assembled into that response. Rationale: s01 + adopter protocol decision. Priority: Must. Validation: `tests/query_engine_check.py`, `tests/provider_check.py`. Linked story: US4.
- `REQ-002`: The system SHALL ship one OpenAI-compatible implementation that POSTs to `{api_base}/chat/completions` with Bearer auth, supports non-stream JSON and SSE `data:` / `[DONE]`, and maps assistant content and function tool calls into domain messages. Rationale: first adapter. Priority: Must. Validation: `tests/provider_check.py`. Linked story: US4, US1.
- `REQ-003`: The system SHALL resolve provider settings as constructor args > `OPENAI_API_BASE` / `OPENAI_API_KEY` / `OPENAI_MODEL` > JSON object at `$CONFIG_FILE` or `.secrets/config.json`. Missing any of base/key/model SHALL raise a provider error before any network call. Rationale: existing contract. Priority: Must. Validation: `tests/provider_check.py`, `tests/cli_check.py`. Linked story: US5.
- `REQ-004`: On each user prompt the engine SHALL append a user message, persist, call complete with current history and tool schemas, append the assistant message, persist, and if tool calls are present execute each call and append a tool-role result with the originating call id, persist, then complete again. Rationale: s01 loop kernel. Priority: Must. Validation: `tests/query_engine_check.py`. Linked story: US1, US2.
- `REQ-005`: Loop continuation SHALL be determined by presence of tool calls on the assembled assistant message, not solely by a provider `stop_reason` field (streaming `stop_reason` is unreliable). Rationale: ShareAI s01 / CC query.ts note. Priority: Must. Validation: `tests/query_engine_check.py`, streaming assembly in `tests/provider_check.py`. Linked story: US2, US4.
- `REQ-006`: The engine SHALL accept a configurable `max_turns` (default 8) counting provider completions in one user turn. When the bound is hit with tool calls still pending, the turn SHALL stop and report termination reason `max_turns_reached`. A clean stop with no tool calls SHALL report `completed`. Rationale: adopter turn-limit decision. Priority: Must. Validation: new focused check in `tests/query_engine_check.py`. Linked story: US3.
- `REQ-007`: HIGH and MEDIUM tools SHALL require an authorize callback before execution. Denial SHALL emit `tool_denied`, append an error tool result `"Tool execution denied by user."`, and continue the loop. LOW tools SHALL run without that prompt. Rationale: preserved s03-adjacent baseline already in tree. Priority: Must. Validation: `tests/query_engine_check.py`. Linked story: US2.
- `REQ-008`: History SHALL persist after every user, assistant, and tool append, and on KeyboardInterrupt. Persisted JSON SHALL omit dict keys whose names contain `api_key` or `authorization` (case-insensitive). Rationale: no data loss; no secret leak in session files. Priority: Must. Validation: `tests/session_check.py`, CLI interrupt path. Linked story: US1, US5.
- `REQ-009`: Provider and CLI errors SHALL NOT include the API key string. HTTP and empty-choice failures SHALL be actionable provider errors. Rationale: secret hygiene. Priority: Must. Validation: `tests/provider_check.py`. Linked story: US4, US5.
- `REQ-010`: The REPL SHALL keep flags `--session`, `--json`, `--debug`; missing config exit `2`; empty/EOF exit `0`; KeyboardInterrupt exit `130` with session saved. JSON mode SHALL emit structured events including `text`, `tool`, `tool_denied`, and `error`. Rationale: preserved operator contract. Priority: Must. Validation: `tests/cli_check.py`, `tests/terminal_ui_check.py`. Linked story: US5.

## Acceptance Criteria

- `AC-001`: Given a fake provider that returns only assistant text, When `QueryEngine.turn("Hi")` runs, Then history is `[user, assistant]`, a single `text` event contains that content, and the turn result termination reason is `completed`. Linked REQ-004, REQ-006 / US1. Proof: `python3 tests/query_engine_check.py`.
- `AC-002`: Given a fake provider that first returns an approved `read_file` tool call then final text, When the turn runs, Then history has four messages, the third is role `tool` with matching `call_id`, and a `tool` event is emitted. Linked REQ-004, REQ-005 / US2. Proof: `python3 tests/query_engine_check.py`.
- `AC-003`: Given a HIGH `bash` tool call and `authorize` returning false, When the turn runs, Then the tool result `is_error` is true, content error is `Tool execution denied by user.`, and the first event type is `tool_denied`. Linked REQ-007 / US2. Proof: `python3 tests/query_engine_check.py`.
- `AC-004`: Given `max_turns=2` and a provider that always returns a tool call, When the turn runs, Then `complete` is invoked at most twice and the turn result termination reason is `max_turns_reached`. Linked REQ-006 / US3. Proof: new test in `tests/query_engine_check.py` (must be added during implement).
- `AC-005`: Given a turn that completes in one text-only completion, When it returns, Then termination reason is `completed` even though `max_turns` default is 8. Linked REQ-006 / US3. Proof: `tests/query_engine_check.py`.
- `AC-006`: Given an object that only implements `complete(messages, tools, stream=False)`, When it is passed as the engine provider, Then the engine runs US1/US2 scenarios without importing `OpenAIProvider`. Linked REQ-001 / US4. Proof: `FakeProvider` in `tests/query_engine_check.py`.
- `AC-007`: Given env `OPENAI_*` set and a JSON config with different values, When the OpenAI-compatible provider is constructed without kwargs, Then env values win. Linked REQ-003 / US4. Proof: `python3 tests/provider_check.py`.
- `AC-008`: Given missing env and a nonexistent `CONFIG_FILE`, When the OpenAI-compatible provider is constructed, Then it raises `ProviderError` mentioning the three env vars or `.secrets/config.json`, and `run([])` returns `2`. Linked REQ-003, REQ-010 / US5. Proof: `python3 tests/provider_check.py`; `python3 tests/cli_check.py`.
- `AC-009`: Given a mocked HTTP 401 whose body contains an API error and whose key is `secret-key`, When `complete` runs, Then the raised error includes `HTTP 401` and the server message and does not include `secret-key`. Linked REQ-002, REQ-009 / US4. Proof: `python3 tests/provider_check.py`.
- `AC-010`: Given a mocked SSE stream with split tool-call argument chunks ending in `data: [DONE]`, When `complete(..., stream=True)` is consumed, Then assembled text and tool calls match the chunks. Linked REQ-002, REQ-005 / US4. Proof: `python3 tests/provider_check.py`.
- `AC-011`: Given a session saved with user/assistant/tool messages, When it is loaded, Then messages round-trip equal and the file text does not contain `OPENAI_API_KEY`. Linked REQ-008 / US5. Proof: `python3 tests/session_check.py`.
- `AC-012`: Given `--session s --json` and `--debug`, When args are parsed, Then those flags are set as today. Linked REQ-010 / US5. Proof: `python3 tests/cli_check.py`.

## Success Criteria (Measurable Outcomes)

- `SC-001`: An operator with valid config can complete a text-only turn and a one-tool-call turn without losing history on success or Ctrl+C.
- `SC-002`: A runaway tool-calling model cannot exceed `max_turns` provider calls in a single user prompt (default 8).
- `SC-003`: A second provider implementation can be introduced later by satisfying the complete contract only — no QueryEngine rewrite.
- `SC-004`: Existing 18 unit checks remain green; new max_turns coverage is added and green. No live provider call is required to prove this feature.

## Non-Functional Requirements

- `NFR-001`: Secret hygiene — API keys never appear in provider error strings or session JSON keys. Linked ACs: AC-009, AC-011.
- `NFR-002`: Fail loud — missing config and bad provider payloads raise explicit provider errors, not silent empty replies. Linked ACs: AC-008, AC-009.
- `NFR-003`: Stdlib-only runtime unless a later spec adds a dependency. Linked ACs: AC-006, AC-007 (no SDK required).
- `NFR-004`: Default turn bound is 8 provider completions per user prompt. Linked ACs: AC-004, AC-005.

## Constraints and Risk
- Constraints: Python 3.11+ (`StrEnum`); no third-party packages unless explicitly approved; do not treat `documents/BUILDING_A_CODING_AGENT.md` later sessions as in-scope.
- Dependencies/touchpoints: `src/domain/`, `src/application/query_engine.py`, `src/infrastructure/providers/openai.py`, `src/presentation/cli.py`, `src/tools/`, `tests/*_check.py`.
- Risks and mitigations:
  - Changing `QueryEngine.turn` return shape may break callers — keep `ProviderResponse` and attach termination reason without dropping `.message`.
  - Counting "turns" ambiguously (user prompts vs provider completions) — this spec locks **provider completions per user prompt**.
  - Existing tests do not cover `max_turns` — implement must add AC-004 before claiming done.
- Open questions (blocking only): none.

## Decisions
- Locked decisions:
  - Feature slug on disk: `1-the-agent-loop` (harness cannot accept `1.the-agent-loop`).
  - Formalize a provider-neutral complete protocol and `max_turns` (adopter, 2026-04-08).
  - Delivery profile: Complex.
  - Continue-on-tool-calls by inspecting assembled tool_calls, not `stop_reason` alone.
  - Default `max_turns=8` (blueprint QueryEngineconfig).
  - Gates remain deferred; proof is the unittest scripts, not harness Done.
- Related `ADR-*`: none that conflict. Kit `ADR-001` is format-only.

## Spec Amendments
- None yet.
