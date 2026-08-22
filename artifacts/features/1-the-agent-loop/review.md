# Verification Review

## Metadata

- Feature slug: `1-the-agent-loop`
- Date: 2026-08-22
- Status: Verifying

## Decision

- Decision: Pass with Follow-Up Debt
- Release recommendation: Ship the product loop. Do not treat harness `Done` as mechanically verified — gates remain adopter-deferred. Closeout uses an explicit verification override.
- Short summary: Provider protocol, `termination_reason`, and `max_turns=8` match the approved spec/plan. Fresh product suite is 20/20. Harness `verify` reports `verified: false` because `gates: []`.

## Findings

- Finding ID: HV-001
  Severity: Low
  Area: Verification / harness
  Evidence: `python3 core-zero/scripts/core/cli.py verify --feature 1-the-agent-loop --skill harness-verify` → `status: deferred`, `details.verified: false`, finding `no confirmed verification gates are configured`. `core-zero/project/harness-config.yaml` has `gates: []`, `project_setup.status: deferred`, `verification.mode: advisory`.
  Why it matters: `/harness-verify` cannot report `verified: true` without confirmed gates. Product proof is the unittest suite, not the harness runner.
  Recommended action: Keep gates deferred (adopter lock). Record a reasoned `--verification-override`. Optionally confirm `python3 -m unittest discover -s tests -p "*_check.py"` later as a named gate.

- Finding ID: HV-002
  Severity: Low
  Area: Standards / tests
  Evidence: `tests/query_engine_check.py` imports `Provider` and `ToolResult` but neither name is referenced after `test_provider_protocol_conformance` dropped `isinstance(..., Provider)`.
  Why it matters: Unused imports are leftover from the protocol-conformance slice. Behavior is unaffected.
  Recommended action: Delete the unused imports in a later polish pass. Not a reopen.

## Evidence Review

- Fresh automated evidence reviewed:
  - `python3 -m compileall -q src tests` — exit 0
  - `python3 -m unittest discover -s tests -p "*_check.py"` — 20 tests, OK (2026-08-22, this verify pass)
  - `python3 core-zero/scripts/core/cli.py artifact-check --feature 1-the-agent-loop --skill harness-verify --trace` — OK; REQ 10 / AC 12 / TASK 5; no orphan links
  - `python3 core-zero/scripts/core/cli.py verify --feature 1-the-agent-loop --skill harness-verify` — deferred, `verified: false`, 0 gates
- Fresh manual evidence reviewed: none required (stdlib CLI; no live provider)
- Stale or missing evidence: harness gate runs (none configured). `core-zero/generated/verification-runs.json` records this verify as `verified: false`.

## AC-to-Proof Mapping

| AC-ID | Task-ID | Proof evidence | Pass/Fail |
|---|---|---|---|
| AC-001 | T-002, T-005 | `test_direct_response_emits_text_once`: history `[user, assistant]`, one `text` event, `termination_reason == "completed"` | Pass |
| AC-002 | T-002, T-005 | `test_approved_tool_execution_turn`: 4 messages, role `tool`, matching `call_id`, `tool` event | Pass |
| AC-003 | T-002, T-005 | `test_denied_tool_execution_turn`: `is_error`, `"Tool execution denied by user."`, first event `tool_denied` | Pass |
| AC-004 | T-003, T-005 | `test_max_turns_reached_stops_loop`: `max_turns=2`, `call_count == 2`, `termination_reason == "max_turns_reached"` | Pass |
| AC-005 | T-002, T-005 | Same text-only turn as AC-001 reports `completed` under default `max_turns=8` | Pass |
| AC-006 | T-001, T-003, T-005 | `Provider` protocol + `FakeProvider` drives `QueryEngine` without `OpenAIProvider` | Pass |
| AC-007 | T-004, T-005 | `tests/provider_check.py::test_environment_overrides_json` | Pass |
| AC-008 | T-004, T-005 | `test_missing_environment` + `cli_check.test_missing_configuration_is_actionable` exit `2` | Pass |
| AC-009 | T-004, T-005 | `test_http_error_response_raises_actionable_provider_error`: `HTTP 401`, no `secret-key` | Pass |
| AC-010 | T-004, T-005 | `test_complete_streaming`: assembled text `Hello` + tool call from split SSE | Pass |
| AC-011 | T-004, T-005 | `tests/session_check.py::test_session_round_trip`: equal messages, no `OPENAI_API_KEY` | Pass |
| AC-012 | T-004, T-005 | `cli_check.test_args` / `test_debug_arg`: `--session`, `--json`, `--debug` | Pass |

## Design Conformance

