# Feature Specification

## Metadata
- Feature: `5-system-prompt`
- Profile: `Complex`
- Status: `Approved`
- Owner: adopter
- Requested artifact name: `5.system-prompt` (harness slug `5-system-prompt`)
- References (scoped, not global architecture): Session 10 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s10/

## Problem Statement
- Who is affected, what fails, and why now: A coding-agent CLI user needs the model to operate with a complete, up-to-date view of its identity, workspace, security policies, registered tools, available skills, and project instruction files (`AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`). Today the system message is only Feature 3 planning text plus the Feature 4 skill catalog. The model has no named identity, no cwd, no security policy text, no tool-name list in the prompt, and no injection of local instruction files. Adding those as more hardcoded lines would make the prompt unmaintainable and would still miss mid-session file changes. This feature replaces the two-part string with named runtime sections assembled on every `complete()`.

## Outcome
- Observable result:
  1. On every provider `complete()`, the first message is `role=system` and its content is the assembled prompt: identity, workspace (process cwd), Feature 3 planning string (verbatim), security policy, registered-tool list, Feature 4 skill catalog (verbatim format), and — only when at least one instruction file exists — an instruction section.
  2. Instruction files are read from process cwd only, in this order: `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`. Missing files are skipped. Identical content (SHA-256 of the raw file bytes after UTF-8 decode) is injected once. Each file is capped at 4000 characters; the instruction section as a whole is capped at 12000 characters. Truncation is marked. Unreadable files are skipped without crashing.
  3. The tools section lists every currently registered tool as `- <name>: <description>`. Full JSON schemas are not copied into the system message (they remain on the API `tools` argument).
  4. The security section states workspace bound, hard-deny / deny-list, protected paths/keys, and that MEDIUM/HIGH tools require approval. It does not dump `.cda/.permission_rules/rules.json`.
  5. Mid-session edits to instruction files, the skill tree, or the tool registry appear on the next `complete()` without restarting the process.
  6. The assembled system message is never written to `.cda/.sessions/<id>.json`. Feature 1–4 event contracts, tools, slash commands, nag, and session JSON shape are unchanged.
- Minimum useful release: US1–US6 (assembler + always-on sections + instruction files + tools list + security text + transcript isolation / freshness).

## Scope
- In scope:
  - Named prompt sections assembled on every `complete()`.
  - Always-on sections: identity, workspace, planning (Feature 3 string unchanged), security, tools, skill catalog (Feature 4 format unchanged).
  - On-demand instruction section from cwd `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` with per-file 4000-char cap, 12000-char total cap, hash dedup, skip missing/unreadable.
  - QueryEngine continues to prepend one system message and not persist it.
  - Unit tests for assembly order, missing files, truncation, dedup, tools list, security text, Feature 3/4 substrings, freshness, and session JSON isolation.
- Out of scope / non-goals:
  - Session 09 memory / `MEMORY.md` / `.memory/`.
  - Parent-directory walk or `~/.` instruction files.
  - `.claude/CLAUDE.md` (not in the locked cwd list).
  - Dumping project permission rules JSON into the prompt.
  - Full JSON schemas inside the tools section.
  - Mode-specific prompts (Simple / KAIROS / coordinator / MCP).
  - API-level prompt cache / `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`.
  - Required in-process assembly cache (allowed later if the key includes file mtimes and tool/skill lists; not required for MVP).
  - Changing `load_skill`, slash expansion, planning tools, nag, or permission-gate enforcement.
- Preserved behavior:
  - Feature 1: workspace bound, concurrent batch, human/JSON events.
  - Feature 2: hard deny, project rules, numbered authorize for MEDIUM/HIGH.
  - Feature 3: six planning tools, `.cda/.todos/`, 3-round nag, planning string content, messages-only session JSON.
  - Feature 4: skill scan roots, catalog format including `(no skills found)`, `load_skill`, slash `/<name>`.

## User Stories & Journeys (Moderate/Complex)

