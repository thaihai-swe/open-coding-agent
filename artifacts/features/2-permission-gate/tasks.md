# Tasks

## Metadata

- Feature/profile: `2-permission-gate` / Complex
- Plan approved date: 2026-08-23

## Implementation Strategy

- Strategy: Incremental
- Reason: Shared files (`permissions.py`, `query_engine.py`, `query_engine_check.py`) make fake parallelism unsafe. Follow the plan’s four tracer slices: hard deny → numbered ask + project rules → `.cda/` defaults → regression. `AuthorizeDecision` is an expand–contract: T-004 replaces `bool` authorize; T-005 is the first reader of `persist` (no dual bool adapter).

## Task Contract

Each task includes ID, target paths from the plan module map, `Covers: AC-*`, `Depends on: T-NNN`, entry proof (failing test), and exit proof. Status is `Not Started` until `/spec-implement` runs `task-start`. No `[P]` markers: later tasks edit the same modules.

## Tasks

### Phase 1: Setup / Foundational — P1 hard deny on `invoke` (US1, US3)

- Goal: Deny-list and protected path/key hard deny run inside `check_permission` before HIGH `bypass_permissions`. Bare `invoke` never consults project rules. `repl` is not on the shell deny list.
- Entry proof: `python3 tests/tools_check.py` lacks deny-list / HIGH-without-bypass / protected-key cases (or they fail).
- Exit proof: `python3 tests/tools_check.py` exit 0.

