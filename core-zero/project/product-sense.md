# Product Sense

> Ownership: `Adopter-owned`
> Status: Evidence-backed skeleton only. Product decisions are `[USER REVIEW NEEDED]`.

## Product Vision

open-coding-agent is an OpenAI-compatible Python coding-agent REPL: a local terminal loop that talks to a chat-completions endpoint and can run file, search, network, and shell tools after user approval.

Remaining product detail (personas, SLOs, competitive positioning) is `[USER REVIEW NEEDED]`.

## Problem Statement

`[USER REVIEW NEEDED]`

Observed gap the code already tries to cover: drive an LLM coding loop from the terminal with persisted sessions, streaming text, and an interactive approve/deny gate on HIGH/MEDIUM tools.

## Target Users & Personas

| Persona | Role | Primary Goal | Key Pain Point |
|-|-|-|-|
| `[USER REVIEW NEEDED]` | `[UNKNOWN]` | `[UNKNOWN]` | `[UNKNOWN]` |

Inferred (unconfirmed): a developer running `python3 -m src.cli` against a local or remote OpenAI-compatible model.

## Success Metrics

| Metric | Current | Target | Measurement Method |
|-|-|-|-|
| Unit checks passing | 18/18 `tests/*_check.py` (2026-04-08) | Keep green | `python3 -m unittest discover -s tests -p "*_check.py"` |
| `[USER REVIEW NEEDED]` product SLO | `[UNKNOWN]` | `[USER REVIEW NEEDED]` | `[UNKNOWN]` |

## Domain Context & Business Rules

Observed (not product-confirmed):

- Missing provider config is fatal at process start (exit `2`).
- HIGH/MEDIUM tools require interactive approve; denial does not abort the session.
- Sessions persist under `.sessions/` and survive Ctrl+C (exit `130`).
- `web_search` is a stub returning `example.com`; `skill` only accepts `"known"`.

## Competitive / Market Context

`[USER REVIEW NEEDED]`

`documents/BUILDING_A_CODING_AGENT.md` cites Claude Code, Claw Code, Learn Claude Code, and Cordum as design references. That is a roadmap, not a shipping comparison.

## Product Principles

`[USER REVIEW NEEDED]` — interim engineering principles from AGENTS.md / observed code:

1. Preserve existing observable CLI and test contracts unless a spec changes them.
2. Do not invent product vision, SLOs, or compliance.
3. Fail loud: missing config and provider errors are explicit `ProviderError`s.

## User Journeys

### Journey 1: Start a new REPL session (observed)

1. Configure `.secrets/config.json` or `OPENAI_*` env vars (`documents/how-to-run.md`; example file missing).
2. Run `python3 -m src.cli`.
3. Type prompts at `> `; approve or deny HIGH/MEDIUM tools when asked.
4. Ctrl+C saves the session and exits `130`.

### Journey 2: Resume a session (observed)

1. Run `python3 -m src.cli --session <session-id>`.
2. `SessionStore.load` restores `.sessions/<id>.json` history.

### Journey 3: `[USER REVIEW NEEDED]`

## Open Questions

- Who is the primary user and what job are they hiring this CLI for?
- What does success look like (quality, latency, cost, safety)?
- Is the blueprint the intended product, or is the current stdlib REPL the product?
- Should `.secrets/` be gitignored and should an example config ship?
