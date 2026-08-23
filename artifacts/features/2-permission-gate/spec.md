# Feature Specification

## Metadata
- Feature: `2-permission-gate`
- Profile: `Complex`
- Status: `Approved`
- Owner: adopter
- Requested artifact name: `2.permission-gate` (harness slug `2-permission-gate`)
- References (scoped, not global architecture): Session 03 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s03/

## Problem Statement
- Who is affected, what fails, and why now: A coding-agent CLI user can already approve or deny MEDIUM/HIGH tools, but approved `bash`/`powershell` can still run permanently forbidden command patterns (`sudo`, `rm -rf /`, and the rest of the Session 03 deny list). Protected paths/keys are hard-blocked only after a prompt. Direct `invoke` of HIGH tools is a second, easy-to-desync gate. Repeating the same allowed or denied pattern every turn is extra prompts with no project-level memory. Session 03 must make deny / ask / allow a code-enforced router on the live turn and `invoke` paths, with always-allow / always-deny for matching patterns stored at the project, without switching in-workspace writes to silent allow.

## Outcome
- Observable result: Every tool call is routed to **allow**, **ask**, or **deny** before the handler runs. LOW runs without a prompt. Hard-denied calls (deny list and protected path/key) never prompt, never run, and cannot be overridden by Yes, “don't ask again”, `bypass_permissions`, or a project rules-file allow entry. MEDIUM/HIGH that are not hard-denied and have no matching project permission rule prompt numbered `1`–`4`. `1`/`2` allow this call; `3`/`4`/anything else deny this call. `2`/`4` persist a project permission rule for that tool + primary-argument pattern in `.cda/.permission_rules/rules.json`; later matching calls in any session of this project skip the prompt. Project always-deny is the same class as user deny (`tool_denied`). Sibling calls in the same assistant message still get results. Default sessions, secrets, and permission rules live under `.cda/` at process cwd. `.cda/.sessions/<id>.json` stays messages-only.
- Minimum useful release: US1–US6 (hard deny + ask/allow + project rules + `.cda` data dir + protected path/key + sequential batch gates).

## Scope
- In scope:
  - Deny / ask / allow routing on every tool call before handler execution.
  - Hard deny list on `bash` and `powershell` `command` strings (substring match). Not bypassable, including by project always-allow.
  - MEDIUM/HIGH ask prompt with numbered `1`–`4` (once / always for this pattern). LOW skips authorize.
  - Project permission rules: match tool name + primary argument; persist in `.cda/.permission_rules/rules.json` at process cwd; shared by every session in that project; the user can edit that file; `2`/`4` answers write through before the turn returns; the file is the source of truth for the next gated call.
  - Project-local CLI data dir `.cda/` under process cwd holding `.permission_rules`, `.sessions`, and `.secrets`. Defaults: `.cda/.permission_rules/rules.json`, `.cda/.sessions/<id>.json`, `.cda/.secrets/config.json`. `CONFIG_FILE` still overrides the config path. Cwd `.permission_rules/`, `.sessions/`, and `.secrets/` are not used.
  - Protected path/key hard blocks remain and skip authorize (same deny class as the deny list).
  - Sequential gate walk in listed order before overlapping execution of that batch (Feature 1 authorize-then-overlap preserved, with hard deny first, then project-rule match, then ask).
  - Live-path only: deny list, protected lists, project permission rules, authorize, and HIGH `bypass_permissions` are consulted by the paths that own them. No unused permission helpers, unused mode enums, disconnected lists, or permission fields on session JSON.
  - Proof tests for hard deny, user deny, project always-allow/deny, persisted/shared/edited rules, `.cda` default paths, protected path/key, HIGH-without-bypass, and batch isolation.
- Out of scope / non-goals:
  - `/permissions` modes (`ReadOnly`, `WorkspaceWrite`, `DangerFullAccess`).
  - AST command analysis, YOLO/auto-approve of unmatched tools or patterns.
  - Claude Code four-behavior/`passthrough` pipeline and eight rule-source files.
  - Workspace-jailing `bash` / `powershell` / `repl` (Feature 1 AC-008 preserved).
  - Lifecycle hooks (Session 04).
  - Changing Feature 1 workspace bound, `glob` alias, concurrent batch, extra registered tools, prompt submit, Markdown, or JSON event types.
  - Adding a new JSON event type for hard deny or for project-rule hits.
  - Applying the shell deny list to `repl` `code`.
  - Storing permission rules in `.cda/.sessions/<id>.json`.
  - Dual-write or dual-read of cwd `.sessions/`, `.secrets/`, or `.permission_rules/` (Feature 1 default paths are superseded; no auto-migration).
  - Project always-allow applying to bare `invoke`. Bare `invoke` keeps hard deny + HIGH `bypass_permissions` only.