- [x] T-001 [US1] `src/tools/types.py`, `src/tools/permissions.py`, `tests/tools_check.py` — add `DENY_LIST` and `hard_deny_reason`; `check_permission` consults it before the HIGH bypass short-circuit; `invoke` of deny-listed `bash`/`powershell` returns `Blocked:` + pattern and does not start `subprocess.run`; non-listed `echo ping` with bypass still runs; without bypass still `Permission denied for high-risk tool`; `repl` `code` containing `sudo` is not deny-listed; prove all seven REQ-006 substrings
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-005`, `AC-017`
  - Depends on:
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:
  Validation evidence: python3 tests/tools_check.py exit 0; 16 tests OK. AC-001 sudo bash + bypass returns Blocked: sudo and subprocess.run not called; AC-002 powershell shutdown Blocked:; AC-003 echo ping + bypass succeeds; AC-004 echo ping without bypass Permission denied for high-risk tool; AC-005 repl code sudo = 1 not deny-listed; AC-017 all seven DENY_LIST patterns blocked with bypass. hard_deny_reason consulted before HIGH bypass.


- [x] T-002 [US3] `src/tools/permissions.py`, `src/tools/handlers/settings.py`, `tests/tools_check.py` — extend `hard_deny_reason` for MEDIUM `file_path`/`key` vs `PROTECTED_PATHS` and `config` SET vs `PROTECTED_KEYS`; `config` GET is not hard-denied; remove the handler `PROTECTED_KEYS` raise so that list is only live in `hard_deny_reason`; `write_file` `.env` is `Protected path blocked:` and not written
  - Covers: `AC-006`, `AC-007`
  - Depends on: `T-001`
  - Status: Done
  - Proof: `python3 tests/tools_check.py`
  - Evidence:

### Phase 2: User Stories 1, 3, 4 — Hard deny on `QueryEngine.turn` (Priority: P1) 🎯 MVP

- Goal: Turn path skips authorize and `tool_denied` for hard-denied calls; LOW still does not prompt; siblings still get results. `authorize` remains `bool` until T-004.
- Entry proof: `python3 tests/query_engine_check.py` lacks hard-deny / protected-path turn cases (or they fail).
- Exit proof: `python3 tests/query_engine_check.py` exit 0.
  Validation evidence: python3 tests/tools_check.py exit 0; 20 tests OK. AC-006 write_file .env returns Protected path blocked: and does not write file; AC-007 config set secret returns Protected key blocked:; config get secret returns success; config set .gitconfig returns Protected path blocked:; settings.py duplicate raise removed.


- [x] T-003 [US1] `src/application/query_engine.py`, `tests/query_engine_check.py` — `_run_batch` calls `hard_deny_reason` before authorize; deny-listed `bash` does not call authorize, does not emit `tool_denied`, records `Blocked:` + pattern, and does not run the handler; listed hard-deny then LOW `read_file` keeps both results in order
  - Covers: `AC-008`, `AC-009`, `AC-013`
  - Depends on: `T-001`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:
  Validation evidence: python3 tests/query_engine_check.py exit 0; 15 tests OK. AC-008 deny-listed bash sudo id skips authorize, no tool_denied, Blocked: sudo, handler not run; AC-009 LOW read_file does not authorize; AC-013 hard-deny bash then LOW read_file keeps listed order and sibling result.


- [x] T-004 [US3] `src/application/query_engine.py`, `tests/query_engine_check.py` — turn path uses the same `hard_deny_reason` for `write_file` `id_rsa` and `config` SET `secret`: authorize is not called, no file write, no key set
  - Covers: `AC-015`, `AC-016`
  - Depends on: `T-002`, `T-003`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:

### Phase 3: User Stories 2, 4, 5 — Numbered ask and project rules (Priority: P1) 🎯 MVP

- Goal: MEDIUM/HIGH that are not hard-denied and have no matching rule prompt `1`–`4`. `1`/`2` allow this call; anything else is user deny. `2`/`4` persist tool + primary argument in `.cda/.permission_rules/rules.json`; later matching calls in any session skip the prompt. Hard deny still wins over a rules-file allow.
- Entry proof: `python3 tests/terminal_ui_check.py` still treats `a`/`approve` as allow; `python3 tests/query_engine_check.py` lacks rules-file cases (or they fail).
- Exit proof: `python3 tests/terminal_ui_check.py` and `python3 tests/query_engine_check.py` exit 0.
  Validation evidence: python3 tests/query_engine_check.py exit 0; 17 tests OK. AC-015 write_file id_rsa skips authorize, Protected path blocked:, file not written; AC-016 config SET secret skips authorize, handler not called, error result recorded.


- [x] T-005 [US2] `src/tools/permissions.py`, `src/application/query_engine.py`, `src/presentation/terminal_ui.py`, `tests/terminal_ui_check.py`, `tests/query_engine_check.py` — expand: add `AuthorizeDecision(allow, persist)`; `Authorize` returns it (no bool adapter); `TerminalUI.authorize` numbered prompt; after trim `1`/`2` allow this call, `3`/`4`/empty/`a`/`approve`/other deny this call; QueryEngine uses `.allow` only; migrate every existing `True`/`False` authorize lambda (helper `_once(allow)`); once-allow HIGH still injects `bypass_permissions`; user deny still `tool_denied` + `"Tool execution denied by user."` and does not skip siblings
  - Covers: `AC-010`, `AC-011`, `AC-012`, `AC-014`
  - Depends on: `T-004`
  - Status: Done
  - Proof: `python3 tests/terminal_ui_check.py` && `python3 tests/query_engine_check.py`
  - Evidence:
  Validation evidence: python3 tests/terminal_ui_check.py exit 0 (17 OK); python3 tests/query_engine_check.py exit 0 (18 OK). AC-012 numbered 1-4 prompt; 1/2 allow this call, 3/4/empty/a/approve/other deny; persist flags 2 and 4. QueryEngine uses .allow only; _once helper migrated all bool lambdas; AC-010 once-allow HIGH injects bypass_permissions; AC-011/AC-014 user deny tool_denied + sibling isolation.


- [x] T-006 [US5] `src/tools/permission_rules.py`, `src/application/query_engine.py`, `tests/query_engine_check.py` — contract: QueryEngine reads `.persist`; `match_rule` then ask then `upsert_rule` for MEDIUM/HIGH that are not hard-denied; tests `chdir` a temp cwd; `2` writes allow for `bash`+`command`; `1` does not create the file; `4` later-matches `write_file` `file_path` (any `content`) as user deny; different session id shares the file; sibling same command after `2` prompts once; rules-file allow cannot override deny-listed `sudo`; invalid entries skipped; rule lands at `.cda/.permission_rules/rules.json` not cwd `.permission_rules/`; `invoke` still does not import this module; session JSON gains no permission fields
  - Covers: `AC-018`, `AC-019`, `AC-020`, `AC-021`, `AC-022`, `AC-023`, `AC-025`, `AC-029`
  - Depends on: `T-005`
  - Status: Done
  - Proof: `python3 tests/query_engine_check.py`
  - Evidence:

### Phase 4: User Story 6 — `.cda/` data root (Priority: P1) 🎯 MVP

- Goal: Default sessions and secrets live under `.cda/`. `.cda/` is gitignored. Session files stay messages-only. No dual-read of cwd `.sessions/` / `.secrets/`.
- Entry proof: default `SessionStore()` still writes `.sessions/`; missing-config error still names `.secrets/config.json`.
- Exit proof: `python3 tests/session_check.py`, `python3 tests/provider_check.py`, and `python3 tests/cli_check.py` exit 0.
  Validation evidence: python3 tests/query_engine_check.py exit 0; 26 tests OK. AC-018 answer 2 writes allow bash+command to .cda/.permission_rules/rules.json; session JSON messages-only; AC-019 different session id skips ask; AC-020 answer 4 later-matches write_file file_path as user deny; AC-021 answer 1 does not create file; AC-022 sibling same command prompts once; AC-023 rules-file allow cannot override sudo hard deny; AC-025 invalid entries skipped; AC-029 rule not at cwd .permission_rules/; invoke does not import permission_rules.


- [x] T-007 [US6] `src/infrastructure/session_store.py`, `tests/session_check.py` — default directory `.cda/.sessions`; save in a temp cwd writes `.cda/.sessions/<id>.json` not cwd `.sessions/<id>.json`; load a messages-only session; a later messages-only save does not add permission-rule fields and does not change an existing `.cda/.permission_rules/rules.json`; with no rules file, matching MEDIUM/HIGH still prompt
  - Covers: `AC-024`, `AC-026`, `AC-027`
  - Depends on: `T-006`
  - Status: Done
  - Proof: `python3 tests/session_check.py`
  - Evidence:
  Validation evidence: python3 tests/session_check.py exit 0; 4 tests OK. AC-027 default SessionStore() in temp cwd writes .cda/.sessions/<id>.json not cwd .sessions/<id>.json; AC-024 load messages-only session; AC-026 later messages-only save does not add permission-rule fields and does not change existing .cda/.permission_rules/rules.json; with no rules file matching MEDIUM/HIGH still prompt.


- [x] T-008 [US6] `src/infrastructure/providers/openai.py`, `.gitignore`, `documents/how-to-run.md`, `tests/provider_check.py`, `tests/cli_check.py` — default config `.cda/.secrets/config.json`; missing-config error text includes that path and does not require cwd `.secrets/config.json`; `CONFIG_FILE` still overrides; add `.cda/` to `.gitignore`; update how-to-run
  - Covers: `AC-028`, `AC-030`
  - Depends on: `T-007`
  - Status: Done
  - Proof: `python3 tests/provider_check.py` && `python3 tests/cli_check.py`
  - Evidence:

### Phase 5: Polish — regression pack

- Goal: Full unittest surface still green after the Session 03 slices.
- Entry proof: prior tasks Done.
- Exit proof: compile + discover exit 0.
  Validation evidence: python3 tests/provider_check.py && python3 tests/cli_check.py exit 0; 9 provider tests OK, 5 cli tests OK. AC-028 missing default config ProviderError names .cda/.secrets/config.json and does not require cwd .secrets/config.json; CONFIG_FILE still overrides; AC-030 .gitignore contains .cda/; documents/how-to-run.md updated to point to .cda/.secrets/config.json.


- [x] T-009 `src/`, `tests/` — run the full app check pack; fix only regressions caused by this feature
  - Covers: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-013`, `AC-014`, `AC-015`, `AC-016`, `AC-017`, `AC-018`, `AC-019`, `AC-020`, `AC-021`, `AC-022`, `AC-023`, `AC-024`, `AC-025`, `AC-026`, `AC-027`, `AC-028`, `AC-029`, `AC-030`
  - Depends on: `T-008`
  - Status: Done
  - Proof: `python3 -m compileall -q src` && `python3 -m unittest discover -s tests -p '*_check.py'`
  - Evidence:

