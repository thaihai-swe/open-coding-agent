# Session Extracts: `6-compact-memory`

## Candidate Lessons

- `[CANDIDATE]` Cheap-first compaction: Persist oversized tool results, snip the middle, and placeholder old tool bodies before spending a summarizer `complete()`. The LLM path is last and is the only layer that needs a circuit breaker.
- `[CANDIDATE]` Tool-pair boundary: Never cut between an assistant `tool_calls` message and its following `tool` results. OpenAI-compatible APIs reject the orphaned pair with HTTP 400.
- `[CANDIDATE]` Hard config cutover: One `.cda/config.json` for UI and compact knobs. Leaving `.cda/ui-config.json` as a fallback hides the migration; ignore it.
- `[CANDIDATE]` Builtin `/compact` must be reserved before skill expansion. A skill named `compact` would otherwise swallow the command.
- `[CANDIDATE]` Character-count estimate plus reactive compact on `prompt_too_long` / 413 is enough without tiktoken. Dual trigger (count or chars) plus one overflow retry covers the window.
