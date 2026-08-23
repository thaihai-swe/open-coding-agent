# Verification Review: 1-tool-and-execution

## Metadata
- Feature slug: `1-tool-and-execution`
- Date: 2026-08-22
- Skill: `harness-verify`
- Phase: `Verifying` -> `Done` (on closeout)

## Decision
- Decision: **Pass with Follow-Up Debt**
- Release recommendation: Release to adopter. Brownfield, stdlib-only (3.11+). No public breakages to dispatch/registry/CLI contract; only an additive `glob` schema entry.
- Short summary: All 23 acceptance criteria are covered by fresh unittest proof across 9 `Done` tasks. Fresh evidence: `tools_check.py` 10/10, `query_engine_check.py` 12/12, `terminal_ui_check.py` 12/12, `cli_check.py` 4/4, `compileall` exit 0, `unittest discover` 47/47 OK. Mechanical `verify` + `artifact-check --trace` pass. Gates remain `[DEFERRED]` (0 configured; advisory mode) per repo policy, so this run closes with a deliberate verification override; `## Post-Ship Sync` in `session-extracts.md` is the required precondition before `skill-exit` to `Done`. Two Low advisory debts recorded below; neither breaks an AC.

## Findings

- Finding ID: STD-01
  - Severity: Low
  - Area: Observable contract drift on glob_search / grep_search result path form.
  - Evidence: src/tools/handlers/search.py diff — bound_path(path) then glob.glob(os.path.join(str(root), pattern)) operates from the resolved absolute cwd, so returned match strings are now absolute paths instead of ./ prefixed relative ones. grep_search similarly walks str(root).
  - Why it matters: spec.md locks that contracts stay the same except the path bound and the glob alias. Absolute vs relative is a form change beyond that exception. No AC breaks (match set identical for in-cwd patterns AC-002/AC-007; no outside content returned AC-006).
  - Recommended action: Accept as documented debt this slice. If a consumer needs the old ./ form, relativize returns against cwd inside glob_search/grep_search only.

- Finding ID: STD-02
  - Area: Memory / doc sync debt.
  - Severity: Low
  - Evidence: corebase-specharness/memories/repo/core-policies.md still describes src/tools/handlers/file_io.py as having no workspace jail.
  - Why it matters: Post-feature this is stale; file/search handlers are now bound via src/tools/workspace.py bound_path.
  - Recommended action: Promote correction via /context-memory (Post-Ship Sync candidate MEM-01 below). Not edited in this review to keep harness-verify scoped to verification artifacts.

No other findings. No High or Medium findings on either axis.

## Evidence Review

- Fresh automated evidence reviewed in this turn: python3 tests/tools_check.py -v => 10 tests OK; python3 tests/query_engine_check.py -v => 12 tests OK; python3 tests/terminal_ui_check.py -v => 12 tests OK; python3 tests/cli_check.py -v => 4 tests OK; python3 -m compileall -q src exit 0; python3 -m unittest discover -s tests -p '*_check.py' => Ran 47 tests, OK.
- Fresh manual evidence reviewed: none required. Every AC names a unittest script as its proof per spec Constraints; all were run fresh here.
- Stale or missing evidence: none.

## AC-to-Proof Mapping

