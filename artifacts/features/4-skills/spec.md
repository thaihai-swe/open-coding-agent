# Feature Specification

## Metadata
- Feature: `4-skills`
- Profile: `Complex`
- Status: `Approved`
- Owner: adopter
- Requested artifact name: `4.skills` (harness slug `4-skills`)
- References (scoped, not global architecture): Session 07 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s07/

## Problem Statement
- Who is affected, what fails, and why now: A coding-agent CLI user needs the agent to follow domain-specific instructions, coding guidelines, and reusable workflows without permanently carrying thousands of tokens in every system prompt. Currently, the repository contains a stub `skill` tool that only responds to `"known"`, while `skills/` or `.agents/skills/` directories are not scanned. The agent cannot discover or load real domain instructions dynamically. Furthermore, the human user cannot invoke a skill directly via a slash command in the REPL. This feature implements two-level on-demand skill loading: a dynamic catalog in the system message on every provider completion, a single LOW `load_skill(name: str)` tool to load full `SKILL.md` content on demand, and interactive REPL slash command support (`/<skill-name>`).

## Outcome
- Observable result:
  1. The agent discovers skills from two directories: project-level `.agents/skills/` (under process cwd) and user-level `~/.agents/skills/` (under `Path.home() / ".agents" / "skills"`). In case of name collision, the project-level skill takes precedence.
  2. Each skill directory containing a `SKILL.md` file is parsed using a pure Python stdlib YAML parser to extract frontmatter fields (`name`, `description`, `when_to_use`). If `name` is omitted, the directory name is used. If `description` is omitted, the first non-empty line or Markdown heading is used.
  3. On every provider `complete()`, the system message dynamically combines the Feature 3 planning instructions with the current skill catalog (`Skills available:\n- **<name>**: <description> (When to use: ...)\nUse load_skill to get full details when needed.`). If no skills exist, `(no skills found)` is displayed. This system message is not saved into session JSON.
  4. The model can call the single LOW tool `load_skill(name="<skill-name>")` to receive the full `SKILL.md` text content in `tool_result`. Looking up an unknown skill name returns a tool error `Skill not found: <name>`.
  5. The old stub `skill` tool is unregistered; no dead or duplicate skill tool remains in `registry`.
  6. In interactive REPL mode, entering `/<skill-name>` (or `/<skill-name> <args...>`) expands that skill into one user turn whose prompt is the full `SKILL.md` wrapped as `<skill name="<name>">\n{content}\n</skill>` plus a trailing newline and the remaining args (or nothing after the wrapper if there are no args). Entering an unknown slash command reports `Unknown skill: /<name>` without crashing or sending a provider turn.
  7. Human and JSON modes preserve all event contracts from Features 1, 2, and 3.

- Minimum useful release: US1–US5 (Skill discovery & stdlib frontmatter parser + `load_skill` tool + Dynamic system prompt catalog + REPL slash command invocation + Old stub cleanup & test proof).

## Scope
- In scope:
  - Skill discovery from project `.agents/skills/` (process cwd) and global `~/.agents/skills/` (`Path.home() / ".agents" / "skills"`).
  - Precedence rule: project-level skill overrides global skill with the same name.
  - Frontmatter parser in stdlib Python extracting `name`, `description`, `when_to_use` from `SKILL.md` (tolerant of missing frontmatter or missing fields).
  - Single registered tool `load_skill(name: str)` with category `Agent` and risk `LOW`.
  - Unregistering the old `skill` tool.
  - Dynamic skill catalog generation on every provider `complete()`, appended to the Feature 3 planning instructions in the system message.
  - Safe registry lookup for `load_skill` preventing path traversal.
  - REPL slash command handling: `/<skill-name>` expands skill instructions and invokes `engine.turn()`. Unknown `/<cmd>` outputs an error message.
  - Unit tests covering discovery, precedence, frontmatter parsing, `load_skill` execution, dynamic system prompt catalog injection, slash command dispatch, unknown skill handling, and session transcript isolation.
- Out of scope / non-goals:
  - Third-party YAML libraries (e.g. PyYAML) in `src/` (must be 100% Python stdlib).
  - Subagent context isolation or forked execution (`context: fork`) from Session 06.
  - Automatic recursive inclusion of referenced files in `references/`, `scripts/`, or `assets/` (the model accesses them on demand using `read_file` or `bash`).
  - Allowed-tools filtering or automated tool restrictions per skill.
  - Modifying permission gate rules or session JSON structure.