### User Story 1 - Named always-on prompt sections (Priority: P1) 🎯 MVP
- Description: Every `complete()` receives a system message whose sections appear in a fixed order: identity, workspace, planning, security, tools, skill catalog. Planning text is exactly the Feature 3 string. Skill catalog uses the Feature 4 formatter.
- Why this priority: Replaces the current two-part string without losing Feature 3/4 contracts.
- Independent Test: FakeProvider records the first message; assert section markers and Feature 3/4 substrings.
- Acceptance Scenarios:
  1. Given a turn, When `complete()` is called, Then the first message has `role=system` and contains identity, `Working directory:`, the Feature 3 planning sentence including the six tool names, a security heading or equivalent marker, a tools list, and `Skills available:`.
  2. Given zero skills, When `complete()` is called, Then the system message still contains `Skills available:\n(no skills found)`.
  3. Given any turn, When session JSON is loaded, Then it has no `role=system` message.

### User Story 2 - Workspace identity (Priority: P1) 🎯 MVP
- Description: The workspace section states the process current working directory so the model knows where file tools apply.
- Why this priority: Session 10 always-on workspace fact; required for grounded file edits.
- Independent Test: Change cwd in a test and assert the system message contains that path.
- Acceptance Scenarios:
  1. Given process cwd `/tmp/proj`, When the prompt is assembled, Then it contains `Working directory: /tmp/proj` (or an equivalent line that includes the resolved cwd string).

### User Story 3 - Instruction files (Priority: P1) 🎯 MVP
- Description: If any of `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` exist in process cwd, an instruction section is appended after the skill catalog. Files are read in that order. Missing or unreadable files are skipped. Duplicate content is injected once. Each file is truncated at 4000 characters; the section stops at 12000 characters total, with a visible truncation marker.
- Why this priority: The Session 10 / blueprint goal is combining instruction files with tools, skills, and security.
- Independent Test: Temp cwd with combinations of the three files, oversized files, and duplicate content.
- Acceptance Scenarios:
  1. Given cwd `AGENTS.md` containing `Follow repo rules.`, When `complete()` runs, Then the system message contains `Follow repo rules.` and an instruction-section marker that names `AGENTS.md`.
  2. Given none of the three files exist, When `complete()` runs, Then the system message has no instruction-section marker and does not invent file contents.
  3. Given `AGENTS.md` and `CLAUDE.md` with identical content, When assembled, Then that content appears once.
  4. Given `AGENTS.md` longer than 4000 characters, When assembled, Then at most 4000 characters of that file appear and a truncation marker is present.
  5. Given files whose combined kept text would exceed 12000 characters, When assembled, Then the instruction section is at most 12000 characters of file text plus markers, and a truncation marker is present.
  6. Given `AGENTS.md` is created or edited mid-session, When the next `complete()` runs, Then the new content appears without process restart.
  7. Given an unreadable instruction file, When assembled, Then the process does not crash and the other sections remain.

### User Story 4 - Registered tools list (Priority: P1) 🎯 MVP
- Description: The tools section lists every tool currently in the registry as `- <name>: <description>`. It does not embed JSON schemas.
- Why this priority: Session 10 always-on tools section; schemas already travel on the API `tools` field.
- Independent Test: Inspect assembled prompt for known registered names (`bash`, `load_skill`, `create_task`) and absence of a schema `properties` dump for those tools.
- Acceptance Scenarios:
  1. Given the default registry, When assembled, Then the tools section contains `- bash:` (or `- bash: <description>`) and `- load_skill:` and `- create_task:`.
  2. Given the assembled prompt, When inspected, Then it does not contain the JSON schema key `"properties"` as part of a dumped tool schema block.

