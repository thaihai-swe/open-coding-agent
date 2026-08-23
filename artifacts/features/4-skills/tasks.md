# Tasks

## Metadata

- Feature/profile: `4-skills` / Complex
- Plan approved date: 2026-08-23

## Implementation Strategy

- Strategy: Incremental
- Reason: The implementation follows 4 tracer slices across shared files (`src/tools/skills.py`, `src/tools/handlers/agent.py`, `src/application/query_engine.py`, `src/presentation/cli.py`). Modules build cleanly in sequence: discovery & frontmatter parser -> tool handler -> dynamic system prompt catalog -> REPL slash command routing -> regression pack. No `[P]` markers.

## Task Contract

Each task includes ID, target paths from the plan module map, `Covers: AC-*`, `Depends on: T-NNN`, entry proof (failing test), and exit proof. Status is `Not Started` until `/spec-implement` runs `task-start`. No `[P]` markers.

## Tasks

### Phase 1: Setup / Foundational — Skill Discovery & stdlib Frontmatter Parser (US1)

- Goal: Implement `src/tools/skills.py` with pure stdlib frontmatter parser (`parse_frontmatter`), directory scanner (`scan_skills`) supporting project `.agents/skills/` and global `~/.agents/skills/` (project precedence), catalog formatter (`format_catalog`), content loader (`load_skill_content`), system message builder (`build_system_message`), and slash expander (`expand_slash_prompt`).
- Entry proof: `python3 -c "import src.tools.skills"` fails (module not found).
- Exit proof: `python3 tests/tools_check.py` exit 0 with frontmatter, discovery, precedence, and fallback test cases passing.

- [x] T-001 [US1] `src/tools/skills.py`, `tests/tools_check.py` — add `src/tools/skills.py` with pure stdlib `parse_frontmatter` (handles `---` blocks, extracts `name`, `description`, `when_to_use`, strips quotes/comments, fallback `name` to dir name, fallback `description` to first Markdown heading or non-empty line), `scan_skills` (scans global `~/.agents/skills/` then project `.agents/skills/`, project wins on collision, skips dirs without `SKILL.md`), `format_catalog` (`Skills available:\n- **<name>**: <description>...` or `(no skills found)`), `load_skill_content`, `build_system_message` (combines planning `SYSTEM_MESSAGE` with `format_catalog`), and `expand_slash_prompt`; add unit tests in `tests/tools_check.py`.
  - Covers: `AC-001`, `AC-002`, `AC-003`
  - Depends on:
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:

### Phase 2: User Story 2 & 5 — `load_skill` Tool Handler & Legacy `skill` Stub Removal (US2, US5)

- Goal: Expose `load_skill(name: str)` as a LOW-risk Agent tool in `src/tools/handlers/agent.py` and unregister the legacy `skill` tool. `load_skill` returns full `SKILL.md` content or `Skill not found: <name>`.
- Entry proof: `registry.get("load_skill")` is None or `registry.get("skill")` is not None.
- Exit proof: `python3 tests/tools_check.py` exit 0 with `load_skill` schema, invocation, error handling, path traversal safety, and legacy `skill` rejection tests passing.
  Validation evidence: python3 tests/tools_check.py passed 43 tests (AC-001, AC-002, AC-003, REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-007, REQ-010, REQ-011, REQ-013).


- [x] T-002 [US2] `src/tools/handlers/agent.py`, `src/tools/registry.py`, `tests/tools_check.py` — rewrite `src/tools/handlers/agent.py` to register `load_skill` (category `Agent`, risk `LOW`, required `name`) and unregister old `skill` stub; handler invokes `skills.load_skill_content(name)`; test `registry.get("load_skill")` is LOW Agent, `registry.get("skill")` is `None`; test `invoke("load_skill", name="...")` returns full content for known skill; test unknown skill returns error containing `Skill not found: <name>`; test path traversal strings (e.g. `../../etc/passwd`) return `Skill not found: ../../etc/passwd` without raising or reading outside; test `invoke("skill", ...)` returns unknown tool error.
  - Covers: `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`
  - Depends on: `T-001`
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:

### Phase 3: User Story 3 — Dynamic System Prompt Catalog Injection (US3)

- Goal: On every provider `complete()`, `QueryEngine` dynamically builds the system message combining Feature 3 planning instructions and the skills catalog. System message is not stored in session JSON. `load_skill` skips authorization prompts.
- Entry proof: `QueryEngine._with_system` passes static `SYSTEM_MESSAGE` without skills catalog.
- Exit proof: `python3 tests/query_engine_check.py` exit 0 with dynamic catalog, empty catalog, mid-session skill update, authorization skip, and transcript isolation tests passing.
  Validation evidence: python3 tests/tools_check.py passed 48 tests. AC-004 load_skill LOW Agent required name, skill unregistered; AC-005 invoke load_skill returns SKILL.md; AC-006 Skill not found: missing-skill; AC-007 path traversal Skill not found: ../../etc/passwd; AC-008 invoke skill is unknown tool. invoke() made positional-only so name= can be a tool argument.


