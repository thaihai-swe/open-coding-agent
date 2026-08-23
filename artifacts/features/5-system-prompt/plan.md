# Implementation Plan

## Metadata
- Feature/profile: `5-system-prompt` / Complex
- Spec approved date: 2026-08-23
- Status: Draft
- Heuristics applied: `LH-001` (machine-verifiable proof commands on every seam), `LH-002` (test proof before implementation changes)

## Lightweight Design

Brownfield change_request. Replace monolithic/two-part system prompt construction (`Feature 3 planning string + Feature 4 skills catalog`) with modular runtime prompt assembly in `src/tools/prompt.py` (or `src/prompt/assembler.py`). Assembles identity, workspace (process cwd), planning (Feature 3 string verbatim), security policy text, registered tools list, skill catalog (Feature 4 format verbatim), and on-demand instruction files (`AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`) with character caps (4000/12000) and SHA-256 deduplication.

- Approach and affected modules:
  - Add `src/tools/prompt.py`: `discover_instructions`, `format_tools_section`, `format_security_section`, `assemble_system_prompt`.
  - Update `src/tools/skills.py`: deprecate/delegate `build_system_message` to `prompt.assemble_system_prompt`.
  - Update `src/application/query_engine.py`: call `prompt.assemble_system_prompt()` dynamically in `_with_system()`.
  - Update test suites: `tests/tools_check.py`, `tests/query_engine_check.py`.
- First useful slice and proof: pure prompt assembler functions in `src/tools/prompt.py` + tests in `tests/tools_check.py` (`AC-004`–`AC-011`, `AC-016`, `AC-017`). Then QueryEngine integration + tests in `tests/query_engine_check.py` (`AC-001`–`AC-003`, `AC-012`–`AC-015`).
- Key constraints or risks: stdlib Python 3.11+ only. System prompt never persisted into `.cda/.sessions/<id>.json`. Dynamic assembly on every `complete()` ensures mid-session edits to `AGENTS.md` / `SKILL.md` appear immediately on the next turn.

## Technical Context

- Language/Version: Python 3.11+ (`StrEnum`, `pathlib`, `hashlib`, `typing`). Observed 3.13.13.
- Primary Dependencies: Python standard library only (`pathlib`, `hashlib`, `typing`, `unittest`). Zero third-party dependencies in `src/`.
- Storage/Data: Reads instruction files from process cwd only (`AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`). Reads skills from project `.agents/skills/` and `~/.agents/skills/`. Transcripts stay `{"messages": [...]}` under `.cda/.sessions/` without system messages.
- Target Platform: Local CLI (`python3 -m src.cli`).
- Performance Goals: Reading and assembling 3 small instruction files + registered tools + skills takes <3ms per turn; zero perceptible latency.
- Key Constraints: Zero third-party dependencies in `src/`; strict character caps (4000 chars per file, 12000 chars total instruction section); SHA-256 hash deduplication; cwd-only discovery for instruction files (no parent-directory walk-up); Feature 3 planning text and Feature 4 skill catalog format preserved verbatim.

## Constraints
- Non-goals:
  - Session 09 persistent memory (`MEMORY.md` / `.memory/`).
  - Scanning parent directories or user home `~/.` for instruction files.
  - Scanning `.claude/CLAUDE.md` (locked cwd filenames: `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`).
  - Embedding full JSON schemas in the prompt string.
  - Dumping project permission rules from `.cda/.permission_rules/rules.json`.
  - Mode-specific prompts (Simple / Proactive / KAIROS / Coordinator / MCP).
  - API-level prompt caching headers or boundaries (`SYSTEM_PROMPT_DYNAMIC_BOUNDARY`).
- Security/trust boundaries:
  - Instruction file discovery is strictly limited to process cwd: `(Path.cwd() / filename)`.
  - Unreadable or missing files are skipped without raising unhandled exceptions or crashing the CLI.
  - File truncation limits (4000 / 12000 chars) prevent prompt injection/overflow attacks from oversized files.
