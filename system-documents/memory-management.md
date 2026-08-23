# Persistent Memory Management System

This document outlines the architecture, data models, end-to-end lifecycle flow, storage format, and operational behavior of the cross-session **Persistent Memory Management System** in `open-coding-agent`.

---

## 1. Architectural Concept

Conversational context stored in session transcripts (`.cda/.sessions/<session_id>.json`) is ephemeral to individual sessions and subject to context-window compaction (Feature 6). 

The **Persistent Memory System** provides durable, cross-session knowledge persistence that survives session resets, compaction, and application restarts. It operates on five core architectural principles:

1. **Human-Readable, File-Based Markdown Storage**: Memories are stored as standalone Markdown files with structured YAML frontmatter under `.cda/memory/<slug>.md`.
2. **Deterministic Central Index (`MEMORY.md`)**: A catalog file `.cda/memory/MEMORY.md` is automatically maintained and synchronized upon every write or consolidation.
3. **Two-Path Context Integration**:
   - **Path 1 (System Prompt Catalog)**: Injects the active `MEMORY.md` catalog and usage guidance into `assemble_system_prompt()`.
   - **Path 2 (Dynamic Relevance Retrieval)**: Lightweight pre-turn retrieval injects relevant memory contents into outgoing model request messages without polluting saved session JSON.
4. **Pre-Compression Snapshot Extraction**: Post-turn memory extraction runs against a pre-compaction dialogue snapshot so that compaction layers never starve the memory extractor.
5. **Bounded Store via Periodic Consolidation ("Dreaming")**: When memory file count reaches or exceeds `consolidate_threshold`, the system automatically triggers an LLM-assisted deduplication and pruning pass.

---

## 2. End-to-End Flow

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   User Submits Prompt                                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                ┌───────────────────────────┴───────────────────────────┐
                ▼                                                       ▼
  Path 1: System Prompt Catalog                          Path 2: Relevant Memory Retrieval
┌────────────────────────────────────────┐             ┌────────────────────────────────────────┐
│ assemble_system_prompt() reads         │             │ select_relevant_memories() evaluates   │
│ .cda/memory/MEMORY.md.                 │             │ recent user messages (up to 3 msgs,    │
│ Injects available memory catalog       │             │ <=2000 chars) against memory catalog.  │
│ into the dynamic system prompt.        │             │ Fallback: Keyword token overlap (>3ch).│
└──────────────────┬─────────────────────┘             └───────────────────┬────────────────────┘
                   │                                                       │
                   │                                                       ▼
                   │                                   ┌────────────────────────────────────────┐
                   │                                   │ Injects <relevant_memories> into       │
                   │                                   │ provider request messages copy ONLY.   │
                   │                                   │ (QueryEngine.history unmodified).      │
                   │                                   └───────────────────┬────────────────────┘
                   │                                                       │
                   └────────────────────────┬──────────────────────────────┘
                                            ▼
                           ┌──────────────────────────────────┐
                           │  Provider.complete(turn_request) │
                           └────────────────┬─────────────────┘
                                            │
                                            ▼
                           ┌──────────────────────────────────┐
                           │     Tool Execution Loop / Turn   │
                           └────────────────┬─────────────────┘
                                            │
                        Turn Completion (stop_reason != tool_use)
                                            │
                ┌───────────────────────────┴───────────────────────────┐
                ▼                                                       ▼
   Post-Turn Memory Extraction                            Periodic Memory Consolidation
┌────────────────────────────────────────┐             ┌────────────────────────────────────────┐
│ extract_memories() inspects            │             │ When file count >= threshold (def 10): │
│ pre-compression dialogue snapshot      │             │ consolidate_memories() merges          │
│ (last 10 msgs, <=4000 chars).          │             │ duplicates, resolves contradictions,   │
│ Writes new .md files & rebuilds index. │             │ prunes stale memories, updates index.  │
│ Emits status event: "extracted N"      │             │ Emits status event: "consolidated N->M"│
└────────────────────────────────────────┘             └────────────────────────────────────────┘
```

---

## 3. Memory File & Frontmatter Storage

### 3.1 Directory Structure

All persistent memories are contained within the workspace-bound directory `.cda/memory/`:

```
.cda/
└── memory/
    ├── MEMORY.md                      # Auto-generated central index catalog
    ├── user-preference-tabs.md        # Individual memory files with YAML frontmatter
    ├── feedback-no-db-mock.md
    └── project-auth-rewrite.md
```

### 3.2 File Format & YAML Frontmatter

Every memory file contains a standardized frontmatter header followed by a Markdown body:

```markdown
---
name: user-preference-tabs
description: User prefers tabs for indentation
type: user
---