| AC-ID | Task-ID | Proof evidence | Pass/Fail |
| --- | --- | --- | --- |
| AC-001 | T-001, T-009 | tools_check.py test_read_file_in_cwd OK | Pass |
| AC-002 | T-001, T-009 | tools_check.py test_glob_and_glob_search_same_matches OK | Pass |
| AC-003 | T-001, T-009 | tools_check.py test_schemas_include_glob_and_glob_search OK | Pass |
| AC-004 | T-003, T-009 | query_engine_check.py test_unknown_tool_records_error_and_continues OK | Pass |
| AC-005 | T-001, T-009 | tools_check.py test_extra_grep_search_still_registered OK | Pass |
| AC-006 | T-002, T-009 | tools_check.py test_file_and_search_refuse_parent_path + test_symlink_escape_is_refused OK | Pass |
| AC-007 | T-002, T-009 | tools_check.py test_in_cwd_paths_still_succeed OK | Pass |
| AC-008 | T-002, T-009 | tools_check.py test_bash_is_not_workspace_jailed OK | Pass |
| AC-009 | T-003, T-009 | query_engine_check.py test_batch_history_order_when_second_finishes_first OK | Pass |
| AC-010 | T-003, T-009 | query_engine_check.py test_batch_failure_does_not_skip_sibling OK | Pass |
| AC-011 | T-004, T-009 | query_engine_check.py test_denied_call_does_not_run_but_siblings_do OK | Pass |
| AC-012 | T-004, T-009 | query_engine_check.py test_authorize_is_sequential_before_overlap OK | Pass |
| AC-013 | T-003, T-009 | query_engine_check.py test_next_complete_waits_for_full_batch OK | Pass |
| AC-014 | T-005, T-009 | terminal_ui_check.py test_human_prints_plain_tool_status_and_result_lines OK | Pass |
| AC-015 | T-004, T-005, T-009 | query_engine_check.py test_status_then_tool_then_tool_result_events OK | Pass |
| AC-016 | T-005, T-009 | terminal_ui_check.py test_json_emits_additive_event_types OK | Pass |
| AC-017 | T-006, T-009 | cli_check.py test_keyboard_interrupt_saves_session_and_exits_130 OK | Pass |
| AC-018 | T-007, T-009 | terminal_ui_check.py test_period_submits_multiline OK | Pass |
| AC-019 | T-007, T-009 | terminal_ui_check.py test_empty_first_line_quits OK | Pass |
| AC-020 | T-007, T-009 | terminal_ui_check.py test_eof_submits_accumulation OK | Pass |
| AC-021 | T-008, T-009 | terminal_ui_check.py test_human_text_renders_markdown_heading_and_bold OK | Pass |
| AC-022 | T-008, T-009 | terminal_ui_check.py test_human_non_text_events_stay_plain OK | Pass |
| AC-023 | T-008, T-009 | terminal_ui_check.py test_json_text_keeps_markdown_source OK | Pass |

Zero unmapped ACs. Zero-tolerance rule satisfied.

## Design Conformance

| Design element | Evidence location | Pass/Fail |
| --- | --- | --- |
| bound_path(path, *, cwd=None) deep helper in new src/tools/workspace.py | file present; signature matches plan | Pass |
| Handlers call bound_path before IO/walk | file_io.py read/write/edit; search.py glob/grep roots | Pass |
| write_file binds before makedirs | file_io.py write_file order of operations | Pass |
| glob dual register, same schema/description/risk as glob_search, no alias map | search.py TOOLS list; registry unchanged | Pass |
| _run_batch replaces serial loop; ThreadPoolExecutor inside QueryEngine; no ToolBatchExecutor class | query_engine.py _run_batch/_invoke_call | Pass |
| Sequential authorize before pool submit; deny emits tool_denied without invoke | query_engine.py authorize walk precedes approved/pool block | Pass |
| One status event then tool-start events on main thread; tool_result events after wait in listed order; single save per batch | query_engine.py event emission + history append sequence | Pass |
| No events emitted from worker threads | only main thread calls self.on_event | Pass |
| Multiline prompt via input_fn loop; empty first line exits; solo dot submits; EOF submits | terminal_ui.py prompt() | Pass |
| Private _render_markdown, ATX + bold only, human text branch only | terminal_ui.py _render_markdown with ponytail comment | Pass |
| cli.py untouched (plan decision 6: change only if AC-017 fails) | git diff shows no change to src/presentation/cli.py | Pass |
| Dependency direction preserved (presentation -> application -> tools; workspace -> stdlib only) | imports across changed files | Pass |

## Security Audit

- Findings: none. The path-bound narrowing is the whole point of REQ-005 and has no new attack surface. bash remains unrestricted (REQ-006 explicit non-goal). No secrets or credentials touched. No new deps (stdlib only: concurrent.futures, re, pathlib). core-policies.md security-sensitive path list for file_io.py is stale (see STD-02 above); correction deferred to Post-Ship Sync via /context-memory, not this review scope.
- Evidence: grep diff for secret/auth keywords across changed files shows none. read_file, write_file, edit_file all call bound_path before IO. glob_search/grep_search filter matches before return. QueryEngine bypass_permissions for HIGH-risk tools unchanged. subprocess shell=True in shell.py (bash) is untouched.
- Result: **Pass**

## Dropped Behavior

- Behavior reviewed: _run_call private method replaced by _run_batch/_invoke_call (private scope only; QueryEngine.turn signature unchanged). SessionStore.save moves from per-call-in-loop to one-save-per-batch. glob_search/grep_search result string form changes from relative (./) to absolute paths.
- Result: **Accepted** (saves-per-batch matches the plan design decision; glob result form drift is STD-01 documented debt).
- Evidence: plan.md decision 3 specifies single save after ordered append; spec preserved-behavior clause carves out path bound changes.

