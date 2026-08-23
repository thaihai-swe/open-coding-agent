# Project Constraints

> Ownership: `Adopter-owned`

Filled from `/starter-init` evidence where facts exist. Product SLOs, compliance, and ops remain `[USER REVIEW NEEDED]`.

## Performance Budgets

| Metric | Budget | Measurement | Enforcement |
|-|-|-|-|
| QueryEngine tool/provider loop | `max_turns=8` default | `src/application/query_engine.py`; `tests/query_engine_check.py` | Loop stops with `termination_reason="max_turns_reached"` |
| `web_fetch` body | 4000 characters | `src/tools/handlers/network.py` | Truncate |
| `web_fetch` timeout | 10 seconds | same | `urlopen(..., timeout=10)` |
| `bash` timeout | min(requested, 600000) ms | `src/tools/handlers/shell.py` | `subprocess.run` timeout |
| Provider HTTP timeout | `[UNKNOWN]` | `OpenAIProvider` `urlopen` has no timeout argument | None |
| API response time (p95) | `[USER REVIEW NEEDED]` | | |
| Memory usage | `[USER REVIEW NEEDED]` | | |

## Compliance Requirements

| Standard | Scope | Key Requirements | Verification |
|-|-|-|-|
| `[USER REVIEW NEEDED]` | | | |

## Security Requirements

- Authentication model: Provider Bearer token from env or `.secrets/config.json`. No end-user auth.
- Authorization model: Interactive approve/deny for MEDIUM/HIGH tools; `check_permission` + `PROTECTED_PATHS` / `PROTECTED_KEYS`. LOW tools (including `read_file`) skip UI approval.
- Data classification: `[USER REVIEW NEEDED]`
- Encryption requirements: `[UNKNOWN]` — default urllib TLS only
- Secret management: JSON file and/or env vars. Session encode drops dict keys containing `api_key` or `authorization`. `.secrets/` is **not** in `.gitignore`.
- Audit logging: `[UNKNOWN]` — JSON UI events to stdout; no audit log file

## Deployment Model

- Environments: Local developer machine only (evidence)
- Release cadence: `[USER REVIEW NEEDED]`
- Deployment method: `python3 -m src.cli` after venv (`documents/how-to-run.md`)
- Rollback strategy: `[USER REVIEW NEEDED]`
- Feature flags: none found

## Technology Constraints

### Approved

| Category | Approved Options |
|-|-|
| Languages | Python 3.11+ for `src/` (`StrEnum`); harness CLI Python >=3.10 |
| Frameworks | None in `src/` (stdlib only) |
| LLM transport | OpenAI-compatible HTTP `/chat/completions` |
| Databases | Local JSON session files |
| Infrastructure | Local process |

### Forbidden

| Technology | Reason |
|-|-|
| `[USER REVIEW NEEDED]` | No explicit forbid list in repo |

### Version Requirements

- App: Python 3.11+ (evidence: `from enum import StrEnum`)
- Harness: Python >=3.10 (`manifest.json`)
- No pinned third-party versions (no lockfile)

## Operational Constraints

- Uptime SLA: `[USER REVIEW NEEDED]`
- Monitoring: `[USER REVIEW NEEDED]`
- Alerting: `[USER REVIEW NEEDED]`
- On-call: `[USER REVIEW NEEDED]`
- Incident response: `[USER REVIEW NEEDED]`
- CI: none (no `.github/workflows`)

## Accessibility Requirements

- Standard: `[USER REVIEW NEEDED]`
- Testing tools: none found
- Key requirements: Terminal REPL; JSON mode for structured events

## Budget & Resource Constraints

- No third-party runtime dependencies declared for `src/`
- Provider cost/rate limits: `[USER REVIEW NEEDED]`