- Preserved behavior:
  - Extra tools remain registered; risk classes stay as they are today unless a call is hard-denied or a matching project rule applies.
  - User deny (answer `3`/`4`/other, or a matching project deny rule): `tool_denied` event and history error `"Tool execution denied by user."`; that handler does not run.
  - Feature 1: workspace-bound file/search tools; concurrent batch with listed-order results; a failed/denied call does not skip siblings; next provider completion waits for the batch.
  - Env vars for provider config, `CONFIG_FILE` override, missing-config exit `2`, `max_turns` default 8, Ctrl+C exit `130`, session JSON redaction of `api_key`/`authorization` keys. Default config file path moves to `.cda/.secrets/config.json`.
  - Existing unittest `*_check.py` proof style.
  - Session files remain `{"messages": [...]}` only. `--session` resume loads transcript from `.cda/.sessions/`, not permission rules.

## User Stories & Journeys (Moderate/Complex)

### User Story 1 - Hard deny never executes (Priority: P1) 🎯 MVP
- Description: Permanently forbidden `bash`/`powershell` commands are blocked before any approve prompt and before the handler. Yes, “don't ask again”, `bypass_permissions`, and a project rules-file allow entry cannot override that block.
- Why this priority: Session 03 teaching gap vs today’s “ask then run anything.” Without this, the permission gate is only a prompt.
- Independent Test: `invoke` and `QueryEngine.turn` with a deny-listed command; assert no handler effect, no authorize call, error result. A rules-file allow for `sudo` still blocked.
- Acceptance Scenarios:
  1. Given a `bash` or `powershell` command whose string contains a deny-list pattern, When the model requests that tool, Then the handler does not run and authorize is not called.
  2. Given the same command, When `invoke` is called with `bypass_permissions=True`, Then it is still blocked.
  3. Given a `bash` command that does not contain a deny-list pattern, When the user answers `1` or `2`, Then the command may run (Feature 1: still not workspace-jailed).
  4. Given a `.cda/.permission_rules/rules.json` allow entry for a deny-listed command, When the call is gated, Then it is still hard-denied.

### User Story 2 - Ask MEDIUM/HIGH, allow LOW (Priority: P1) 🎯 MVP
- Description: Tools that are not hard-denied and have no matching project permission rule still follow today’s risk classes: LOW runs without a prompt; MEDIUM/HIGH prompt numbered `1`–`4`. `1`/`2` allow this call; any other answer denies this call. `--json` still reads the answer from stdin.
- Why this priority: Product-sense Journey 1 and Feature 1 sequential authorize must not be replaced by teaching auto-allow for in-workspace writes.
- Independent Test: Existing authorize tests plus LOW `read_file` with authorize recording that it was not called. TerminalUI answers `1`–`4`.
- Acceptance Scenarios:
  1. Given a LOW tool (`read_file`), When the model calls it, Then authorize is not called and the handler may run (workspace bound still applies).
  2. Given a MEDIUM or HIGH tool that is not hard-denied and has no matching project permission rule, When the user answers `1` or `2`, Then the handler may run.
  3. Given a MEDIUM or HIGH tool that is not hard-denied and has no matching project permission rule, When the user answers `3`, `4`, empty, or any other string, Then `tool_denied` is emitted, history records `"Tool execution denied by user."`, and the handler does not run.
  4. Given `--json`, When a MEDIUM/HIGH tool that is not hard-denied and has no matching project permission rule is requested, Then the same numbered `1`–`4` prompt is issued on stdin.

### User Story 3 - Protected path and key hard blocks (Priority: P1) 🎯 MVP
- Description: MEDIUM calls whose `file_path` or `key` substring-matches a protected path, and `config` SET of a protected key, are hard-denied: no prompt, no handler side effect. A project allow rule cannot override.
- Why this priority: These blocks already exist but are easy to skip in the UI path; Session 03 must treat them as deny, not as a post-approve surprise.
- Independent Test: `invoke` and `QueryEngine.turn` with `.env` / `id_rsa` paths and `config` SET `secret`.
- Acceptance Scenarios:
  1. Given `write_file` or `edit_file` with `file_path` containing a protected-path token, When the call is gated, Then authorize is not called and no file is written.
  2. Given `config` with action `set` and a protected key, When the call is gated, Then authorize is not called and the set does not take effect.
  3. Given `config` GET of a protected key, When the user answers `1` or `2`, Then this slice does not add a GET hard deny.

