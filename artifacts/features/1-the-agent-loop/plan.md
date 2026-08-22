# Implementation Plan: 1-the-agent-loop

## Metadata
- Feature/profile: `1-the-agent-loop` (Complex)
- Spec approved date: 2026-04-08
- Status: `Draft`

## Technical Context

- Language/Version: Python 3.11+ (`StrEnum` used in `src/tools/types.py`; tested on 3.13.13)
- Primary Dependencies: None (zero 3rd-party dependencies, stdlib `urllib.request`, `dataclasses`, `typing.Protocol`, `unittest`)
- Storage/Data: Local JSON files in `.sessions/<session_id>.json`
- Target Platform: Cross-platform local CLI (macOS, Linux, Windows)
- Performance Goals: Turn loop overhead <10ms local processing per step (excluding network/model latency); instant Ctrl+C graceful persistence
- Key Constraints:
  - Keep 18/18 existing unit checks passing without modification or breaking interface signatures
  - No new external pip dependencies (maintain zero-dependency architecture)
  - Strict preservation of security boundaries and credential redaction in session files

## Constraints

- Non-goals:
  - Multi-agent coordination, subagents, mailboxes (Session 06 / 15)
  - Model Context Protocol (MCP) clients (Session 19)
  - Interactive slash-command taxonomy (Session 03+)
  - Context compaction or background dreaming (Session 08 / 09)
- Security/trust boundaries:
  - Never print or leak `OPENAI_API_KEY` in error strings or persisted transcripts
  - Keep `.secrets/` gitignored
  - Maintain interactive user authorization gate for HIGH/MEDIUM tools
- Preserved behavior:
  - Missing credentials raise `ProviderError` and CLI exits `2`
  - Constructor arguments > Environment variables > JSON config
  - Session histories persist after every mutation and on `KeyboardInterrupt` (exit `130`)
- Explicit out of scope:
  - Live API testing against paid OpenAI endpoints during automated test runs

## Approach

### Interfaces & Data Flow

```
User Prompt (str)
       │
       ▼
QueryEngine.turn(prompt)
       │
       ├──> 1. Appends ChatMessage("user", prompt) & calls _save()
       │
       └──> 2. Turn Loop: while turn_count < max_turns:
                  │
                  ├──> Invokes Provider.complete(history, tool_schemas, stream=True)
                  │    [Assembles stream deltas or takes ProviderResponse]
                  │    Appends assistant message to history & calls _save()
                  │
                  ├──> If NO tool_calls:
                  │    Returns ProviderResponse with termination_reason="completed"
                  │
                  └──> If tool_calls present:
                       For each call:
                         - Check risk & authorize
                         - If denied: append error ToolResult, emit "tool_denied"
                         - If approved: invoke tool, append ToolResult, emit "tool"
                         - _save()
                       turn_count += 1
                       [Loop continues if turn_count < max_turns]
       │
       └──> 3. If loop exits due to turn_count >= max_turns with tools still pending:
               Returns ProviderResponse with termination_reason="max_turns_reached"
```

### Public Seams & Structural Protocol

1. **Provider Protocol (`src/domain/provider.py`)**:
   ```python
   from typing import Any, Iterable, Protocol
   from .models import ChatMessage, ProviderResponse, StreamDelta

   class Provider(Protocol):
       def complete(
           self,
           messages: list[ChatMessage],
           tools: list[dict[str, Any]],
           stream: bool = False,
       ) -> ProviderResponse | Iterable[StreamDelta]:
           ...
   ```
2. **Termination Reason on ProviderResponse (`src/domain/models/provider_response.py`)**:
   ```python
   @dataclass(frozen=True)
   class ProviderResponse:
       message: ChatMessage
       finish_reason: Optional[str] = None
       termination_reason: str = "completed"  # "completed" | "max_turns_reached"
   ```
3. **QueryEngine Constructor & Turn Method (`src/application/query_engine.py`)**:
   ```python
   class QueryEngine:
       def __init__(
           self,
           provider: Provider,
           session: SessionStore,
           session_id: str,
           authorize: Authorize,
           on_event: Callable[[dict[str, Any]], None] | None = None,
           max_turns: int = 8,
       ) -> None:
           self.provider = provider
           self.session = session
           self.session_id = session_id
           self.authorize = authorize
           self.on_event = on_event or (lambda event: None)
           self.max_turns = max_turns
           self.history = session.load(session_id) if session_id in session.list() else []
   ```

