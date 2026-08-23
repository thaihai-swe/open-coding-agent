# Verification Review: 2-permission-gate

## Metadata

- Feature slug: `2-permission-gate`
- Date: 2026-08-23
- Skill: `harness-verify`
- Status: `Verifying` -> `Done` (on closeout)

## Decision

- Decision: **Pass with Follow-Up Debt**
- Release recommendation: Release to adopter. Pure stdlib Python 3.11+ implementation; live gate path enforces hard deny before project rules before numbered ask; data defaults consolidated under `.cda/`.
- Short summary: All 30 acceptance criteria are covered by fresh unittest evidence across 9 completed tasks (T-001 through T-009). Fresh test execution shows 81/81 tests passing (`tools_check.py` 20/20, `terminal_ui_check.py` 17/17, `query_engine_check.py` 26/26, `session_check.py` 4/4, `provider_check.py` 9/9, `cli_check.py` 5/5, and `python3 -m unittest discover` 81/81 OK). Mechanical `verify` and `artifact-check --trace` pass traceability. Project verification gates remain deferred in `harness-config.yaml` (0 configured; advisory mode), matching Feature 1 closeout protocol with an audited verification override. Advisory memory sync debt is recorded for promotion via `/context-memory`.

## Findings

- Finding ID: STD-01
  - Severity: Low
  - Area: Memory / doc sync debt in repo core policies.
  - Evidence: `corebase-specharness/memories/repo/core-policies.md` §Security Policy still references `.secrets/config.json` (as not gitignored) and `src/tools/handlers/settings.py` having a handler-level raise, plus interactive approve/deny instead of numbered 1-4 prompt.
  - Why it matters: Post-feature, secret config default moved to `.cda/.secrets/config.json`, `.cda/` is gitignored, protected-key checks live exclusively in `hard_deny_reason`, and prompt uses `[1] Yes [2] Yes, don't ask again [3] No [4] No, don't ask again:`.
  - Recommended action: Promote corrections via `/context-memory` (candidate MEM-01 in `session-extracts.md`).

No other findings on either axis. No High or Medium findings.

## Evidence Review

- Fresh automated evidence reviewed:
  - `python3 tests/tools_check.py` -> 20 tests OK (covers AC-001..007, AC-017; deny-list substrings, HIGH bypass checks, protected path/keys).
  - `python3 tests/terminal_ui_check.py` -> 17 tests OK (covers AC-012; numbered 1-4 prompt, trim, allow/deny mapping).
  - `python3 tests/query_engine_check.py` -> 26 tests OK (covers AC-008..011, AC-013..016, AC-018..023, AC-025, AC-029; hard-deny turn skip, rule match/upsert, sibling isolation).
  - `python3 tests/session_check.py` -> 4 tests OK (covers AC-024, AC-026, AC-027; default `.cda/.sessions/`, transcript-only JSON).
  - `python3 tests/provider_check.py` -> 9 tests OK (covers AC-028; default config `.cda/.secrets/config.json` error reporting).
  - `python3 tests/cli_check.py` -> 5 tests OK (covers AC-030; `.gitignore` contains `.cda/`).
  - `python3 -m compileall -q src` -> exit 0.
  - `python3 -m unittest discover -s tests -p '*_check.py'` -> 81 tests OK.
- Fresh manual evidence reviewed: None required. Every AC specifies executable unittest verification.
- Stale or missing evidence: None.

## AC-to-Proof Mapping

