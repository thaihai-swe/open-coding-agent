# Product Sense

> Ownership: `Adopter-owned`

Adopter decision during `/starter-init` on 2026-08-22: the product is the **coding-agent CLI** under `src/`. CoreBase SpecHarness is the delivery kit, not the product.

## Product Vision

A local OpenAI-compatible coding-agent REPL that runs tools (files, shell, search, network) against a configured chat-completions endpoint.

## Problem Statement

[USER REVIEW NEEDED] — users, jobs-to-be-done, and why this agent vs existing CLIs were not stated.

## Target Users & Personas

| Persona | Role | Primary Goal | Key Pain Point |
|-|-|-|-|
| [USER REVIEW NEEDED] | | | |

## Success Metrics

| Metric | Current | Target | Measurement Method |
|-|-|-|-|
| [USER REVIEW NEEDED] | | | |

## Domain Context & Business Rules

- Provider settings come from env (`OPENAI_API_BASE`, `OPENAI_API_KEY`, `OPENAI_MODEL`) or `.secrets/config.json` (`CONFIG_FILE` override).
- Missing configuration is a hard start failure (CLI exit 2).
- `documents/BUILDING_A_CODING_AGENT.md` is out of scope and is not a product or architecture contract.

## Competitive / Market Context

[USER REVIEW NEEDED]

## Product Principles

1. `src/` is the system of record for agent behavior.
2. CoreBase SpecHarness skills govern delivery artifacts; they are not runtime agent features.
3. [USER REVIEW NEEDED] — remaining product tiebreakers

## User Journeys

### Journey 1: Start a REPL session

1. Configure provider via env or `.secrets/config.json`.
2. Run `python3 -m src.cli`.
3. Chat; approve or deny MEDIUM/HIGH tools when prompted.
4. Interrupt with Ctrl+C to preserve the session (exit 130).

### Journey 2: Resume a session

1. Run `python3 -m src.cli --session <session-id>`.
2. History loads from `.sessions/<id>.json` when that file exists.

### Journey 3: JSON event mode

1. Run `python3 -m src.cli --json`.
2. UI emits structured JSON events (authorize prompt still uses stdin).

## Open Questions

- Who are the users and what is success?
- Should a `config.example.json` exist (documented path is missing)?
- When should verification gates be confirmed so features can close without override?
