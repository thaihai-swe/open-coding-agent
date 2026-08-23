# Feature Proposal: 6-compact-memory

## Metadata
- Feature slug: `6-compact-memory`
- Profile: `Complex`
- Date / owner: 2026-08-23 / adopter
- Requested artifact name: `6.compact-memory` (harness slug `6-compact-memory`)
- References: Session 08 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s08/

## Problem & Outcome
- Problem statement: As a coding agent interacts with large repositories, runs numerous commands, and reads files, the conversation history grows without bound. Eventually the accumulated message history exceeds the model's finite context window, resulting in API rejection errors (`prompt_too_long` or HTTP 413 / context length exceeded) or massive latency and token cost. The agent needs a structured, multi-layer context compaction pipeline that progressively compresses older conversational history (cheap operations first, expensive LLM summarization last) while preserving recent turns, critical context, and tool call/result invariants.
- Desired observable outcome:
  1. **Unified Configuration**: All project settings consolidate into `.cda/config.json` (replacing `.cda/ui-config.json` via hard cutover), supporting UI options (`show_tool_results`) and compaction knobs (`auto_compact`, `max_messages`, `max_chars`, `keep_head`, `keep_recent`, `keep_recent_tool_results`, `tool_result_max_bytes`, `persist_preview_chars`, `reactive_retries`, `compact_fail_retries`).
  2. **Multi-Layer Compaction Pipeline**:
     - **L3 (`tool_result_budget`)**: When tool results in the last message batch exceed `tool_result_max_bytes` (default 200,000 bytes), persist large outputs to disk under `.cda/task_outputs/tool-results/<call_id>.txt` and replace with a `<persisted-output>` marker and preview text (default 2,000 characters).
     - **L1 (`snip_compact`)**: When message count exceeds `max_messages` (default 50), preserve the initial head messages (default 3) and the recent tail messages, snipping middle messages with `[snipped N messages from conversation middle]` while respecting tool call / tool result pairing invariants.
     - **L2 (`micro_compact`)**: Keep the most recent `keep_recent_tool_results` (default 3) tool results intact, replacing older results exceeding 120 characters with a compact placeholder `[Earlier tool result compacted. Re-run if needed.]`.
     - **L4 (`compact_history`)**: When message count or estimated character count exceeds thresholds (`max_chars` default 80,000), or on manual `/compact` slash command, or when the model calls the `compact` tool:
       - Save a full pre-compaction transcript snapshot to `.cda/.transcripts/<session_id>-<timestamp>.jsonl`.
       - Query the provider to summarize older messages using `src/prompts/compact.md` (overridable at `.cda/prompts/compact.md`).
       - Replace older messages with a single summary message `<compacted-summary>...</compacted-summary>` while retaining the boundary-safe recent window (`keep_recent`, default 4 messages).
       - Apply a circuit breaker stopping retries after 3 consecutive failures.
  3. **Reactive Compaction (`reactive_compact`)**: On provider context-overflow errors (`prompt_too_long` or 413), perform emergency compaction and retry once (`reactive_retries=1`).
  4. **Invocation Interfaces**:
     - Built-in `/compact` slash command in REPL.
     - Model-facing `compact` tool (LOW risk, Agent category).
     - Automatic execution in `QueryEngine` turn loop before provider completion.
  5. **Persistence & Isolation**: Compacted history is immediately saved to `.cda/.sessions/<session_id>.json`. The dynamic system prompt is never persisted.
- Non-goals:
  - Session 09 cross-session persistent memory (`MEMORY.md` / `.memory/`).
  - Third-party tokenizers (e.g. tiktoken) in `src/` (character-based heuristic on stdlib Python 3.11+).
  - Transcript retrieval tools in MVP (transcripts are archival snapshots for Session 08).
  - Workspace jail for persisted outputs outside `.cda/`.

## Proposed Approach
- High-level architecture / public seams:
  - `src/tools/compact.py` (or `src/application/compact.py`):
    - `tool_result_budget(messages, max_bytes, preview_chars, persist_dir)` -> L3 large result persister.
    - `snip_compact(messages, max_messages, keep_head)` -> L1 middle snip with boundary guard.
    - `micro_compact(messages, keep_recent_results)` -> L2 old tool result placeholder.
    - `compact_history(engine, messages, keep_recent)` -> L4 transcript backup + LLM summarization + history replacement.
    - `reactive_compact(engine, messages, tail_count)` -> Emergency context reduction.
    - `is_safe_cut(messages, index)` / `adjust_safe_boundary(messages, index)` -> Invariant protector preventing orphaned tool results.
  - `src/prompts/compact.md`: Bundled default compaction prompt template, overridable via `.cda/prompts/compact.md`.
  - `src/tools/handlers/agent.py`: Register `compact` tool (LOW, Agent category) invoking `QueryEngine` compaction.
  - `src/presentation/cli.py`: Consolidated `.cda/config.json` loading; intercept `/compact` in REPL loop before skill expansion.
  - `src/application/query_engine.py`: Integrate 4-layer pre-processors and reactive compact into the turn loop; manage transcript backup and circuit breaker.
- Alternatives rejected and why (Design-it-Twice comparison):
  - *Alternative A: Pure LLM summarization without L1-L3 pre-processors.*
    Rejected because raw LLM summarization of a 500KB tool output wastes massive tokens and can fail API limits before the summarizer even runs. Cheap pre-processors (L3 persist, L1 snip, L2 micro) reduce payload size with 0 API calls.
  - *Alternative B: Truncating history strictly by fixed index count without boundary guards.*
    Rejected because splitting between an assistant `tool_calls` message and its `tool_result` breaks OpenAI chat completion API schema requirements, causing hard API 400 errors.
  - *Alternative C: Maintaining separate ui-config.json and compact-config.json.*
    Rejected in favor of single unified `.cda/config.json` for cleaner project-level configuration management.
- Preserved behavior:
  - Feature 1: Tool execution, workspace bounding, concurrent batch execution, live terminal events, JSON mode.
  - Feature 2: Permission gate, hard deny list, project rules in `.cda/.permission_rules/rules.json`, interactive authorize.
  - Feature 3: Task planning tools (`create_task`, `list_tasks`, etc.), per-session task board, 3-round planning nag.
  - Feature 4: Dynamic skill loading, `load_skill` tool, `/<skill-name>` slash command expansion.
  - Feature 5: Dynamic runtime system prompt assembly from markdown templates with `.cda/prompts/` overrides.

## Risks & Dependencies
- Component dependencies: `src/application/query_engine.py`, `src/tools/prompt.py`, `src/presentation/cli.py`, `src/infrastructure/session_store.py`, `src/tools/registry.py`.
- Security or migration risks:
  - Large tool outputs persisted to `.cda/task_outputs/tool-results/` must remain within workspace cwd and protected from path traversal.
  - Hard cutover from `.cda/ui-config.json` to `.cda/config.json`: existing UI tests and scripts need updating to `.cda/config.json`.
  - Circuit breaker ensures infinite loops cannot occur if the LLM provider fails during summarization.
- Open questions (blocking only): None.

## Disposition
- Approval decision: `Approved`
- Next skill/action: `/spec-requirements` spec authoring -> `/spec-plan`
