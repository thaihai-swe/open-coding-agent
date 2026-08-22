## Context Loading

Enter a skill through the envelope. That loads the named route, opens the session, and sets the enter state:

```bash
python3 core-zero/scripts/core/cli.py skill-enter --skill <name> [--feature <slug>] [--task <T-NNN>] --intent "<intent>"
```

`context-load` remains available when you need the pack without changing session or status:

```bash
python3 core-zero/scripts/core/cli.py context-load --skill <name> [--feature <slug>] [--task <T-NNN>] --intent "<intent>"
```

`references/context-routes.yaml` defines the route phase, profile, feature requirement, prerequisites, feature artifacts, writes, handoffs, and source sections. The CLI rejects missing skill names and unknown routes. Feature-bound skills also reject a missing feature slug.

Every pack includes the universal communication and policy bootstrap. `Must`
sources are never dropped for budget reasons; if they exceed the configured
payload, CoreZero retains them and reports the overrun. `Should` sources may be
omitted to remain within budget.

Intent-matched domain packs join the pack when `--intent` words intersect
`triggers:` in `core-zero/memories/domain/<name>/glossary.md`. Record any
loaded pack in `status.md` when the skill procedure asks for it.

CoreZero also retrieves bounded local evidence from the configured repository
roots using the active intent, feature, and task. Inspect the pack with
`python3 core-zero/scripts/core/cli.py context-explain ... --json`; it reports source provenance, trust,
token estimates, and omission reasons. Use repeatable
`--add-source <repo-relative-path>` for an explicit focused expansion.