### User Story 4 - Sequential gates in a concurrent batch (Priority: P1) 🎯 MVP
- Description: For one assistant message’s tool list, hard deny then project-rule match then authorize run sequentially in listed order on the main/UI path. Allowed calls may then overlap. Hard deny and user deny do not drop siblings. Hard deny does not emit `tool_denied`.
- Why this priority: Feature 1 already overlapping-executes batches; stdin must stay single-threaded; mixed deny/ask/allow in one message is the Session 03 proof.
- Independent Test: Fake provider returns LOW + hard-denied HIGH + user-denied MEDIUM + approved MEDIUM + project-allowed repeat in one message.
- Acceptance Scenarios:
  1. Given listed calls A (hard deny) then B (ask, approved with `1`), When the batch finishes, Then A’s handler never ran, B ran, history is A then B, and authorize was not called for A.
  2. Given listed calls where one is user-denied, When the batch finishes, Then `tool_denied` is emitted only for that call and other calls still have results.
  3. Given mixed hard deny and user deny, When events are inspected, Then only user deny emits `tool_denied`; hard deny is a tool-error result without `tool_denied`.
  4. Given listed calls A then B with the same tool + primary argument, When the user answers `2` for A, Then B does not prompt and is allowed.

### User Story 5 - Project always-allow / always-deny for a pattern (Priority: P1) 🎯 MVP
- Description: Answer `2` records an allow rule and `4` a deny rule for this tool + primary-argument pattern in `.cda/.permission_rules/rules.json`. Later matching MEDIUM/HIGH calls in any session of this project skip the prompt. User edits of that file are honored on the next gated call. Hard deny still wins. Session JSON is unchanged.
- Why this priority: Adopter change request: one-shot Yes/No is not enough; Claude Code-shaped “don't ask again” plus an editable project rules file, not per-conversation memory.
- Independent Test: `QueryEngine.turn` writes/reads `.cda/.permission_rules/rules.json` in cwd; a second engine with a different session id in the same cwd reuses the file; session JSON has no permission fields.
- Acceptance Scenarios:
  1. Given a non-hard-denied `bash` `echo ping`, When the user answers `2`, Then this call runs and `.cda/.permission_rules/rules.json` contains an allow rule for `bash` + `command=echo ping`.
  2. Given that rules file, When a new QueryEngine (same or different session id) in the same cwd requests the same `bash` command, Then authorize is not called and the handler may run.
  3. Given the user answers `4` for `write_file` `notes.txt`, When a later matching `write_file` to `notes.txt` (any `content`) is requested, Then authorize is not called, `tool_denied` is emitted, and the file is not written.
  4. Given the user answers `1` or `3`, When the turn finishes, Then `.cda/.permission_rules/rules.json` is not created or does not gain a rule for that tool + pattern.
  5. Given the user edits `.cda/.permission_rules/rules.json` to add an allow rule for `web_fetch` + a URL, When the next gated `web_fetch` to that URL runs, Then it skips the prompt.
  6. Given a later turn that only appends messages, When the session is saved, Then `.cda/.sessions/<id>.json` still has no permission-rule fields and `.cda/.permission_rules/rules.json` is unchanged except by `2`/`4` or user edits.

### User Story 6 - CLI data lives under `.cda` (Priority: P1) 🎯 MVP
- Description: Permission rules, session transcripts, and default secrets all sit under `.cda/` in the project cwd: `.cda/.permission_rules/rules.json`, `.cda/.sessions/<id>.json`, `.cda/.secrets/config.json`. The CLI does not write the old cwd `.permission_rules/`, `.sessions/`, or `.secrets/` locations.
- Why this priority: Adopter required one project data folder so local state is not three top-level dot-directories.
- Independent Test: Default `SessionStore` and provider config paths; QueryEngine `2` writes rules under `.cda/`; `.gitignore` lists `.cda/`.
- Acceptance Scenarios:
  1. Given default CLI settings, When a session is saved, Then the file is `.cda/.sessions/<id>.json` and cwd `.sessions/<id>.json` is not created.
  2. Given no `CONFIG_FILE`, When the provider looks up config, Then the default path is `.cda/.secrets/config.json`.
  3. Given the user answers `2`, When the turn finishes, Then the rule is in `.cda/.permission_rules/rules.json` and cwd `.permission_rules/rules.json` is not created.

