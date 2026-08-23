# Feature Status: 2-permission-gate

- Phase: Done
- Delivery profile: Complex
- Status: Active
- Active task: None
- Next step: /context-memory

## Progress
- [x] Research/spec complete
- [x] Spec approved
- [x] Plan/tasks complete (Moderate/Complex only)
- [x] Plan approved
- [ ] Implementation complete
- [ ] Validation complete

## Intake
- Input type: `change_request`
- One-line restatement: Close Session 03 permission-gate gaps; project always-allow/deny in `.cda/.permission_rules/rules.json`; store rules, sessions, and secrets under `.cda/`.
- Artifact name requested: `2.permission-gate` (harness slug: `2-permission-gate`)
- Why now: Clarify-reentry. Adopter requires `.permission_rules`, `.sessions`, and `.secrets` under `.cda/`. Numbered `1`–`4` and tool+primary-argument matching stay. Session 03 sources remain in-scope references for this feature only.
- Analysis: `analysis.md` absent. User skipped `/spec-research`.
- ADR conflict: none (empty log).
- Domain packs: none matched beyond default project files.

## Facts (not decisions)
- Feature 1 (`1-tool-and-execution`) is Done. It preserved MEDIUM/HIGH sequential `[A]pprove/[D]eny`, `tool_denied`, and listed-order batch results. It deferred permission modes, deny-list expansion, and AST command analysis to Session 03+.
- QueryEngine already prompts `authorize` for every MEDIUM and HIGH tool before a concurrent batch; deny records a tool-error result and does not invoke. LOW tools skip UI approval.
- After HIGH approve, QueryEngine injects `bypass_permissions=True` into `invoke`. Direct `invoke` of HIGH without that flag raises `PermissionError`.
- `check_permission` hard-blocks MEDIUM calls whose `file_path` or `key` substring-matches `PROTECTED_PATHS` (`.gitconfig`, `.bashrc`, `.zshrc`, `.env`, `id_rsa`) even after UI approve.
- `config` SET of `PROTECTED_KEYS` (`.env`, `secret`) raises `PermissionError` in the handler. No bash/powershell/repl hard deny list exists; approved `bash` is still `shell=True` and not workspace-jailed (Feature 1 AC-008).
- Prompt contract before this change request: `[A]pprove/[D]eny:`; `a`/`approve` allow; any other answer denies. JSON mode still uses stdin for authorize (`product-sense` Journey 3). Spec now replaces that with numbered `1`–`4`.
- Session files today are `{"messages": [...]}` under default `.sessions/` (`SessionStore.save` overwrites the whole file). Default config is `.secrets/config.json` (not gitignored). Spec moves both under `.cda/` with permission rules; session JSON stays messages-only.
- MEDIUM/HIGH tools that prompt: `bash`/`powershell` (`command`), `repl` (`code`), `write_file`/`edit_file` (`file_path`), `config` (`action`+`key`), `web_fetch` (`url`).
- Teaching s03 three-gate (hard deny → rule-ask → default allow) and CC extras (four behaviors, eight rule sources, YOLO classifier, permission modes, AST analysis) are not implemented.
- No dedicated permission-gate tests for deny-list, protected-path hard block, or HIGH-without-bypass. Existing proofs: `tests/query_engine_check.py` (deny skip + sequential authorize), `tests/terminal_ui_check.py` (a/d prompt).
- `skill-enter` expected `skills/_shared/status-template.md`; this tree keeps the template at `.agents/skills/_shared/status-template.md`. Status was seeded from that template so the envelope could set `Specifying`.

## Blockers / Decisions
- Blocker:
- Locked decision: Product is the coding-agent CLI (`src/`). Session 03 sources are in-scope references for this feature only, not a global architecture contract.
- Locked decision: Hybrid C / Claude Code-shaped router: deny / ask / allow. Always-ask MEDIUM/HIGH that are not hard-denied and have no matching project rule. Hard deny never executes and is not bypassable (Yes, don't-ask-again, `bypass_permissions`, and a rules-file allow cannot override).
- Locked decision: Non-goals — `/permissions` modes, AST, YOLO/auto-approve of unmatched patterns, CC passthrough/eight sources, bash cwd jail, Session 04 hooks, new JSON event type, shell deny list on `repl`, permission fields on session JSON, project rules on bare `invoke`, auto-migration or dual-use of cwd `.sessions/` / `.secrets/` / `.permission_rules/`.
- Locked decision: Prompt is numbered `1`–`4` (`1` Yes once, `2` Yes don't ask again, `3` No once, `4` No don't ask again). Other input denies this call. JSON stdin same. Prior Q3 one-shot `[A]pprove/[D]eny` is superseded.
- Locked decision: Rule grain = tool name + primary argument (Q1). Always-deny = user deny / `tool_denied` (Q3). Rules persist in `.cda/.permission_rules/rules.json`. Shared by all session ids in that cwd. File is source of truth for the next gated call.
- Locked decision: CLI local data root is `.cda/` — `.cda/.permission_rules/`, `.cda/.sessions/`, `.cda/.secrets/`. Feature 1 cwd defaults superseded. `.cda/` gitignored. `CONFIG_FILE` still overrides config.
- Locked decision: Deny-list substrings on `bash`/`powershell` `command`: `rm -rf /`, `sudo`, `shutdown`, `reboot`, `mkfs`, `dd if=`, `> /dev/sda`. Hard deny before project-rule match before ask; no `tool_denied` for hard deny.
- Locked decision: Protected paths/keys are hard deny (skip prompt). HIGH `bypass_permissions` does not override hard deny.
- Locked decision: Live path only — every permission list/flag/function for this feature is consulted by the live gate path; no unused permission code; no unused session-JSON permission fields.

## Blocked Recovery
- Reason:
- Owner:
- Evidence:
- Next review at:
- Recommended handoff:
