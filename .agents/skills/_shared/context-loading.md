## Context Loading

Enter a skill through the envelope. That loads the named route, opens the session, and sets the enter state:

```bash
python3 corebase-specharness/scripts/core/cli.py skill-enter --skill <name> [--feature <slug>] [--task <T-NNN>] --intent "<intent>"
```

`context-load` remains available when you need the pack without changing session or status:

```bash
python3 corebase-specharness/scripts/core/cli.py context-load --skill <name> [--feature <slug>] [--task <T-NNN>] --intent "<intent>"
```

`references/context-routes.yaml` defines the route phase, profile, feature requirement, prerequisites, feature artifacts, writes, handoffs, and source sections. The CLI rejects missing skill names and unknown routes. Feature-bound skills also reject a missing feature slug.

### Token Cost Estimation & Budgeting

1. **Token Calculation**:
   - `cl100k_base` BPE tokenizer if `tiktoken` is installed.
   - Heuristic fallback (`len(text) / 4.0`) in pure stdlib Python environments.
2. **Budget Ceiling**:
   - Total payload budget is `min(profile_payload or --budget, max_injected_tokens - reserve_tokens)`.
3. **Channel Caps**:
   - Limits per category (`bootstrap`, `project`, `feature`, `task`, `retrieved`, `durable_memory`) prevent one source type from crowding out others.
4. **Source Tiers**:
   - `Must` sources are never dropped for budget reasons; if they exceed the configured payload, CoreBase SpecHarness retains them and reports an overrun warning.
   - `Should` sources are omitted when total budget or channel limits are exceeded.

### Token-cost rules

- On implement coding turns, pass `--task T-NNN` to `context-load` after `task-start`. The compiler then omits full `tasks.md` and injects only the active task plus its direct dependencies.
- Keep `--intent` to a few keywords. Do not paste the user request essay into `--intent`.
- Use repeatable `--add-source <repo-relative-path>` for a known file. Do not ask retrieval to dump the tree.
- Omit `--full` unless the pack is known stale. Session auto-delta compares SHA-256 fingerprints in `session.md` `last_context_fingerprint` and keeps unchanged sources out of later loads.
- Inspect spend with `context-explain --json` (`estimated_tokens`, `budget_categories`, omit reasons, `delta` / `unchanged_selected` when a baseline exists).
- When `memory-audit` warns, run `/context-memory` before the next delivery skill. Compact prose 30–50% without deleting `##` headings or stable IDs (`LH-*`, `CC-*`, `ADR-*`, `REQ-*`, `AC-*`).

Intent-matched domain packs join the pack when `--intent` words intersect
`triggers:` in `corebase-specharness/memories/domain/<name>/glossary.md`. Record any
loaded pack in `status.md` when the skill procedure asks for it.

CoreBase SpecHarness also retrieves bounded local evidence from the configured repository
roots using the active intent, feature, and task. Inspect the pack with
`python3 corebase-specharness/scripts/core/cli.py context-explain ... --json`; it reports source provenance, trust,
token estimates, and omission reasons. Use repeatable
`--add-source <repo-relative-path>` for an explicit focused expansion.