## Traceability

| ID | Tasks |
| --- | --- |
| REQ-001 | T-001, T-003 |
| REQ-002 | T-003 |
| REQ-003 | T-005, T-006 |
| REQ-004 | T-005 |
| REQ-005 | T-005, T-006 |
| REQ-006 | T-001 |
| REQ-007 | T-001, T-003, T-006 |
| REQ-008 | T-003 |
| REQ-009 | T-001 |
| REQ-010 | T-002, T-004 |
| REQ-011 | T-002, T-004 |
| REQ-012 | T-001, T-005, T-006 |
| REQ-013 | T-003, T-006 |
| REQ-014 | T-003, T-005 |
| REQ-015 | T-001, T-003, T-006 |
| REQ-016 | T-006 |
| REQ-017 | T-006 |
| REQ-018 | T-006, T-007 |
| REQ-019 | T-003, T-006 |
| REQ-020 | T-006, T-007, T-008 |
| REQ-021 | T-008 |
| AC-001–AC-005, AC-017 | T-001, T-009 |
| AC-006, AC-007 | T-002, T-009 |
| AC-008, AC-009, AC-013 | T-003, T-009 |
| AC-015, AC-016 | T-004, T-009 |
| AC-010–AC-012, AC-014 | T-005, T-009 |
| AC-018–AC-023, AC-025, AC-029 | T-006, T-009 |
| AC-024, AC-026, AC-027 | T-007, T-009 |
| AC-028, AC-030 | T-008, T-009 |

## Resume Notes

- Next recommended task: `T-001`
- First ready (no unfinished deps): `T-001`
- Implement with `/spec-implement`; `task-start --task T-001` before coding.
- Gates remain deferred; task Proof commands are not closeout.
  Validation evidence: python3 -m compileall -q src exit 0; python3 -m unittest discover -s tests -p '*_check.py' exit 0; 81 tests OK. Full app check pack green after Session 03 slices. No regressions to fix.

