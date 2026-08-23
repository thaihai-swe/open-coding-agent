# Context, Memory, and Providers

CoreBase SpecHarness compiles bounded project context from one explicit named-skill route,
then performs budgeted local evidence retrieval for the active intent and task.
It does not fall back to a phase matrix or dump the repository into the model.
Intent-matched domain packs (`glossary.md` `triggers`) join the pack as
`Should` sources, and retrieved excerpts redact detected secrets.

## Request Lifecycle and Token Budgeting

When a user submits a prompt or invokes a skill (e.g. `/spec-plan`):

1. **Route Selection & Entry (`skill-enter`)**:
   Resolves the skill route from `references/context-routes.yaml`, verifies required preconditions, updates `status.md`, and initializes or resumes `.corebase-specharness/sessions/<slug>/session.md`.

2. **Context Compilation (`context_engine.py`)**:
   Gathers mandatory bootstrap policies (`caveman.md`, `core-policies.md`), route-declared files, active feature artifacts, task-specific excerpts, matching domain packs, and bounded local search excerpts.

3. **Token Estimation (`_lib/token_counter.py`)**:
   - **Exact Mode (`cl100k_base`)**: Uses `tiktoken` BPE encoding (`cl100k_base`) when installed.
   - **Heuristic Mode (`chars_per_token_estimate`)**: Computes `int(len(text) / 4.0)` when running on stdlib Python without extra dependencies.
   - The active mode is reported in `manifest.tokenizer`.

4. **Budget Math and Omission**:
   - **Effective Ceiling**: `max(max_injected_tokens - reserve_tokens, 1)`
   - **Payload Budget**: `min(requested --budget or profile payload, Effective Ceiling)`
   - **Must Sources**: Always included; if they exceed the budget or channel caps, they are retained and an overrun warning is emitted.
   - **Should Sources**: Dropped when total payload or channel limits (`bootstrap`, `project`, `feature`, `retrieved`, `durable_memory`) are exceeded.

5. **Skill Execution & Closeout (`skill-exit`)**:
   The agent performs the procedural work outlined in `skills/<name>/SKILL.md`, creates/updates feature artifacts, and hands off to the next lifecycle skill.

Seed profile ceilings are not the main cost lever. Typical packs already sit
under those ceilings; `Must` sources stay even when over budget.

How to keep packs small:

- **Task-scoped implement**: after `task-start`, run
  `context-load --skill spec-implement --feature <slug> --task T-NNN`. Full
  `tasks.md` is omitted.
- **Session auto-delta**: the user only invokes skills (`/spec-requirements`,
  `/spec-plan`, …). In the same uncompacted chat, the agent omits `--full` on
  `skill-enter`. The session accumulates fingerprints across skills. Later
  skills keep only files and H2 sections whose SHA-256 fingerprint is new or
  changed since `session.md` `last_context_fingerprint` /
  `last_context_slices`. If `/spec-requirements` already injected a source,
  `/spec-plan` does not inject it again unless the content or requested
  section set changed. Pass `--full` when the user compacted this
  conversation, on the first skill of a new chat for the same feature, when
  the user asks to reload context, or when the pack is known stale.
  `session-end` does not clear fingerprints. The compiler cannot detect
  compact or a new chat.
- **Bounded retrieval**: keep `--intent` to a few keywords. Scope
  `context.retrieval.roots` and `exclude` in `harness-config.yaml`. Excerpts
  are capped by `max_retrieval_files` (seed 4) and `max_source_excerpt_tokens`
  (seed 400) and pass through secret redaction. Profiles `bootstrap`,
  `verify`, and `compact` set `retrieval_files: 0` so they skip automatic
  local retrieval. After `/spec-tasks`, omit `--full` on `/spec-implement`
  and `/harness-verify` **in the same uncompacted chat** so session
  auto-delta keeps unchanged `spec.md` / `plan.md` / `tasks.md` out of later
  packs. The same omit-`--full` rule applies at every same-chat handoff:
  `/spec-research` → `/spec-requirements` → `/spec-plan` → `/spec-tasks`.
  After compact or a new chat on the same feature, pass `--full` on the
  next enter, then omit it again for later skills in that chat.

- **Durable memory**: log `[CANDIDATE]` during implement. `/harness-verify`
  writes `## Post-Ship Sync`. `/context-memory` promotes only recurrent or
  hard-safety lessons, then compacts prose 30–50% while keeping `##` headings
  and stable IDs. Run `memory-audit` / `memory-gate` before the next skill
  when a file is near the line threshold.

```bash
# Preview budget bar and selected files
python3 corebase-specharness/scripts/core/cli.py context-pack --skill spec-plan --feature <slug> --intent "design change" --json

# Load compiled text payload
python3 corebase-specharness/scripts/core/cli.py context-load --skill spec-plan --feature <slug> --intent "design change" --json

# Inspect detailed token counts, selections, and omissions
python3 corebase-specharness/scripts/core/cli.py context-explain --skill spec-plan --feature <slug> --intent "design change" --json
```

Sessions live under `.corebase-specharness/sessions/<slug>/`. Durable memory remains adopter-owned Markdown under `corebase-specharness/memories/` and `corebase-specharness/project/`. `/context-memory` triages `[CANDIDATE]` lessons; `memory-audit` and `memory-gate` are read-only diagnostics.

Each context pack includes source paths, selection reasons, provenance, trust
labels, token estimates, and omitted-source reasons. Use
`--add-source <repo-relative-path>` only for a focused expansion; paths outside
the repository and policy-excluded paths are rejected. When
`retrieval.pinnable_sources` is configured, the added path must also match one
of its repository-relative glob patterns.

Optional providers are configured in `corebase-specharness/project/tool-providers.md`. Use `provider-list` and `provider-check` to inspect selection and local availability. Provider setup, authentication, indexing, and MCP query execution remain explicit adopter or agent actions.