- Preserved behavior:
  - Feature 1: Workspace bound, concurrent batch tool execution, output rendering.
  - Feature 2: Permission gate, hard deny list, project rules in `.cda/.permission_rules/rules.json`, authorize prompt for MEDIUM/HIGH tools.
  - Feature 3: Task planning tools (`create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`), per-session board, 3-round nag, messages-only session JSON.
  - Feature 4: Two-level skill loading (`load_skill` LOW Agent tool), skill catalog format, REPL slash command routing (`/<skill-name>`).
- Explicit out of scope:
  - Complex template engines (e.g. Jinja2, Mako).
  - Complex prompt caching daemons or persistent state caches.

## Approach

Keep clean boundaries across layers. `src/tools/prompt.py` owns prompt section definitions, instruction file discovery, truncation, deduplication, and string assembly. `QueryEngine` in `src/application/query_engine.py` calls `assemble_system_prompt()` on every `complete()`. `src/tools/skills.py` remains responsible for scanning skills, formatting catalog, and slash commands.

### Interfaces & Data Flow

```
[ QueryEngine._with_system(history) ]
               │
               ▼
   src/tools/prompt.py: assemble_system_prompt()
               │
   ┌───────────┼────────────────────────────────────────┐
   │ 1. Identity ("You are a coding agent...")          │
   │ 2. Workspace ("Working directory: <cwd>")          │
   │ 3. Planning (Feature 3 SYSTEM_MESSAGE verbatim)    │
   │ 4. Security (format_security_section)              │
   │ 5. Tools (format_tools_section from registry)      │
   │ 6. Skills (format_catalog from skills.scan_skills) │
   │ 7. Instructions (discover_instructions, on-demand) │
   └───────────┼────────────────────────────────────────┘
               │
               ▼
   Returns full assembled system string
               │
               ▼
   Prepended as ChatMessage("system", ...) to provider.complete()
   (NOT appended to engine.history, NOT saved in session JSON)
```

### Public Seams (Test Surface)

| Seam | Observes | ACs |
| --- | --- | --- |
| `src/tools/prompt.py` (`discover_instructions`, `format_tools_section`, `format_security_section`, `assemble_system_prompt`) | Instruction file discovery in cwd (`AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`); 4000 char per-file cap; 12000 char total cap; SHA-256 dedup; error tolerance; tools list formatting; security policy formatting; section ordering | AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010, AC-011, AC-016, AC-017 |
| `src/application/query_engine.py` (`_with_system`, `turn`) | Dynamic system message passed to `provider.complete()`; transcript isolation (no system message in `.cda/.sessions/<id>.json`); mid-session freshness of `AGENTS.md` and skills; rules token exclusion | AC-001, AC-002, AC-003, AC-005, AC-012, AC-013, AC-014, AC-015 |
| `src/tools/skills.py` (`build_system_message`) | Backward compatibility wrapper delegating to `prompt.assemble_system_prompt()` | AC-001, AC-015 |

### Key Decisions and Trade-offs

1. **`src/tools/prompt.py` Single Responsibility Module (Chosen)**
   - Module contents:
     - `INSTRUCTION_FILENAMES = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md")`
     - `MAX_FILE_CHARS = 4000`
     - `MAX_TOTAL_INSTRUCTION_CHARS = 12000`
     - `discover_instructions(cwd: Path | None = None) -> list[tuple[str, str]]`: Reads files from cwd, computes SHA-256 hash of decoded text for dedup, applies per-file 4000-char cap and 12000-char overall cap, appends `\n[... TRUNCATED ...]` when truncated. Returns list of `(filename, content)`. Missing or unreadable files skipped.
     - `format_security_section() -> str`:
       ```text
       Security & Permission Policies:
       - File and search tools are restricted to the working directory. Paths outside the workspace are refused.
       - Dangerous shell commands and disk operations matching the deny list are blocked.
       - Operations targeting protected paths and sensitive configuration keys are blocked.
       - High-risk and medium-risk tool operations require explicit user authorization.
       ```
     - `format_tools_section(tools: list[Tool] | None = None) -> str`:
       Lists all registered tools sorted by name: `- <name>: <description>`.
     - `assemble_system_prompt(cwd: Path | None = None, tools: list[Tool] | None = None, skills: dict[str, Any] | None = None) -> str`:
       Assembles sections joined by `\n\n`:
       1. Identity: `You are a coding agent. Act, don't explain.`
       2. Workspace: `Working directory: {cwd.resolve()}`
       3. Planning: `src.tools.task_board.SYSTEM_MESSAGE`
       4. Security: `format_security_section()`
       5. Tools: `format_tools_section(tools)`
       6. Skills: `src.tools.skills.format_catalog(skills)`
       7. Instructions: if `discover_instructions()` returns items, formats `Instructions:\n` followed by each `### {filename}\n{content}`.
   - *Rationale*: Deletion test shows assembling system instructions is a distinct responsibility separate from task board CRUD and skill package parsing.

