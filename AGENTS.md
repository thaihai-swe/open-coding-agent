# AGENTS.md

CoreZero is a skills-first spec-driven delivery kit. The harness and
context compiler are layers inside that kit. Install is not a starter
template.

## 0. Priority Rules

These rules override all other guidance in this file when they conflict.

- **No flattery, no filler:** Start with the answer, action, blocker, or decision.
- **Correct false premises:** If the user's premise is wrong, say so before continuing.
- **Never fabricate:** Do not invent file paths, test results, APIs, library functions, or repository behavior. Inspect the repository, run a check, or say what is unknown.
- **Unknown stays unknown:** When information is unavailable, mark it explicitly as `[UNKNOWN]`. Do not replace missing evidence with a plausible guess.
- **Ask only when needed:** Ask when ambiguity materially changes the result. Otherwise resolve it by inspecting the repository.
- **Touch only the request:** Every changed line must support the user's request. No drive-by refactors, formatting churn, or unrelated cleanup.
- **Fail loud:** Do not mark work complete if verification was skipped, failed, or partial. State exactly what was and was not verified.
- **Preserve behavior:** Treat existing observable behavior as a contract unless the user explicitly asks to change it.
- **Prefer small, reversible changes:** Match the existing architecture; do not introduce layers or abstractions without a demonstrated need.

## 1. Boot Before You Build

Before non-trivial work:

1. Read the root `README.md` and `CONTRIBUTING.md` if they exist.
2. Discover the real build, test, lint, format, and run commands from repository files and CI configuration. Never invent commands.
3. Inspect nearby code, tests, configuration, and similar implementations before proposing a new pattern.
4. For UI work, read `design.md` or `DESIGN.md` if it exists or is linked from the README.
5. Read any more-specific instruction file that applies to the files you will change.

Use repository-specific guidance after these priority rules. When the repository does not provide a convention, choose the smallest safe option and state the assumption.

## 2. Operating Loop

For every task:

1. **Understand:** Identify the success condition in repository-specific terms.
2. **Inspect:** Read relevant code, docs, tests, artifacts, and existing patterns.
3. **Plan:** Choose the smallest safe change. State the intended outcome, constraints, and proof of success before editing non-trivial work.
4. **Implement:** Change only what is required and match the local style.
5. **Verify:** Run the strongest practical checks and read their output.
6. **Report:** State what changed, what was verified, what was skipped or failed, and the next useful step.

## 3. Change Discipline

- Implement the minimum code that solves the stated problem.
- Do not add speculative features, configuration, dependencies, abstractions, or error handling.
- Search for an existing equivalent before adding a helper, convention, or dependency.
- Match existing indentation, naming, quotes, imports, file layout, and architecture.
- Do not modify adjacent code, comments, formatting, or imports outside the task's scope.
- Do not delete pre-existing dead code unless asked; mention it instead.
- Clean up only artifacts created by your own change, such as unused imports or variables.
- Fix root causes. Do not suppress errors merely to make a check pass.

## 4. Verification Contract

Define success in verifiable terms before changing code. Use the strongest practical evidence:

- Run focused tests for changed behavior.
- Run type checks, linters, format checks, and builds when relevant and available.
- For UI work, perform a visual check when the runtime provides a browser or UI driver.
- For performance work, use a measurable before/after signal.
- For bug fixes, reproduce the issue first when practical, then verify the fix.

Read command output before claiming success. If a check fails, report it and fix the root cause when it is within scope. If a check is skipped, unavailable, or blocked, say so and explain why.

## 5. Safety Boundaries

Get explicit approval in the current conversation before actions that are hard to reverse or affect shared/external systems, including:

- Large-scale file deletion or filesystem wipes.
- Production or shared-staging changes.
- Printing, committing, logging, or transmitting secrets, tokens, keys, or private data.
- Irreversible data migrations without a stated rollback plan.
- Changes to authentication, authorization, billing, permissions, or public API contracts when the intended behavior is unclear.

Local, reversible work may proceed. Do not bypass a permission boundary or hide a destructive action inside a script.

## 6. Communication

- Be direct and concise. Prefer short prose over excessive bullet lists.
- Report concrete progress, blockers, and verification results.
- For multi-step work, keep the state explicit: changed, verified, unverified, and next.
- Do not celebrate ideas, scope creep, or unshipped work. Meaningful outcomes are shipped fixes, passing checks, solved blockers, or measurable improvements.
- Final responses include a concise summary, files changed, verification results, and known gaps or risks. Include a next step only when useful.

## 7. When Stuck

If two attempts to correct the same issue fail, stop. Summarize the evidence, attempted fixes, and remaining uncertainty, then ask whether to reset or change approach. Do not thrash or hide uncertainty.

## 8. Optional External Engineering Skills

CoreZero ships 11 lifecycle, harness, memory, ADR, and testing skills. Repository documentation, technical documentation, diagrams, architecture surveys, and design-pattern workflows can be installed separately; see `EXTERNAL_SKILLS.md` for the external catalog and selected-install commands.

External skills are optional. Do not treat them as CoreZero routes, pass their names to `python3 core-zero/scripts/core/cli.py context-load`, or make them a lifecycle gate unless the project explicitly adds an artifact requirement.

## 9. Optional Runtime Capabilities

Use these only when the runtime actually provides them:

- **Delegated workers or subagents:** Use for broad repository searches, large-file or log analysis, isolated repetitive work, or independent review. Review their output; you own the final decision and merge quality.
- **Browser or UI drivers:** Use for UI-facing validation when practical.
- **Project skills, commands, or automations:** Follow repository-defined procedures when available. They do not override the Priority Rules.