| Design element | Evidence location | Pass/Fail |
|---|---|---|
| `typing.Protocol` `Provider.complete(messages, tools, stream=False)` | `src/domain/provider.py` | Pass |
| `ProviderResponse.termination_reason: str = "completed"` | `src/domain/models/provider_response.py` | Pass |
| Re-export `Provider` from domain and `src/provider.py` | `src/domain/__init__.py`, `src/provider.py` | Pass |
| `QueryEngine(max_turns: int = 8)` | `src/application/query_engine.py` `__init__` | Pass |
| Loop bound = provider completions per user prompt | `turn()` increments `turn_count` after each `complete` | Pass |
| Continue on assembled `tool_calls`, not `stop_reason` | `if not response.message.tool_calls` | Pass |
| `completed` vs `max_turns_reached` via `dataclasses.replace` | `query_engine.py` return sites | Pass |
| No ABC / no `TurnResult` wrapper | constructors still return `ProviderResponse` | Pass |
| OpenAI adapter unchanged (already matches contract) | `src/infrastructure/providers/openai.py` not edited | Pass |
| AC-004 + protocol tests | `tests/query_engine_check.py` | Pass |

## Security Audit

- Findings: None on the changed surface. `QueryEngine` is a high-attention path; this edit only added `max_turns` / `termination_reason`. Authorize, deny, and `bypass_permissions=True` for HIGH tools are unchanged. Provider errors still omit the API key (AC-009). Session JSON still redacts `api_key` / `authorization` keys (AC-011). `.secrets/` not read into artifacts.
- Evidence: `src/application/query_engine.py` `_run_call`; `tests/provider_check.py` HTTP 401; `tests/session_check.py`; `core-policies.md` Security Policy.
- Result: Pass

## Dropped Behavior

- Behavior reviewed: Product diff is additive (`Provider` protocol, `termination_reason` field, `max_turns` constructor arg, two new tests, empty `tests/__init__.py`). No public method deleted. Existing 18 checks remain and 2 were added (20 total). CLI flags, exit 2/0/130, config cascade untouched.
- Result: None
- Evidence: `git` status of `src/` and `tests/`; discovery count 20.

## Standards Review

Procedure-only. Isolated from Spec Review.

- Standards findings:
  - Protocol lives in domain and does not import infrastructure — matches `code-design.md` (interfaces only at a real boundary; two adapters: `OpenAIProvider` + test fakes).
  - `termination_reason` default keeps one public return type — no speculative wrapper.
  - Stdlib only (`typing.Protocol`, `dataclasses.replace`, `unittest`).
  - Unused `Provider` / `ToolResult` imports in `tests/query_engine_check.py` (HV-002). Advisory.
- Smell findings (judgement calls, cite hunk):
  - Primitive Obsession (advisory): `termination_reason` is a bare `str` rather than an enum. Plan locked the string default to avoid a new type. Leave as specified.
  - Speculative Generality: none. Protocol was requested; no factory.
- Result: Pass

## Spec Alignment Review

Procedure-only. Isolated from Standards Review.

- Missing or partial acceptance criteria: none. AC-001–AC-012 each have a completed task and a fresh passing check (see mapping table).
- Unrequested behavior (scope creep): `tests/__init__.py` is a package marker so `python3 -m unittest tests/query_engine_check.py` loads. Not product behavior. No extra providers, slash commands, or MCP.
- Requirements that look implemented but the implementation looks wrong: none. Loop inspects `response.message.tool_calls` (spec REQ-005). `max_turns` counts `complete` calls (REQ-006). FakeProvider still works without subclassing (REQ-001 / US4).
- Result: Pass

## Drift Review

- Drift detected: No
- Drift summary: Implementation matches approved spec and plan. No spec amendment after plan approval.
- Return-to-spec required: No

## Risk Review

- Security or privacy notes: High-attention `query_engine.py` touched only for turn budget. Secret hygiene tests still green.
- Regression risk: Low. Existing 18 checks plus 2 new ones, all green. `turn()` return type unchanged.
- Operational or observability risk: `termination_reason` is on the response object; CLI does not print it today (not required).

## Provider Review

- Provider command: `python3 core-zero/scripts/core/cli.py verify --feature 1-the-agent-loop --skill harness-verify`
- Provider status: deferred (`No review provider is enabled`; optional, not required)
- Provider findings summary: none executed

## Capabilities Used / Deferred

- Used optional helpers: isolated Standards and Spec subagent reviews
- Deferred optional helpers: live-network e2e, review provider
- Why deferred: spec non-goal (no live paid provider); no review provider configured

## Follow-Up

- Reopened tasks: none
- Deferred work:
  - Confirm project-native unittest discovery as a harness gate when adopter is ready (`/starter-init`)
  - Drop unused test imports (HV-002)
- Next required action: Close with `--verification-override` (adopter-deferred gates; product 20/20). Then `/context-memory` to promote `[CANDIDATE]` extracts.
