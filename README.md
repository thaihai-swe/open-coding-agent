# CoreBase SpecHarness adopter kit

**Version 1.0.0**

CoreBase SpecHarness is a skills-first spec-driven delivery kit. The harness and
context compiler are layers inside that kit. Install copies files and
seeds adopter stubs; `/starter-init` only tailors an untailored repo.

The installed payload has 11 direct peer skills, inspectable bounded
context, spec-driven artifacts, sessions, advisory-by-default
verification, and optional local tool providers.

## Start

### New or untailored repository

1. Run `python3 corebase-specharness/scripts/core/cli.py doctor --json` and read warnings.
2. Invoke `/starter-init` before delivery skills. It tailors project context and
   asks the adopter to confirm repository-native verification gates.
3. Start the appropriate named delivery skill only after tailoring or an
   explicit `[DEFERRED]` decision.

### Existing tailored repository or upgrade

1. Run `python3 corebase-specharness/scripts/core/cli.py doctor --json`.
2. Continue with the appropriate named skill, for example `/spec-plan`.
3. If native slash routing is unavailable, read `skills/<name>/SKILL.md`.

```bash
python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-plan --feature <slug> --intent "design change" --json
python3 corebase-specharness/scripts/core/cli.py context-explain --skill spec-plan --feature <slug> --intent "design change" --json
python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-plan --feature <slug> --handoff spec-tasks --json
python3 corebase-specharness/scripts/core/cli.py task-check --feature <slug>
python3 corebase-specharness/scripts/core/cli.py verify --feature <slug> --skill harness-verify --json
```

A fresh install has `project_setup.status: deferred`, `verification.mode:
advisory`, and no gates. A `verify` exit code of `0` in advisory mode is not a
verification verdict. `Done` requires a successful current-config
`verify --skill harness-verify` record plus `review.md` and Post-Ship Sync, or
a deliberate `--verification-override --override-reason "..."` audit record.
Configure only confirmed project gates in `corebase-specharness/project/harness-config.yaml`.

`references/context-routes.yaml` is the routing authority for CoreBase SpecHarness skills.
`corebase-specharness/project/state-machine.yaml` is the lifecycle authority; adopter `lifecycle_overrides` extend it and add preconditions rather than replacing kit requirements. Coarse phases are labels. `phase-check --skill` and `verify` use one readiness evaluator.
Context packs combine declared route sources, intent-matched domain packs, and
bounded automatic local retrieval with secret redaction, and always expose a
selection manifest. `tasks.md` is canonical task state; `tasks.json` is its
generated sidecar. The root `AGENTS.md` is the portable agent
router; CoreBase SpecHarness does not create vendor-specific instruction files.
`references/tool-providers-registry.json` is the provider inventory. Providers
are optional and are never installed or enabled by CoreBase SpecHarness.
