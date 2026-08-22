# TDD Loop

The red → green loop that makes task proofs worth keeping. Consult this before and during every locked `T-NNN`, not after.

When exploring the area, use the project's glossary vocabulary and respect ADRs in the modules you touch.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests should not. A good test reads like a specification: it names a capability and survives refactors because it does not care about internal structure.

## Seams: where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams declared in `plan.md` or the locked task's proof command.

Confirm the seam before writing any test. No test is written at an unconfirmed seam. If the public seam is missing or the only available seam is too shallow to exercise the real bug or behavior, halt back to `/spec-plan` rather than inventing an internal mock seam.

See `../spec-plan/references/deep-modules.md` for module, interface, depth, seam, adapter, leverage, and locality.

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests private methods, or verifies through a side channel. The tell: the test breaks when you refactor but behavior has not changed.
- **Tautological**: the assertion recomputes the expected value the way the code does, so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth: a known-good literal, a worked example, or the spec.
- **Horizontal slicing**: writing all tests first, then all implementation. Bulk tests verify imagined behavior. Work in **vertical slices** instead: one test → one implementation → repeat.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Do not anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** Design cleanup belongs to a follow-up `T-NNN` or to `/harness-verify`, not the red → green implementation cycle.

## Cycle inside a locked task

1. Confirm the task's public seam from `plan.md` / the task proof command.
2. Write or identify the failing proof. Watch it fail for the right reason.
3. Write only enough production code to pass it.
4. Re-run the proving command. Record the fresh evidence on `task-done`.