## Requirements (Moderate/Complex)
- `REQ-001`: Every tool call is routed to allow, ask, or deny before the handler runs. Rationale: Session 03 “check before execute”; do not trust the model. Priority: Must. Validation: `QueryEngine.turn`, `invoke`. Linked story: US1, US2, US3, US5.
- `REQ-002`: Allow = registered LOW tools that are not otherwise hard-denied. No authorize prompt. Priority: Must. Linked story: US2.
- `REQ-003`: Ask = registered MEDIUM or HIGH tools that are not hard-denied and have no matching project permission rule. The user must allow this call (`1` or `2`) before the handler runs. Priority: Must. Linked story: US2, US5.
- `REQ-004`: Human and JSON authorize prompt is `Approve {name} {arguments}? [1] Yes [2] Yes, don't ask again [3] No [4] No, don't ask again:`. After trim, answers `1` and `2` allow this call; `3`, `4`, empty, `a`, `approve`, and any other string deny this call. JSON mode still uses stdin. Priority: Must. Linked story: US2.
- `REQ-005`: User deny (answer `3`/`4`/other, or a matching project deny rule) emits JSON/human event `type=tool_denied` with the tool name and arguments, records history tool error `"Tool execution denied by user."`, and does not run that handler. Priority: Must. Linked story: US2, US4, US5.
- `REQ-006`: Hard deny list applies to `bash` and `powershell` argument `command` with case-sensitive substring match against exactly: `rm -rf /`, `sudo`, `shutdown`, `reboot`, `mkfs`, `dd if=`, `> /dev/sda`. Priority: Must. Linked story: US1.
- `REQ-007`: Hard deny is not bypassable: UI Yes, “don't ask again”, `bypass_permissions=True`, and a project rules-file allow entry do not run the handler. Priority: Must. Linked story: US1, US5.
- `REQ-008`: Hard deny does not call authorize and does not emit `tool_denied`. History records a tool-error result whose error text includes `Blocked:` and the matched pattern. Priority: Must. Linked story: US1, US4.
- `REQ-009`: `repl` is not matched against the shell deny list. Priority: Must. Linked story: US1.
- `REQ-010`: MEDIUM `file_path` or `key` values that substring-match `PROTECTED_PATHS` (`.gitconfig`, `.bashrc`, `.zshrc`, `.env`, `id_rsa`) are hard-denied (same no-prompt / no-handler / not-bypassable rules as REQ-007/REQ-008, error text includes `Protected path blocked:`). Priority: Must. Linked story: US3.
- `REQ-011`: `config` SET with `key` in `PROTECTED_KEYS` (`.env`, `secret`) is hard-denied (no prompt, no set, not bypassable). `config` GET of those keys is not hard-denied by this feature. Priority: Must. Linked story: US3.
- `REQ-012`: HIGH tools that are not hard-denied still cannot run via `invoke` unless `bypass_permissions` is true (today’s HIGH contract). The turn path may set that flag only after this call is allowed (answer `1`/`2` or a matching project allow rule). Project rules are not consulted by bare `invoke`. Priority: Must. Linked story: US2, US5.
- `REQ-013`: For one assistant message, hard-deny then project-rule match then ask decisions run sequentially in listed order before overlapping execution of allowed calls. A `2`/`4` answer applies to later listed siblings in that same walk. Priority: Must. Linked story: US4, US5.
- `REQ-014`: Hard deny or user deny of one listed call does not skip remaining listed calls. Results stay listed order. Priority: Must. Linked story: US4.
- `REQ-015`: Deny-list patterns, protected path/key sets, project permission rules, authorize, and HIGH `bypass_permissions` are consulted on the live paths that own them (`QueryEngine.turn` for project rules and authorize; `invoke` and `QueryEngine.turn` for hard deny). This feature must not add permission lists, flags, or functions that are never consulted by those paths, and must not add permission fields to session JSON. Priority: Must. Linked story: US1–US5.
- `REQ-016`: A project permission rule matches when the tool name equals `tool` and the call’s primary-argument fields equal `pattern` (exact string equality per field). Primary fields: `bash`/`powershell` → `command`; `write_file`/`edit_file` → `file_path`; `config` → `action` and `key`; `web_fetch` → `url`; `repl` → `code`; any other MEDIUM/HIGH tool → the full argument map. Priority: Must. Linked story: US5.
- `REQ-017`: Answer `2` writes an allow rule and answer `4` writes a deny rule for that tool + pattern into `.cda/.permission_rules/rules.json` before the turn returns (creating the directory and file if needed). Answer `1` or `3` does not write a rule. At most one rule per tool + pattern; a new `2`/`4` for the same pair replaces the previous decision. Priority: Must. Linked story: US5.
- `REQ-018`: Project rules live only at `.cda/.permission_rules/rules.json` under process cwd. The file is a JSON array of `{"tool": "<name>", "pattern": {<primary fields>}, "decision": "allow"|"deny"}`. Missing file means no rules. The file is the source of truth: user edits apply on the next gated call. Invalid entries (missing `tool`, `pattern` not an object, `decision` not `allow` or `deny`) are skipped; an unreadable or non-array file is treated as no rules (calls still ask, process does not crash). Duplicate matching rules: the last valid entry in the array wins. Every session id in that cwd shares this file. `.cda/.sessions/<id>.json` must not contain permission-rule fields. Priority: Must. Linked story: US5, US6.
- `REQ-019`: Project permission rules are consulted only for MEDIUM/HIGH calls that are not hard-denied. LOW calls and hard-denied calls ignore matching JSON rules (hard deny still wins; LOW still runs without a prompt). Priority: Must. Linked story: US1, US2, US5.
- `REQ-020`: Process-cwd `.cda/` is the only default local-data root. Defaults are `.cda/.permission_rules/rules.json`, `.cda/.sessions/<id>.json`, and `.cda/.secrets/config.json`. The CLI does not read or write cwd `.permission_rules/`, `.sessions/`, or `.secrets/` when using defaults. `CONFIG_FILE` still overrides the config path. Missing default config still exits `2`; the error text names `.cda/.secrets/config.json`. Priority: Must. Linked story: US6.
- `REQ-021`: `.gitignore` lists `.cda/` so sessions, secrets, and permission rules under it are not committed. Priority: Must. Linked story: US6. No unused path constants: default session, secret, and rules locations are the `.cda/` paths actually consulted.

