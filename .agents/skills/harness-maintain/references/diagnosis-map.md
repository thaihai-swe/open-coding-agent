# Diagnosis Map: When Agents Underperform

The problem is almost always the harness, not the model.

## Symptom → Root Cause → Fix

| User Complaint | Layer | Root Cause | Fix | Route |
|-|-|-|-|-|
| Same mistake repeats | Constraints | No preventing rule | Add lint, type check, or test | `/harness-maintain improve` → draft LH-* |
| Ignores conventions | Context | Conventions not documented | Write convention; reference from AGENTS.md | `/spec-research` brownfield map |
| Broke working behavior | Verification | No regression test | Add test before changing | `/spec-testing-scenario` |
| Goes off on tangents | Scope | No clear task scope | Structured task list, WIP=1 | `/spec-tasks` |
| Mediocre code | Context | No good examples in context | Add examples to domain pack | `/context-memory` → patterns.md |
| Shallow wrappers | Architecture | Speculative one-adapter seams | Deletion test + two-adapter rule | `/spec-plan` + `code-design.md` |
| Debugs by guessing | Feedback | No red-capable command first | Require a fast failing command | `/spec-research` tight loop |
| Forgets the discussion | Memory | Cross-session context not persisted | Write decisions to `session.md` | `session-end` → session-extracts |
| Declares done too early | Verification | No verification step | AC with proof; run `/harness-verify` | `/harness-verify` |
| Uses wrong patterns | Context | Competing patterns, no guidance | Document which pattern when | `/context-memory` → domain pack |
| Inconsistent quality | Feedback | No eval loop | Add rubric; multi-pass eval | `/harness-maintain eval` |
| Too slow / too costly | Architecture | Over-engineered harness | Remove components that add no value | `## When to Simplify` |

## Diagnosis Process

### Step 1: Identify the Layer

1. **Context**: missing information → fix routing or docs
2. **Constraints**: errors not prevented → add lint/test/type rule
3. **Feedback**: agent does not know it failed → add verification
4. **Architecture**: single agent cannot handle complexity → split only if proven
5. **Scope**: task too big or ambiguous → break it up

### Step 2: Apply Minimal Fix

- Missing context → one doc or domain-pack entry
- Missing constraint → one lint rule or test
- Missing feedback → one verification step
- Architecture → two agents only if one truly cannot handle it
- Scope → smaller pieces

One rule per mistake. Do not over-engineer.

### Step 3: Verify

1. Reproduce the original scenario
2. Confirm the fix prevents it
3. Confirm nothing else broke

## One Rule Per Mistake

1. Fix the immediate issue
2. Ask: could a rule prevent this forever?
3. Yes → add lint, test, type, or convention
4. No → add context (docs, examples, domain pack)

See CC-008 in `corebase-specharness/memories/repo/core-policies.md`.

## When to Simplify

Over-engineered if: more time on harness than work; redundant checks; rules that never fire; cost up without quality gain.

1. Disable one component and benchmark
2. No quality drop → remove it
3. Quality dropped → keep it and document why
4. Repeat

Treat simplification as maintenance.