## Standards Review

Procedure-only. Audit against repo standards (code-design.md, security.md, ponytail.md) and Fowler smell baseline. Repo rules override the baseline. Smells are judgement calls, never hard violations.

Report:
- Standards findings: none (CC-003 surgical scope; CC-001 fresh evidence; CC-005 failures surfaced, not suppressed).
- Smell findings (judgement calls, cite hunk):
  - Duplicated Code (adjacent): glob/grep match-filter logic (bound_path + ValueError catch or _inside_workspace) appears in both glob_search and grep_search. Extracted to _inside_workspace helper in search.py, which both use — this meets the Ponytail DRY-across-package row threshold (same pattern in two functions in one module) and is exactly the right response.
  - Speculative Generality: none. No unused parameters, no config for values that never change, no extra types.
  - All other Fowler smells (Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery): not observed in the diff.
- Result: **Pass**

## Spec Alignment Review

Procedure-only. Audit the diff line-by-line against spec.md.

Report:
- Missing or partial acceptance criteria: none. All 23 ACs mapped in the AC-to-Proof Mapping table above with fresh evidence, all Pass.
- Unrequested behavior (scope creep): glob result string form is absolute instead of relative (STD-01 above). This is the only unrequested observable change; documented as Low debt. Nothing else added beyond spec.
- Requirements that look implemented but the implementation looks wrong: none found. Key mechanics verified by reading code: authorize sequence precedes executor creation (REQ-010), deny path records result without calling invoke (REQ-010), unknown tool records error and continues (REQ-003), ThreadPoolExecutor shutdown(wait=True) happens before tool_result emission (REQ-011).
- Result: **Pass**

## Drift Review

- Drift detected: **Yes** (minor only)
- Drift summary: glob/grep result strings are absolute vs ./relative (STD-01); glob description parameterization via _GLOB_DESCRIPTION / _GLOB_SCHEMA constants (minor DRY improvement within spec scope; no functional drift). No other drift.
- Return-to-spec required: **No**

## Risk Review

- Security or privacy notes: none introduced. Path-bound narrowing reduces attack surface; no secrets or external data touched.
- Regression risk: all 47 existing+new tests pass fresh; compileall OK; no old behaviors broken; cli.py untouched.
- Operational or observability risk: glob returning absolute paths is arguably more useful for model consumption (unambiguous); no operational concern. ThreadPoolExecutor handles thread shutdown cleanly; KeyboardInterrupt during batch has no AC but prior turns are saved.

## Provider Review

- Provider command: verify --skill harness-verify (advisory mode; no OCR binary configured)
- Provider status: deferred (not configured; mode optional per harness-config.yaml)
- Provider findings summary: n/a — no open-code-review binary in this environment; not a Fail per skill rules.

## Capabilities Used / Deferred

- Used optional helpers: none of the external engineering skills
- Deferred optional helpers: open-code-review (ocr) for automated standards scan
- Why deferred: not installed; mode is optional; two-axis review covered the Standards axis manually.

## Post-Ship Sync

### Candidate memories for /context-memory

- MEM-01 [PROMOTE]: core-policies.md security-sensitive path list is stale for file_io.py. Post-feature: file/search handlers now call bound_path via src/tools/workspace.py before IO. Update the security-sensitive paths paragraph. Source: STD-02 finding.
- MEM-02 [PROMOTE]: tools_check.py is the first tool-handler test under tests/. Proves that testing via invoke/registry public seam is viable for tool-handler validation without mocking QueryEngine. Source: T-001 evidence.
- MEM-03 [PROMOTE]: Dual registry.register for glob/glob_search alias works cleanly; TOOLS snapshot is evaluated at import time and order of handler imports relative to TOOLS assignment matters. Keep search imported before TOOLS = list(). Source: plan.md risk note, confirmed in implementation.

## Follow-Up

- Reopened tasks: none
- Deferred work: core-policies.md doc sync (STD-02 / MEM-01, to be completed by /context-memory now); optional ocr provider setup (not required by this feature).
- Next required action: run /context-memory to promote MEM-01 MEM-02 MEM-03 candidates into durable repo memory, then confirm session transition to Done.
