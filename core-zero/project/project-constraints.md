# Project Constraints

> Ownership: `Adopter-owned`
> Source: Phase A evidence (2026-04-08). Policy rows remain `[USER REVIEW NEEDED]` until adopter confirmation.

This seed is intentionally blank project input. Fill it with adopter-specific constraints; do not copy kit security policy or rules into this file.

## Performance Budgets

| Metric | Budget | Measurement | Enforcement |
|-|-|-|-|
| API response time (p95) | `[USER REVIEW NEEDED]` | `[UNKNOWN]` | `[UNKNOWN]` |
| Page load time | N/A (CLI, no web UI) | N/A | N/A |
| Bundle size | N/A (no frontend bundle) | N/A | N/A |
| Memory usage | `[USER REVIEW NEEDED]` | `[UNKNOWN]` | `[UNKNOWN]` |
| Database query time | N/A (no database) | N/A | N/A |
| Tool `bash` timeout | 600000 ms cap (`src/tools/handlers/shell.py`) | Handler `min(timeout, 600000)` | Code |
| `web_fetch` timeout | 10 seconds (`src/tools/handlers/network.py`) | `urlopen(..., timeout=10)` | Code |
| `web_fetch` body | First 4000 chars | Handler slice | Code |
| `glob_search` results | 100 paths, newest first | Handler slice | Code |
| `grep_search` results | `head_limit` default 250 | Handler early return | Code |

## Compliance Requirements

| Standard | Scope | Key Requirements | Verification |
|-|-|-|-|
| `[USER REVIEW NEEDED]` | `[UNKNOWN]` | None declared in repo | `[UNKNOWN]` |

## Security Requirements

- Authentication model: Bearer token to an OpenAI-compatible endpoint. No end-user auth.
- Authorization model: Interactive `[A]pprove/[D]eny` for HIGH/MEDIUM tools. LOW tools run unprompted. After HIGH approve, engine sets `bypass_permissions=True`.
- Data classification: `[USER REVIEW NEEDED]`. Live provider credentials sit in `.secrets/config.json` (mode `0644` observed).
- Encryption requirements: `[USER REVIEW NEEDED]`. Provider uses HTTPS only if `api_base` is `https://`.
- Secret management: Env vars or `.secrets/config.json`. Session store redacts dict keys containing `api_key` / `authorization` only. `.gitignore` currently comments out `# .secrets/`.
- Audit logging: `[UNKNOWN]`. No audit log implemented.

## Deployment Model

- Environments: Local developer machine only (observed)
- Release cadence: `[USER REVIEW NEEDED]`
- Deployment method: Run `python3 -m src.cli` after configuring secrets
- Rollback strategy: `[USER REVIEW NEEDED]`
- Feature flags: None implemented

## Technology Constraints

### Approved

| Category | Approved Options |
|-|-|
| Languages | Python 3.11+ (observed 3.13.13; `StrEnum`) |
| Frameworks | Standard library only (no third-party packages observed) |
| Databases | None |
| Infrastructure | Local process; OpenAI-compatible HTTP endpoint |

### Forbidden

| Technology | Reason |
|-|-|
| `[USER REVIEW NEEDED]` | No explicit forbid list in repo |

### Version Requirements

- Python `>=3.11` required by `enum.StrEnum` in `src/tools/types.py`
- Kit `manifest.json` states `requires_python: ">=3.10"` — that applies to CoreZero scripts, not this app

## Operational Constraints

- Uptime SLA: `[USER REVIEW NEEDED]` (local CLI; no hosted SLA observed)
- Monitoring: `[UNKNOWN]`
- Alerting: `[UNKNOWN]`
- On-call: `[UNKNOWN]`
- Incident response: `[USER REVIEW NEEDED]`

## Accessibility Requirements

- Standard: `[USER REVIEW NEEDED]`
- Testing tools: None observed
- Key requirements: JSON event mode exists (`--json`) as a machine-readable alternative to the REPL renderer

## Budget & Resource Constraints

- Third-party Python packages: none today. Adding one is a product decision, not a default.
- Provider spend / token budget: `[USER REVIEW NEEDED]`. Query engine has no `max_turns` or token cap implemented.