## Acceptance Criteria
- `AC-001`: Given `invoke("bash", command="sudo rm -rf /tmp/x", bypass_permissions=True)`, When it returns, Then `status` is `error`, the error text includes `Blocked:` and `sudo`, and no subprocess for that command is started. Covers REQ-006, REQ-007, REQ-015. Proof: `python3 tests/tools_check.py`.
- `AC-002`: Given `invoke("powershell", command="shutdown /s", bypass_permissions=True)`, When it returns, Then `status` is `error` and the error text includes `Blocked:` and `shutdown`. Covers REQ-006, REQ-007. Proof: `python3 tests/tools_check.py`.
- `AC-003`: Given `invoke("bash", command="echo ping", bypass_permissions=True)`, When it returns, Then it is not a deny-list error (Feature 1 in-cwd bash still succeeds). Covers REQ-006. Proof: `python3 tests/tools_check.py`.
- `AC-004`: Given `invoke("bash", command="echo ping")` with no `bypass_permissions`, When it returns, Then `status` is `error` and the error text includes `Permission denied for high-risk tool`. Covers REQ-012. Proof: `python3 tests/tools_check.py`.
- `AC-005`: Given `invoke("repl", code="sudo = 1", bypass_permissions=True)`, When it returns, Then it is not blocked by the shell deny list solely because `sudo` appears in `code`. Covers REQ-009. Proof: `python3 tests/tools_check.py`.
- `AC-006`: Given `invoke("write_file", file_path=".env", content="x")` (or any `file_path` containing `.env`), When it returns, Then `status` is `error`, the error text includes `Protected path blocked:`, and the file is not written. Covers REQ-010. Proof: `python3 tests/tools_check.py`.
- `AC-007`: Given `invoke("config", action="set", key="secret", value="n")`, When it returns, Then `status` is `error` and the protected key is not set. Covers REQ-011. Proof: `python3 tests/tools_check.py`.
- `AC-008`: Given `QueryEngine.turn` with one `bash` tool call `command="sudo id"` and an authorize callback that records calls, When the turn finishes, Then authorize was not called, no `tool_denied` event was emitted, the tool result is an error containing `Blocked:` and `sudo`, and the handler did not run. Covers REQ-001, REQ-007, REQ-008, REQ-015. Proof: `python3 tests/query_engine_check.py`.
- `AC-009`: Given `QueryEngine.turn` with one `read_file` call and an authorize callback that records calls, When the turn finishes, Then authorize was not called and a tool result is present (success or file error, not permission deny). Covers REQ-002. Proof: `python3 tests/query_engine_check.py`.
- `AC-010`: Given `QueryEngine.turn` with one non-deny-listed `bash` call and authorize allowing this call without recording a project rule (answer `1`), When the turn finishes, Then the handler ran (or returned a non-permission tool error). Covers REQ-003, REQ-012. Proof: `python3 tests/query_engine_check.py`.
- `AC-011`: Given `QueryEngine.turn` with one non-deny-listed MEDIUM or HIGH call and authorize denying this call without recording a project rule (answer `3` or other), When the turn finishes, Then events include `tool_denied`, history error is `"Tool execution denied by user."`, and the handler did not run. Covers REQ-005. Proof: `python3 tests/query_engine_check.py`.
- `AC-012`: Given `TerminalUI.authorize`, When the input is `1` or `2` (surrounding whitespace allowed), Then this call is allowed; when the input is `3`, `4`, empty, `a`, `approve`, or any other string, Then this call is denied. Prompt text includes `[1]`, `[2]`, `[3]`, `[4]`, `Yes`, `No`, and `don't ask again`. Covers REQ-004. Proof: `python3 tests/terminal_ui_check.py`.
- `AC-013`: Given one assistant message listing call A = deny-listed `bash` then call B = LOW `read_file`, When the batch finishes, Then history has A’s blocked error then B’s result, authorize was not called for A, and B still has a result. Covers REQ-013, REQ-014. Proof: `python3 tests/query_engine_check.py`.
- `AC-014`: Given one assistant message listing a user-denied MEDIUM call and an approved or LOW sibling, When the batch finishes, Then `tool_denied` is emitted only for the user-denied call and the sibling still has a result. Covers REQ-005, REQ-014. Proof: `python3 tests/query_engine_check.py`.
- `AC-015`: Given `QueryEngine.turn` with `write_file` `file_path` containing `id_rsa` and an authorize recorder, When the turn finishes, Then authorize was not called and no file was written. Covers REQ-010, REQ-008. Proof: `python3 tests/query_engine_check.py`.
- `AC-016`: Given `QueryEngine.turn` with `config` SET `key=secret` and an authorize recorder, When the turn finishes, Then authorize was not called and the key was not set. Covers REQ-011. Proof: `python3 tests/query_engine_check.py`.
- `AC-017`: Given the seven deny-list patterns in REQ-006, When each is used as a substring inside an otherwise different `bash` `command` via `invoke(..., bypass_permissions=True)`, Then each call is blocked. Covers REQ-006, REQ-015. Proof: `python3 tests/tools_check.py`.
- `AC-018`: Given `QueryEngine.turn` with `bash` `command="echo ping"` and the user answering `2`, When the turn finishes, Then the handler ran (or a non-permission tool error), `.cda/.permission_rules/rules.json` is a JSON array containing `{"tool": "bash", "pattern": {"command": "echo ping"}, "decision": "allow"}`, and the session JSON has no permission-rule fields. Covers REQ-016, REQ-017, REQ-018, REQ-015. Proof: `python3 tests/query_engine_check.py`.
- `AC-019`: Given `.cda/.permission_rules/rules.json` with that allow rule, When a new `QueryEngine` with a **different** session id in the same cwd `turn`s the same `bash` command, Then authorize is not called and the handler may run. Covers REQ-003, REQ-012, REQ-018. Proof: `python3 tests/query_engine_check.py`.
- `AC-020`: Given the user answers `4` for `write_file` with `file_path="notes.txt"`, When a later `write_file` with the same `file_path` and different `content` is requested in a following turn, Then authorize is not called, `tool_denied` is emitted, history error is `"Tool execution denied by user."`, and the file is not written. Covers REQ-005, REQ-016, REQ-017, REQ-019. Proof: `python3 tests/query_engine_check.py`.
- `AC-021`: Given the user answers `1` for a non-deny-listed MEDIUM/HIGH call and no rules file exists yet, When the turn finishes, Then `.cda/.permission_rules/rules.json` does not exist. Covers REQ-017. Proof: `python3 tests/query_engine_check.py`.
- `AC-022`: Given one assistant message listing two `bash` calls with the same `command` (not deny-listed), When the user answers `2` for the first, Then authorize is called once, both handlers may run, and `.cda/.permission_rules/rules.json` has one allow rule for that command. Covers REQ-013, REQ-017. Proof: `python3 tests/query_engine_check.py`.
- `AC-023`: Given `.cda/.permission_rules/rules.json` with an allow entry for `bash` `command="sudo id"`, When `QueryEngine.turn` requests that call, Then the result is still hard deny (`Blocked:` + `sudo`), authorize is not called, and the handler does not run. Covers REQ-007, REQ-019. Proof: `python3 tests/query_engine_check.py`.
- `AC-024`: Given no `.cda/.permission_rules/rules.json` and a `messages`-only session file, When the session is loaded, Then history loads and matching MEDIUM/HIGH calls still prompt. Covers REQ-018. Proof: `python3 tests/session_check.py`.
- `AC-025`: Given `.cda/.permission_rules/rules.json` with a valid allow rule for `web_fetch` + `url` and an invalid entry (`decision` not `allow`/`deny`), When `QueryEngine.turn` requests that `web_fetch`, Then authorize is not called and the invalid entry did not crash the turn. Covers REQ-018. Proof: `python3 tests/query_engine_check.py`.
- `AC-026`: Given `.cda/.permission_rules/rules.json` already has rules, When a later turn appends only messages and the session is saved, Then the session JSON still has no permission-rule fields and the rules file still has the same decisions. Covers REQ-018. Proof: `python3 tests/session_check.py`.
- `AC-027`: Given `SessionStore()` with no directory argument (or the CLI default store) in a temp cwd, When a session is saved, Then the file exists at `.cda/.sessions/<id>.json` and `.sessions/<id>.json` does not exist in that cwd. Covers REQ-020. Proof: `python3 tests/session_check.py`.
- `AC-028`: Given no `CONFIG_FILE` env and no env provider settings, When provider init fails for missing config, Then the error text includes `.cda/.secrets/config.json` and does not require cwd `.secrets/config.json`. Covers REQ-020. Proof: `python3 tests/provider_check.py`.
- `AC-029`: Given `QueryEngine.turn` answering `2` for a non-deny-listed `bash` command in a temp cwd, When the turn finishes, Then `.cda/.permission_rules/rules.json` exists and cwd `.permission_rules/rules.json` does not. Covers REQ-017, REQ-020. Proof: `python3 tests/query_engine_check.py`.
- `AC-030`: Given `.gitignore` at the repository root, When it is read, Then it contains a `.cda/` ignore entry. Covers REQ-021. Proof: `python3 tests/cli_check.py`.

