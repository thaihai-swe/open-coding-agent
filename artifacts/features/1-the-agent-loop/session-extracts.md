# Session Extracts: 1-the-agent-loop

## Candidate Lessons

- [CANDIDATE] `ProviderResponse.termination_reason`: Adding `termination_reason: str = "completed"` with default value preserved full backwards compatibility with all existing `QueryEngine.turn()` callers without introducing a breaking wrapper dataclass.
- [CANDIDATE] `typing.Protocol` without ABC inheritance: Structural typing via `Protocol` in `src/domain/provider.py` cleanly decouples domain logic and test fakes from `OpenAIProvider` without requiring test adapters to inherit from abstract base classes.
- [CANDIDATE] Tool-calling loop bound: Counting provider completions per user prompt (rather than user turns or tool executions) is the exact metric that protects API budgets against runaway recursive tool calls.

## Post-Ship Sync

Verification passed; sync pending.

Promote after Done via `/context-memory`:

- [CANDIDATE] `ProviderResponse.termination_reason` default preserves `QueryEngine.turn()` callers without a `TurnResult` wrapper.
- [CANDIDATE] `typing.Protocol` (not ABC) lets FakeProvider drive the loop without subclassing.
- [CANDIDATE] `max_turns` counts provider completions per user prompt.

No additional candidates.
