# Feature Proposal: 7-memory-management

## Metadata
- Feature slug: `7-memory-management`
- Profile: `Complex`
- Date / owner: 2026-08-23 / adopter
- Requested artifact name: `7-memory-management` (harness slug `7-memory-management`)
- References: Session 09 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s09/

## Problem & Outcome
- Problem statement: While Feature 6 (`6-compact-memory`) enables conversation history compression within a single session, all knowledge and user preferences (e.g. coding style, architectural conventions, tool choices, project background, workflow guidelines) are lost across sessions or degraded when context is compacted. A user must repeatedly explain their constraints and project specifics. The agent requires a persistent, cross-session memory management system that automatically stores, indexes, retrieves, extracts, and consolidates knowledge over time across session restarts and context resets.
- Desired observable outcome:
  1. **Persistent Memory Storage & Indexing (`.cda/memory/`)**:
     - Memory items are stored as Markdown files with YAML frontmatter (`---`, `name`, `description`, `type`, `---`, `\n\nbody`) under `.cda/memory/<slug>.md`.
     - Four standardized memory types: `user` (preferences), `feedback` (guidelines/instructions), `project` (facts/background), `reference` (pointers/locations).
     - Automatically maintained index file `.cda/memory/MEMORY.md` listing markdown links and descriptions (`- [name](<filename>) — description`).
  2. **Two-Path Context Integration**:
     - **Path 1 (System Prompt Catalog)**: `assemble_system_prompt()` reads `.cda/memory/MEMORY.md` and injects an active memory catalog and usage guidance into the dynamic system prompt.
     - **Path 2 (Relevant Memory Dynamic Injection)**: At the beginning of each user turn, the engine runs a lightweight side-query (LLM side-query with fallback to keyword matching) to select up to `max_relevant` (default 5) memory files based on recent conversation, and injects their full contents into the turn request context wrapped in `<relevant_memories>...</relevant_memories>` without mutating persistent session history.
  3. **Automatic Post-Turn Extraction**:
     - When an agent turn finishes naturally without requesting further tool calls (`stop_reason != "tool_use"` or end of turn execution), the engine runs a lightweight LLM extraction pass over recent dialogue (using a pre-compression snapshot to prevent loss of fidelity).
     - New user preferences, feedback, or facts are converted into memory files and the index is immediately rebuilt.
     - Emits a status event or notification when new memories are created.
  4. **Periodic Consolidation ("Dreaming")**:
     - When the memory file count reaches or exceeds `consolidate_threshold` (default 10), the engine invokes an LLM consolidation pass to deduplicate, resolve contradictions, merge related entries, and prune obsolete memories, ensuring memory size remains bounded.
  5. **Configuration & Inspection**:
     - Memory knobs configured in `.cda/config.json` under `"memory"` (`enabled`: bool, `max_relevant`: int, `consolidate_threshold`: int, `auto_extract`: bool, `auto_consolidate`: bool).
     - Built-in REPL slash command `/memory` displaying current memory entries, categories, descriptions, and utilization statistics.
- Non-goals:
  - Vector database or external embedding model dependencies (uses LLM side-query + keyword fallback, keeping `src/` stdlib-only).
  - Multi-agent team shared memory synchronization (deferred to agent platform roadmap).
  - Persisting system prompts or temporary memory injection tags into `.cda/.sessions/<session_id>.json`.
  - Mutating files outside `.cda/memory/`.

## Proposed Approach
- High-level architecture / public seams:
  - `src/tools/memory.py` / `src/domain/memory.py`:
    - `Memory` dataclass (`name`, `description`, `type`, `body`, `filename`).
    - `parse_memory_frontmatter(text: str) -> tuple[dict[str, str], str]`.
    - `write_memory_file(name, type, description, body, cwd) -> Path`.
    - `read_memory_file(filename, cwd) -> str | None`.
    - `list_memory_files(cwd) -> list[Memory]`.
    - `rebuild_memory_index(cwd) -> str`.
    - `select_relevant_memories(provider, messages, cwd, max_items) -> list[str]` with keyword fallback.
    - `extract_memories(provider, messages, cwd) -> int`.
    - `consolidate_memories(provider, cwd, threshold) -> tuple[int, int]`.
  - `src/tools/prompt.py`:
    - Incorporate `MEMORY.md` index and behavioral instructions into `assemble_system_prompt()`.
  - `src/tools/config.py`:
    - Add default `"memory"` config block (`enabled=True`, `max_relevant=5`, `consolidate_threshold=10`, `auto_extract=True`, `auto_consolidate=True`).
  - `src/application/query_engine.py`:
    - Memory prefetch / relevant memory injection into turn request messages.
    - Post-turn memory extraction and periodic consolidation triggering on natural turn completion.
  - `src/presentation/cli.py`:
    - Built-in `/memory` slash command handling before skill expansion.
- Alternatives rejected and why (Design-it-Twice comparison):
  - *Alternative A: Vector embeddings and external vector database.*
    - Rejected because adding sqlite-vec, chromadb, or numpy violates the strict stdlib-only requirement for `src/`. LLM side-query + keyword fallback on markdown files is lightweight, transparent, human-editable, and follows Learn Claude Code Session 09 architecture.
  - *Alternative B: Single monolithic memory file without individual frontmatter markdown files.*
    - Rejected because a single file cannot easily support fine-grained relevance selection, selective updates, metadata categorization (`user`, `feedback`, `project`, `reference`), or clean individual diffs.
  - *Alternative C: Persisting injected memory directly into session history JSON.*
    - Rejected because injected memories would permanently bloat session transcripts and duplicate across compaction cycles. Memories must be injected dynamically into request messages.
- Preserved behavior:
  - Feature 1: Tool execution, workspace bounds, concurrent batches, terminal events.
  - Feature 2: Permission gate, hard deny rules, `.cda/.permission_rules/rules.json`.
  - Feature 3: Planning tools, task board, nag reminders.
  - Feature 4: Dynamic skill loading, `load_skill`, `/<skill-name>` expansion.
  - Feature 5: Dynamic system prompt assembly from markdown templates.
  - Feature 6: Four-layer compaction pipeline (`tool_result_budget`, `snip_compact`, `micro_compact`, `compact_history`), reactive compact, `/compact` slash command.

## Risks & Dependencies
- Component dependencies: `src/application/query_engine.py`, `src/tools/prompt.py`, `src/tools/config.py`, `src/presentation/cli.py`, `src/infrastructure/session_store.py`.
- Security or migration risks:
  - Memory files must strictly remain under `.cda/memory/` within the workspace root; path traversal attempts in memory file names must be sanitized.
  - LLM side-query failures (e.g. rate limits or network issues) during memory extraction or relevance selection must fail gracefully and not break the main agent turn.
  - Infinite loops during extraction or consolidation must be prevented by using non-tool completions and strict token bounds.
- Open questions (blocking only): None.

## Disposition
- Approval decision: `Approved`
- Next skill/action: `/spec-requirements` spec authoring -> `/spec-plan`
