# Harness Config

## Index

- Repository Identity
- Work Tracking
- Artifact Routing
- Verification Commands
- Session Defaults
- Environment And Access
- Conventions That Affect Automation
- Delivery Loop Lifecycle
- Known Limits & Workarounds

## Repository Identity

- Project name: open-coding-agent — OpenAI-compatible Python coding-agent REPL
- Repository type: Brownfield Python coding-agent CLI with CoreZero installed as harness
- Primary code roots: `src/`, `tests/`, `documents/`
- Default working branch: `main`
- Supported agent clients: portable `AGENTS.md`

## Work Tracking

- Issue tracker mode: `[USER REVIEW NEEDED]`
- Issue/project location: `[UNKNOWN]`
- Default work item format: `[USER REVIEW NEEDED]`
- Required labels or states: `[UNKNOWN]`
- Escalation / blocker handling: Stop and ask user

## Artifact Routing

- Feature artifact root: `artifacts/features/<slug>/`
- Docs root: `core-zero/` and `documents/`
- Architecture doc path: `core-zero/project/architecture.md`
- Security policy path: `core-zero/memories/repo/core-policies.md` `## Security Policy`
- Learned heuristics path: `core-zero/memories/repo/learned-heuristics.md`
- ADR location: `core-zero/project/adr/[number]-[slug].md`
- Generated documentation location: `core-zero/generated/`
- Brownfield map: `core-zero/memories/repo/brownfield/brownfield-map.md`

## Verification Commands

- Project unit checks (observed, unconfirmed as harness gates):
  - `python3 tests/provider_check.py`
  - `python3 tests/session_check.py`
  - `python3 tests/query_engine_check.py`
  - `python3 tests/terminal_ui_check.py`
  - `python3 tests/cli_check.py`
  - or `python3 -m unittest discover -s tests -p "*_check.py"`
- Lint / format command: none observed
- Typecheck command: none observed
- Build command: none (interpreted Python)
- Mechanical gate command: `python3 core-zero/scripts/core/cli.py verify --feature <slug> --skill harness-verify`
- Project gate commands: `[DEFERRED]` — `core-zero/project/harness-config.yaml` keeps `gates: []` and `project_setup.status: deferred` by adopter choice

## Session Defaults

- Session bootstrap skill: `/starter-init`
- Session state path: `.corezero/sessions/<slug>/session.md`
- When to checkpoint: After completing a skill or major edit wave
- Context compaction triggers: Raw grep output, large file listings, superseded design detail
- Stale-context eviction rules: Summarize raw tool output after extracting findings
- When to stop and escalate: After two failed corrections on the same issue

## Environment And Access

- Required local services: an OpenAI-compatible `/chat/completions` endpoint to run the REPL
- Required env files or secrets handling: `.secrets/config.json` or `OPENAI_API_BASE` + `OPENAI_API_KEY` + `OPENAI_MODEL`; optional `CONFIG_FILE`
- Sandbox / permission watchouts: do not print secrets; `.secrets/` is gitignored as of Phase B
- Browser / UI verification target: N/A (terminal CLI)

## Conventions That Affect Automation

- Feature slug format: kebab-case
- Branch naming format: `[USER REVIEW NEEDED]`
- Commit / PR expectations: `[USER REVIEW NEEDED]`
- Required reviewers or owners: `[UNKNOWN]`

## Delivery Loop Lifecycle

Every feature follows the peer-skill delivery route. `/starter-init` is only
for an untailored repository. First feature on this brownfield repo should
start at `/spec-research` unless the subsystem is already mapped. Then
`/spec-requirements`, `/spec-plan`, `/spec-tasks`, `/spec-implement`,
`/harness-verify`, and `/context-memory` when candidate lessons exist.

## Known Limits & Workarounds

- No package manifest, CI, linter, or formatter.
- Tool handlers are untested.
- `documents/config.example.json` is missing.
- `web_search` and several tools are stubs.
- Observability log: Empty until real failures get captured.
