## Context Loading

The user invokes a named skill (`/spec-research`, `/spec-requirements`, `/spec-plan`, …). They do not call the Python CLI. `--full` is an agent flag, not a user command. The agent enters through the envelope:
- Loads named route, opens feature session, sets enter state.
- Same-chat sequential skills on one feature omit `--full` (delta mode: skips already-injected files and H2 slices).
- Auto-delta reads SHA-256 hashes from `.corebase-specharness/sessions/<slug>/session.md`. It cannot see that the chat was compacted.
- `references/context-routes.yaml` is the only routing authority.

```text
/spec-research      → skill-enter spec-research     (full pack)
/spec-requirements  → skill-enter spec-requirements (delta)
/spec-plan          → skill-enter spec-plan         (delta)
/spec-tasks         → skill-enter spec-tasks        (delta)
/spec-implement     → skill-enter, then context-load --task T-NNN (delta)
/harness-verify     → skill-enter harness-verify    (delta)
```

### When to pass `--full`

| Situation | Agent action |
| --- | --- |
| Same chat, next skill | Omit `--full` (delta) |
| Conversation was compacted | Pass `--full` on next skill |
| First skill in a **new chat** on existing feature | Pass `--full` |
| User asked to reload context | Pass `--full` |
| Files changed on disk, pack known stale | Pass `--full` |
| New feature slug | Omit `--full` (first pack is always full) |

`session-end` does not clear hashes. Reopening a feature in a new chat still needs `--full` on turn 1. `/context-memory` compacting a memory file on disk is different: that file's hash changes so a later skill re-injects it. That does not restore dropped chat history.

### CLI Envelopes

```bash
# Direct entry (envelope sets phase & session)
python3 corebase-specharness/scripts/core/cli.py skill-enter --skill <name> [--feature <slug>] [--task <T-NNN>] --intent "<intent>" [--full]

# Standalone context fetch (no phase mutation)
python3 corebase-specharness/scripts/core/cli.py context-load --skill <name> [--feature <slug>] [--task <T-NNN>] --intent "<intent>"
```

### Token-Cost Rules

- **Implement Coding Turns**: Pass `--task T-NNN` to `context-load` after `task-start`. Drops full `tasks.md` and injects only active task + direct dependencies.
- **Intent**: Keep `--intent` to 2–5 keywords. Never paste full prompt essays.
- **Explicit Sources**: Use `--add-source <path>` for known targets. Do not dump directory trees.
- **Auto-Delta**: Omit `--full` across sequential skills in the same chat.
- **Retrieval**: Disabled for `bootstrap`, `verify`, `compact` profiles. Global caps: max 4 files, 400 tokens per excerpt.
- **Budget Inspection**: Run `context-explain --json` to inspect selections, omit reasons, and token estimates.
- **Tiers**: `Must` sources are never dropped for budget; `Should` sources drop when payload or channel caps (`bootstrap`, `project`, `feature`, `task`, `retrieved`, `durable_memory`) are exceeded.
- **Memory Compaction**: When `memory-audit` warns, run `/context-memory` to compact memory files 30–50% while preserving `##` headings and stable IDs.
