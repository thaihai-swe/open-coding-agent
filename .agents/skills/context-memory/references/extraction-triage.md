# Extraction Triage

When processing extracted-tier or auto-tier memory entries:

1. Locate candidate sources:
   - Per-feature: `artifacts/features/<slug>/session-extracts.md`
   - Across active features: `artifacts/features/*/session-extracts.md`
2. Process each pending candidate in order:
   - Read the candidate's category, confidence, and evidence
   - Decide: promote, defer, or discard
   - Distillation & Deduplication Check: Before promoting any candidate, cross-reference it with the existing guidelines/heuristics in the target file. If there is semantic overlap or the target already covers the core lesson, merge the evidence, increment the recurrence count, and distill the rule to keep the descriptions concise, active-voice, and distinct. Do not append separate duplicate entries.
3. Promote when the candidate is durable, evidence-backed, and matches an instruction-tier file:
   - Heuristic with confirming evidence or a hard safety/data-loss rule -> append to `learned-heuristics.md`
   - Pattern or boundary fact -> integrate into `project-knowledge-base.md` or `core-zero/project/architecture.md`
   - Normative rule with team agreement -> amend `core-policies.md` (CC-*)
   - Permission, trust, or sandbox rule -> amend `core-policies.md` `## Security Policy`
   - Domain term that crystallized in the session -> append to `core-zero/project/glossary.md` or the matching domain pack
   - Harness gap -> route to `harness-maintain` Improve Mode
   - Spec gap -> route back to `spec-requirements`
4. Defer when the candidate is plausible but under-evidenced:
   - Mark as `deferred` with a one-line reason
   - It stays available for re-triage after future sessions strengthen the signal
5. Discard when the candidate is feature-local, contradicted, or already covered:
   - Mark as `discarded` with a one-line reason
   - Do not delete — the trail matters
6. Update the source file:
   - Move processed candidates from `## Pending Candidates` to `## Triaged` in `session-extracts.md`
   - Update `Status:` and add `Triage notes:` in `artifacts/features/*/session-extracts.md`; move retired entries to `## Retired Entries`
7. Verify:
   - No candidate left in `pending` without an explicit triage decision in this pass
   - Promoted content actually changed an instruction-tier file (link the new identifier)
   - Discarded content has a recorded reason

Stop Conditions:
- The candidate's evidence references files or sessions that no longer exist — mark as `discarded` with reason
- Multiple sessions contradict the candidate — discard with the contradiction recorded
- The candidate is genuinely feature-local — discard, do not promote

Anti-patterns:
- Promoting every candidate to look thorough. Defer or discard is often the right call.
- Editing candidate text instead of moving it. Source candidates are append-only history.
- Promoting on a single session's evidence when the heuristic threshold requires repetition.
- Creating a new `LH-*` or `CC-*` that restates an existing rule instead of merging evidence and incrementing recurrence.

## Mechanical Audit Fields

Use `python3 core-zero/scripts/core/cli.py memory-audit --json` file counts and threshold warnings before promotion or distillation.