### User Story 5 - Security policy text (Priority: P1) 🎯 MVP
- Description: An always-on security section tells the model that file/search tools are workspace-bound, that listed deny-list commands are blocked, that protected paths/keys are blocked, and that MEDIUM/HIGH tools require user approval. Project rules JSON is not copied into the prompt.
- Why this priority: Session 10 / user goal includes security policies without leaking the live rules file.
- Independent Test: Assert required phrases; assert `rules.json` contents are absent even when a rules file exists.
- Acceptance Scenarios:
  1. Given a turn, When assembled, Then the system message mentions workspace bound (or that paths outside the working directory are refused), hard deny or deny-list, protected paths or keys, and approval for MEDIUM/HIGH tools.
  2. Given `.cda/.permission_rules/rules.json` containing a distinctive pattern string `UNIQUE-RULE-TOKEN`, When assembled, Then that token does not appear in the system message.

### User Story 6 - Freshness and transcript isolation (Priority: P1) 🎯 MVP
- Description: Assembly runs on every `complete()`. Skill catalog and instruction files reflect disk state at that call. Session JSON remains messages-only.
- Why this priority: Matches Feature 4 freshness; Feature 3 locked that system text is not persisted.
- Independent Test: Mid-session file add; load session file after a turn.
- Acceptance Scenarios:
  1. Given a new skill added mid-session, When the next `complete()` runs, Then the catalog lists that skill (Feature 4 AC-015 preserved).
  2. Given any successful turn, When `.cda/.sessions/<id>.json` is loaded, Then no message has `role=system`.

## Requirements (Moderate/Complex)
- `REQ-001`: On every provider `complete()`, QueryEngine must prepend exactly one `role=system` message whose content is the assembled prompt, and must not append that message to `history` or session JSON. Priority: Must. Validation: `query_engine_check.py`. Linked story: US1, US6.
- `REQ-002`: Assembled sections must appear in this order, separated by blank lines (`\n\n`): identity, workspace, planning, security, tools, skill catalog, then instruction section only if at least one instruction file contributed text. Priority: Must. Validation: `query_engine_check.py`, `tools_check.py`. Linked story: US1.
- `REQ-003`: Identity section must state that the assistant is a coding agent. Priority: Must. Validation: `tools_check.py`. Linked story: US1.
- `REQ-004`: Workspace section must include the process cwd path. Priority: Must. Validation: `tools_check.py`. Linked story: US2.
- `REQ-005`: Planning section must be exactly the Feature 3 `SYSTEM_MESSAGE` string (`You should plan before executing. Tools: create_task, list_tasks, get_task, claim_task, complete_task, cancel_task.`). Priority: Must. Validation: `query_engine_check.py`. Linked story: US1.
- `REQ-006`: Skill catalog section must be exactly the Feature 4 `format_catalog` output, including `(no skills found)` when empty. Priority: Must. Validation: `query_engine_check.py`. Linked story: US1, US6.
- `REQ-007`: Tools section must list each currently registered tool as `- <name>: <description>` and must not embed tool JSON schemas. Priority: Must. Validation: `tools_check.py`. Linked story: US4.
- `REQ-008`: Security section must state workspace bound, deny-list / hard deny, protected paths/keys, and MEDIUM/HIGH approval. It must not include contents of `.cda/.permission_rules/rules.json`. Priority: Must. Validation: `tools_check.py`, `query_engine_check.py`. Linked story: US5.
- `REQ-009`: Instruction files must be discovered only in process cwd, in order `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`. Missing or unreadable files are skipped. Parent directories and home-directory instruction files are not scanned. Priority: Must. Validation: `tools_check.py`. Linked story: US3.
- `REQ-010`: Instruction-file content that is byte-identical after UTF-8 decode (SHA-256 of the decoded text) must be injected only once. Priority: Must. Validation: `tools_check.py`. Linked story: US3.
- `REQ-011`: Each instruction file contributes at most 4000 characters. The instruction section's contributed file text is at most 12000 characters. Truncation must include a visible marker containing `TRUNCATED`. Priority: Must. Validation: `tools_check.py`. Linked story: US3.
- `REQ-012`: If no instruction file contributes text, the instruction section must be omitted entirely. Priority: Must. Validation: `tools_check.py`, `query_engine_check.py`. Linked story: US3.
- `REQ-013`: Assembly must run on every `complete()` so mid-session instruction-file and skill changes appear on the next call without process restart. Priority: Must. Validation: `query_engine_check.py`. Linked story: US3, US6.
- `REQ-014`: `src/` remains Python 3.11+ stdlib only. Priority: Must. Validation: `tools_check.py`. Linked story: US1–US6.
- `REQ-015`: Feature 1–4 public behavior is unchanged: permission gate, planning tools and nag, `load_skill`, slash commands, messages-only session JSON. Priority: Must. Validation: existing `*_check.py` suites. Linked story: US1, US6.

