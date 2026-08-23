# Session Extracts: `7-memory-management`

## Candidate Lessons

- `[CANDIDATE]` Request-only memory injection: Injecting `<relevant_memories>` only into the ephemeral request messages copy keeps session JSON strictly pure conversation history and avoids duplicate memory pollution across compaction cycles.
- `[CANDIDATE]` Pre-compression snapshot for extraction: Capturing dialogue history before L1-L4 compaction ensures post-turn memory extraction has full fidelity access to recent user preferences and project facts.
- `[CANDIDATE]` Two-tier relevance selection: Combining LLM side-query indexing with keyword matching fallback guarantees that transient side-query errors or invalid JSON will never break memory retrieval or fail the user turn.
- `[CANDIDATE]` YAML frontmatter in standalone Markdown files + MEMORY.md index: Human-readable individual files with an index catalog make memory transparent, editable by operators, and easily injected into system prompts without database dependencies.
