# Feature Proposal: 1-the-agent-loop

## Metadata
- Feature slug: `1-the-agent-loop`
- Profile: `Complex`
- Date / owner: 2026-04-08 / open-coding-agent team

## Problem & Outcome
- Problem statement: The agent harness has an initial concrete implementation of `OpenAIProvider`, `QueryEngine`, and domain message models, but lacks a formal provider-neutral protocol/interface (`Provider` Protocol), has no loop guardrails (runs indefinitely without `max_turns` enforcement), and lacks structured termination reasons.
- Desired observable outcome:
  1. A formal Python `typing.Protocol` defining the provider-neutral interface (`complete(messages, tools, stream=bool) -> ProviderResponse | Iterable[StreamDelta]`).
  2. `QueryEngine` accepts any provider adhering to this protocol.
  3. `QueryEngine` enforces a configurable `max_turns` boundary (default: 8), halting runaway tool recursion and setting a clear termination reason (`completed` vs `max_turns_reached`).
  4. Full multi-turn streaming and non-streaming tool invocation loop with history persistence after each turn/tool boundary.
  5. Clean CLI session persistence on graceful exit and interrupt.
- Non-goals:
  - Sub-agents or child agent coordination (belongs to s06).
  - Dynamic slash-command parser (belongs to command graph roadmap).
  - Multi-provider implementations beyond OpenAI-compatible (Anthropic/Ollama adapters belong to later provider extensions).
  - Context compaction / dreaming (belongs to s08/s09).

## Proposed Approach
- High-level architecture / public seams:
  - Domain: `src/domain/provider.py` defining `Provider` protocol.
  - Domain models: update `ProviderResponse` / `ChatMessage` to support standard termination metadata.
  - Application: `src/application/query_engine.py` parameterized with `max_turns: int = 8`.
  - Infrastructure: `src/infrastructure/providers/openai.py` implementing `Provider` protocol.
  - Presentation: `src/presentation/cli.py` passing configuration to engine.
- Alternatives rejected and why (Design-it-Twice comparison):
  - *Option A (Abstract Base Class / ABC)*: Use `abc.ABC` with `@abstractmethod`. Rejected in favor of structural subtyping (`typing.Protocol`) to allow third-party providers without rigid inheritance trees.
  - *Option B (Infinite While Loop without turn bounds)*: Keep the status quo `while True:`. Rejected because runaway model tool hallucination consumes API budget indefinitely.
- Preserved behavior:
  - Missing credentials raise `ProviderError` and CLI exits `2`.
  - Env vars override JSON config; kwargs override env vars.
  - Interactive authorization for HIGH/MEDIUM tools continues to emit `tool_denied` on reject.
  - Session JSON redacts credentials and persists to `.sessions/<session_id>.json`.
  - `KeyboardInterrupt` persists session and exits `130`.

## Risks & Dependencies
- Component dependencies: `src/domain/`, `src/application/`, `src/infrastructure/`, `src/presentation/`, `src/tools/`.
- Security or migration risks: Ensure `Provider` protocol does not leak credentials in string representations. Keep existing 18/18 test suite passing.
- Open questions: None blocking.

## Disposition
- Approval decision: `Approved`
- Next skill/action: `/spec-plan`