2. **Fresh Dynamic Assembly on Every Complete (Chosen)**
   - `QueryEngine._with_system()` invokes `assemble_system_prompt()` on every `complete()`.
   - *Rationale*: Instant mid-session responsiveness for newly created or modified `AGENTS.md`, `CLAUDE.md`, or skill packages without needing cache invalidation hooks. Reading 1-3 local files takes under 1ms.

3. **Strict Capping and Dedup Logic (Chosen)**
   - Per-file slice: `content[:4000] + ("\n[... TRUNCATED ...]" if len(content) > 4000 else "")`.
   - Total accumulation tracks character count of file text. If adding the next file exceeds remaining budget, the file is sliced to fit and marked truncated.
   - SHA-256 of raw decoded text tracks seen files so identical files (e.g. `AGENTS.md` and `CLAUDE.md` identical symlinks/copies) are only included once.

4. **Preserving Feature 3 and 4 Contracts (Chosen)**
   - Planning section uses the exact string from `src.tools.task_board.SYSTEM_MESSAGE`.
   - Skills section uses the exact string from `src.tools.skills.format_catalog(skills)`.
   - `src.tools.skills.build_system_message()` is updated to call `assemble_system_prompt()` so existing callers/tests remain functional.

### Module Map

| Path | Public Seam | Responsibility | Depends on | Split / Co-locate |
| --- | --- | --- | --- | --- |
| `src/tools/prompt.py` **new** | `discover_instructions`, `format_tools_section`, `format_security_section`, `assemble_system_prompt` | System prompt section definitions, instruction discovery, truncation, dedup, prompt assembly | `pathlib`, `hashlib`, `src.tools.task_board.SYSTEM_MESSAGE`, `src.tools.skills.format_catalog`, `src.tools.registry` | New single-responsibility domain module |
| `src/tools/skills.py` | `build_system_message` | Retains catalog parsing/formatting; delegates `build_system_message` to `prompt.assemble_system_prompt` | `src.tools.prompt` | Backward compatibility |
| `src/application/query_engine.py` | `QueryEngine._with_system` | Prepends dynamically assembled system prompt to `provider.complete()` | `src.tools.prompt.assemble_system_prompt` | Application turn orchestration |
| `tests/tools_check.py` | Unittest suite | Tests instruction discovery, 4000/12000 capping, hash dedup, error tolerance, tools list formatting, security section formatting, prompt assembly order | `src.tools.prompt`, `src.tools` | Extended |
| `tests/query_engine_check.py` | Unittest suite | Tests dynamic prompt injection into `provider.complete()`, mid-session file updates, transcript isolation, rules exclusion | `src.application.query_engine`, `src.tools.prompt` | Extended |

Dependency direction:
```
application (query_engine.py) ──► tools/prompt.py ──► tools/skills.py
                                          │      ──► tools/task_board.py
                                          │      ──► tools/registry.py
                                          ▼
                                      pathlib / hashlib (stdlib)
```