### Module Map & Dependency Direction

| File / Module | Responsibility | Seam & Exports | Dependency Direction | Rationale |
|---|---|---|---|---|
| `src/domain/provider.py` | Defines `Provider` structural protocol | `Provider` | Outward: depends on `domain.models` | Co-locates domain contracts without importing infrastructure |
| `src/domain/models/provider_response.py` | Extends `ProviderResponse` dataclass with `termination_reason` | `ProviderResponse` | Domain model | Backwards-compatible addition with default `"completed"` |
| `src/domain/__init__.py` & `src/provider.py` | Exposes `Provider` protocol | `Provider` | Re-exports | Canonical symbol availability |
| `src/application/query_engine.py` | Enforces `max_turns`, loop execution, tool dispatch | `QueryEngine` | Depends on `domain.provider`, `domain.models`, `infrastructure.session_store`, `tools` | Core orchestration logic |
| `src/infrastructure/providers/openai.py` | OpenAI-compatible HTTP/SSE implementation | `OpenAIProvider` | Implements `domain.provider.Provider` | Concrete adapter |
| `tests/query_engine_check.py` | Verification suite for `QueryEngine` and loop mechanics | `TestQueryEngine` | Tests `application.query_engine` and `FakeProvider` | Adds AC-004 `max_turns_reached` test and protocol compliance |

## Alternatives Considered

| Option | Depth / Seam / Blast Radius | Chosen? | Why Rejected or Kept |
|---|---|---|---|
| **Option A: `typing.Protocol` (Structural Subtyping)** | High leverage. Any class implementing `complete()` works without subclassing. Zero runtime overhead. | **YES** | Kept: Pythonic, decoupled, allows fake providers and 3rd-party adapters without forced inheritance. |
| **Option B: `abc.ABC` Base Class** | Rigid inheritance. Requires `isinstance` checks and subclassing `Provider(ABC)`. | NO | Rejected: Forces unnecessary coupling on test fakes and external adapters. |
| **Option C: Separate `TurnResult` dataclass wrapping `ProviderResponse`** | Changes return type of `QueryEngine.turn()`. Breaks callers expecting `ProviderResponse`. | NO | Rejected: Would break backwards compatibility with `cli.py` and existing tests. Adding `termination_reason` to `ProviderResponse` is non-breaking. |

## Complexity Tracking

| Violation / Shortcut | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Add `Provider` protocol to domain | Formalizes the provider contract requested in s01 / spec | Omitting protocol leaves provider duck-typed as `Any` without clear IDE / static typing contracts |
| `termination_reason` default on `ProviderResponse` | Distinguishes normal completion from budget/turn truncation | Returning bare boolean or tuple breaks existing callers of `turn()` |

## Delivery

### Ordered Milestone Roadmap
1. **M1 (Domain & Protocol)**: Create `src/domain/provider.py` with `Provider` protocol; update `ProviderResponse` dataclass with `termination_reason: str = "completed"`; export in `src/domain/__init__.py` and `src/provider.py`.
2. **M2 (Query Engine Hardening)**: Update `QueryEngine.__init__` with `max_turns: int = 8`; implement bounded `while turn_count < self.max_turns:` loop in `QueryEngine.turn()`; set `termination_reason` on final `ProviderResponse`.
3. **M3 (Test Suite Expansion)**: Add `test_max_turns_reached_stops_loop` and `test_provider_protocol_conformance` in `tests/query_engine_check.py`.
4. **M4 (Verification)**: Run all 5 unit test scripts (`python3 -m unittest discover -s tests -p "*_check.py"`), verify 19+ passing tests, run `py_compile`.

### Rollback / Migration
- All changes are additive and strictly backwards compatible.
- Rollback: Revert `query_engine.py`, `provider_response.py`, and delete `provider.py`.

### Open Risks
- None. Full test suite remains isolated from live network.
