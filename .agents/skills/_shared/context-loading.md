## Context Loading

The user invokes a named skill (`/spec-research`, `/spec-requirements`,
`/spec-plan`, `/spec-tasks`, `/spec-implement`, `/harness-verify`, …). They
do not call the Python CLI. The agent enters that skill through the envelope.
That loads the named route, opens the feature session, and sets the enter
state.

Same-chat sequential skills on one feature omit `--full`. The first skill
for a feature is a full pack. Later skills skip files and H2 sections
already injected in **this conversation**. Auto-delta reads hashes from
`.corebase-specharness/sessions/<slug>/session.md`. It cannot see that the chat was
compacted or that this is a new conversation.

```text
User:  /spec-research          → agent skill-enter spec-research     (full pack)
User:  /spec-requirements      → agent skill-enter spec-requirements (delta)
User:  /spec-plan              → agent skill-enter spec-plan         (delta)
User:  /spec-tasks             → agent skill-enter spec-tasks        (delta)
User:  /spec-implement         → agent skill-enter, then per-task
                                 context-load --task T-NNN           (delta)
User:  /harness-verify         → agent skill-enter harness-verify    (delta)
```

Same feature slug keeps one on-disk session. A new feature slug starts a
new session and a full pack again.

**Pass `--full` on `skill-enter` / `context-load` when any of these is true:**

| Situation | Agent action |
| --- | --- |
| Same chat, next skill, no compact | Omit `--full` (delta) |
| User compacted this conversation | Pass `--full` on the next skill |
| First skill in a **new chat** on an existing feature | Pass `--full` |
| User asked to reload context / reload everything | Pass `--full` |
| Files changed on disk after they were loaded, pack known stale | Pass `--full` |
| New feature slug | Omit `--full` (no hashes yet; pack is already full) |

`--full` is an agent flag, not a user command. The user types the skill
and, after compact or a new chat, says reload context. `/context-memory`
compacting a **memory file on disk** is different: that file’s hash
changes, so a later skill that still needs it re-injects it. That does
not restore dropped chat history.

`session-end` does not clear fingerprints. Reopening the same feature in
a new chat still requires `--full` on the first skill.

Agent envelope (user does not type this):

```bash
python3 corebase-specharness/scripts/core/cli.py skill-enter --skill <name> [--feature <slug>] [--task <T-NNN>] --intent "<intent>" [--full]
```

`context-load` remains available when the agent needs the pack without changing session or status:

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
- After `/spec-requirements`, omit `--full` on `/spec-plan` so unchanged bootstrap and overlapping artifacts are not re-injected. After `/spec-tasks`, omit `--full` on `/spec-implement` and `/harness-verify`. Do **not** omit `--full` after a conversation compact or on the first skill of a new chat for the same feature: hashes in `session.md` would skip files that are no longer in the live window. Session auto-delta accumulates SHA-256 fingerprints in `session.md` (`last_context_fingerprint`, `last_context_slices`) across skills. Later skills in the **same uncompacted chat** inject only new or changed files, and only new or changed H2 sections.
- Automatic local retrieval is off for profiles `bootstrap`, `verify`, and `compact` (`retrieval_files: 0`). Other profiles use the global caps (`max_retrieval_files: 4`, `max_source_excerpt_tokens: 400`, `max_retrieved_tokens: 1000`).
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
