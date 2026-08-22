## Brownfield Mode

Activate when the repository has existing code, tests, CI, or history. Do not assume a clean baseline.

Brownfield mode activates Phase A (archaeology sweep) automatically before Phase B (bootstrap). No separate command is needed — `/starter-init` handles the full flow.

**Additional steps in Brownfield Mode:**

1. **Existing entrypoint check**: If `AGENTS.md` (or legacy files like `CLAUDE.md`, `.cursorrules`) already exists, read it before creating or overwriting. Preserve any rules that are still valid; flag conflicts explicitly.
2. **Broken test inventory**: Run the test suite. Do NOT fix broken tests silently. Document every failing test in `core-zero/memories/repo/core-policies.md` under a `## Known Broken Tests` section. A brownfield baseline is the current state, not an idealized clean state.
3. **Security-sensitive path flagging**: Before proceeding, scan for auth middleware, payment handlers, secret loading, and external API integrations. List them in `core-zero/memories/repo/core-policies.md` `## Security Policy` as high-attention paths requiring explicit confirmation before modification.
4. **Archaeology sweep check**: If the archaeology findings (baseline commands, security paths, and preserved behaviors) have already been recorded in `core-zero/project/tech-stack.md`, `core-zero/project/architecture.md`, `core-zero/memories/repo/project-knowledge-base.md`, and `core-zero/memories/repo/core-policies.md` from a prior sweep, skip Phase A and continue to Phase B directly. If they are missing, run Phase A first.
5. **Brownfield first feature rule**: Route the first feature through `spec-research` (`brownfield-map` mode) into `artifacts/features/<slug>/analysis.md` using `../../spec-research/references/analysis-template.md` before behavior-changing work begins unless the current behavior is already fully mapped and the feature is demonstrably isolated.
6. **Preserved behavior baseline**: Identify at least 3 behaviors that must not change regardless of what feature work follows. Record them in `core-zero/memories/repo/project-knowledge-base.md` under `## Preserved Behavior Baseline`.
7. **AI-Driven Code Archaeology**: Explore the codebase structure systematically. The agent must run recursive directory listing, search for package configuration files, and inspect configuration scripts natively to map architecture boundaries without using external script helpers.
8. **Fact vs decision**: Archaeology findings are facts. Ask the adopter only whether a failing test, security path, or preserved behavior is accepted as the baseline. Do not invent missing commands or policies.

**Brownfield Mode stop conditions:**
- The repository has no tests and no build script — document this explicitly and require user acknowledgment before proceeding.
- Phase A was not run and archaeology findings are missing from `core-policies.md`, `project-knowledge-base.md`, `tech-stack.md`, or `architecture.md` — run Phase A before continuing Phase B.
- Existing `AGENTS.md` contains rules that directly conflict with the harness kit — surface the conflict and ask the user to resolve it before continuing.