| AC-ID | Task-ID | Proof evidence | Pass/Fail |
|---|---|---|---|
| AC-001 | T-001, T-009 | `tests/tools_check.py` `test_bash_sudo_hard_denied_with_bypass_and_no_subprocess` OK | Pass |
| AC-002 | T-001, T-009 | `tests/tools_check.py` `test_powershell_shutdown_hard_denied` OK | Pass |
| AC-003 | T-001, T-009 | `tests/tools_check.py` `test_bash_non_deny_with_bypass_succeeds` OK | Pass |
| AC-004 | T-001, T-009 | `tests/tools_check.py` `test_bash_without_bypass_permission_denied` OK | Pass |
| AC-005 | T-001, T-009 | `tests/tools_check.py` `test_repl_code_with_sudo_not_deny_listed` OK | Pass |
| AC-006 | T-002, T-009 | `tests/tools_check.py` `test_write_file_env_hard_denied_not_written` OK | Pass |
| AC-007 | T-002, T-009 | `tests/tools_check.py` `test_config_set_protected_key_hard_denied`, `test_config_get_protected_key_not_hard_denied`, `test_config_set_protected_path_key_hard_denied` OK | Pass |
| AC-008 | T-003, T-009 | `tests/query_engine_check.py` `test_hard_denied_bash_skips_authorize_and_handler` OK | Pass |
| AC-009 | T-003, T-009 | `tests/query_engine_check.py` `test_low_read_file_does_not_authorize` OK | Pass |
| AC-010 | T-005, T-009 | `tests/query_engine_check.py` `test_ac010_bash_allowed_once_runs_handler_with_bypass` OK | Pass |
| AC-011 | T-005, T-009 | `tests/query_engine_check.py` `test_denied_tool_execution_turn`, `test_denied_call_does_not_run_but_siblings_do` OK | Pass |
| AC-012 | T-005, T-009 | `tests/terminal_ui_check.py` `test_authorization_prompt` OK | Pass |
| AC-013 | T-003, T-009 | `tests/query_engine_check.py` `test_hard_deny_then_low_sibling_keeps_order` OK | Pass |
| AC-014 | T-005, T-009 | `tests/query_engine_check.py` `test_denied_call_does_not_run_but_siblings_do` OK | Pass |
| AC-015 | T-004, T-009 | `tests/query_engine_check.py` `test_write_file_id_rsa_hard_denied_on_turn` OK | Pass |
| AC-016 | T-004, T-009 | `tests/query_engine_check.py` `test_config_set_secret_hard_denied_on_turn` OK | Pass |
| AC-017 | T-001, T-009 | `tests/tools_check.py` `test_all_seven_deny_list_patterns_blocked` OK | Pass |
| AC-018 | T-006, T-009 | `tests/query_engine_check.py` `test_ac018_answer_2_persists_rule_and_runs_handler` OK | Pass |
| AC-019 | T-006, T-009 | `tests/query_engine_check.py` `test_ac019_different_session_uses_persisted_rule_without_ask` OK | Pass |
| AC-020 | T-006, T-009 | `tests/query_engine_check.py` `test_ac020_answer_4_persists_deny_and_blocks_later_call_without_ask` OK | Pass |
| AC-021 | T-006, T-009 | `tests/query_engine_check.py` `test_ac021_answer_1_does_not_create_rules_file` OK | Pass |
| AC-022 | T-006, T-009 | `tests/query_engine_check.py` `test_ac022_sibling_same_command_prompts_once_on_answer_2` OK | Pass |
| AC-023 | T-006, T-009 | `tests/query_engine_check.py` `test_ac023_rules_file_allow_cannot_override_deny_listed_sudo` OK | Pass |
| AC-024 | T-007, T-009 | `tests/session_check.py` `test_messages_only_session_without_rules_still_prompts` OK | Pass |
| AC-025 | T-006, T-009 | `tests/query_engine_check.py` `test_ac025_invalid_rule_entry_skipped_and_valid_rule_matches` OK | Pass |
| AC-026 | T-007, T-009 | `tests/session_check.py` `test_later_save_does_not_add_permission_fields_or_change_rules` OK | Pass |
| AC-027 | T-007, T-009 | `tests/session_check.py` `test_default_store_writes_under_cda_sessions` OK | Pass |
| AC-028 | T-008, T-009 | `tests/provider_check.py` `test_ac028_missing_default_config_error_names_cda_secrets_path` OK | Pass |
| AC-029 | T-006, T-009 | `tests/query_engine_check.py` `test_ac029_rule_persists_under_dot_cda_not_cwd_root` OK | Pass |
| AC-030 | T-008, T-009 | `tests/cli_check.py` `test_ac030_gitignore_contains_cda_entry` OK | Pass |

Zero unmapped ACs. Zero-tolerance alignment rule satisfied.

## Design Conformance

| Design element | Evidence location | Pass/Fail |
|---|---|---|
| `hard_deny_reason(tool, kwargs)` in `src/tools/permissions.py` | `src/tools/permissions.py:13` | Pass |
| `check_permission` consults `hard_deny_reason` before HIGH bypass | `src/tools/permissions.py:38` | Pass |
| `AuthorizeDecision(allow, persist)` frozen dataclass | `src/tools/permissions.py:7` | Pass |
| Numbered `1`–`4` prompt on `TerminalUI.authorize` | `src/presentation/terminal_ui.py:171` | Pass |
| `src/tools/permission_rules.py` module functions (`load_rules`, `match_rule`, `upsert_rule`, `primary_pattern`) | `src/tools/permission_rules.py:1` | Pass |
| Turn-path evaluation order: `hard_deny_reason` -> `match_rule` -> `authorize` -> `upsert_rule` | `src/application/query_engine.py:77-98` | Pass |
| Bare `invoke` does not import `permission_rules` | `src/tools/__init__.py` (verified no import) | Pass |
| `SessionStore` default directory `.cda/.sessions` | `src/infrastructure/session_store.py:12` | Pass |
| `OpenAIProvider` default config `.cda/.secrets/config.json` & error message | `src/infrastructure/providers/openai.py:21, 93` | Pass |
| `.gitignore` contains `.cda/` | `.gitignore:225` | Pass |
| `documents/how-to-run.md` updated with `.cda/.secrets/config.json` | `documents/how-to-run.md:19-24` | Pass |
| Live path only; dead `PROTECTED_KEYS` check removed from handler | `src/tools/handlers/settings.py` (no redundant raise) | Pass |