### Non-Functional Considerations
- `NFR-001` Stdlib-Only: Zero third-party dependencies in `src/` (`AC-015`).
- `NFR-002` Transcript Isolation: Saved session transcripts in `.cda/.sessions/<id>.json` contain only conversation history without system messages (`AC-003`).
- `NFR-003` Instruction Capping: 4000 chars per file and 12000 chars total budget enforced with explicit `TRUNCATED` marker (`AC-008`, `AC-009`).
- `NFR-004` Dynamic Freshness: System message assembled dynamically per `complete()`, capturing real-time filesystem edits (`AC-013`, `AC-014`).
- `NFR-005` Backward Compatibility: Feature 3 planning text and Feature 4 skill catalog format preserved verbatim (`AC-001`, `AC-002`).

## Alternatives Considered

| Option | Depth / seam / blast radius | Chosen? | Why rejected or kept |
| --- | --- | --- | --- |
| `src/tools/prompt.py` dedicated module | High depth; encapsulates discovery, capping, dedup, and formatting behind one clean assembly seam | Yes | Cleanly separates prompt assembly from task board and skill parsing. |
| Inlining prompt assembly into `src/application/query_engine.py` | Low depth, bloats QueryEngine with file reading, hashlib, and string formatting logic | No | Violates Single Responsibility Principle and complicates unit testing of discovery and capping. |
| Walk up parent directories to filesystem root for instruction files | Broad search; risks picking up unwanted parent configuration or dotfiles | No | Strictly rejected to preserve workspace isolation and prevent unintentional context leakage. |
| API-level prompt caching / `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` | Volatile headers/boundaries across provider types | No | Out of scope for OpenAI-compatible completions MVP; simple string assembly takes <3ms. |
| Dump full JSON schemas in the prompt Tools section | Duplicates tool parameter schemas already sent via the `tools` API parameter | No | Doubles token overhead on every turn with zero functional benefit. |

## Complexity Tracking

| Violation / Shortcut | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| New `src/tools/prompt.py` module | Isolates prompt section formatting, instruction discovery, character capping, and hash dedup | Putting logic in `query_engine.py` or `skills.py` violates separation of concerns and creates circular dependencies |
| Pure stdlib string assembly without template engine | Zero third-party dependencies in `src/` | Adding Jinja2 or Mako violates project constraints; `\n\n`.join() with f-strings is robust and fast |
| Linear file scanning per `complete()` without caching | Instant mid-session responsiveness for edited `AGENTS.md` or skills | Process-level caching requires file watcher or mtime comparison logic; scanning 1-3 local files takes <1ms |

## Delivery

Ordered milestone roadmap:

1. **M1: Prompt Assembler & Instruction Discovery (`src/tools/prompt.py`)**
   - Implement `discover_instructions` with 4000/12000 char caps and SHA-256 dedup.
   - Implement `format_security_section`, `format_tools_section`, and `assemble_system_prompt`.
   - Unit tests in `tests/tools_check.py` for cwd resolution, missing files, capping, dedup, unreadable files, tools list, security text, and section order.
   - Covers: `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-016`, `AC-017`.
2. **M2: QueryEngine Integration & Skill Delegation (`src/application/query_engine.py`, `src/tools/skills.py`)**
   - Update `src/tools/skills.py` `build_system_message` to delegate to `assemble_system_prompt`.
   - Update `QueryEngine._with_system` to invoke `assemble_system_prompt()` dynamically.
   - Unit tests in `tests/query_engine_check.py` for dynamic prompt assembly on `complete()`, empty catalog fallback, mid-session freshness, rules token exclusion, and transcript isolation.
   - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-012`, `AC-013`, `AC-014`.
3. **M3: Full Regression & Verification**
   - Update any existing tests in `tests/tools_check.py` and `tests/query_engine_check.py` whose assertions expected the legacy 2-part string.
   - Run `python3 -m unittest discover -s tests -p '*_check.py'` and `python3 -m compileall -q src`.
   - Covers: `AC-015`.

Rollback or migration: Revert `src/tools/prompt.py` and edits to `skills.py`, `query_engine.py`, and test files. No database or disk transcript migrations required.

Open risks:
- Existing tests in `tests/query_engine_check.py` and `tests/tools_check.py` checking `first.content.startswith(SYSTEM_MESSAGE)`: The system message now begins with identity and workspace before planning. Tests will be updated to check that the planning string is present in the assembled system message.

Next step: execute `/spec-tasks` to build the executable task graph.
