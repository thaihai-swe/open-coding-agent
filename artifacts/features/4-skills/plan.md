# Implementation Plan

## Metadata
- Feature/profile: `4-skills` / Complex
- Spec approved date: 2026-08-23
- Status: Draft
- Heuristics applied: `LH-001` (machine-verifiable proof commands on every seam), `LH-002` (test proof before implementation changes)

## Lightweight Design

Brownfield change_request. Replace legacy stub `skill` tool with two-level dynamic skill loading: a dynamic catalog in the system message on every provider `complete()`, a single LOW `load_skill(name: str)` tool that returns full `SKILL.md` content via `tool_result`, and interactive REPL slash command handling (`/<skill-name>`).

- Approach and affected modules:
  - Add `src/tools/skills.py`: pure stdlib frontmatter parser (`parse_frontmatter`), discovery scanner for project `.agents/skills/` and global `~/.agents/skills/` (`scan_skills`), catalog formatter (`format_catalog`), system message builder (`build_system_message`), and REPL slash prompt expander (`expand_slash_prompt`).
  - Rewrite `src/tools/handlers/agent.py`: unregister stub `skill`, register `load_skill(name: str)` (category `Agent`, risk `LOW`).
  - Update `src/application/query_engine.py`: build dynamic system message on every `complete()` combining Feature 3 planning instructions and the skills catalog.
  - Update `src/presentation/cli.py`: intercept `/<skill-name> [args]` in the REPL input loop, expand to `<skill name="...">\n{content}\n</skill>\n{args}`, or report `Unknown skill: /<name>` on unrecognized commands.
  - Test suites: extend `tests/tools_check.py`, `tests/query_engine_check.py`, and `tests/cli_check.py`.
- First useful slice and proof: stdlib frontmatter parser + scanner + `load_skill` tool + stub `skill` removed (`AC-001`–`AC-008`). Then dynamic system message catalog injection + transcript isolation (`AC-009`–`AC-012`, `AC-015`). Then REPL slash command routing (`AC-013`–`AC-014`, `AC-016`–`AC-017`).
- Key constraints or risks: stdlib-only in `src/` (no PyYAML). Project `.agents/skills/` takes precedence over `~/.agents/skills/`. Safe dictionary lookup by name prevents path traversal. System message is never persisted to `.cda/.sessions/<id>.json`.

## Technical Context

- Language/Version: Python 3.11+ (`StrEnum`, `pathlib`, `typing`). Observed 3.13.13.
- Primary Dependencies: Python standard library only (`pathlib`, `re`, `json`, `typing`, `unittest`). Zero third-party dependencies in `src/`.
- Storage/Data: Reads `SKILL.md` from project `.agents/skills/<name>/SKILL.md` and user `~/.agents/skills/<name>/SKILL.md`. Session transcripts stay `{"messages": [...]}` under `.cda/.sessions/`.
- Target Platform: Local CLI (`python3 -m src.cli`).
- Performance Goals: Lightweight directory iteration and stdlib frontmatter parsing on each turn/completion (~1-2ms for dozens of skills); zero perceptible latency.
- Key Constraints: Zero third-party dependencies; pure stdlib frontmatter parser; `load_skill` is LOW risk and skips authorization; project skills override global skills on name collision; dynamic scan ensures fresh skill visibility mid-session.

## Constraints
- Non-goals:
  - Third-party YAML parsing libraries (e.g. PyYAML) in `src/`.
  - Subagent context isolation or forked execution (`context: fork`) from Session 06.
  - Auto-bundling or recursive injection of files in `references/`, `scripts/`, or `assets/` (the model accesses them on demand via `read_file`/`bash`).
  - Allowed-tools filtering or tool restrictions per skill.
  - Modifying permission gate rules or session transcript persistence format.
- Security/trust boundaries:
  - `load_skill` is strictly a name-based dictionary lookup into the scanned registry; file path parameters are forbidden to prevent path traversal.
  - Scans only `.agents/skills/` under process cwd and `Path.home() / ".agents" / "skills"`.
  - Missing or malformed `SKILL.md` files are skipped gracefully without crashing.
- Preserved behavior:
  - Feature 1: Workspace bound, `glob` alias, concurrent batch execution for non-planning tools, human Markdown rendering, JSON event format.
  - Feature 2: Permission gate (hard deny list, project rules in `.cda/.permission_rules/rules.json`, numbered authorize prompts for MEDIUM/HIGH).
  - Feature 3: Planning tools (`create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`), per-session task board at `.cda/.todos/<session_id>.json`, 3-round planning nag, and messages-only session JSON.