User prefers using tabs, not spaces, for indentation across all code files.
**Why:** Consistency with existing repository formatting.
**How to apply:** Always use tabs for Python, JavaScript, and shell scripts.
```

### 3.3 Four Core Memory Types

| Memory Type | Purpose | Example |
|---|---|---|
| `user` | User persona, coding style, preferences | `"User prefers tabs over spaces"`, `"Prefer typed Python"` |
| `feedback` | Operational rules, instructions, behavioral guidelines | `"Don't mock database in integration tests"`, `"Keep functions concise"` |
| `project` | Project context, business logic, architectural facts | `"Auth rewrite is compliance-driven"`, `"Targeting Python 3.11+"` |
| `reference` | Pointers to documentation, issue trackers, file paths | `"Docker deployment scripts are in deploy/docker"` |

### 3.4 Index File (`MEMORY.md`)

Whenever a memory file is written, removed, or consolidated, `rebuild_memory_index()` regenerates `.cda/memory/MEMORY.md`:

```markdown
- [feedback-no-db-mock](feedback-no-db-mock.md) — Don't mock database in integration tests
- [project-auth-rewrite](project-auth-rewrite.md) — Auth rewrite is compliance-driven
- [user-preference-tabs](user-preference-tabs.md) — User prefers tabs for indentation
```

---

## 4. Relevance Retrieval & Injection

### 4.1 Two-Tier Selection Strategy

1. **Lightweight LLM Side-Query**: The engine queries the model with recent user messages and the catalog of memory titles/descriptions to return a JSON list of matching indices (e.g. `[0, 2]`), capped at `max_relevant` (default: 5).
2. **Deterministic Keyword Fallback**: If the model call fails, times out, or returns invalid JSON, the engine falls back to matching tokens (>3 characters) from the user prompt against memory names and descriptions.

### 4.2 Request-Only Injection Contract

When relevant memories are selected:
- The full contents of selected memory files are formatted into XML:
  ```xml
  <relevant_memories>
  ---
  name: user-preference-tabs
  description: User prefers tabs for indentation
  type: user
  ---

  User prefers using tabs, not spaces, for indentation.
  </relevant_memories>
  ```
- This block is prepended **only** to the outgoing user message in the ephemeral `request_messages` list passed to `Provider.complete()`.
- **Invariance**: Neither `QueryEngine.history` nor saved `.cda/.sessions/<id>.json` transcripts contain `<relevant_memories>`, preventing duplicate token inflation across sessions and compaction cycles.

---

## 5. Post-Turn Extraction & Consolidation ("Dreaming")

### 5.1 Post-Turn Extraction
- **Trigger**: When a turn completes without scheduling further tool calls (`stop_reason != "tool_use"` or loop termination).
- **Dialogue Source**: A snapshot of dialogue captured immediately **before** Feature 6 context compaction runs (`pre_compress`).
- **Prompting**: The LLM analyzes the last 10 messages (capped at 4000 characters) against existing memory titles and extracts non-duplicate items as JSON:
  `[{"name": "...", "type": "...", "description": "...", "body": "..."}]`
- **Error Handling**: Non-blocking; any extraction error is swallowed so user-facing turns never fail.

### 5.2 Consolidation ("Dreaming")
- **Trigger**: Runs after extraction when `len(list_memory_files()) >= consolidate_threshold` (default: 10).
- **Process**: Sends all existing memory bodies to the LLM with deduplication instructions. Replaces old files with consolidated results and rebuilds `MEMORY.md`.

---

## 6. Configuration & REPL Command

### 6.1 First-Run Initialization & Configuration (`.cda/config.json`)

On the application's first run (at startup in `src/presentation/cli.py`), `ensure_default_config()` checks if `.cda/config.json` exists. If missing, it initializes `.cda/config.json` using the recommended defaults defined in `src/tools/default_config.json`:

```json
{
  "show_tool_results": true,
  "compact": {
    "auto_compact": true,
    "max_messages": 50,
    "max_chars": 80000,
    "keep_head": 3,
    "keep_recent": 4,
    "keep_recent_tool_results": 3,
    "tool_result_max_bytes": 200000,
    "persist_preview_chars": 2000,
    "reactive_retries": 1,
    "compact_fail_retries": 3
  },
  "memory": {
    "enabled": true,
    "max_relevant": 5,
    "consolidate_threshold": 10,
    "auto_extract": true,
    "auto_consolidate": true
  }
}
```

- **Startup Initialization**: If `.cda/config.json` does not exist, it is written automatically from `src/tools/default_config.json`. Existing configuration files are preserved and never overwritten.
- **Missing Keys Fallback**: If `.cda/config.json` is partially defined by the user (e.g. only setting `"memory": {"max_relevant": 2}`), unmentioned keys fall back to the defaults in `src/tools/default_config.json`.

### 6.2 Slash Command (`/memory`)

Users can inspect persistent memories and utilization statistics directly from the REPL:

```
user >> /memory
[Status: Memories: 3 / 10
- [user] user-preference-tabs: User prefers tabs for indentation
- [feedback] feedback-no-db-mock: Don't mock database in integration tests
- [project] project-auth-rewrite: Auth rewrite is compliance-driven]
```

- Handled before skill expansion without starting a model turn or incurring token cost.

---

## 7. Verification & Quality Gates

The implementation is verified with pure Python 3.11+ standard library tests:

```bash
# Verify memory storage, YAML frontmatter, index rebuilding, and prompt assembly
python3 tests/tools_check.py

# Verify relevance selection, request-only injection, snapshot extraction, and dreaming
python3 tests/query_engine_check.py

# Verify REPL /memory slash command handling
python3 tests/cli_check.py

# Full regression suite across all features
python3 -m unittest discover -s tests -p '*_check.py'
```