- Preserved behavior:
  - Feature 1: Workspace bound, `glob` alias, concurrent batch execution, human Markdown rendering, JSON event format.
  - Feature 2: Permission gate (hard deny list, project rules in `.cda/.permission_rules/rules.json`, numbered authorize prompts for MEDIUM/HIGH). `load_skill` is LOW and skips authorize.
  - Feature 3: Task planning tools (`create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`), per-session task board under `.cda/.todos/`, 3-round planning nag, and messages-only session JSON.

## User Stories & Journeys (Moderate/Complex)

### User Story 1 - Skill Discovery and stdlib Frontmatter Parsing (Priority: P1) 🎯 MVP
- Description: The agent scans `.agents/skills/` in the working directory and `~/.agents/skills/` in the user's home directory. For every subdirectory with a `SKILL.md`, it parses YAML frontmatter using standard library Python to extract `name`, `description`, and `when_to_use`. If the same skill name exists in both directories, the project skill overrides the global one.
- Why this priority: Core discovery engine required for all downstream skill features.
- Independent Test: Create temp project and global `.agents/skills/` folders with valid, minimal, and conflicting `SKILL.md` files; verify parsed registry entries.
- Acceptance Scenarios:
  1. Given a directory `.agents/skills/code-review/SKILL.md` with frontmatter `name: code-review` and `description: Review pull requests`, When skills are scanned, Then `code-review` is indexed with that name, description, and full content.
  2. Given a global skill `~/.agents/skills/code-review/SKILL.md` and a project skill `.agents/skills/code-review/SKILL.md`, When skills are scanned, Then the project skill's content and metadata win.
  3. Given a `SKILL.md` without frontmatter or with missing `name`/`description`, When scanned, Then `name` defaults to the directory name and `description` defaults to the first non-empty line or markdown heading.
  4. Given a directory without `SKILL.md` or an unreadable file, When scanned, Then it is safely ignored without crashing the agent.

### User Story 2 - `load_skill` Tool Execution (Priority: P1) 🎯 MVP
- Description: The agent exposes `load_skill(name: str)` as a LOW-risk Agent tool. When called by the model, it returns the full text of `SKILL.md` in `tool_result`. Calling an unknown skill name returns a tool error `Skill not found: <name>`.
- Why this priority: Primary runtime mechanism for on-demand knowledge injection into model context.
- Independent Test: `invoke("load_skill", name="...")` with known and unknown skill names in a temp environment.
- Acceptance Scenarios:
  1. Given a scanned skill `code-review`, When `load_skill(name="code-review")` is called, Then the tool result contains the exact text of `SKILL.md` and authorize is not triggered.
  2. Given no skill named `unknown-skill`, When `load_skill(name="unknown-skill")` is called, Then the tool returns an error result containing `Skill not found: unknown-skill`.
  3. Given an input attempting path traversal (e.g. `../../etc/passwd`), When `load_skill` is called, Then it performs a dictionary lookup by name and returns `Skill not found: ../../etc/passwd` without accessing arbitrary files.

### User Story 3 - Dynamic System Prompt Catalog (Priority: P1) 🎯 MVP
- Description: On every provider `complete()`, the system message dynamically includes a catalog of all currently discovered skills (`Skills available:\n- **<name>**: <description>...`) along with the Feature 3 planning instructions. If no skills exist, `(no skills found)` is displayed. This system message is never persisted to session JSON.
- Why this priority: Allows the model to be aware of available domain skills without token bloat, enabling it to call `load_skill` when relevant.
- Independent Test: Inspect the system message passed to `provider.complete()` when skills exist vs when no skills exist; inspect saved session file on disk.
- Acceptance Scenarios:
  1. Given two scanned skills `pdf` and `sql-style`, When `complete()` is called, Then the system message begins with the Feature 3 planning instructions, contains `Skills available:`, and lists `- **pdf**: ...` and `- **sql-style**: ...`.
  2. Given zero skills in project or global directories, When `complete()` is called, Then the system message contains `Skills available:\n(no skills found)`.
  3. Given a skill is added to `.agents/skills/` mid-session, When the next `complete()` runs, Then the new skill appears in the catalog without restarting the CLI.
  4. Given any turn execution, When `.cda/.sessions/<id>.json` is inspected, Then no system message is written to disk.

