# Tasks

## Metadata

- Feature/profile: `1-the-agent-loop` (Complex)
- Plan approved date: 2026-04-08

## Implementation Strategy

- Strategy: MVP-first
- Reason: Foundational domain contracts and loop bounds (US1, US2, US3, US4) must be solid before validating end-to-end CLI session resumption (US5).

## Task Contract

Each task must include an ID, target, linked `REQ-*`/`AC-*`, action, and proof. Use `[P]` only for genuinely independent work. For story phases, include `[US1]`, `[US2]`, and so on after the optional `[P]` marker. Tasks are the single executable checklist and source of machine-controlled status.

## Tasks

## Phase 1: Setup / Foundational — Domain Protocol & Models

- Goal: Introduce the structural `Provider` protocol and `termination_reason` field without breaking existing callers or imports.
- Entry proof: `python3 -c "from src.domain.models import ChatMessage, ProviderResponse; r = ProviderResponse(ChatMessage('assistant', 'ok')); assert not hasattr(r, 'termination_reason')"` (currently passes).
- Exit proof: `python3 -c "from src.domain.provider import Provider; from src.domain.models import ChatMessage, ProviderResponse; from src.provider import Provider as Reexport; r = ProviderResponse(ChatMessage('assistant', 'ok')); assert r.termination_reason == 'completed'; assert Reexport is Provider"` succeeds.

- [x] T-001 [US4] `src/domain/provider.py`, `src/domain/models/provider_response.py`, `src/domain/__init__.py`, `src/provider.py` — Define `Provider` protocol and add `termination_reason` default to `ProviderResponse`
  Status: Done
  - Covers: `AC-006`
  - Depends on:
  - Proof: `python3 -c "from src.domain.provider import Provider; from src.domain.models import ChatMessage, ProviderResponse; from src.provider import Provider as Reexport; r = ProviderResponse(ChatMessage('assistant', 'ok')); assert r.termination_reason == 'completed'; assert Reexport is Provider"`
  - Evidence:

## Phase 2: User Story 1 & 2 & 3 — Bounded Query Engine Loop (Priority: P1) 🎯 MVP

- Goal: Harden `QueryEngine` with `max_turns` limit (default 8), continue tool loop while tool calls are present, set `termination_reason` (`completed` vs `max_turns_reached`), and verify all loop behaviors.
- Entry proof: `python3 -c "from src.application.query_engine import QueryEngine; import inspect; assert 'max_turns' in inspect.signature(QueryEngine.__init__).parameters"` (currently fails).
- Exit proof: `python3 -m unittest tests/query_engine_check.py` passes all test cases including `test_max_turns_reached_stops_loop`.
  Validation evidence: Verified Provider protocol defined in src/domain/provider.py, termination_reason default 'completed' on ProviderResponse, and re-exported in src/provider.py via python3 assertions


- [x] T-002 [US1] [US2] [US3] `src/application/query_engine.py` — Implement `max_turns` counter and loop termination logic in `QueryEngine`
  Status: Done
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-005`
  - Depends on: `T-001`
  - Proof: `python3 -m unittest tests/query_engine_check.py`
  - Evidence:
  Validation evidence: QueryEngine now accepts max_turns=8; turn() increments on each provider.complete and returns termination_reason completed or max_turns_reached. python3 -m unittest tests/query_engine_check.py: 3 tests OK. Existing AC-001/002/003 plus completed reason.


- [x] T-003 [US3] [US4] `tests/query_engine_check.py` — Add unit checks for `max_turns_reached` bound and `Provider` protocol conformance
  Status: Done
  - Covers: `AC-004`
  - Depends on: `T-002`
  - Proof: `python3 -m unittest tests/query_engine_check.py`
  - Evidence:

## Phase 3: User Story 4 & 5 — Provider Configuration & Session Hardening (Priority: P2)

- Goal: Verify provider configuration cascade, secret redaction, CLI error codes, and session persistence across the complete check suite.
- Entry proof: `python3 -m unittest tests/provider_check.py tests/cli_check.py tests/session_check.py`
- Exit proof: `python3 -m unittest discover -s tests -p "*_check.py"` runs and passes 19+ tests cleanly.
  Validation evidence: Added test_max_turns_reached_stops_loop (AC-004) and test_provider_protocol_conformance (AC-006). python3 -m unittest tests/query_engine_check.py: 5 tests OK. AlwaysToolProvider with max_turns=2 invoked complete twice and returned max_turns_reached.


- [x] T-004 [US4] [US5] `tests/provider_check.py`, `tests/cli_check.py`, `tests/session_check.py` — Verify config precedence, error masking, session secret redaction, and CLI exit codes
  Status: Done
  - Covers: `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-012`
  - Depends on: `T-003`
  - Proof: `python3 -m unittest discover -s tests -p "*_check.py"`
  - Evidence:

## Phase 4: Polish & Integration Verification

- Goal: Run all static and runtime checks across the codebase to ensure zero regressions and full compliance.
- Entry proof: `python3 -m unittest discover -s tests -p "*_check.py"`
- Exit proof: `python3 -m py_compile src/**/*.py tests/*.py && python3 -m unittest discover -s tests -p "*_check.py"`
  Validation evidence: python3 -m unittest discover -s tests -p '*_check.py': 20 tests OK. Covers AC-007 env-over-json, AC-008 missing-config exit 2, AC-009 HTTP 401 without secret-key, AC-010 SSE stream assembly, AC-011 session redaction, AC-012 --session/--json/--debug flags. stderr Error: Set OPENAI_* is the missing-config fixture.


- [x] T-005 `src/` & `tests/` — Run complete test suite and byte-compilation check across all modules
  Status: Done
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-012`
  - Depends on: `T-004`
  - Proof: `python3 -m compileall -q src tests && python3 -m unittest discover -s tests -p "*_check.py"`
  - Evidence:

## Traceability

| REQ | Tasks | ACs |
|---|---|---|
| REQ-001 | T-001, T-003 | AC-006 |
| REQ-002 | T-004 | AC-009, AC-010 |
| REQ-003 | T-004 | AC-007, AC-008 |
| REQ-004 | T-002 | AC-001, AC-002 |
| REQ-005 | T-002, T-004 | AC-002, AC-010 |
| REQ-006 | T-002, T-003 | AC-001, AC-004, AC-005 |
| REQ-007 | T-002 | AC-003 |
| REQ-008 | T-004 | AC-011 |
| REQ-009 | T-004 | AC-009 |
| REQ-010 | T-004 | AC-008, AC-012 |

Every AC-001–AC-012 is linked from at least one `Covers:` line. No blocking open questions.

## Resume Notes

- Next recommended task: T-001
  Validation evidence: python3 -m compileall -q src tests completed with 0 syntax errors. python3 -m unittest discover -s tests -p '*_check.py' passed 20/20 checks across all test suites.

