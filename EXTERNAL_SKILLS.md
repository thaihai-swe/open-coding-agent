# External Engineering Skills

CoreBase SpecHarness ships 11 workflow, harness, memory, ADR, and testing skills. Optional technical specialist workflows are maintained separately in the Agent Engineering Skills toolkit. Architecture health surveys (`improve-codebase-architecture`) are optional and installed only when an adopter wants them.

CoreBase SpecHarness does not install, route, load, or validate these external skills. Their installation is optional and does not add Node.js or `npx` as a CoreBase SpecHarness requirement.

## Discover and install selected skills

Preview the external catalog:

```bash
npx skills add thaihai-swe/Agent-Engineering-Skills --list
```

Install one selected skill:

```bash
npx skills add thaihai-swe/Agent-Engineering-Skills \
  --skill codebase-documenter
```

Install multiple selected skills:

```bash
npx skills add thaihai-swe/Agent-Engineering-Skills \
  --skill technical-docs \
  --skill visualize-diagram
```

Install the optional architecture health survey:

```bash
npx skills add thaihai-swe/Agent-Engineering-Skills \
  --skill improve-codebase-architecture
```

Use the `npx skills` prompts or flags to select the target coding agent and project or global installation scope. CoreBase SpecHarness intentionally does not recommend installing every external skill by default.

## Migration from embedded CoreBase SpecHarness skills

| Removed CoreBase SpecHarness skill | Closest external skill | Notes |
| --- | --- | --- |
| `repo-documenter` | `codebase-documenter` | Repository onboarding and architecture documentation. |
| `technical-contracts` | `technical-docs` | API, CLI, schema, migration, and integration documentation. |
| `visualize-diagram` | `visualize-diagram` | Same skill name; now maintained outside CoreBase SpecHarness. |
| `design-analysis` | `design-patterns` | Closest specialist; its current focus is TypeScript/JavaScript design patterns. |
| `improve-codebase-architecture` | `improve-codebase-architecture` | Codebase health survey, shallow module detection, and visual HTML report. |

The external toolkit also offers `architecture-diagram` and `coding-rules-generator`. These are optional additions, not replacements for former CoreBase SpecHarness routes.

## Working with CoreBase SpecHarness

External skills can produce documentation and diagrams that are linked from project documentation or feature artifacts. CoreBase SpecHarness verifies those outputs only when a feature acceptance criterion or task explicitly puts them in scope.

Do not pass external skill names to:

```bash
python3 corebase-specharness/scripts/core/cli.py context-load --skill <external-skill>
```

External skills do not own CoreBase SpecHarness phase transitions, task state, acceptance decisions, or final verification. `/harness-verify` remains the CoreBase SpecHarness authority for closing a feature.

CoreBase SpecHarness support covers only this separation and its own route/runtime behavior. External-skill installation, Node/npx availability, dependency conflicts, vendor behavior, and external-skill output are outside CoreBase SpecHarness runtime support.

## Upgrade behavior

When an existing project upgrades, the installer backs up and removes only the old CoreBase SpecHarness-owned specialist files listed in the manifest. It preserves unrelated files that an adopter placed in those old directories and does not manage agent-specific external-skill installations.