### User Story 4 - Interactive REPL Slash Command Invocation (Priority: P1) 🎯 MVP
- Description: In the interactive CLI, a user can enter `/<skill-name>` (e.g. `/code-review` or `/code-review check this file`). The CLI recognizes the slash command, loads the skill's `SKILL.md` instructions, and initiates a turn with that skill context. Entering an unknown slash command prints an error message without crashing.
- Why this priority: Standard developer experience matching Claude Code / Codex agent CLI interfaces.
- Independent Test: Feed `/<skill-name>` and `/unknown-skill` to the REPL input loop with a mocked/fake engine and UI.
- Acceptance Scenarios:
  1. Given a known skill `code-review` whose `SKILL.md` text is `BODY`, When the user types `/code-review please check line 10` in the REPL, Then `QueryEngine.turn` is called once with prompt exactly `<skill name="code-review">\nBODY\n</skill>\nplease check line 10`.
  2. Given that same skill, When the user types `/code-review` with no args, Then `QueryEngine.turn` is called once with prompt exactly `<skill name="code-review">\nBODY\n</skill>`.
  3. Given no skill named `foo`, When the user types `/foo` in the REPL, Then output includes `Unknown skill: /foo` and `QueryEngine.turn` is not called.
  4. Given a regular prompt without a leading `/`, When entered, Then that exact string is passed to `QueryEngine.turn`.

### User Story 5 - Tool Stub Removal and Regression Safety (Priority: P1) 🎯 MVP
- Description: The old stub tool `skill` is removed from `src/tools/registry.py` and `src/tools/handlers/agent.py`. Calling `skill` returns an unknown tool error. All existing test suites pass.
- Why this priority: Prevents dead code, schema collisions, and confusion between the legacy stub and `load_skill`.
- Independent Test: Query `registry.get("skill")`, run `tools_check.py`, `query_engine_check.py`, and `cli_check.py`.
- Acceptance Scenarios:
  1. Given the tool registry, When inspected, Then `registry.get("load_skill")` is present and `registry.get("skill")` is `None`.
  2. Given `invoke("skill", skill="known")`, When executed, Then it returns an unknown tool error.
  3. Given existing test suites in `tests/`, When run, Then all tests continue to pass.

## Requirements (Moderate/Complex)
- `REQ-001`: The system must scan project `.agents/skills/` (relative to process cwd) and global `~/.agents/skills/` (`Path.home() / ".agents" / "skills"`) for skill packages. Priority: Must. Validation: `tools_check.py`. Linked story: US1.
- `REQ-002`: A skill package is defined as any directory containing a `SKILL.md` file. Priority: Must. Validation: `tools_check.py`. Linked story: US1.
- `REQ-003`: The system must parse `SKILL.md` YAML frontmatter using standard library Python only (no PyYAML). It must extract `name` (string), `description` (string), and `when_to_use` (string or None). Priority: Must. Validation: `tools_check.py`. Linked story: US1.
- `REQ-004`: If frontmatter is missing or lacks `name`, `name` defaults to the folder name. If `description` is missing, `description` defaults to the first non-empty line or Markdown heading. Priority: Must. Validation: `tools_check.py`. Linked story: US1.
- `REQ-005`: If a skill name exists in both project and global directories, the project-level skill must take precedence and override the global skill. Priority: Must. Validation: `tools_check.py`. Linked story: US1.
- `REQ-006`: The system must register a single tool named `load_skill` with category `Agent` and risk `LOW`. Required parameter: `name` (string). Priority: Must. Validation: `tools_check.py`. Linked story: US2.
- `REQ-007`: `load_skill` must look up the skill by name in the parsed registry and return the full content of `SKILL.md`. It must not accept file paths and must be immune to path traversal. Priority: Must. Validation: `tools_check.py`. Linked story: US2.
- `REQ-008`: If `load_skill` is called with an unknown skill name, it must return a tool error string containing `Skill not found: <name>`. Priority: Must. Validation: `tools_check.py`. Linked story: US2.
- `REQ-009`: The old `skill` tool must be unregistered and removed from tool schemas. Priority: Must. Validation: `tools_check.py`. Linked story: US5.
- `REQ-010`: On every provider `complete()`, the QueryEngine must dynamically scan and construct the system message combining the Feature 3 planning instructions and the current skill catalog. Priority: Must. Validation: `query_engine_check.py`. Linked story: US3.
- `REQ-011`: The skill catalog in the system message must format each skill as `- **<name>**: <description>` (and include `(when to use: <when_to_use>)` if present). If no skills are discovered, it must format the catalog as `(no skills found)`. Priority: Must. Validation: `query_engine_check.py`. Linked story: US3.
- `REQ-012`: The system message must never be stored in session JSON transcripts (`.cda/.sessions/<id>.json`). Priority: Must. Validation: `session_check.py`, `query_engine_check.py`. Linked story: US3.
- `REQ-013`: In the interactive REPL, a first-line input that starts with `/` is a slash. The token after `/` up to the first whitespace is the skill name. If that name is in the current catalog, the CLI must call `QueryEngine.turn` once with prompt `<skill name="{name}">\n{SKILL.md}\n</skill>` and, if any remaining text exists after the first whitespace, a trailing `\n` plus that remaining text (unstripped except the single separating whitespace after the name). If the name is not in the catalog, the CLI must write `Unknown skill: /{name}` and must not call `QueryEngine.turn`. A prompt that does not start with `/` is passed through unchanged. Priority: Must. Validation: `cli_check.py`. Linked story: US4.
- `REQ-014`: `load_skill` must be categorized as `LOW` risk and must skip interactive authorization prompts in `QueryEngine` and `TerminalUI`. Priority: Must. Validation: `query_engine_check.py`. Linked story: US2.
- `REQ-015`: All implementation in `src/` must remain compatible with Python 3.11+ standard library without adding third-party dependencies. Priority: Must. Validation: `tools_check.py`. Linked story: US1–US5.

