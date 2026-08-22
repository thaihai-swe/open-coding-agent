## Handoff Rules

Before switching skills or closing a session:

1. Record decided and rejected choices (with depth, seam, and blast radius context).
2. List open risks, unresolved questions, and any active `[:HALT ...]` markers.
3. Reference context omitted for budget reasons.
4. Write the handoff to `.corezero/sessions/<slug>/session.md` with `session-checkpoint` or `session-end`.
5. Run `phase-check --skill <name>`, then `artifact-check --skill <name>` or `verify --skill <name>` as the skill requires.
6. Verify that required writes for the leaving skill exist before calling `skill-exit`.

Keep the handoff readable in under 30 seconds.
