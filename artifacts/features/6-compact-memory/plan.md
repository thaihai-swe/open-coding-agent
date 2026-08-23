# Implementation Plan

## Metadata
- Feature/profile: `6-compact-memory` / Complex
- Spec approved date: 2026-08-23
- Status: Draft
- Heuristics applied: `LH-001` (machine-verifiable proof commands on every seam), `LH-002` (test proof before implementation changes)

## Lightweight Design

Brownfield change_request. Implement the 4-layer context compaction pipeline (Session 08 / s08) in Python 3.11+ stdlib:
1. **Config consolidation**: Replace `.cda/ui-config.json` with `.cda/config.json` (hard cutover) holding `show_tool_results` and compaction knobs (`auto_compact`, `max_messages`, `max_chars`, `keep_head`, `keep_recent`, `keep_recent_tool_results`, `tool_result_max_bytes`, `persist_preview_chars`, `reactive_retries`, `compact_fail_retries`).
2. **Compact prompt template**: Bundled `src/prompts/compact.md` with `.cda/prompts/compact.md` override support via `load_prompt_section("compact")`.
3. **Cheap pre-processors (0 API calls)**: L3 `tool_result_budget` (persists oversized tool outputs to `.cda/task_outputs/tool-results/`), L1 `snip_compact` (trims middle of history when message count > `max_messages`), L2 `micro_compact` (replaces older tool results >120 chars with placeholders), with boundary guards preserving `assistant(tool_calls)` -> `tool(tool_result)` pairings.
4. **LLM summarization (1 API call)**: L4 `compact_history` creates a pre-compaction transcript in `.cda/.transcripts/<session_id>-<timestamp>.jsonl`, calls provider for summary, replaces older prefix with `<compacted-summary>...</compacted-summary>`, and keeps a `keep_recent` message tail. Protected by a circuit breaker (max 3 consecutive failures).
5. **Reactive compact**: Catches context overflow errors (`prompt_too_long`, `context length`, HTTP 413) and retries with emergency tail compaction (`reactive_retries=1`).
6. **Invocation interfaces**: Reserved REPL `/compact` slash command, model-facing LOW `compact` tool, and auto-compaction before `complete()`.

- Approach and affected modules:
  - `src/tools/config.py`: Single configuration loader for `.cda/config.json` with default fallbacks.
  - `src/prompts/compact.md`: Bundled default compaction summary prompt.
  - `src/tools/compact.py`: Pure functions for L1 snip, L2 micro, L3 budget persister, character estimation, and boundary-guard calculation.
  - `src/tools/handlers/agent.py`: Register LOW `compact` tool in registry.
  - `src/tools/prompt.py`: Update `PROMPT_SECTIONS` and `FALLBACK_SECTIONS` for `"compact"`.
  - `src/application/query_engine.py`: Integrate L3->L1->L2->L4 pipeline, transcript snapshots, reactive retry, manual compact, and tool compact.
  - `src/presentation/cli.py`: Switch to `.cda/config.json`; intercept `/compact` in REPL before skill expansion.
  - `tests/`: `tests/tools_check.py`, `tests/query_engine_check.py`, `tests/cli_check.py`.
- First useful slice and proof:
  - Slice 1: Config loader and pure compaction pipeline functions (`tools_check.py`: AC-001, AC-002, AC-004–AC-008, AC-011, AC-024).
  - Slice 2: QueryEngine L4 compaction, transcript snapshots, prompt template, reactive compact, and circuit breaker (`query_engine_check.py`: AC-009, AC-010, AC-012, AC-015–AC-022).
  - Slice 3: CLI `/compact` slash command and `.cda/config.json` hard cutover (`cli_check.py`: AC-003, AC-013, AC-014, AC-023).

## Technical Context

- Language/Version: Python 3.11+ (`StrEnum`, `dataclasses`, `pathlib`, `json`, `datetime`). Observed Python 3.13.13.
- Primary Dependencies: Python standard library only (`argparse`, `dataclasses`, `json`, `pathlib`, `re`, `typing`, `unittest`, `urllib`). Zero third-party packages in `src/`.
- Storage/Data:
  - Config: `.cda/config.json`
  - Transcripts: `.cda/.transcripts/<session_id>-<utc-timestamp>.jsonl`
  - Persisted tool outputs: `.cda/task_outputs/tool-results/<sanitized_call_id>.txt`
  - Transcripts/sessions: `.cda/.sessions/<session_id>.json`
- Target Platform: Local CLI (`python3 -m src.cli`).
- Performance Goals:
  - Cheap layers (L1, L2, L3) execute in <2ms with zero network calls.
  - Character estimation runs in <1ms over hundreds of messages.
  - Summarization latency equals one standard provider completion turn.
