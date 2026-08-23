## Brownfield Mode

Activate when the repo has existing code, tests, CI, or history. Phase A (archaeology) runs before Phase B. `/starter-init` handles both.

**Additional steps:**

1. **Existing entrypoint:** Read `AGENTS.md` (or `CLAUDE.md`, `.cursorrules`) before overwrite. Preserve valid rules; flag conflicts.
2. **Broken tests:** Run the suite. Do NOT fix silently. Record every failure in `corebase-specharness/memories/repo/core-policies.md` `## Known Broken Tests`.
3. **Security paths:** Scan auth, payments, secrets, external APIs. List them in `core-policies.md` `## Security Policy`.
4. **Sweep check:** If tech-stack, architecture, PKB, and core-policies already record archaeology findings, skip Phase A. Otherwise run it first.
5. **First feature:** Route through `spec-research` (`brownfield-map`) into `analysis.md` unless current behavior is fully mapped and the feature is isolated.
6. **Preserved baseline:** Record ≥3 must-not-change behaviors in `project-knowledge-base.md` `## Preserved Behavior Baseline`.
7. **Archaeology:** Recursively list dirs, find package configs, inspect scripts. Map boundaries without external helpers.
8. **Fact vs decision:** Findings are facts. Ask only whether a failing test, security path, or preserved behavior is accepted as baseline. Do not invent commands or policies.

**Stop conditions:**
- No tests and no build script — document and require acknowledgment.
- Phase A skipped and findings missing — run Phase A before Phase B.
- Existing `AGENTS.md` conflicts with the kit — surface and ask before continuing.

---

## Rules-Bootstrap Conventions (Optional)

Use when the adopter asks for stack-specific conventions:

1. Inspect source, formatter/linter config, tests, and CI.
2. Identify existing rules before proposing new ones.
3. Draft naming, module, test, error, and format conventions.
4. Present draft for confirmation.
5. Write only missing or seed-placeholder policy. Never replace a non-empty section on re-sync.
6. Record unknown conventions as `[USER REVIEW NEEDED]`.