- Explicit out of scope:
  - `SkillManager` class hierarchy or complex plugin architectures.
  - In-memory caching that misses filesystem edits.

## Approach

Keep clean boundaries across layers. `src/tools/skills.py` owns discovery, frontmatter parsing, catalog generation, and slash expansion. `src/tools/handlers/agent.py` exposes the thin `load_skill` tool handler. `QueryEngine` dynamically requests the system message string on `complete()`. `src/presentation/cli.py` handles interactive slash command parsing before calling `turn()`.

### Interfaces & Data Flow

```
[ REPL / User Input ]
       │
       ▼
src/presentation/cli.py
  if prompt.startswith("/"):
      expanded, err = skills.expand_slash_prompt(prompt)
      if err:
          ui.event({"type": "error", "message": err})
          continue
      prompt = expanded
  engine.turn(prompt)
       │
       ▼
src/application/query_engine.py
  turn():
      _with_system(history):
          system_text = skills.build_system_message()
          # includes Feature 3 planning prompt + skills.format_catalog()
          return [ChatMessage("system", system_text), *history]
      provider.complete(...)
       │
       ▼ (if model calls load_skill)
src/tools/invoke("load_skill", name="...")
       │
       ▼
src/tools/handlers/agent.py: load_skill(name)
       │
       ▼
src/tools/skills.py: load_skill_content(name)
       │
       ▼
  return SKILL.md text via ToolResult (status="success")
```

### Public Seams (Test Surface)

| Seam | Observes | ACs |
| --- | --- | --- |
| `src/tools/skills.py` (`parse_frontmatter`, `scan_skills`, `format_catalog`, `load_skill_content`, `build_system_message`, `expand_slash_prompt`) | YAML frontmatter parsing with stdlib; project/global discovery; project precedence; fallback name/description; catalog formatting; safe content lookup; slash prompt expansion | AC-001, AC-002, AC-003, AC-005, AC-006, AC-007, AC-009, AC-010, AC-013, AC-014, AC-016, AC-017 |
| `src.tools.invoke` / `registry` | `load_skill` registered as LOW Agent tool; `skill` unregistered; `load_skill` returns file content on success and `Skill not found: <name>` on error; path traversal fails safe | AC-004, AC-005, AC-006, AC-007, AC-008 |
| `QueryEngine.turn` | Dynamic system message prepended to `provider.complete()`; catalog freshness on file changes mid-session; transcript isolation (system message not in `.cda/.sessions/<id>.json`); `load_skill` skips authorization | AC-009, AC-010, AC-011, AC-012, AC-015 |
| `src/presentation/cli.py` (REPL loop) | `/<skill-name> [args]` expands to `<skill name="...">\n{content}\n</skill>\n{args}`; unknown slash prints error without calling `turn()`; normal prompt passthrough | AC-013, AC-014, AC-016, AC-017 |

### Key Decisions and Trade-offs

1. **`src/tools/skills.py` Functional Design (Chosen)**
   - Standalone module with pure functions and explicit defaults.
   - Module functions:
     - `parse_frontmatter(text: str, default_name: str) -> tuple[dict[str, str], str]`: Handles `---` blocks, extracts `name`, `description`, `when_to_use`. Handles inline quotes, comments, multiline text. Fallback `name = default_name`, fallback `description` = first markdown heading `# ...` or first non-empty body line.
     - `scan_skills(project_root: Path | None = None, global_root: Path | None = None) -> dict[str, dict[str, str]]`: Scans global then project paths, yielding a name-indexed dictionary of `{name, description, when_to_use, content, path}`. Project overrides global.
     - `format_catalog(skills: dict[str, dict[str, str]] | None = None) -> str`: Produces `Skills available:\n- **<name>**: <description> (when to use: <when_to_use>)\nUse load_skill to get full details when needed.` or `Skills available:\n(no skills found)`.
     - `load_skill_content(name: str, skills: dict[str, dict[str, str]] | None = None) -> str`: Looks up `name` in scanned skills; raises `ValueError(f"Skill not found: {name}")` if missing.
     - `build_system_message(skills: dict[str, dict[str, str]] | None = None) -> str`: Combines `src.tools.task_board.SYSTEM_MESSAGE` with `format_catalog(skills)`.
     - `expand_slash_prompt(prompt: str, skills: dict[str, dict[str, str]] | None = None) -> tuple[str | None, str | None]`: Checks leading `/`. Extracts command name and trailing arguments. If found in catalog, returns `(expanded_prompt, None)`. If unknown, returns `(None, f"Unknown skill: /{cmd}")`.
   - *Rationale*: Deletion test shows discovery, parsing, cataloging, and slash expansion are shared across tool handlers, query engine, and CLI presentation. Keeping them in a dedicated module prevents duplication and circular imports.