- Key Constraints:
  - 100% Python stdlib in `src/`.
  - System prompt is dynamic and never persisted into session JSON.
  - Session JSON structure remains strictly `{"messages": [...]}`.
  - Tool calls and their matching tool results must never be separated across compaction boundaries.
  - `.cda/ui-config.json` is ignored (hard cutover to `.cda/config.json`).

## Constraints

- Non-goals:
  - Session 09 persistent memory (`MEMORY.md`, `.memory/`, dreaming).
  - Third-party tokenizers (e.g. tiktoken).
  - Transcript retrieval tools in MVP.
  - Complex custom template engines.
- Security/trust boundaries:
  - All disk writes (transcripts, persisted tool outputs, sessions, config) remain within process cwd (`.cda/`).
  - Tool call IDs in file paths are sanitized against path traversal (`..` or `/` / `\`).
  - Redaction of `api_key` and `authorization` keys is applied to transcript JSONL snapshots.
- Preserved behavior:
  - Feature 1: Tool execution, workspace bound, concurrent batch dispatch, terminal and JSON event output.
  - Feature 2: Permission gate, hard deny list, project rules in `.cda/.permission_rules/rules.json`, interactive authorize.
  - Feature 3: Six planning tools, per-session task board under `.cda/.todos/`, 3-round planning nag, messages-only session JSON.
  - Feature 4: Two-level skill loading (`load_skill`), dynamic skill catalog, `/<skill-name>` slash expansion.
  - Feature 5: Dynamic runtime system prompt assembly with markdown section overrides (`identity`, `planning`, `security`).

## Approach

### Interfaces & Data Flow

```
User Turn / Model Turn
        │
        ▼
[ QueryEngine.turn() ]
        │
        ├──► 1. Pre-complete Compaction Pipeline (if auto_compact=true):
        │       ├── L3 tool_result_budget() ──► Persist >200KB results to .cda/task_outputs/tool-results/
        │       ├── L1 snip_compact()       ──► Trim middle if len > max_messages (safe boundary)
        │       └── L2 micro_compact()      ──► Replace older tool results >120 chars with placeholder
        │
        ├──► 2. Threshold Check (len > max_messages OR chars > max_chars):
        │       └── L4 compact_history():
        │           ├── Snapshot history to .cda/.transcripts/<session_id>-<ts>.jsonl
        │           ├── Load compact prompt (src/prompts/compact.md / .cda/prompts/compact.md)
        │           ├── Provider.complete(summary_prompt, tools=[])
        │           └── Replace history with [summary_user_message] + recent_window (safe boundary)
        │
        ├──► 3. Provider.complete(with_system(history), tools):
        │       └── If ProviderError("prompt_too_long" / "context length" / 413):
        │           └── Emergency reactive_compact() + retry (up to reactive_retries)
        │
        ├──► 4. Tool Execution:
        │       └── If tool == "compact":
        │           └── Run L4 compact_history() and terminate turn loop
        │
        └──► 5. Save compacted history to .cda/.sessions/<session_id>.json
```

### Public Seams (Test Surface)

| Seam | Observes | ACs |
| --- | --- | --- |
| `src/tools/config.py` (`load_config`, `resolve_compact_config`) | Unified `.cda/config.json` loading; defaults; hard cutover (ignoring `ui-config.json`) | AC-001, AC-002, AC-003 |
| `src/tools/compact.py` (`estimate_history_chars`, `tool_result_budget`, `snip_compact`, `micro_compact`, `find_safe_boundary`, `sanitize_filename`) | L3 output persister; L1 middle snip; L2 micro placeholder; boundary-guard pairing invariant; path traversal sanitization; character estimation | AC-004, AC-005, AC-006, AC-007, AC-008, AC-011, AC-024 |
| `src/prompts/compact.md` & `src/tools/prompt.py` (`load_prompt_section("compact")`) | Compaction prompt template; default markdown and `.cda/prompts/` override | AC-020 |
| `src/tools/handlers/agent.py` (`compact` tool) | LOW `compact` tool registration and dispatch | AC-015 |
| `src/application/query_engine.py` (`turn`, `compact_history`, `reactive_compact`, `_save`) | Auto-compaction before `complete()`; L4 transcript snapshot; history replacement; recent window; reactive compact retry; circuit breaker; status event emission; session JSON formatting; Feature 5 prompt assembly preservation | AC-009, AC-010, AC-012, AC-015, AC-016, AC-017, AC-018, AC-019, AC-020, AC-021, AC-022 |
| `src/presentation/cli.py` (REPL loop & config wiring) | Builtin `/compact` slash command intercepted before skills; `.cda/config.json` UI setting resolution | AC-003, AC-013, AC-014, AC-023 |

### Key Decisions and Trade-offs

1. **Dedicated `src/tools/compact.py` Module (Chosen)**
   - Encapsulates pure transformation functions (`estimate_history_chars`, `tool_result_budget`, `snip_compact`, `micro_compact`, `find_safe_boundary`) without coupling to provider or session I/O.
   - *Rationale*: Cleanly isolates unit-testable array slicing and boundary math from network and file orchestration.

2. **Unified `.cda/config.json` with Hard Cutover (Chosen)**
   - Replaces `.cda/ui-config.json`. Single configuration point for `show_tool_results` and `compact` parameters.
   - *Rationale*: Eliminates scattered config files while providing operators a single configuration surface.

3. **Safe Boundary Guard Invariant (Chosen)**
   - In both L1 snip and L4 history splitting, if the cut index falls on a `tool` (tool_result) message whose preceding message is an assistant `tool_calls`, the cut index is adjusted so the assistant message and its tool results are never separated.
   - *Rationale*: OpenAI-compatible API schemas require every tool result to correspond to an active tool call in the same immediate context block. Breaking them causes immediate HTTP 400 rejection.

4. **Transcript Archival Snapshots (Chosen)**
   - Before L4 or reactive compaction, full history is appended/written to `.cda/.transcripts/<session_id>-<utc_timestamp>.jsonl` with API key redaction.
   - *Rationale*: Preserves complete recoverable records on disk while bounding the active context window.

5. **Circuit Breaker on Summarizer Failures (Chosen)**
   - Tracks `_consecutive_compact_failures`. If provider completion fails 3 times consecutively during summarization, compaction is skipped and the turn continues with cheap-layer edits rather than entering an infinite retry loop.

### Module Map

| Path | Public Seam | Responsibility | Depends on | Split / Co-locate |
| --- | --- | --- | --- | --- |
| `src/tools/config.py` **new** | `load_config`, `resolve_compact_config`, `DEFAULT_CONFIG` | Reads `.cda/config.json`, resolves defaults, provides unified configuration | `pathlib`, `json` | New single-responsibility config module |
| `src/prompts/compact.md` **new** | Markdown prompt | Default compaction instruction template | None | Co-located with other prompt templates |
| `src/tools/compact.py` **new** | `estimate_history_chars`, `tool_result_budget`, `snip_compact`, `micro_compact`, `find_safe_boundary`, `sanitize_filename` | Pure history compression functions (L1, L2, L3) and boundary guards | `pathlib`, `src.domain.models` | New pure compression helper module |
| `src/tools/prompt.py` | `load_prompt_section("compact")` | Add `"compact"` to prompt sections and fallback definitions | `src.tools.config` | Extends prompt loader |
| `src/tools/handlers/agent.py` | `compact` tool registration | Exposes `compact` tool in registry (LOW, Agent) | `src.tools.registry` | Co-located with agent tools (`load_skill`) |
| `src/application/query_engine.py` | `QueryEngine.turn`, `compact_history`, `reactive_compact` | Orchestrates 4-layer pipeline before `complete()`, reactive retry, transcript snapshot, circuit breaker | `src.tools.compact`, `src.tools.config`, `src.tools.prompt` | Application turn orchestration |
| `src/presentation/cli.py` | REPL loop & `_resolve_show_tool_results` | Intercept `/compact` before skill expansion; load UI settings from `.cda/config.json` | `src.tools.config` | Presentation entrypoint |
| `tests/tools_check.py` | Unittest suite | Unit tests for config loading, L1 snip, L2 micro, L3 budget, boundary guard, file sanitization | `src.tools.config`, `src.tools.compact` | Extended |
| `tests/query_engine_check.py` | Unittest suite | Integration tests for auto-compact, L4 summary, transcript snapshot, reactive retry, circuit breaker, compact tool | `src.application.query_engine` | Extended |
| `tests/cli_check.py` | Unittest suite | Tests for REPL `/compact` handling and `.cda/config.json` cutover | `src.presentation.cli` | Extended |

Dependency direction:
```
presentation (cli.py) ──► application (query_engine.py) ──► tools/compact.py
         │                               │               ──► tools/config.py
         ▼                               │               ──► tools/prompt.py
tools/config.py                          ▼               ──► tools/registry.py
                                   domain / models
```

### Non-Functional Considerations

- `NFR-001` Stdlib-Only: Zero third-party dependencies in `src/` (`AC-023`).
- `NFR-002` Transcript Isolation: Saved session transcripts in `.cda/.sessions/<id>.json` contain only conversation history without system messages (`AC-012`, `AC-022`).
- `NFR-003` Workspace Bounded Persistence: Transcripts under `.cda/.transcripts/` and tool outputs under `.cda/task_outputs/tool-results/` stay in process cwd (`AC-004`, `AC-009`, `AC-024`).
- `NFR-004` Boundary Integrity: Tool calls and tool results are never separated across compaction slices (`AC-006`, `AC-011`).
- `NFR-005` Bounded Failure Recovery: Summarizer retries capped at 3, reactive retries capped at 1 (`AC-018`, `AC-019`).
- `NFR-006` Unified Config Cutover: `.cda/config.json` is the sole source of truth for runtime settings (`AC-001`, `AC-003`).

## Alternatives Considered

| Option | Depth / seam / blast radius | Chosen? | Why rejected or kept |
| --- | --- | --- | --- |
| Dedicated `src/tools/compact.py` pure functions | High depth; isolates compression transformations from I/O and turn loop | Yes | Makes all 4 layers independently testable with standard unit assertions. |
| Inlining all compression logic inside `QueryEngine` | Low depth; overcomplicates `QueryEngine` with file I/O, regex, slicing, and config parsing | No | Violates Single Responsibility and complicates test isolation. |
| Token-based estimation using `tiktoken` | High precision, but introduces external C/Rust binary dependency | No | Violates project constraint of Python 3.11+ stdlib only in `src/`. |
| Separate `ui-config.json` and `compact-config.json` | Splits configuration across multiple files in `.cda/` | No | Consolidating into `.cda/config.json` provides a clean, unified config point for the user. |

## Complexity Tracking

| Violation / Shortcut | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Character-based token estimation heuristic | Eliminates third-party tokenizer dependencies in `src/` | Standard library has no BPE tokenizer; character sum is fast and sufficient when paired with reactive compaction |
| Multi-file `.cda/.transcripts/` snapshots | Preserves full historical auditability before destructive compaction | Without transcript snapshots, lost conversation history is unrecoverable |
| Boundary sliding logic | Guarantees valid OpenAI API message structure | Arbitrary slicing orphans `ToolResult` messages, causing hard API 400 failures |

## Delivery

Ordered milestone roadmap:

1. **M1: Configuration & Pure Compaction Transformers (`src/tools/config.py`, `src/tools/compact.py`, `src/prompts/compact.md`)**
   - Implement `load_config` and default config resolution in `src/tools/config.py`.
   - Implement `estimate_history_chars`, `tool_result_budget`, `snip_compact`, `micro_compact`, `find_safe_boundary`, and filename sanitization in `src/tools/compact.py`.
   - Add `src/prompts/compact.md` and update `src/tools/prompt.py`.
   - Unit tests in `tests/tools_check.py` for config loading, defaults, L3 budget persister, L1 snip, L2 micro, and boundary safety.
   - Covers: `AC-001`, `AC-002`, `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-011`, `AC-024`.

2. **M2: QueryEngine Compaction & Tool Integration (`src/application/query_engine.py`, `src/tools/handlers/agent.py`)**
   - Register LOW `compact` tool in `src/tools/handlers/agent.py`.
   - Update `QueryEngine` with pre-complete pipeline (L3 -> L1 -> L2 -> L4 check), transcript snapshotting to `.cda/.transcripts/`, L4 summarization, circuit breaker, and emergency `reactive_compact`.
   - Unit tests in `tests/query_engine_check.py` for auto-compaction, L4 summarizer, session transcript persistence, reactive recovery, circuit breaker, and `compact` tool execution.
   - Covers: `AC-009`, `AC-010`, `AC-012`, `AC-015`, `AC-016`, `AC-017`, `AC-018`, `AC-019`, `AC-020`, `AC-021`, `AC-022`.

3. **M3: CLI Slash Command & Config Cutover (`src/presentation/cli.py`, `tests/cli_check.py`)**
   - Update `src/presentation/cli.py` to use `src/tools/config.py` (cutting over from `.cda/ui-config.json` to `.cda/config.json`).
   - Add `/compact` intercept in REPL loop before skill expansion.
   - Unit tests in `tests/cli_check.py` for `/compact` execution, skill expansion preservation, and config migration.
   - Run full regression suite `python3 -m unittest discover -s tests -p '*_check.py'` and `python3 -m compileall -q src`.
   - Covers: `AC-003`, `AC-013`, `AC-014`, `AC-023`.

Rollback or migration:
- Revert added files (`src/tools/config.py`, `src/tools/compact.py`, `src/prompts/compact.md`) and edits to `cli.py`, `query_engine.py`, `agent.py`, `prompt.py`.
- No database migrations or irreversible storage formats.

Open risks:
- Existing tests referencing `.cda/ui-config.json` in `tests/cli_check.py` and `tests/terminal_ui_check.py` will be updated to `.cda/config.json`.

Next step: execute `/spec-tasks` to build the executable task graph.