## Success Criteria (Measurable Outcomes)
- `SC-001`: In one REPL session a user can read a workspace file without a prompt, answer `2` for a normal `echo` bash call and not be asked again for that command, answer `4` for a `write_file` and not be asked again for that path, and never be asked to approve `sudo` or `rm -rf /` — those never run.
- `SC-002`: `--json` consumers still parse existing event types; user deny and project deny remain `tool_denied`; hard deny appears as an error `tool_result` without a new event type.
- `SC-003`: Disconnecting the deny list, protected lists, or `.cda/.permission_rules/rules.json` load/consult from the live gate makes AC-001, AC-008, AC-015, AC-017, AC-018, or AC-019 fail (no silent unused permission tables; no unused session-JSON permission fields).
- `SC-004`: After answering `2` or `4`, the user can edit `.cda/.permission_rules/rules.json` and have the next gated call in this project honor it — including a new CLI process or a different `--session` id — except hard-denied calls stay blocked.
- `SC-005`: After a normal REPL run, the only new project-local CLI directories under cwd are inside `.cda/`; cwd `.sessions/`, `.secrets/`, and `.permission_rules/` are unused.

## Constraints and Risk
- Constraints:
  - App remains Python 3.11+ stdlib-first; no pytest requirement. Linked ACs: AC-001–AC-030.
  - NFR-001 Hard deny is not bypassable, including by project rules-file allow entries. Linked ACs: AC-001, AC-002, AC-008, AC-017, AC-023.
  - NFR-002 No dead permission code: every deny-list pattern, protected token, and project permission-rule field in this spec is observed by the live gate (`invoke` and/or `QueryEngine.turn` + `.cda/.permission_rules/rules.json`). Session JSON has no unused permission keys. Linked ACs: AC-001, AC-008, AC-015, AC-017, AC-018, AC-019, AC-026.
  - NFR-003 JSON event types stay the Feature 1 set; hard deny and project-rule hits do not require a new type. Linked ACs: AC-008, AC-011, AC-014, AC-020.
  - NFR-004 Sequential gates before overlapping execute; stdin is not concurrent. Linked ACs: AC-013, AC-014, AC-022.
  - NFR-005 Feature 1 workspace bound and extra tools unchanged. Linked ACs: AC-003, AC-009.
  - NFR-006 `.cda/.permission_rules/rules.json` is user-editable; session files stay messages-only under `.cda/.sessions/`; default secrets path is `.cda/.secrets/config.json`; `api_key`/`authorization` key redaction is unchanged. Linked ACs: AC-018, AC-019, AC-024, AC-025, AC-026, AC-027, AC-028, AC-029.
  - NFR-007 `.cda/` is gitignored so local sessions, secrets, and rules are not committed. Linked ACs: AC-030.
  - Verification gates remain `[DEFERRED]`; proof commands are the unittest scripts on each AC.