## Acceptance Criteria
- `AC-001`: Given a FakeProvider, When `QueryEngine.turn()` runs, Then `complete()`'s first message has `role=system` and contains, in order, a coding-agent identity, `Working directory:`, `You should plan before executing.`, `create_task`, a security mention of workspace bound or working-directory refusal, `- bash:`, `Skills available:`. Covers REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-007. Proof: `python3 tests/query_engine_check.py`.
- `AC-002`: Given zero skills, When `QueryEngine.turn()` runs, Then the system message contains `Skills available:\n(no skills found)`. Covers REQ-006. Proof: `python3 tests/query_engine_check.py`.
- `AC-003`: Given any turn, When `.cda/.sessions/<id>.json` is loaded, Then no message has `role=system`. Covers REQ-001, REQ-015. Proof: `python3 tests/query_engine_check.py`.
- `AC-004`: Given process cwd is a temp directory `P`, When the prompt is assembled, Then it contains `Working directory: ` followed by `P` (resolved path string). Covers REQ-004. Proof: `python3 tests/tools_check.py`.
- `AC-005`: Given cwd `AGENTS.md` with body `REPO-RULE-ALPHA`, When assembled or `QueryEngine.turn()` runs, Then the system message contains `REPO-RULE-ALPHA` and names `AGENTS.md`. Covers REQ-009. Proof: `python3 tests/tools_check.py`, `python3 tests/query_engine_check.py`.
- `AC-006`: Given none of `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` exist in cwd, When assembled, Then the system message has no instruction-file heading and does not contain a fabricated instruction body. Covers REQ-012. Proof: `python3 tests/tools_check.py`.
- `AC-007`: Given `AGENTS.md` and `CLAUDE.md` with the same text `DUP-BODY`, When assembled, Then `DUP-BODY` occurs once in the instruction section. Covers REQ-010. Proof: `python3 tests/tools_check.py`.
- `AC-008`: Given `AGENTS.md` of 5000 `A` characters, When assembled, Then at most 4000 of those `A` characters appear and the text `TRUNCATED` appears. Covers REQ-011. Proof: `python3 tests/tools_check.py`.
- `AC-009`: Given three instruction files whose kept text would exceed 12000 characters, When assembled, Then contributed file text in the instruction section is at most 12000 characters and `TRUNCATED` appears. Covers REQ-011. Proof: `python3 tests/tools_check.py`.
- `AC-010`: Given default registry, When assembled, Then the tools section includes `- bash:`, `- load_skill:`, and `- create_task:`, and the system message does not contain a dumped JSON object with `"properties"` for those tools. Covers REQ-007. Proof: `python3 tests/tools_check.py`.
- `AC-011`: Given a turn, When assembled, Then the system message mentions workspace bound or refusal of paths outside the working directory, deny-list or hard deny, protected paths or keys, and approval for MEDIUM or HIGH tools. Covers REQ-008. Proof: `python3 tests/tools_check.py`.
- `AC-012`: Given `.cda/.permission_rules/rules.json` containing `UNIQUE-RULE-TOKEN`, When assembled, Then `UNIQUE-RULE-TOKEN` is absent from the system message. Covers REQ-008. Proof: `python3 tests/query_engine_check.py`.
- `AC-013`: Given `AGENTS.md` is created in cwd after the first turn, When the next `QueryEngine.turn()` runs, Then the new file body appears in that turn's system message. Covers REQ-013. Proof: `python3 tests/query_engine_check.py`.
- `AC-014`: Given a new skill added mid-session, When the next `complete()` runs, Then the catalog lists that skill. Covers REQ-006, REQ-013, REQ-015. Proof: `python3 tests/query_engine_check.py`.
- `AC-015`: Given existing Feature 1–4 suites, When `python3 -m unittest discover -s tests -p '*_check.py'` runs, Then all tests pass. Covers REQ-014, REQ-015. Proof: `python3 -m unittest discover -s tests -p '*_check.py'`.
- `AC-016`: Given `CLAUDE.md` only (no `AGENTS.md`), When assembled, Then the instruction section includes `CLAUDE.md` content and does not require `AGENTS.md`. Covers REQ-009. Proof: `python3 tests/tools_check.py`.
- `AC-017`: Given an unreadable `AGENTS.md` (or a file that raises `OSError`/`UnicodeDecodeError` on read), When assembled, Then assembly succeeds and always-on sections are still present. Covers REQ-009. Proof: `python3 tests/tools_check.py`.

