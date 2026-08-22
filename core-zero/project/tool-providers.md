---
schema_version: 1
providers:
  review:
    active: none
    mode: optional
  code-intelligence:
    active: none
    mode: optional
---

# Tool Providers

CoreZero routes specialized work through optional local tool providers. The installer does not install, authenticate, index, or enable providers. An adopter explicitly selects a provider after setup. Providers remain optional unless a project policy sets a category to `required`.

CoreZero supports its provider registry and recorded adapter outcomes. Provider installation, credentials, model selection, MCP setup, vendor output, and vendor availability remain adopter/vendor responsibilities.

## Configuration

- `providers.review.active`: review provider ID, normally `open-code-review` or `none`.
- `providers.code-intelligence.active`: code intelligence provider ID, such as `gitnexus`, `codebase-memory-mcp`, or `none`.
- `mode`: `optional` records unavailable providers as deferred; `required` blocks the relevant gate when the provider is unavailable.

Provider IDs and supported local actions are listed in `references/tool-providers-registry.json`.

## Review provider

Install OpenCodeReview, then set `providers.review.active: open-code-review`:

```bash
npm install -g @alibaba-group/open-code-review
ocr config provider
ocr config model
```

Run a workspace diff review with `ocr review`. Use `ocr review --from <base> --to <head>` for a branch range, `ocr review --commit <sha>` for one commit, or `ocr scan --path <path>` for a full-file audit. `/harness-verify` records provider status and findings in `artifacts/features/<slug>/review.md` and appends machine-readable run history to `core-zero/generated/provider-runs.json` (capped to the 50 most recent runs).

## Code intelligence providers

Setup and capability maps:

- OpenCodeReview: `core-zero/project/providers/open-code-review.md`
- GitNexus: `core-zero/project/providers/gitnexus.md`
- codebase-memory-mcp: `core-zero/project/providers/codebase-memory-mcp.md`

```bash
npm install -g gitnexus
gitnexus analyze && gitnexus setup
```

The codebase memory MCP provider can be configured through its own MCP integration and indexed with `codebase-memory-mcp index <repository>`.

Use capability intents rather than provider-specific names: concept exploration, symbol context, upstream/downstream impact, changed-symbol detection, and safe rename. GitNexus and codebase-memory MCP semantic queries run through their own agent/MCP integrations; `python3 core-zero/scripts/core/cli.py provider-run --category code-intelligence --action refresh` only runs a declared local refresh action.

## Adding a provider

1. Add the provider to `references/tool-providers-registry.json`.
2. Add setup and capability mapping guidance under `core-zero/project/providers/<id>.md`.
3. Add registry validation and an argv-safe local action to the provider handler when execution is required.
4. Document whether the provider is optional or required and its failure behavior.
5. Run `python3 core-zero/scripts/core/cli.py doctor --root <project>` and the installer dry-run from the engine checkout before shipping.