## Acceptance Criteria
- `AC-001`: Given a directory `.agents/skills/my-skill/SKILL.md` with valid YAML frontmatter `name: my-skill` and `description: A custom skill`, When scanned, Then the registry contains `my-skill` with description `A custom skill` and the file's full content. Covers REQ-001, REQ-002, REQ-003. Proof: `python3 tests/tools_check.py`.
- `AC-002`: Given `~/.agents/skills/shared/SKILL.md` and `.agents/skills/shared/SKILL.md` with different descriptions, When scanned, Then the project skill's metadata and content are returned. Covers REQ-005. Proof: `python3 tests/tools_check.py`.
- `AC-003`: Given a `SKILL.md` file without `---` frontmatter whose first line is `# Document Helper`, When scanned, Then `name` is the folder name and `description` is `Document Helper`. Covers REQ-004. Proof: `python3 tests/tools_check.py`.
- `AC-004`: Given `registry.get("load_skill")`, When inspected, Then it has category `Agent`, risk `LOW`, schema requiring `name` (string), and `registry.get("skill")` is `None`. Covers REQ-006, REQ-009, REQ-014. Proof: `python3 tests/tools_check.py`.
- `AC-005`: Given a scanned skill `tester`, When `invoke("load_skill", name="tester")` is called, Then `status` is `success` and `result` equals the complete content of `SKILL.md`. Covers REQ-007. Proof: `python3 tests/tools_check.py`.
- `AC-006`: Given no skill named `missing-skill`, When `invoke("load_skill", name="missing-skill")` is called, Then `status` is `error` and `error` contains `Skill not found: missing-skill`. Covers REQ-008. Proof: `python3 tests/tools_check.py`.
- `AC-007`: Given `invoke("load_skill", name="../../etc/passwd")`, When called, Then it returns an error containing `Skill not found: ../../etc/passwd` without raising an unhandled filesystem exception or reading outside `.agents/skills/`. Covers REQ-007, REQ-008. Proof: `python3 tests/tools_check.py`.
- `AC-008`: Given `invoke("skill", skill="known")`, When called, Then it returns an unknown tool error. Covers REQ-009. Proof: `python3 tests/tools_check.py`.
- `AC-009`: Given a FakeProvider recording calls, When `QueryEngine.turn()` runs with available skills `s1` and `s2`, Then the first message passed to `provider.complete()` is a `role="system"` message containing `You should plan before executing.`, `create_task`, `Skills available:`, `- **s1**:`, and `- **s2**:`. Covers REQ-010, REQ-011. Proof: `python3 tests/query_engine_check.py`.
- `AC-010`: Given zero skills in `.agents/skills/` and `~/.agents/skills/`, When `QueryEngine.turn()` runs, Then the system message contains `Skills available:\n(no skills found)`. Covers REQ-011. Proof: `python3 tests/query_engine_check.py`.
- `AC-011`: Given a turn execution that successfully calls `load_skill`, When the session transcript `.cda/.sessions/<id>.json` is loaded from disk, Then it contains the user message, assistant message, and tool result message, but contains no `role="system"` message. Covers REQ-012. Proof: `python3 tests/query_engine_check.py`, `python3 tests/session_check.py`.
- `AC-012`: Given a `QueryEngine` with an authorize callback, When the model calls `load_skill`, Then authorize is not called and execution succeeds. Covers REQ-014. Proof: `python3 tests/query_engine_check.py`.
- `AC-013`: Given interactive CLI mode and a cataloged skill `code-review` whose `SKILL.md` is `BODY`, When the user inputs `/code-review please check line 10`, Then `QueryEngine.turn` is called once with prompt `<skill name="code-review">\nBODY\n</skill>\nplease check line 10`. Covers REQ-013. Proof: `python3 tests/cli_check.py`.
- `AC-014`: Given interactive CLI mode, When the user inputs `/nonexistent-skill`, Then output includes `Unknown skill: /nonexistent-skill` and `QueryEngine.turn` is not called. Covers REQ-013. Proof: `python3 tests/cli_check.py`.
- `AC-016`: Given interactive CLI mode and cataloged skill `code-review` with body `BODY`, When the user inputs `/code-review` with no args, Then `QueryEngine.turn` is called once with prompt `<skill name="code-review">\nBODY\n</skill>`. Covers REQ-013. Proof: `python3 tests/cli_check.py`.
- `AC-017`: Given interactive CLI mode, When the user inputs a prompt that does not start with `/`, Then `QueryEngine.turn` receives that exact prompt. Covers REQ-013. Proof: `python3 tests/cli_check.py`.
- `AC-015`: Given a new skill file created in `.agents/skills/new-skill/SKILL.md` while a session is running, When the next prompt is sent, Then the system message passed to the provider includes `new-skill` without restarting the process. Covers REQ-010. Proof: `python3 tests/query_engine_check.py`.

