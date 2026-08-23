# Feature Proposal

## Metadata
- Feature slug: `2-permission-gate`
- Profile: `Complex`
- Date / owner: 2026-08-23 / adopter

## Problem & Outcome
- Problem statement: MEDIUM/HIGH already prompt, but an approved (or `bypass_permissions`) `bash`/`powershell` call can still run permanently forbidden patterns. Protected path/key blocks can happen after the user has already approved. Repeating the same pattern every turn has no project-level memory. Local CLI state is split across cwd `.sessions/` and `.secrets/`. Session 03 must make deny / ask / allow a live gate, with “don't ask again” rules in `.cda/.permission_rules/rules.json`, and group sessions, secrets, and rules under `.cda/`.
- Desired observable outcome: LOW runs without a prompt; MEDIUM/HIGH that are not hard-denied and have no matching project rule ask numbered `1`–`4`; `2`/`4` persist tool + primary-argument rules in `.cda/.permission_rules/rules.json`; those rules apply to every session in that cwd; deny-listed shell commands and protected path/key writes never prompt and never run; user deny and project deny still emit `tool_denied`; batches keep listed-order results; session JSON stays messages-only under `.cda/.sessions/`; default config is `.cda/.secrets/config.json`.
- Non-goals: permission modes, AST analysis, YOLO/auto-approve of unmatched patterns, CC passthrough/eight rule sources, bash workspace jail, Session 04 hooks, new JSON event types, shell deny list on `repl`, permission fields on session JSON, project rules on bare `invoke`, auto-migration or dual-use of cwd `.sessions/`, `.secrets/`, or `.permission_rules/`.

## Proposed Approach
- High-level architecture / public seams:
  - Router shape (Claude Code deny / ask / allow) on existing seams: `QueryEngine.turn` (before handler) and `invoke` (hard deny + HIGH bypass). Project rules live on the turn + `.cda/.permission_rules/rules.json` path only.
  - Deny (hard): deny-list substrings on `bash`/`powershell` `command`; `PROTECTED_PATHS` on MEDIUM `file_path`/`key`; `PROTECTED_KEYS` on `config` SET. Not bypassable. No authorize call. No `tool_denied` event.
  - Project rule: tool + primary argument; `decision` `allow` or `deny`; persisted as a JSON array at `.cda/.permission_rules/rules.json`. Matching allow skips prompt; matching deny is user deny. Hard deny still wins. Shared across session ids.
  - Local data root: `.cda/` holds `.permission_rules/`, `.sessions/`, and `.secrets/`. Feature 1 cwd defaults are superseded. `CONFIG_FILE` still overrides config. `.cda/` is gitignored.
  - Ask: remaining MEDIUM/HIGH. Sequential numbered `1`–`4` then overlapping execute of allowed calls (Feature 1). `2`/`4` write through to the rules file.
  - Allow: LOW. No authorize.
  - HIGH `bypass_permissions` remains the post-allow `invoke` flag on the turn path only; it does not override hard deny.
  - SessionStore stays transcript-only. Do not add unused permission keys to session JSON.
- Alternatives rejected and why (Design-it-Twice comparison):
  - Teaching-only three-gate (auto-allow in-workspace writes; ask only on rule match): rejected. Conflicts with Feature 1 preserved always-ask and product-sense Journey 1. Adopter chose hybrid C.
  - Spec existing prompt-only gate (no deny list): rejected. Approved `sudo` / `rm -rf /` would still run; Session 03 teaching gap unclosed.
  - Full Claude Code pipeline (eight rule sources, YOLO, passthrough, `/permissions` modes): rejected. Adopter locked those out in Q2.
  - One-shot `[A]pprove/[D]eny` only (prior Q3): superseded. Adopter chose numbered `1`–`4`.
  - Tool-name-only always-allow: rejected (Q1). Too close to YOLO for `bash`.
  - Persist in `.sessions/<id>.json` (prior Q4): superseded. Adopter requires project-level `.cda/.permission_rules/rules.json`, then grouped under `.cda/` with sessions and secrets.
  - Project always-deny as hard deny (`Blocked:`): rejected (Q3). Project deny stays `tool_denied`.
- Preserved behavior:
  - Extra tools stay registered. Feature 1 workspace bound, glob alias, concurrent batch, listed-order results, sibling isolation.
  - User deny message and `tool_denied` event (now also for project deny and answers `3`/`4`/other).
  - `bash` is not workspace-jailed. `max_turns` 8, config exit 2, cancel exit 130.
  - Session files stay `{"messages": [...]}` under `.cda/.sessions/`. `api_key`/`authorization` redaction unchanged. `CONFIG_FILE` override unchanged.

## Risks & Dependencies
- Component dependencies: QueryEngine authorize walk, `invoke` / `check_permission`, TerminalUI.authorize, `.cda/` defaults, shell and config handlers, `.gitignore`, existing `tests/*_check.py`. SessionStore is not a permission store.
- Security or migration risks: substring deny list is bypassable (case, spacing, equivalent commands). Accepted teaching-demo weakness; AST out of scope. User-edited project rules can always-allow non-hard-denied HIGH commands for every session in that cwd; hard deny still wins for the teaching list. Default config path move has no auto-migration; `CONFIG_FILE` remains. Gitignoring `.cda/` also ignores secrets (fixes Feature 1 `.secrets/` not gitignored).
- Open questions (blocking only): none (Q1=primary argument, Q2=numbered 1–4, Q3=user-deny class, Q4 superseded → `.cda/.permission_rules/rules.json`, Q5=hard deny always wins, this request → all three under `.cda/`).

## Disposition
- Approval decision: `Approved`
- Next skill/action: `/spec-plan`
