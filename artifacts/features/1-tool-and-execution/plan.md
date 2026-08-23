# Implementation Plan

## Metadata
- Feature/profile: `1-tool-and-execution` / Complex
- Spec approved date: 2026-08-22
- Status: Draft
- Heuristics applied: `LH-001` (machine-verifiable proof commands on every seam), `LH-002` (failing tests before handler/engine behavior changes)

## Lightweight Design

Brownfield change_request. Dispatch registry, JSON events, Ctrl+C save, and extra tools already exist. This plan closes Session 02 gaps in place: path bound, `glob` alias, concurrent batch, multiline prompt, Markdown text, additive events.

- Approach and affected modules: extend `registry` / `invoke`, file+search handlers, `QueryEngine.turn` tool loop, `TerminalUI`. Add one deep helper `src/tools/workspace.py`. Add `tests/tools_check.py`. No new orchestrator type, no new dependency.
- First useful slice and proof: workspace bound + `glob` alias + `tests/tools_check.py` (AC-001–AC-008). Then concurrent batch (AC-009–AC-013). Then terminal (AC-014–AC-023).
- Key constraints or risks: all-tool overlap can race writes/shells (accepted). `bash` stays unjailed. Gates deferred — proof is unittest scripts named in the spec.

## Technical Context

- Language/Version: Python 3.11+ (`StrEnum` already required). Observed 3.13.13.
- Primary Dependencies: stdlib only (`pathlib`, `concurrent.futures`, `unittest`). No new packages. Markdown is a local renderer, not a library (spec + Ponytail).
- Storage/Data: `.sessions/` JSON unchanged. Tool handlers still read/write caller paths after the cwd bound.
- Target Platform: local CLI (`python3 -m src.cli`).
- Performance Goals: one assistant message’s tool list may overlap; next provider `complete` waits for the full batch. No latency SLO.
- Key Constraints: stdlib-first; extra tools stay; MEDIUM/HIGH authorize remains; `max_turns` default 8; missing config exit 2; cancel exit 130.

## Constraints
- Non-goals: Session 03 permission modes, Session 04 hooks, streaming-while-generating tool start, oversized-result persistence, deleting extra tools, jailing `bash`/`powershell`/`repl`, TTY themes, image/PDF `read_file`, pytest.
- Security/trust boundaries: file/search tools must not follow a resolved real path outside process cwd (symlinks included). `bash` can still escape. Authorize stays on stdin, sequential, before overlap. Repo security policy remains `[DEFERRED]`; this bound is still required.
- Preserved behavior: extra tools registered; env/JSON provider config; session redaction of `api_key`/`authorization`; existing JSON types `text`, `tool`, `tool_denied`, `error`; empty first prompt line exits REPL.
- Explicit out of scope: worker-thread UI emission, asyncio rewrite, `ToolBatchExecutor` type, `markdown`/`rich` packages.

## Approach

Stay inside the current layers. Presentation does not import handlers. Handlers do not import QueryEngine. Domain models stay frozen dataclasses.

### Interfaces / data flow

```
TerminalUI.prompt  →  QueryEngine.turn(prompt)
                         → Provider.complete(history, schemas)
                         → text events (Markdown only in TerminalUI human text)
                         → _run_batch(tool_calls)
                              1. sequential authorize for MEDIUM/HIGH
                              2. status event
                              3. tool-start events (main thread)
                              4. concurrent invoke for approved calls
                              5. assemble ToolResult in listed order
                              6. tool_result events (main thread)
                              7. append history + SessionStore.save once per batch
                         → next complete only after step 7
```

`invoke(name, **kwargs)` remains the tool public seam: validate → `check_permission` → handler. Path bound lives **inside file/search handlers** (and therefore inside `invoke`), not in QueryEngine. QueryEngine must not reimplement path checks.

### Public seams (test surface)

| Seam | Observes | ACs |
| --- | --- | --- |
| `src.tools.invoke` / `registry.list_schemas` / `registry.get` | dispatch, glob alias, extra tools, path-bound errors, bash not jailed | AC-001–AC-008 |
| `QueryEngine.turn` | unknown tool, batch order, failure isolation, authorize-then-overlap, next complete waits, `status`/`tool`/`tool_denied`/`tool_result` events | AC-004, AC-009–AC-013, AC-015 |
| `TerminalUI.prompt` / `TerminalUI.event` | period-submit, empty first line, EOF, Markdown text vs plain other types, JSON additive types | AC-014–AC-016, AC-018–AC-023 |
| `src.presentation.cli.run` | KeyboardInterrupt → 130 + session file | AC-017 |

Do not add mock seams. FakeProvider already drives `QueryEngine` (`tests/query_engine_check.py`).

### Key decisions

1. **Workspace bound (chosen: `src/tools/workspace.py` + `Path.resolve`)**  
   Public function: `bound_path(path: str, *, cwd: Path | None = None) -> Path`. Resolves both arguments, follows symlinks, raises `ValueError` if the real path is not inside `cwd` (`Path.is_relative_to`). Handlers call it **before** open/write/walk. `glob_search`/`grep_search` also drop any match whose resolved path is outside cwd. `write_file` must not `makedirs` until bound succeeds.  
   Deletion test: three files (`file_io.py`, `search.py`, tests) share the same symlink-escape logic → keep the helper. Do not fold into `permissions.py` (Session 03 substring deny-list; different change reason).

2. **`glob` alias (chosen: second `registry.register`)**  
   In `search.py`, register `Tool("glob", ...)` with the **same handler, schema, risk, description** as `glob_search`. `list_schemas` then advertises both names. No alias map, no QueryEngine rewrite of names.

3. **Concurrent batch (chosen: `concurrent.futures.ThreadPoolExecutor` inside QueryEngine)**  
   Replace the `for call in tool_calls: _run_call` loop with `_run_batch`:
   - Walk listed calls on the main thread: unknown name / non-dict args → error `ToolResult` immediately; MEDIUM/HIGH → `authorize` sequential; deny → `tool_denied` + error result, do not submit.
   - Emit one `{"type": "status", ...}` then `{"type": "tool", ...}` for each approved call.
   - Submit approved `invoke(...)` to a pool (`max_workers=len(approved)` or 1). `future.result()` exceptions become error `ToolResult` (same as today’s `_run_call` except).
   - After `shutdown(wait=True)`, emit `{"type": "tool_result", "name", "content", "is_error"}` and append `ChatMessage("tool", tool_result=...)` **in listed order**.
   - One `SessionStore.save` after the ordered append (avoid concurrent `_save`).  
   Do not emit events from worker threads (stdout/JSON would race). Overlap is handler execution only.  
   Deletion test: a `ToolBatchExecutor` class would be a shallow pass-through of this algorithm with one caller — collapse it; keep methods on `QueryEngine`.

4. **Multiline prompt (chosen: `TerminalUI.prompt` loop)**  
   Keep using `input_fn`. First returned line `""` → return `""` (REPL exit). Else accumulate until a line that is only `.` (omit that line, join with `\n`) or `EOFError`/`StopIteration` with non-empty accumulation. JSON mode uses the same prompt assembly.

5. **Markdown (chosen: private `_render_markdown` on `TerminalUI`)**  
   Human `text` events only. Minimum observable: ATX headings (`# `) and `**bold**` so AC-021 fails if output is the raw markers alone. Tool/status/error/`tool_result` stay `[{type}] ...` plain lines. JSON path remains `json.dumps(event)` of the original dict.  
   Deletion test: one caller (`event`) → do not add `src/presentation/markdown.py`.

6. **CLI cancel**  
   `run()` already saves and returns 130. Add a unittest; change `cli.py` only if the test proves a gap (e.g. interrupt during multiline `prompt`).

### Module map

| Path | Public seam | Responsibility | Depends on | Split / co-locate |
| --- | --- | --- | --- | --- |
| `src/tools/workspace.py` **new** | `bound_path(path, *, cwd=None) -> Path` | Resolve + cwd membership | `pathlib` only | New: shared by file_io + search; not permissions |
| `src/tools/handlers/file_io.py` | existing handlers | Call `bound_path` on `file_path` before IO | `workspace`, `registry` | Co-locate with write/edit/read |
| `src/tools/handlers/search.py` | `glob_search`, `grep_search`, **`glob` register** | Bound root `path`; filter matches; dual register | `workspace`, `registry` | Alias lives next to `glob_search` |
| `src/tools/registry.py` | `register` / `get` / `list_schemas` | Unchanged contract | none | No alias feature here |
| `src/tools/__init__.py` | `invoke`, `registry` | Unchanged; path errors surface as `{status: error}` | handlers | Do not add batch logic |
| `src/tools/permissions.py` | `check_permission` | Unchanged Session 03 substring checks | types | Do not mix cwd jail |
| `src/application/query_engine.py` | `QueryEngine.turn` | `_run_batch` + ordered results + status/tool_result events | `invoke`, `registry`, stdlib futures | Keep batch here |
| `src/presentation/terminal_ui.py` | `prompt`, `authorize`, `event` | Multiline; Markdown text; print `status`/`tool_result` | stdlib | Keep renderer private |
| `src/presentation/cli.py` | `run` | Preserve 130 path | engine, UI | Touch only if AC-017 fails |
| `tests/tools_check.py` **new** | invokes public tool seam | AC-001–AC-008 | `invoke`, temp cwd | First tool-handler tests |
| `tests/query_engine_check.py` | `QueryEngine.turn` | AC-004, AC-009–AC-013, AC-015 | FakeProvider | Extend; do not rewrite FakeProvider seam |
| `tests/terminal_ui_check.py` | `TerminalUI` | AC-014–AC-016, AC-018–AC-023 | scripted `input_fn` | Extend |
| `tests/cli_check.py` | `run` | AC-017 | mock interrupt | Extend |

Dependency direction (unchanged, inward):

`presentation` → `application` → `tools` / `domain` / `infrastructure`  
`tools.handlers` → `tools.workspace` / `registry`  
`workspace` → stdlib only

