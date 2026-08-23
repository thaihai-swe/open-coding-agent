# Implementation Plan

## Metadata
- Feature/profile: `7-memory-management` / Complex
- Spec approved date: 2026-08-23
- Status: Draft
- Heuristics applied: `LH-001` (machine-verifiable proof commands on every seam), `LH-002` (test proof before implementation changes)

## Lightweight Design

Brownfield feature implementation. Implement Session 09 persistent cross-session memory management in Python 3.11+ stdlib:
1. **Persistent storage (`.cda/memory/`)**: Store individual memory items as `.md` files with YAML-like frontmatter (`name`, `description`, `type` where type is `user`, `feedback`, `project`, `reference`) and markdown body. Automatically maintain `.cda/memory/MEMORY.md` index file.
2. **Config consolidation (`.cda/config.json`)**: Add `"memory"` configuration block (`enabled`, `max_relevant`, `consolidate_threshold`, `auto_extract`, `auto_consolidate`) to `.cda/config.json` with locked defaults.
3. **Dynamic System Prompt Integration**: Incorporate `MEMORY.md` catalog into `assemble_system_prompt()` via the `"memory"` prompt section (`src/prompts/memory.md` / `.cda/prompts/memory.md` / inline fallback).
4. **Pre-Turn Relevant Memory Retrieval**: Run lightweight side-query on start of user turn to select up to `max_relevant` (default 5) memories with keyword fallback, injecting `<relevant_memories>` into outgoing request messages without modifying `engine.history` or session JSON.
5. **Post-Turn Extraction & Consolidation ("Dreaming")**: Extract new memories from a pre-compaction dialogue snapshot on turn completion; trigger consolidation when file count ≥ `consolidate_threshold` (default 10).
6. **Builtin REPL `/memory` Command**: Intercept `/memory` in REPL before skill expansion to display memory entries and utilization statistics.

- Approach and affected modules:
  - `src/tools/memory.py`: New deep module for memory file I/O, frontmatter parsing, index rebuild, slug sanitization, LLM relevance selection with keyword fallback, LLM extraction, and LLM consolidation.
  - `src/tools/config.py`: Add `DEFAULT_MEMORY_CONFIG` and `resolve_memory_config()`; update `ensure_default_config()`.
  - `src/prompts/memory.md`: Bundled default memory prompt template.
  - `src/tools/prompt.py`: Update `PROMPT_SECTIONS` and `FALLBACK_SECTIONS` with `"memory"`; format memory catalog in `assemble_system_prompt()`.
  - `src/application/query_engine.py`: Integrate relevant memory prefetch, request-only injection, pre-compression snapshot, post-turn extraction, and periodic consolidation into turn loop.
  - `src/presentation/cli.py`: Intercept `/memory` slash command in REPL before skill expansion.
  - `tests/`: `tests/tools_check.py`, `tests/query_engine_check.py`, `tests/cli_check.py`.
- First useful slice and proof:
  - Slice 1: Memory store, frontmatter parser, index builder, and config loader (`tests/tools_check.py`: AC-001–AC-004, AC-006–AC-008).
  - Slice 2: QueryEngine relevant selection, request-only injection, pre-compression snapshot, post-turn extraction, consolidation, and tool-less side-queries (`tests/query_engine_check.py`: AC-005, AC-009–AC-015, AC-018–AC-020).
  - Slice 3: CLI `/memory` slash command and non-regression (`tests/cli_check.py`: AC-016, AC-017, AC-020).

## Technical Context

- Language/Version: Python 3.11+ (`StrEnum`, `dataclasses`, `pathlib`, `json`, `datetime`, `re`). Observed Python 3.13.13.
- Primary Dependencies: Python standard library only (`argparse`, `dataclasses`, `json`, `pathlib`, `re`, `typing`, `unittest`, `urllib`). Zero third-party packages in `src/`.
- Storage/Data:
  - Memory directory: `.cda/memory/<slug>.md`
  - Memory index: `.cda/memory/MEMORY.md`
  - Config: `.cda/config.json`
  - Sessions: `.cda/.sessions/<session_id>.json`
  - Transcripts: `.cda/.transcripts/<session_id>-<utc-timestamp>.jsonl`