2. **Dynamic Scan on Every Provider Complete (Chosen)**
   - `QueryEngine._with_system()` calls `build_system_message()` dynamically on each provider call.
   - *Rationale*: Instant responsiveness when users add or modify a `SKILL.md` during a session, satisfying `REQ-010` and `AC-015`. Directory traversal over dozens of folders takes under 2ms.

3. **Stdlib-Only YAML Frontmatter Parser (Chosen)**
   - Pure Python string scanning for `---` delimited blocks, line splitting on `:`, stripping quotes and comments.
   - *Rationale*: Respects project constraint of zero third-party dependencies in `src/` while providing complete robustness against malformed YAML.

4. **REPL Slash Command Expansion Contract (Chosen)**
   - When the user types `/<skill-name> [args]`, `src/presentation/cli.py` expands it to:
     ```
     <skill name="<name>">
     {full SKILL.md content}
     </skill>
     {args}
     ```
   - If no args are provided, trailing newline and args are omitted.
   - If `/<name>` is not found in the scanned skills, UI emits error event `Unknown skill: /<name>` and does not execute an engine turn.

### Module Map

| Path | Public Seam | Responsibility | Depends on | Split / Co-locate |
| --- | --- | --- | --- | --- |
| `src/tools/skills.py` **new** | `parse_frontmatter`, `scan_skills`, `format_catalog`, `load_skill_content`, `build_system_message`, `expand_slash_prompt` | Skill package discovery, stdlib frontmatter parsing, catalog generation, system prompt formatting, slash command expansion | `pathlib`, `re`, `src.tools.task_board.SYSTEM_MESSAGE` | New single-responsibility domain module |
| `src/tools/handlers/agent.py` | `load_skill` `Tool` registration | Thin tool handler calling `skills.load_skill_content`; stub `skill` removed | `src.tools.registry`, `src.tools.skills` | Co-located with agent handlers |
| `src/tools/registry.py` | `registry` | Holds active tool definitions | none | Legacy `skill` removed |
| `src/application/query_engine.py` | `QueryEngine._with_system` | Prepends dynamic system message (planning + skill catalog) on `complete()` | `src.tools.skills.build_system_message` | Isolated from disk details |
| `src/presentation/cli.py` | `run` (REPL loop) | Intercepts `/<skill-name>` and expands prompt before calling `engine.turn()` | `src.tools.skills.expand_slash_prompt` | Presentation layer input routing |
| `tests/tools_check.py` | Unittest suite | Tests parsing, discovery, collision precedence, `load_skill` invocation, unknown skill error, path traversal safety, stub `skill` removal | `src.tools.skills`, `src.tools` | Extended |
| `tests/query_engine_check.py` | Unittest suite | Tests dynamic catalog injection, empty catalog fallback, mid-session freshness, transcript isolation, authorization skip | `src.application.query_engine`, `src.tools.skills` | Extended |
| `tests/cli_check.py` | Unittest suite | Tests REPL slash command expansion, unknown slash command error, non-slash passthrough | `src.presentation.cli`, `src.tools.skills` | Extended |

Dependency direction:
```
presentation (cli.py) ────────► application (query_engine.py) ──► tools / domain / infra
      │                                       │
      ▼                                       ▼
tools/skills.py ◄────────────────────── tools/skills.py
      ▲
      │
tools/handlers/agent.py (load_skill handler)
```

### Non-Functional Considerations
- `NFR-001` LOW Risk Authorization: `load_skill` is registered with `Risk.LOW`, skipping interactive authorization prompts (`AC-004`, `AC-012`).
- `NFR-002` Dynamic Freshness: Discovered skills are scanned per `complete()` with no stale cache (`AC-009`, `AC-015`).
- `NFR-003` Transcript Isolation: Saved session transcripts in `.cda/.sessions/<id>.json` contain only conversation history without injected system messages (`AC-011`).
- `NFR-004` Stdlib Robustness: Parser handles comments, quotes, and missing frontmatter safely (`AC-001`, `AC-003`).