- [x] T-003 [US3] `src/application/query_engine.py`, `tests/query_engine_check.py` — update `QueryEngine._with_system` to invoke `skills.build_system_message()` on each `complete()`; test FakeProvider sees system message with `You should plan before executing.`, `create_task`, `Skills available:`, `- **<name>**:`; test empty catalog produces `(no skills found)`; test adding a skill mid-session updates the catalog on next prompt without restart; test `load_skill` skips `authorize`; test saved transcript in `.cda/.sessions/<id>.json` has no `role=system` messages.
  - Covers: `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-015`
  - Depends on: `T-002`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:

### Phase 4: User Story 4 — Interactive REPL Slash Command Invocation (US4)

- Goal: Intercept `/<skill-name> [args]` in the interactive REPL loop (`src/presentation/cli.py`), expand prompt to `<skill name="<name>">\n{content}\n</skill>\n{args}`, and call `engine.turn()`. Output `Unknown skill: /<name>` on unknown slash command without running a turn.
- Entry proof: REPL passes `/<skill-name>` directly to `engine.turn()` without expansion.
- Exit proof: `python3 tests/cli_check.py` exit 0 with known slash expansion, unknown slash error, and non-slash passthrough tests passing.
  Validation evidence: python3 tests/query_engine_check.py passed 44 tests. AC-009 catalog lists s1/s2 plus planning tools; AC-010 empty catalog is (no skills found); AC-011 session JSON has no system role; AC-012 load_skill skips authorize; AC-015 new SKILL.md appears on next complete().


- [x] T-004 [US4] `src/presentation/cli.py`, `tests/cli_check.py` — update `run` in `src/presentation/cli.py` to check `prompt.startswith("/")`; use `skills.expand_slash_prompt(prompt)` to resolve skill; if known, set prompt to `<skill name="<name>">\n{content}\n</skill>` (plus `\n{args}` if trailing args present) and run `engine.turn()`; if unknown, emit error event `Unknown skill: /<name>` and continue loop without calling `turn()`; non-slash prompts pass through unchanged; add unit tests in `tests/cli_check.py`.
  - Covers: `AC-013`, `AC-014`, `AC-016`, `AC-017`
  - Depends on: `T-003`
  - Status: Done
  - Proof: `python3 tests/cli_check.py`
  - Evidence:

### Phase 5: Polish — Regression Pack

- Goal: Full test suite passes and Python compilation succeeds with zero errors or regressions.
- Entry proof: prior tasks Done.
- Exit proof: compile + discover exit 0.
  Validation evidence: python3 tests/cli_check.py passed 6 tests. AC-013 /code-review with args expanded; AC-016 /code-review without args expanded; AC-014 /nonexistent-skill emitted Unknown skill error without running turn; AC-017 normal prompt passthrough.


- [x] T-005 `src/`, `tests/` — run the full app test pack; verify no regressions in tools, permissions, session transcripts, query engine, or CLI.
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-013`, `AC-014`, `AC-015`, `AC-016`, `AC-017`
  - Depends on: `T-004`
  - Status: Done
  - Proof: `python3 -m compileall -q src` && `python3 -m unittest discover -s tests -p '*_check.py'`
  - Evidence:

## Traceability

| ID | Tasks |
| --- | --- |
| REQ-001 | T-001 |
| REQ-002 | T-001 |
| REQ-003 | T-001 |
| REQ-004 | T-001 |
| REQ-005 | T-001 |
| REQ-006 | T-002 |
| REQ-007 | T-002 |
| REQ-008 | T-002 |
| REQ-009 | T-002 |
| REQ-010 | T-003 |
| REQ-011 | T-003 |
| REQ-012 | T-003 |
| REQ-013 | T-004 |
| REQ-014 | T-002, T-003 |
| REQ-015 | T-001, T-002, T-003, T-004, T-005 |
| AC-001 | T-001, T-005 |
| AC-002 | T-001, T-005 |
| AC-003 | T-001, T-005 |
| AC-004 | T-002, T-005 |
| AC-005 | T-002, T-005 |
| AC-006 | T-002, T-005 |
| AC-007 | T-002, T-005 |
| AC-008 | T-002, T-005 |
| AC-009 | T-003, T-005 |
| AC-010 | T-003, T-005 |
| AC-011 | T-003, T-005 |
| AC-012 | T-003, T-005 |
| AC-013 | T-004, T-005 |
| AC-014 | T-004, T-005 |
| AC-015 | T-003, T-005 |
| AC-016 | T-004, T-005 |
| AC-017 | T-004, T-005 |

## Resume Notes

- Next recommended task: `T-001`
- First ready (no unfinished deps): `T-001`
- Implement with `/spec-implement`; `task-start --task T-001` before coding.
- Gates remain deferred; task Proof commands are not closeout.
  Validation evidence: python3 -m compileall -q src exit 0; python3 -m unittest discover -s tests -p '*_check.py' exit 0; 145 tests OK. AC-001 through AC-017 covered.