## Success Criteria (Measurable Outcomes)
- `SC-001`: In one REPL session, the model sees identity, cwd, planning tools, security rules, registered tool names, the skill catalog, and cwd instruction files on every turn, without those system bytes appearing in the saved transcript.
- `SC-002`: Editing `AGENTS.md` or adding a skill mid-session changes the next turn's system message without restarting the CLI.
- `SC-003`: Oversized instruction files cannot push the instruction section past the 4000 / 12000 character caps.
- `SC-004`: Zero third-party dependencies added to `src/`.

## Constraints and Risk
- Constraints:
  - NFR-001 Stdlib-only `src/` (Python 3.11+). Linked ACs: AC-015.
  - NFR-002 System message never persisted. Linked ACs: AC-003.
  - NFR-003 Instruction injection bounded (4000 / 12000) with `TRUNCATED` marker. Linked ACs: AC-008, AC-009.
  - NFR-004 Assembly freshness on every `complete()`. Linked ACs: AC-013, AC-014.
  - NFR-005 Feature 3 planning string and Feature 4 catalog format are unchanged. Linked ACs: AC-001, AC-002, AC-014.
- Dependencies/touchpoints: `QueryEngine._with_system`, Feature 3 `SYSTEM_MESSAGE`, Feature 4 `format_catalog` / `scan_skills`, tool registry, cwd instruction files, `tests/tools_check.py`, `tests/query_engine_check.py`.
- Risks and mitigations:
  - Risk: Root `AGENTS.md` is large (SpecHarness kit text) and will consume most of the 4000-char cap in this repo. Mitigation: caps are explicit; remaining files still have budget up to 12000.
  - Risk: Feature 3/4 tests that assert the system message *equals* or *starts with* only planning + catalog will fail. Mitigation: update those asserts to require the planning string and catalog as sections, not as the entire message prefix, during implement.
  - Risk: Instruction files could contain secrets. Mitigation: cwd-only, no parent walk; still the operator's file. Do not add a secret scanner in this feature.
- Open questions (blocking only): none.

## Decisions
- Locked decisions:
  - Session 10 is an in-scope reference for this feature only, not a global architecture contract.
  - Instruction files: cwd `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` in that order. No parent walk. No home-dir instruction files. No `.claude/CLAUDE.md`.
  - Always-on: identity, workspace, planning (Feature 3 verbatim), security, tools (name + description lines), skill catalog (Feature 4 verbatim).
  - On-demand: instruction section iff at least one file contributed text.
  - Out: memory, MCP, git status, mode prompts, rules.json dump, schema dump, required process cache, API prompt cache.
  - Caps: 4000 chars/file, 12000 chars instruction-section file text; marker contains `TRUNCATED`. Hash dedup on decoded file text.
  - Rebuild every `complete()`. System message not stored in session JSON.
- Related `ADR-*`: none.
