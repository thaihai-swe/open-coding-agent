# Extraction Triage

When processing extracted or auto-tier memory entries:

1. Locate candidates:
   - Per-feature: `artifacts/features/<slug>/session-extracts.md`
   - Across features: `artifacts/features/*/session-extracts.md`
2. Process each pending candidate:
   - Read category, confidence, evidence.
   - Decide: promote, defer, or discard.
   - Before promote: merge semantic overlap with the target file. Increment recurrence. Distill; do not append duplicates.
3. Promote only durable, evidence-backed items:
   - Heuristic / hard safety rule → `learned-heuristics.md`
   - Pattern or boundary → `project-knowledge-base.md` or `architecture.md`
   - Normative rule with agreement → `core-policies.md` (`CC-*`)
   - Permission / trust / sandbox → `core-policies.md` `## Security Policy`
   - Domain term → `glossary.md` or matching domain pack
   - Harness gap → `harness-maintain` Improve Mode
   - Spec gap → `spec-requirements`
4. Defer plausible but under-evidenced items. Mark `deferred` with a one-line reason.
5. Discard feature-local, contradicted, or already-covered items. Mark `discarded` with a reason. Do not delete the trail.
6. Update source: move processed items from `## Pending Candidates` to `## Triaged`. Add `Triage notes:`. Move retired entries to `## Retired Entries`.
7. Verify: no leftover `pending`; promoted content changed an instruction file; discarded items have reasons.

Stop:
- Evidence references missing files/sessions → `discarded`
- Sessions contradict the candidate → `discarded` with contradiction
- Feature-local → `discarded`, do not promote

Anti-patterns:
- Promoting every candidate. Defer/discard is often correct.
- Editing candidate text instead of moving it. Candidates are append-only.
- Promoting on one session unless it is a hard safety/data-loss rule.
- Creating a new `LH-*`/`CC-*` that restates an existing rule.

## Mechanical Audit Fields

Run `python3 corebase-specharness/scripts/core/cli.py memory-audit --json` before promotion. If a file is `warning-level` or `hard-cap`, compact first: snapshot `.bak` and `.ids_before`, cut prose 30–50% to bullets, keep every `##` heading and stable ID, confirm `.ids_after` matches. Do not promote a new `LH-*`/`CC-*` into a hard-capped file.