## Success Criteria (Measurable Outcomes)
- `SC-001`: In one REPL session, an agent can dynamically discover project and global skills, list them in the system catalog, and load full instructions via `load_skill` without ever polluting the saved transcript with system messages.
- `SC-002`: Users can trigger skills via `/<skill-name>` directly in the terminal interface.
- `SC-003`: Legacy stub `skill` is removed with 100% test coverage across discovery, parsing, tool invocation, system prompt construction, and REPL slash command routing.
- `SC-004`: Zero third-party dependencies added to `src/`.

## Constraints and Risk
- Constraints:
  - Python 3.11+ stdlib only; zero third-party dependencies in `src/`. Linked ACs: AC-001–AC-015.
  - NFR-001 `load_skill` is LOW risk and skips authorization. Linked ACs: AC-004, AC-012.
  - NFR-002 Dynamic scanning on every `complete()` ensures instant freshness for newly created skills. Linked ACs: AC-009, AC-010, AC-015.
  - NFR-003 Session JSON persistence is strictly transcripts only (`{"messages": [...]}`). Linked ACs: AC-011.
  - NFR-004 Pure stdlib frontmatter parser must handle comments, quotes, and multiline descriptions gracefully without crashing on malformed YAML. Linked ACs: AC-001, AC-003.
- Dependencies/touchpoints: `src/tools/skills.py` (new), `src/tools/handlers/agent.py`, `src/tools/registry.py`, `src/application/query_engine.py`, `src/presentation/cli.py`, `tests/tools_check.py`, `tests/query_engine_check.py`, `tests/cli_check.py`.
- Risks and mitigations:
  - Risk: Malformed YAML frontmatter crashes the scan.
    - Mitigation: stdlib frontmatter parser wraps field extraction in try/except and falls back to directory name / heading heuristics.
  - Risk: Project and global skill name collisions cause non-deterministic behavior.
    - Mitigation: Project directory `.agents/skills/` strictly takes precedence over `~/.agents/skills/`.
  - Risk: Model attempts path traversal via `load_skill`.
    - Mitigation: Registry dictionary lookup by name string only; never accepts or resolves file paths directly from arguments.
- Open questions (blocking only): None.

## Decisions
- Locked decisions:
  - Single tool `load_skill(name: str)` with category `Agent` and risk `LOW`. Stub `skill` is unregistered.
  - Project `.agents/skills/` (cwd) and global `~/.agents/skills/` (`Path.home() / ".agents" / "skills"`). Project wins on collision.
  - Dynamic scan on every provider `complete()`.
  - System prompt dynamically combines Feature 3 planning instructions with the skills catalog:
    `You should plan before executing. Tools: ...\n\nSkills available:\n- **<name>**: <description> (When to use: <when_to_use>)\nUse load_skill to get full details when needed.` (or `(no skills found)`).
  - Stdlib-only frontmatter parsing for `name`, `description`, `when_to_use`.
  - REPL supports direct slash invocation: `/<skill-name> [args]`. Unknown slash command outputs error without running engine turn.
- Related `ADR-*`: None.
