# Session extracts: 2-permission-gate

## Candidates

- [CANDIDATE] Hard deny lives in one function, `hard_deny_reason`, called from both `check_permission` and `QueryEngine._run_batch`. Do not duplicate `DENY_LIST` / `PROTECTED_*` tables.
- [CANDIDATE] Project rules are turn-path only. Bare `invoke` must not import `permission_rules`. Rules persist at `.cda/.permission_rules/rules.json`.
- [CANDIDATE] `AuthorizeDecision(allow, persist)` replaces bool authorize. Numbered `1`–`4` prompt; `2`/`4` upsert immediately so a later sibling in the same batch can match.
- [CANDIDATE] Default local data root is `.cda/` (sessions, secrets, rules). No dual-read of cwd `.sessions/` / `.secrets/` / `.permission_rules/`.

## Post-Ship Sync

- MEM-01 [PROMOTE]: `corebase-specharness/memories/repo/core-policies.md` §Security Policy is stale. Post-feature: default secret store is `.cda/.secrets/config.json` and `.cda/` is gitignored; `PROTECTED_KEYS` / `PROTECTED_PATHS` / `DENY_LIST` are consulted only via `hard_deny_reason` (settings handler no longer raises); `TerminalUI.authorize` is numbered `1`–`4`. Source: STD-01 finding in review.md.
- MEM-02 [PROMOTE]: Permission rules persist in `.cda/.permission_rules/rules.json` and are evaluated on the `QueryEngine.turn` path only; bare `src.tools.invoke` does not import or consult `permission_rules.py`. Source: plan.md decision 3; AC-029.
- MEM-03 [PROMOTE]: `TerminalUI.authorize` returns `AuthorizeDecision(allow, persist)`. Input `1` allow once, `2` allow persist, `4` deny persist; `3` / empty / `a` / `approve` / other deny without persist. Source: plan.md decision 2; AC-012.

## Follow-Up

- Reopened tasks: none
- Deferred work: core-policies.md doc sync (STD-01 / MEM-01, to be completed by /context-memory now); optional ocr provider setup not required by this feature.
- Next required action: promote these candidates via /context-memory then confirm session transition to Done.

## Triaged

<!-- triaged: true, date: 2026-08-23 -->

- [PROMOTED] Hard deny lives in one function, `hard_deny_reason`, called from both `check_permission` and `QueryEngine._run_batch`. Do not duplicate `DENY_LIST` / `PROTECTED_*` tables.
  - Target: `corebase-specharness/memories/repo/core-policies.md` §Security Policy (`src/tools/permissions.py` path)
  - Reason: Safety/data-loss rule independently confirmed by `spec.md` REQ-006/REQ-010, `plan.md` decision 1, and AC-001/AC-008/AC-017/AC-023.

- [PROMOTED] Project rules are turn-path only. Bare `invoke` must not import `permission_rules`. Rules persist at `.cda/.permission_rules/rules.json`.
  - Target: `corebase-specharness/memories/repo/project-knowledge-base.md` Preserved Behavior Baseline
  - Reason: Durable architecture fact independently confirmed by `plan.md` decision 3 and AC-029.

- [PROMOTED] `AuthorizeDecision(allow, persist)` replaces bool authorize. Numbered `1`–`4` prompt; `2`/`4` upsert immediately so a later sibling in the same batch can match.
  - Target: `corebase-specharness/memories/repo/core-policies.md` §Security Policy (`src/presentation/terminal_ui.py` path) and `project-knowledge-base.md` Preserved Behavior Baseline
  - Reason: Durable contract independently confirmed by `spec.md` REQ-004, `plan.md` decision 2, and AC-012/AC-018/AC-022.

- [PROMOTED] Default local data root is `.cda/` (sessions, secrets, rules). No dual-read of cwd `.sessions/` / `.secrets/` / `.permission_rules/`.
  - Target: `corebase-specharness/memories/repo/core-policies.md` §Security Policy and `project-knowledge-base.md` Operational Watchouts
  - Reason: Hard safety/data-loss rule independently confirmed by `spec.md` REQ-020/REQ-021, `plan.md` decision 4, and AC-027/AC-028/AC-030.

- MEM-01 [PROMOTED]: `corebase-specharness/memories/repo/core-policies.md` §Security Policy updated. Source: STD-01 finding in `review.md`.
- MEM-02 [PROMOTED]: `corebase-specharness/memories/repo/project-knowledge-base.md` Preserved Behavior Baseline updated. Source: `plan.md` decision 3; AC-029.
- MEM-03 [PROMOTED]: `corebase-specharness/memories/repo/core-policies.md` §Security Policy and `project-knowledge-base.md` Preserved Behavior Baseline updated. Source: `plan.md` decision 2; AC-012.
