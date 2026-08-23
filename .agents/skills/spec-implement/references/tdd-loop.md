# TDD Loop

Red → green loop for every locked `T-NNN`. Consult before and during the task, not after. Use glossary vocabulary and respect ADRs in touched modules.

## What a good test is

Tests verify behavior through public interfaces, not implementation. A good test names a capability and survives refactors.

## Seams: where tests go

A **seam** is the public boundary you test at. Tests live at seams declared in `plan.md` or the locked task's proof command.

Confirm the seam before writing any test. If the public seam is missing or too shallow, halt to `/spec-plan`. Do not invent an internal mock seam.

See `../spec-plan/references/deep-modules.md`.

## Anti-patterns

- **Implementation-coupled**: mocks internals, tests private methods, or uses a side channel. Tell: test breaks on refactor with unchanged behavior.
- **Tautological**: assertion recomputes the expected value the way the code does. Expected values must come from a literal, worked example, or spec.
- **Horizontal slicing**: all tests first, then all implementation. Use vertical slices: one test → one implementation → repeat.

## Rules of the loop

- **Red before green.** Failing test first, then only enough code to pass it.
- **One slice at a time.** One seam, one test, one minimal implementation.
- **Refactoring is not part of the loop.** Cleanup is a follow-up `T-NNN` or `/harness-verify`.

## Cycle inside a locked task

1. Confirm the public seam from `plan.md` / the proof command.
2. Write or identify the failing proof. Watch it fail for the right reason.
3. Write only enough production code to pass it.
4. Re-run the proving command. Record fresh evidence on `task-done`.