## Security Audit

- Findings: None.
- Evidence:
  - Hard deny list on `bash`/`powershell` (`sudo`, `rm -rf /`, `shutdown`, `reboot`, `mkfs`, `dd if=`, `> /dev/sda`) cannot be overridden by user prompt approval or persisted rules file.
  - Protected paths/keys (`.env`, `id_rsa`, `.gitconfig`, `.bashrc`, `.zshrc`, `secret`) are hard-denied before UI prompt and before handler execution.
  - `.cda/` (containing sessions, rules, and secrets) is added to `.gitignore`.
  - Session transcript JSON contains only `{"messages": [...]}` with API key and Authorization header redaction intact.
- Result: **Pass**

## Dropped Behavior

- Behavior reviewed:
  - Previous `[A]pprove/[D]eny` UI prompt (`a`/`approve` inputs) replaced by numbered `1`–`4` prompt (`[1] Yes [2] Yes, don't ask again [3] No [4] No, don't ask again:`).
  - Default session directory changed from `.sessions/` to `.cda/.sessions/`.
  - Default provider config path changed from `.secrets/config.json` to `.cda/.secrets/config.json`.
  - Redundant handler-level `PROTECTED_KEYS` raise removed from `settings.py` (handled upstream in `hard_deny_reason`).
- Result: **Accepted** (all changes explicitly required by `spec.md` and `plan.md`).
- Evidence: `spec.md` REQ-004, REQ-020, REQ-021; `plan.md` decisions 1, 2, 4.

## Standards Review

Procedure-only. Audit the diff against repo standards and the smell baseline.

Report:
- Standards findings: None.
  - Changes adhere to layer boundaries (`TerminalUI` does not import tool handlers; bare `invoke` does not import `permission_rules`).
  - No new external runtime dependencies added (stdlib only).
  - No dead code or placeholder comments introduced.
- Smell findings (judgement calls, cite hunk):
  - Primitive Obsession: Avoided by introducing `AuthorizeDecision` dataclass instead of multi-value primitive returns.
  - Duplicated Code: `hard_deny_reason` centralized between `check_permission` and `QueryEngine._run_batch` to prevent duplicate tables.
  - Speculative Generality: None. No unused router abstractions or multi-mode systems created.
- Result: **Pass**

## Spec Alignment Review

Procedure-only. Audit the diff line-by-line against `spec.md`.

Report:
- Missing or partial acceptance criteria: None. All 30 ACs implemented and verified with passing unit tests.
- Unrequested behavior (scope creep): None. No AST parsing, no permission modes, no auto-migration logic.
- Requirements that look implemented but the implementation looks wrong: None. Rule matching uses exact tool and primary pattern comparison; last-wins order is respected; invalid entries are skipped; hard deny takes precedence over rules.
- Result: **Pass**

## Drift Review

- Drift detected: **No**
- Drift summary: Implementation exactly mirrors `spec.md` and `plan.md`.
- Return-to-spec required: **No**

## Risk Review

- Security or privacy notes: Substring matching for deny-list and protected paths is a documented baseline heuristic. Attack surface reduced by moving local data under `.cda/` and adding to `.gitignore`.
- Regression risk: Very low. All 81 tests across all test suites pass fresh.
- Operational or observability risk: None. Standard error output and tool result events remain compatible with existing CLI and `--json` contracts.

## Provider Review

- Provider command: `verify --skill harness-verify` (advisory mode; no OCR binary configured)
- Provider status: deferred (not configured; mode optional per `harness-config.yaml`)
- Provider findings summary: n/a — no `open-code-review` binary configured in project setup; deferred status per harness specification.

## Capabilities Used / Deferred

- Used optional helpers: None
- Deferred optional helpers: `open-code-review` (OCR)
- Why deferred: Not configured in `harness-config.yaml`; manual two-axis review completed.

## Post-Ship Sync

### Candidate memories for /context-memory

- MEM-01 [PROMOTE]: `corebase-specharness/memories/repo/core-policies.md` §Security Policy is stale. Update default paths to `.cda/.secrets/config.json`, note `.cda/` is gitignored, reference `hard_deny_reason` for `PROTECTED_KEYS` / `PROTECTED_PATHS` / `DENY_LIST`, and note the numbered 1-4 authorize prompt.
- MEM-02 [PROMOTE]: Permission rules persist in `.cda/.permission_rules/rules.json` and are evaluated on the `QueryEngine.turn` path only; bare `src.tools.invoke` does not import or consult `permission_rules.py`.
- MEM-03 [PROMOTE]: `TerminalUI.authorize` returns `AuthorizeDecision(allow, persist)`. Numbered input `1` (allow once), `2` (allow persist), `4` (deny persist), and all other inputs (`3`, empty, strings) evaluate to deny without persistence.

## Follow-Up

- Reopened tasks: None
- Deferred work: Memory sync of candidate memories via `/context-memory`.
- Next required action: Run `/context-memory` to promote post-ship memory candidates.
