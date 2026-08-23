# Feature Status: `7-memory-management`

- Phase: Implementing
- Delivery profile: `Complex`
- Status: `Active`
- Active task: `None`
- Next step: /harness-verify

## Progress
- [x] Research/spec complete
- [x] Spec approved
- [x] Plan/tasks complete (Moderate/Complex only)
- [x] Plan approved
- [x] Implementation complete
- [ ] Validation complete

## Intake
- Input type: `new_spec`
- One-line restatement: Persistent cross-session memory management system storing knowledge in `.cda/memory/*.md`, cataloging in `MEMORY.md`, injecting catalog into system prompt, retrieving relevant memories into request context, auto-extracting new facts post-turn, consolidating when file count reaches threshold, and exposing `/memory`.
- Artifact name requested: `7-memory-management` (harness slug: `7-memory-management`)
- Why now: User requested Feature `7-memory-management` referencing Session 09 in `documents/BUILDING_A_CODING_AGENT.md` and https://learn.shareai.run/en/s09/.
- Profile: `Complex` (involves markdown store with YAML frontmatter, index rebuilds, dynamic system prompt integration, pre-turn side-query relevance selection with keyword fallback, post-turn LLM extraction from pre-compaction history snapshot, consolidation dreaming at file-count threshold, REPL `/memory` slash command, and `.cda/config.json` memory settings).
- Changed boundaries: `src/tools/memory.py` / `src/domain/memory.py`, `src/tools/prompt.py`, `src/tools/config.py`, `src/application/query_engine.py`, `src/presentation/cli.py`, `src/prompts/memory.md`.
- Preserved behavior: Feature 1 tool execution and event protocol; Feature 2 permission gate; Feature 3 planning tools, task board, and nag; Feature 4 skill loading and `load_skill`; Feature 5 dynamic system prompt assembly; Feature 6 four-layer context compaction pipeline and `/compact`; messages-only session JSON storage.
- Risk flags: Extra side-query completions (select, extract, consolidate) must not fail the primary agent turn if they error or timeout; memory injection must not pollute session history JSON; memory file slugs must be strictly sanitized against path traversal.
- ADR conflict: None (empty log).

## Facts (not decisions)
- `QueryEngine` persists `history: list[ChatMessage]` to `.cda/.sessions/<session_id>.json`.
- System prompt is prepended dynamically at completion time and never stored in session JSON.
- Session 09 (https://learn.shareai.run/en/s09/) defines four memory types (`user`, `feedback`, `project`, `reference`), YAML frontmatter in individual markdown files, `MEMORY.md` index, catalog injection in system prompt, LLM side-query relevant memory selection with keyword fallback, post-turn extraction on `stop_reason != "tool_use"` from pre-compression messages, and consolidation triggered when file count ≥ 10.
- All CLI persistent data lives under `.cda/` (`.cda/.sessions`, `.cda/.todos`, `.cda/.permission_rules`, `.cda/.transcripts`, `.cda/task_outputs/tool-results`, `.cda/config.json`).
- REPL processes slash commands starting with `/` (`/compact` handled built-in, `/skills` expanded).

## Blockers / Decisions
- Blocker: None.
- Locked decision: Product is the coding-agent CLI (`src/`). Session 09 / s09 is an in-scope reference for this feature only.
- Locked decision: Storage directory is `.cda/memory/` (with `.cda/memory/MEMORY.md` index).
- Locked decision: Memory types are `user`, `feedback`, `project`, `reference`.
- Locked decision: Dynamic system prompt includes `MEMORY.md` index catalog and memory-use guidance via section `memory`.
- Locked decision: Relevant memories selected at start of user turn via LLM side-query (capped at `max_relevant=5`) with keyword fallback, prepended into outgoing request messages as `<relevant_memories>...</relevant_memories>` (not stored in `engine.history` or session JSON).
- Locked decision: Post-turn extraction runs over pre-compaction dialogue snapshot (last 10 messages, ≤4000 chars) on natural turn completion.
- Locked decision: Periodic consolidation runs when memory file count ≥ `consolidate_threshold` (default 10).
- Locked decision: Built-in REPL slash command `/memory` displays memory entries and statistics without calling `turn()`.
- Locked decision: Config keys live under `"memory"` in `.cda/config.json` (`enabled=True`, `max_relevant=5`, `consolidate_threshold=10`, `auto_extract=True`, `auto_consolidate=True`).
- Locked decision: Side-queries use tool-less completions and fail gracefully.

## Blocked Recovery
- Reason:
- Owner:
- Evidence:
- Next review at:
- Recommended handoff: /spec-plan