- Dependencies/touchpoints: `QueryEngine.turn` authorize walk, `invoke` / `check_permission`, `TerminalUI.authorize`, `.cda/.permission_rules/rules.json`, `.cda/.sessions/`, `.cda/.secrets/config.json`, `PROTECTED_PATHS` / `PROTECTED_KEYS`, shell handlers, `.gitignore`, existing `tests/*_check.py`. SessionStore stays transcript-only.
- Risks and mitigations:
  - Substring deny list is bypassable (`sudo` vs `SuDo`, `rm -rf /` vs `rm -rf /*`). Mitigation: accepted teaching-demo weakness; AST is an explicit non-goal.
  - `sudo` as a substring can block benign commands that mention the token. Mitigation: accepted for this slice; list is exact and short.
  - Skipping authorize for hard deny changes today’s “ask then fail” protected-path UX. Mitigation: locked as Claude Code-shaped deny-before-ask; ACs require no prompt.
  - User-edited project rules can always-allow non-hard-denied HIGH commands for every session in that cwd. Mitigation: hard deny still wins; YOLO of unmatched patterns remains out of scope.
  - Exact primary-argument match means `echo ping` always-allow does not cover `echo pong`. Mitigation: accepted with Q1; user can add more rules in the file.
  - Moving default config from `.secrets/config.json` to `.cda/.secrets/config.json` breaks an existing how-to-run path with no auto-migration. Mitigation: `CONFIG_FILE` still overrides; missing-config error names the new path.
