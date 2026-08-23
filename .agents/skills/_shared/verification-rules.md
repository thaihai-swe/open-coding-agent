## Verification Rules

- Before marking a task Done, confirm proof matches planned proof surfaces and runs through public seams.
- For code tasks: tests must pass, lint must be clean, build must succeed, and tests must not be tautological or implementation-coupled.
- For spec tasks: all ACs must be written, no HALT markers remaining.
- For design tasks: architecture must be documented with ADR if contested, and module depth / seams must be declared.
- For closeout verification: conduct Two-Axis Code Review (Standards Review + Spec Alignment Review) independently before deciding verdict.
- Prefer `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug> --skill harness-verify` for closeout.
- Bare `verify --feature <slug>` remains the coarse `--phase Verify` compatibility path.
- `verify` runs mechanical gates through the embedded Python runtime.

After verification, set `- Phase:` only through `skill-exit` or `status-set`.
Do not hand-edit `- Phase:`. Update progress checkboxes from evidence.
An advisory `verify` exit code of `0` is not a verification verdict; inspect
`details.verified`.

- `Done` is mechanically protected: `skill-exit --skill harness-verify` runs verification inline. It requires a passing current-config result and a `## Post-Ship Sync` section in `session-extracts.md`.
- `review.md` and advisory `verify` exit code `0` do not independently authorize `Done`.
- Use `--verification-override --override-reason "..."` only for a deliberate, explicit exception; it is never implicit.
