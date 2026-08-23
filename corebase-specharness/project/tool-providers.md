---
providers:
  review:
    active: none
    mode: optional
  code-intelligence:
    active: none
    mode: optional
---

# Tool Providers

CoreBase SpecHarness routes specialized work through optional local tool providers. The installer does not install, authenticate, index, or enable providers. An adopter explicitly selects a provider after setup. Providers remain optional (`mode: optional`) and disabled (`active: none`) by default.

CoreBase SpecHarness supports its provider registry and recorded adapter outcomes. Provider installation, credentials, model selection, MCP setup, vendor output, and vendor availability remain adopter/vendor responsibilities.

## Why providers are opt-in by default

- **Zero hard dependencies**: The base CoreBase SpecHarness runtime requires only Python 3.10+ and standard tools. It works immediately without requiring npm, global node binaries, external provider accounts, or API keys.
- **Independent built-in review**: `/harness-verify` executes a mandatory two-axis review (standards and spec alignment) using agent analysis. External tools like `open-code-review` provide supplementary mechanical evidence rather than replacing review.
- **Adopter control**: Repositories that want automated OCR on every change can opt in and enforce it project-wide by setting `mode: required`.

## Configuration

- `providers.review.active`: review provider ID, normally `open-code-review` or `none` (default: `none`).
- `providers.code-intelligence.active`: code intelligence provider ID, such as `gitnexus`, `codebase-memory-mcp`, or `none` (default: `none`).
- `mode`:
  - `optional` (default): records unavailable providers as `deferred` without blocking verification or feature closeout.
  - `required`: blocks `verify` and fails the verification gate when the provider executable is missing, unconfigured, or returns an error.

Provider IDs and supported local actions are listed in `references/tool-providers-registry.json`.

## Review provider (OpenCodeReview)

### 1. Opt-in setup

Install OpenCodeReview and configure its LLM backend:

```bash
npm install -g @alibaba-group/open-code-review
ocr config provider
ocr config model
```

### 2. Enable in this project

Set the active provider in this file's frontmatter:

```yaml
providers:
  review:
    active: open-code-review
    mode: optional # or "required" to mandate OCR passes for all feature closeouts
```

### 3. Usage and verification

- Check provider status: `python3 corebase-specharness/scripts/core/cli.py provider-check --category review --json`
- Manual diff review: `ocr review` (or `ocr review --from <base> --to <head>` for a branch range)
- Automatic verification: `python3 corebase-specharness/scripts/core/cli.py verify --skill harness-verify` automatically executes the active review provider action (`ocr review`).
- `/harness-verify` records provider status and findings in `artifacts/features/<slug>/review.md` and appends run history to `corebase-specharness/generated/provider-runs.json` (capped to 50 runs).

## Code intelligence providers

Setup and capability maps:

- OpenCodeReview: `corebase-specharness/project/providers/open-code-review.md`
- GitNexus: `corebase-specharness/project/providers/gitnexus.md`
- codebase-memory-mcp: `corebase-specharness/project/providers/codebase-memory-mcp.md`

```bash
npm install -g gitnexus
gitnexus analyze && gitnexus setup
```

The codebase memory MCP provider can be configured through its own MCP integration and indexed with `codebase-memory-mcp index <repository>`.

Use capability intents rather than provider-specific names: concept exploration, symbol context, upstream/downstream impact, changed-symbol detection, and safe rename. GitNexus and codebase-memory MCP semantic queries run through their own agent/MCP integrations; `python3 corebase-specharness/scripts/core/cli.py provider-run --category code-intelligence --action refresh` only runs a declared local refresh action.

## Adding a provider

1. Add the provider to `references/tool-providers-registry.json`.
2. Add setup and capability mapping guidance under `corebase-specharness/project/providers/<id>.md`.
3. Add registry validation and an argv-safe local action to the provider handler when execution is required.
4. Document whether the provider is optional or required and its failure behavior.
5. Run `python3 corebase-specharness/scripts/core/cli.py doctor --root <project>` and the installer dry-run from the engine checkout before shipping.