- Open questions (blocking only): none.

## Decisions
- Locked decisions:
  - Hybrid C / Claude Code-shaped router: deny / ask / allow. Always-ask MEDIUM/HIGH that are not hard-denied and have no matching project rule. Hard deny never executes and is not bypassable (including a rules-file allow).
  - Session 03 sources are in-scope references for this feature only.
  - Non-goals: permission modes, AST, YOLO of unmatched patterns, CC passthrough/eight sources, bash cwd jail, Session 04 hooks, permission fields on session JSON, project rules on bare `invoke`.
  - Prompt is numbered `1`–`4` (Claude Code-shaped Yes / don't ask again / No / don't ask again), including JSON stdin. Prior Q3 one-shot `[A]pprove/[D]eny` is superseded.
  - Rule grain: tool name + primary argument (Q1). Always-deny is user deny, not hard deny (Q3). Rules persist in `.cda/.permission_rules/rules.json`. Shared by all session ids in that cwd. User-editable; file is source of truth for the next gated call.
  - CLI local data root is `.cda/` (this change request): `.cda/.permission_rules/`, `.cda/.sessions/`, `.cda/.secrets/`. Feature 1 cwd `.sessions/` and `.secrets/` defaults are superseded. No dual-read/write. `.cda/` is gitignored.
  - Deny list: the seven teaching substrings on `bash` and `powershell` `command` only; not `repl`.
  - Hard deny before project-rule match before ask; no `tool_denied` for hard deny; error text `Blocked:` + matched pattern.
  - Protected paths/keys are hard deny (skip prompt).
  - Live path only; no unused permission code; no unused session-JSON permission fields.
- Related `ADR-*`: none.