## Alternatives Considered

| Option | Depth / seam / blast radius | Chosen? | Why rejected or kept |
| --- | --- | --- | --- |
| `src/tools/skills.py` standalone module | Pure functional module; single place for discovery, parsing, cataloging, and slash expansion | Yes | High depth, low coupling, tested directly at seam. |
| Inline skill scanning directly inside `QueryEngine` | Low depth, duplicates logic in `cli.py` and `agent.py` | No | Violates Single Responsibility and Clean Architecture; presentation and tools would duplicate parsing. |
| External PyYAML parser | Third-party library dependency | No | Violates project constraint of zero third-party dependencies in `src/`. |
| Static scan at process startup only | Misses mid-session added/edited skills | No | Rejected in favor of dynamic per-complete scanning for developer responsiveness. |
| Accept file paths in `load_skill(path=...)` | Exposes path traversal attack surface | No | Rejected for security; dictionary lookup by name is strictly bounded. |
| Multi-class `SkillManager` / `Skill` dataclass hierarchy | High abstraction overhead for simple dict mappings | No | Violates Ponytail simplicity ladder; functions returning typed dicts provide full functionality with fewer lines. |

## Complexity Tracking

| Violation / Shortcut | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| New `src/tools/skills.py` module | Centralizes frontmatter parsing, project/global scanning, catalog formatting, and slash expansion | Inlining into `query_engine.py` would force `cli.py` and `agent.py` to duplicate parsing logic or create circular imports |
| Custom stdlib YAML frontmatter parser | Zero third-party runtime dependencies in `src/` | Adding PyYAML violates project constraint; stdlib `re` and string splitting reliably handles `name`, `description`, `when_to_use` |
| Dynamic scan on every `complete()` | Ensures mid-session `SKILL.md` additions/modifications are immediately visible | Caching requires complex invalidation mechanisms; scanning local directories takes <2ms |
| Slash command expansion in `cli.py` | Enables direct developer invocation `/<skill-name>` | Adding a slash handler inside `QueryEngine` would pollute domain turn loop with REPL presentation syntax |

## Delivery

Ordered milestone roadmap:

1. **M1: Skill Discovery & stdlib Frontmatter Parser (`src/tools/skills.py`)**
   - Implement `parse_frontmatter`, `scan_skills`, `format_catalog`, `load_skill_content`, `build_system_message`, and `expand_slash_prompt`.
   - Unit tests in `tests/tools_check.py` for frontmatter parsing, folder fallbacks, global vs project precedence, and catalog formatting.
   - Covers: `AC-001`, `AC-002`, `AC-003`.
2. **M2: `load_skill` Tool Handler & Legacy Stub Cleanup (`src/tools/handlers/agent.py`)**
   - Unregister old `skill` tool; register `load_skill` (category `Agent`, risk `LOW`, required `name`).
   - Implement `load_skill` handler calling `skills.load_skill_content`.
   - Unit tests in `tests/tools_check.py` for tool schema, valid execution, unknown skill error, path traversal safety, and legacy `skill` rejection.
   - Covers: `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`.
3. **M3: Dynamic System Prompt Catalog Injection (`src/application/query_engine.py`)**
   - Update `QueryEngine._with_system` to invoke `build_system_message()` dynamically.
   - Unit tests in `tests/query_engine_check.py` for planning + catalog formatting, empty catalog fallback, mid-session file updates, authorization skip, and transcript isolation.
   - Covers: `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-015`.
4. **M4: REPL Slash Command Invocation (`src/presentation/cli.py`)**
   - Intercept `/<skill-name> [args]` in REPL loop; expand prompt or emit error event.
   - Unit tests in `tests/cli_check.py` for known slash expansion, unknown slash error handling, and non-slash passthrough.
   - Covers: `AC-013`, `AC-014`, `AC-016`, `AC-017`.
5. **M5: Full Regression & Verification**
   - Run `python3 -m unittest discover -s tests -p '*_check.py'` and `python3 -m compileall -q src`.

Rollback or migration: Revert the modified and created files. No database or disk transcript migrations required.

Open risks:
- Very large `SKILL.md` files: `load_skill` loads full content into conversation history, which naturally consumes context window tokens until compaction (Session 08).
- Malformed YAML frontmatter: Mitigated by safe stdlib parser with fallback heuristics.

Next step: execute `/spec-tasks` to build the executable task graph.