### Non-functional considerations

- NFR-001 path bound: `bound_path` + match filter. Proof AC-006/007.
- NFR-002 listed order: assemble after `wait=True`, never by completion order. Proof AC-009. Tests should delay the first handler (or use a lock) so B can finish first.
- NFR-003 cancel: existing `KeyboardInterrupt` handler. Proof AC-017.
- NFR-004/005 Markdown isolation: branch in `TerminalUI.event` before `_write`. Proof AC-016, AC-021–AC-023.

## Alternatives Considered

| Option | Depth / seam / blast radius | Chosen? | Why rejected or kept |
| --- | --- | --- | --- |
| `bound_path` helper module | Deep: symlink/resolve hidden; tests hit one function + `invoke` | Yes | Shared across file_io and search |
| Inline resolve in each handler | Shallow duplication | No | Same bug in 5 call sites |
| Fold jail into `permissions.py` | Mixes Session 02 jail with Session 03 deny-list | No | Different reasons to change; LOW `read_file` skips MEDIUM path substring check today |
| Dual `register("glob")` | Zero new types; schemas list both names | Yes | Matches REQ-002 |
| Alias dict in QueryEngine | Extra name-rewrite seam | No | Deletion test fails (one caller, one alias) |
| `ThreadPoolExecutor` on QueryEngine | Overlap behind existing `turn` | Yes | Stdlib; spec requires overlap; authorize stays on main thread |
| `ToolBatchExecutor` class | Shallow wrapper, one caller | No | Ponytail / deletion test |
| asyncio + to_thread | Second runtime | No | Codebase is sync; bigger blast radius |
| CC partition (`isConcurrencySafe`) | Extra policy seam | No | Adopter set safe-set = all tools |
| `markdown` / `rich` package | Full CommonMark, new dep | No | Spec is stdlib-first; AC-021 is heading/emphasis only |
| Private `_render_markdown` | Tiny, local to UI | Yes | One caller |
| Emit tool events from worker threads | “More live” | No | stdout/JSON races; AC-015 is satisfied by a batch `status` + pre-submit `tool` events |
| ADR for executor vs asyncio | Hard-to-reverse platform choice | No | Both stdlib; spec already locked overlap-on-one-message. Revisit via `/spec-adr` only if we later adopt a second concurrency runtime |

No `/spec-adr` this slice: concurrency policy and path-bound rule are locked in `spec.md`; remaining choices are Ponytail stdlib vs extra types.

## Complexity Tracking

| Violation / Shortcut | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Threads in QueryEngine | REQ-007 overlap | Serial `for` loop fails AC-009 “B may finish first” |
| `workspace.py` extra file | Symlink-aware bound in two handler modules | Inline copies fail DRY-across-package Ponytail row |
| Local Markdown subset instead of a library | AC-021 observable heading/bold | Adding `markdown` violates stdlib-first / no new dep |
| Accepted write/shell races under overlap | Adopter chose all-tool concurrency | Partition-by-risk was offered and rejected |
| `ponytail:` Markdown is ATX + `**` only | AC does not require CommonMark | Full renderer is YAGNI |

Technical risk of overlap+authorize is specified (sequential prompt, then pool), not unverified — no halt to `/spec-research`.

## Delivery

Ordered milestone roadmap (tracer slices; each leaves unittest proof):

1. **P1 tools** — `workspace.py`, bind file_io + search, register `glob`, `tests/tools_check.py`. Covers AC-001–AC-008. Proof: `python3 tests/tools_check.py` and `python3 tests/query_engine_check.py` (existing cases still pass).
2. **P1 batch** — `_run_batch` + `status`/`tool_result` events, delayed-handler order test. Covers AC-004, AC-009–AC-013, AC-015. Proof: `python3 tests/query_engine_check.py`.
3. **P1 UI events + cancel** — `TerminalUI.event` for new types (plain); AC-017 on `run`. Covers AC-014–AC-017. Proof: `python3 tests/terminal_ui_check.py`, `python3 tests/cli_check.py`.
4. **P2 prompt + Markdown** — period-submit / EOF; `_render_markdown` on human text only. Covers AC-018–AC-023. Proof: `python3 tests/terminal_ui_check.py`.
5. **Regression pack** — `python3 -m compileall -q src` and `python3 -m unittest discover -s tests -p '*_check.py'`.

Rollback or migration: revert the listed files; no schema migration. Session JSON gains no new required fields. Provider tool list gains `glob` (additive).

Open risks:

- Overlapping `write_file`/`bash` on the same path is racy by spec.
- `glob.glob` + filter-after-resolve may drop matches; tests must use in-cwd patterns.
- `TOOLS = list(registry.tools.values())` is evaluated at import; registering `glob` in `search.py` at import time is enough if `search` is imported from `src.tools` before `TOOLS` is snapshotted — today `from .handlers import ... search` runs **before** `TOOLS = list(...)`. Keep that import order.
- Verification gates still deferred; these commands are proof, not closeout.

Next step: execute `/spec-tasks` to build the executable task graph.
