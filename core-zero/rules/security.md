# Security Rules

Implementation safety guidance for code and scripts. Normative permission tiers and trust boundaries live in `core-zero/memories/repo/core-policies.md` `## Security Policy`.

These rules apply when work touches secrets, auth, shell execution, external input, or cross-boundary data flow.

## Core Rules

- Never hardcode credentials, tokens, or private endpoints.
- Treat environment variables, config files, CLI arguments, API payloads, and generated artifacts as untrusted input unless proven otherwise.
- Prefer allowlists over ad hoc string filtering for file paths, command options, and externally sourced identifiers.
- Do not suppress validation or error handling to make a check pass.
- Do not widen file-system or shell access without documenting why the wider boundary is required.

## Shell and Script Safety

- Keep shell commands explicit and narrowly scoped.
- Avoid passing unchecked user-controlled text into shell evaluation.
- Prefer direct argument passing over string-built shell fragments.
- When a script mutates files, make the target set obvious and reviewable.

## File and Artifact Boundaries

- Distinguish kit-managed files from adopter-owned files before editing.
- Preserve `artifacts/` and adopter-owned seeded docs unless the requested task explicitly changes them.
- Generated placeholders must not be described as current truth unless they were refreshed in the current run.

## Verification

- Security-relevant changes are not complete without fresh verification evidence.
- If a change alters trust boundaries, update the matching docs and rules in the same change wave.

### Principle

More rules → more freedom. Constraints increase agent autonomy by making incorrect paths fail fast. Agents run freely within checked boundaries. When an agent hits a boundary, the fix is to either widen the boundary (if the action was correct) or keep it (if the action was wrong). See CC-013 for the one-rule-per-mistake loop.