- Target Platform: Local CLI (`python3 -m src.cli`).
- Performance Goals:
  - Memory file reads and index rebuild in <2ms.
  - Frontmatter parsing and slug sanitization in <1ms.
  - Pre-turn selection and post-turn extraction execute lightweight side-queries with zero tool loops.
- Key Constraints:
  - 100% Python stdlib in `src/`.
  - Dynamic system prompt and `<relevant_memories>` tags are never persisted into `.cda/.sessions/<session_id>.json`.
  - Session JSON structure remains strictly `{"messages": [...]}`.
  - Memory file operations stay strictly inside `.cda/memory/` within process cwd.
  - Side-query failures (network, invalid JSON) fail gracefully without aborting the main user turn.

## Constraints

- Non-goals:
  - Embeddings, vector databases, or third-party tokenizers.
  - Multi-agent team memory synchronization.
  - Four-gate complex Dream scheduler (time, scan throttle, session count, file lock); teaching-version file-count threshold only.
  - Main-registry memory tool in MVP (memory management is engine-driven and command-inspected).
- Security/trust boundaries:
  - All memory file writes remain within `.cda/memory/` under process cwd.
  - Memory names/slugs are sanitized to prevent directory traversal (`..` or `/` / `\`).
- Preserved behavior:
  - Feature 1: Tool execution, workspace bound, concurrent batch dispatch, terminal and JSON event output.
  - Feature 2: Permission gate, hard deny list, project rules in `.cda/.permission_rules/rules.json`, interactive authorize.
  - Feature 3: Six planning tools, per-session task board under `.cda/.todos/`, 3-round planning nag, messages-only session JSON.
  - Feature 4: Two-level skill loading (`load_skill`), dynamic skill catalog, `/<skill-name>` slash expansion.
  - Feature 5: Dynamic runtime system prompt assembly with markdown section overrides.
  - Feature 6: Four-layer compaction pipeline (`tool_result_budget`, `snip_compact`, `micro_compact`, `compact_history`), reactive compact, `/compact` slash command.

## Approach

### Interfaces & Data Flow

```
User Turn Start
      │
      ▼
[ QueryEngine.turn(prompt) ]
      │
      ├──► 1. Pre-Turn Relevant Memory Selection (if enabled and memory files exist):
      │       ├── Side-Query: Provider.complete(recent_user_text + catalog, tools=[])
      │       ├── Parse JSON indices array -> fallback to keyword matching on error
      │       └── Inject <relevant_memories>...</relevant_memories> into outgoing request copy ONLY
      │
      ├──► 2. Pre-Compression History Snapshot:
      │       └── Capture pre_compress = [m for m in self.history] before compaction
      │
      ├──► 3. Four-Layer Compaction Pipeline (Feature 6):
      │       ├── L3 tool_result_budget()
      │       ├── L1 snip_compact()
      │       ├── L2 micro_compact()
      │       └── L4 compact_history() if thresholds exceeded
      │
      ├──► 4. Provider Completion & Tool Loop:
      │       ├── Provider.complete(with_system(request_messages), tools)
      │       └── Execute tool batches until stop_reason != "tool_use" or max_turns
      │
      └──► 5. Post-Turn Memory Extraction & Consolidation:
              ├── If auto_extract and enabled:
              │   ├── Side-Query: Provider.complete(existing_memories + pre_compress dialogue, tools=[])
              │   ├── Write new memory files to .cda/memory/<slug>.md
              │   └── Rebuild .cda/memory/MEMORY.md
              │
              └── If auto_consolidate and enabled and file_count >= consolidate_threshold:
                  ├── Side-Query: Provider.complete(all_memory_files, tools=[])
                  ├── Replace old memory files with consolidated results
                  └── Rebuild .cda/memory/MEMORY.md
```

### Public Seams (Test Surface)

| Seam | Observes | ACs |
| --- | --- | --- |
| `src/tools/memory.py` (`write_memory_file`, `read_memory_file`, `list_memory_files`, `rebuild_memory_index`, `parse_memory_frontmatter`, `sanitize_slug`) | Frontmatter parsing; YAML metadata formatting; safe file writing in `.cda/memory/`; index generation in `MEMORY.md`; path traversal sanitization | AC-001, AC-002 |
| `src/tools/config.py` (`resolve_memory_config`, `DEFAULT_MEMORY_CONFIG`, `ensure_default_config`) | Unified `.cda/config.json` memory block resolution; defaults; non-interference with compact knobs | AC-003, AC-004 |
| `src/tools/prompt.py` (`assemble_system_prompt`, `load_prompt_section("memory")`) | Injection of `MEMORY.md` index into system prompt; prompt section override via `.cda/prompts/memory.md`; empty index handling | AC-006, AC-007, AC-008 |
| `src/tools/memory.py` (`select_relevant_memories`, `extract_memories`, `consolidate_memories`) | LLM side-query relevance selection; keyword matching fallback; post-turn extraction from dialogue; consolidation at threshold; graceful error swallowing | AC-009, AC-010, AC-012, AC-013, AC-014, AC-015, AC-018 |
| `src/application/query_engine.py` (`turn`, `_with_system`, `_save`) | Memory prefetch; request-only memory injection (not in `history` or session JSON); pre-compression snapshot usage; tool-less side-query invocations; memory disable knob | AC-005, AC-009, AC-011, AC-018, AC-019 |
| `src/presentation/cli.py` (REPL loop) | Builtin `/memory` slash command handling before skills; listing entries and stats; preserving other skill expansions | AC-016, AC-017, AC-020 |

### Key Decisions and Trade-offs

1. **Dedicated `src/tools/memory.py` Deep Module (Chosen)**
   - Encapsulates memory file I/O, frontmatter parsing, index generation, relevance side-queries, extraction, and consolidation behind a clean interface.
   - *Rationale*: Keeps `QueryEngine` focused on orchestration while making all memory operations independently testable without full agent turns.

2. **Request-Only Memory Injection (Chosen)**
   - Injects `<relevant_memories>` only into the ephemeral request messages list sent to `Provider.complete()`, leaving `QueryEngine.history` and `.cda/.sessions/<session_id>.json` unmodified.
   - *Rationale*: Prevents memory duplication across turns and keeps session JSON strictly pure conversation messages without transient context wrappers.

3. **Pre-Compression Snapshot for Extraction (Chosen)**
   - Captures a snapshot of conversation history immediately before running L1-L4 compaction layers. Post-turn extraction runs against this snapshot.
   - *Rationale*: Prevents compaction from pruning recent user preferences before the extractor has had a chance to discover and persist them.

4. **Two-Tier Relevance Selection with Keyword Fallback (Chosen)**
   - Attempts LLM side-query selection first; if the model call fails or returns unparsable JSON, falls back to matching keywords (>3 chars) against memory names and descriptions.
   - *Rationale*: Follows Learn Claude Code s09 architecture, ensuring graceful degradation without network or parsing fragility.

5. **Consolidation by File Count Threshold (Chosen)**
   - Automatically triggers consolidation when `len(list_memory_files()) >= consolidate_threshold` (default 10).
   - *Rationale*: Simple, deterministic, and effective without requiring background timers or multi-process lock systems.

### Module Map

| Path | Public Seam | Responsibility | Depends on | Split / Co-locate |
| --- | --- | --- | --- | --- |
| `src/tools/memory.py` **new** | `Memory`, `write_memory_file`, `read_memory_file`, `list_memory_files`, `rebuild_memory_index`, `parse_memory_frontmatter`, `sanitize_slug`, `select_relevant_memories`, `extract_memories`, `consolidate_memories` | Pure memory management, frontmatter serialization, index builder, side-query selection, extraction, consolidation | `pathlib`, `re`, `json`, `dataclasses`, `src.domain.models`, `src.domain.provider` | New single-responsibility memory subsystem module |
| `src/tools/config.py` | `DEFAULT_MEMORY_CONFIG`, `resolve_memory_config`, `ensure_default_config` | Extends `.cda/config.json` with memory knobs (`enabled`, `max_relevant`, `consolidate_threshold`, `auto_extract`, `auto_consolidate`) | `pathlib`, `json` | Extends existing config loader |
| `src/prompts/memory.md` **new** | Markdown prompt | Default memory guidance and catalog instructions | None | Co-located with other prompt templates |
| `src/tools/prompt.py` | `load_prompt_section("memory")`, `assemble_system_prompt` | Incorporates `MEMORY.md` index and memory prompt section into dynamic system prompt | `src.tools.memory`, `src.tools.config` | Extends prompt assembly |
| `src/application/query_engine.py` | `QueryEngine.turn`, `_with_system`, `_turn` | Pre-turn relevant memory retrieval, request injection, pre-compression snapshotting, post-turn extraction and consolidation | `src.tools.memory`, `src.tools.config`, `src.tools.prompt` | Application turn orchestration |
| `src/presentation/cli.py` | REPL loop | Intercept `/memory` slash command before skill expansion, display memory catalog and stats | `src.tools.memory` | Presentation entrypoint |
| `tests/tools_check.py` | Unittest suite | Unit tests for memory frontmatter parsing, file writing, index rebuilding, slug sanitization, memory config, prompt assembly with memory | `src.tools.memory`, `src.tools.config`, `src.tools.prompt` | Extended |
| `tests/query_engine_check.py` | Unittest suite | Integration tests for pre-turn relevance selection, request-only injection, extraction from pre-compression snapshot, consolidation at threshold, side-query error handling | `src.application.query_engine`, `src.tools.memory` | Extended |
| `tests/cli_check.py` | Unittest suite | Tests for REPL `/memory` command handling and skill expansion preservation | `src.presentation.cli`, `src.tools.memory` | Extended |

Dependency direction:
```
presentation (cli.py) ──► application (query_engine.py) ──► tools/memory.py
         │                               │               ──► tools/compact.py
         ▼                               │               ──► tools/config.py
tools/config.py                          │               ──► tools/prompt.py
tools/memory.py                          ▼               ──► tools/registry.py
                                   domain / models
```

### Non-Functional Considerations

- `NFR-001` Stdlib-Only: Zero third-party dependencies in `src/` (`AC-020`).
- `NFR-002` Session JSON Cleanliness: Saved session transcripts in `.cda/.sessions/<id>.json` contain only conversation history without system messages or `<relevant_memories>` tags (`AC-009`, `AC-019`).
- `NFR-003` Workspace-Bounded Persistence: Memory files stay strictly within `.cda/memory/` under process cwd (`AC-001`, `AC-002`).
- `NFR-004` Tool-Less Side Queries: Relevance selection, extraction, and consolidation run with `tools=[]` and never enter tool loops or recurse (`AC-018`).
- `NFR-005` Graceful Failure Recovery: Side-query errors (LLM failure, malformed JSON) are swallowed and do not fail the user turn (`AC-010`, `AC-015`).
- `NFR-006` Compaction Interoperability: Pre-compression snapshot preserves dialogue history so Feature 6 compaction does not starve memory extraction (`AC-011`, `AC-019`).

## Alternatives Considered

| Option | Depth / seam / blast radius | Chosen? | Why rejected or kept |
| --- | --- | --- | --- |
| Dedicated `src/tools/memory.py` module | High depth; isolates all memory parsing, indexing, selection, extraction, and consolidation from the query engine | Yes | Provides a clean, cohesive, and unit-testable module for all memory domain logic. |
| Inlining memory logic directly in `QueryEngine` | Low depth; pollutes `QueryEngine` with file I/O, frontmatter regex, catalog formatting, and side-query prompts | No | Violates Single Responsibility and complicates test isolation. |
| Vector embeddings (e.g. SQLite-vec / Chroma) | High complexity and requires C-extensions/external dependencies | No | Violates project constraint of Python 3.11+ stdlib only in `src/`. |
| Writing injected memories into `engine.history` | Pollutes persistent history and session JSON transcripts | No | Violates session JSON integrity and causes duplicate memories across compactions. |

## Complexity Tracking

| Violation / Shortcut | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Keyword matching fallback for LLM selector | Prevents memory lookup failure if the LLM side-query errors or returns invalid JSON | Failing silently or crashing would degrade user experience on transient model hiccups |
| Pre-compression snapshot before L1-L4 compaction | Ensures memory extraction has access to full fidelity dialogue even if compaction runs in the same turn | Extracting from compacted summary misses fine-grained user preferences |
| File count threshold for consolidation | Binds the maximum number of memory files without complex multi-process background daemons | Four-gate background daemon adds unnecessary concurrency complexity to local CLI |

## Delivery

Ordered milestone roadmap:

1. **M1: Memory Storage, Indexing, Config & Prompts (`src/tools/memory.py`, `src/tools/config.py`, `src/prompts/memory.md`, `src/tools/prompt.py`)**
   - Implement `Memory` dataclass, `parse_memory_frontmatter`, `write_memory_file`, `read_memory_file`, `list_memory_files`, `rebuild_memory_index`, and `sanitize_slug` in `src/tools/memory.py`.
   - Update `src/tools/config.py` with `DEFAULT_MEMORY_CONFIG`, `resolve_memory_config()`, and `ensure_default_config()`.
   - Add `src/prompts/memory.md` and update `src/tools/prompt.py` (`load_prompt_section("memory")`, `assemble_system_prompt()` with `MEMORY.md` index catalog).
   - Unit tests in `tests/tools_check.py` for storage, frontmatter, index rebuilding, slug sanitization, config resolution, and prompt catalog assembly.
   - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-006`, `AC-007`, `AC-008`.

2. **M2: Relevance Selection, Request Injection, Post-Turn Extraction & Consolidation (`src/tools/memory.py`, `src/application/query_engine.py`)**
   - Implement `select_relevant_memories`, `format_relevant_memories`, `extract_memories`, and `consolidate_memories` in `src/tools/memory.py`.
   - Integrate pre-turn memory prefetch and `<relevant_memories>` request-only injection into `QueryEngine.turn()`.
   - Capture pre-compression snapshot before `_apply_pre_complete_compaction()`.
   - Add post-turn extraction and periodic consolidation triggering on natural turn completion.
   - Unit tests in `tests/query_engine_check.py` for selection, keyword fallback, request injection isolation, pre-compression snapshotting, post-turn extraction, threshold consolidation, error swallowing, and tool-less side-queries.
   - Covers: `AC-005`, `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-013`, `AC-014`, `AC-015`, `AC-018`, `AC-019`.

3. **M3: CLI `/memory` Slash Command & Full Regression (`src/presentation/cli.py`, `tests/cli_check.py`)**
   - Implement `/memory` slash command handling in `src/presentation/cli.py` before skill expansion.
   - Output formatted memory list and file count statistics via `status` events.
   - Unit tests in `tests/cli_check.py` for `/memory` execution, listing, no turn execution, and skill expansion preservation.
   - Run full regression suite `python3 -m unittest discover -s tests -p '*_check.py'` and `python3 -m compileall -q src`.
   - Covers: `AC-016`, `AC-017`, `AC-020`.

Rollback or migration:
- Revert added files (`src/tools/memory.py`, `src/prompts/memory.md`) and edits to `config.py`, `prompt.py`, `query_engine.py`, `cli.py`.
- No database migrations or irreversible storage formats.

Open risks:
- None identified; all storage is scoped to `.cda/memory/`.

Next step: execute `/spec-tasks` to build the executable task graph.
