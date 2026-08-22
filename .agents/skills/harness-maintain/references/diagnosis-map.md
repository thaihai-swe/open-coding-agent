# Diagnosis Map: When Agents Underperform

When the user is frustrated with agent output, the problem is almost always in the harness, not the model. This map identifies the failing harness layer and routes to the targeted fix.

## Symptom → Root Cause → Fix

| User Complaint | Harness Layer | Root Cause | Fix | CoreZero Route |
|-|-|-|-|-|
| "It keeps making the same mistake" | Constraints | No rule preventing it | Add lint rule, type check, or test | `/harness-maintain improve` → draft LH-* rule |
| "It doesn't follow our conventions" | Context | Conventions not documented or discoverable | Write convention in `docs/`, reference from AGENTS.md | `/spec-research` brownfield mapping |
| "It broke something that was working" | Verification | No regression test for existing behavior | Add test before changing | `/spec-testing-scenario` |
| "It goes off on tangents" | Scope | No clear task scope or feature list | Add structured task list, enforce WIP=1 | `/spec-tasks` tasks.md |
| "It writes mediocre code" | Context | No examples of good code in context | Add code examples or patterns to domain pack | `/context-memory` → domain pack patterns.md |
| "It writes shallow wrappers" | Architecture | Speculative seams or one-adapter abstractions | Apply deletion test and two-adapter rule | `/spec-plan` + `code-design.md` Abstraction Check |
| "It debugs by guessing" | Feedback | No red-capable command before hypotheses | Require a fast deterministic failing command first | `/spec-research` tight feedback loop |
| "It forgets what we discussed" | Memory | Cross-session context not persisted | Write decisions to `session.md` | `python3 core-zero/scripts/core/cli.py session-end` → session-extracts |
| "It declares done too early" | Verification | No verification step or checklist | Add AC with proof command, run `/harness-verify` | `/harness-verify` |
| "It uses wrong patterns" | Context | Competing patterns, no guidance on which to use | Document which pattern when in domain pack | `/context-memory` → domain pack |
| "Output quality is inconsistent" | Feedback | No evaluation/feedback loop | Add eval rubric, run multi-pass eval | `/harness-maintain eval` |
| "It takes forever and costs too much" | Architecture | Over-engineered harness or wrong approach | Simplify — remove harness components that don't add value | See `core-zero/rules/ponytail.md` § Harness Simplification |

## Diagnosis Process

### Step 1: Identify the Layer

Ask: Where in the harness stack is the failure?

1. **Context**: Agent doesn't have the right information → fix routing or docs
2. **Constraints**: Agent isn't prevented from making errors → add lint/test/type rule
3. **Feedback**: Agent doesn't know it's failing → add verification step
4. **Architecture**: Single-agent can't handle the task's complexity → split into subagents
5. **Scope**: Task is too big or ambiguous → break into smaller tasks

### Step 2: Apply Minimal Fix

Apply the smallest change that addresses the root cause:

- Missing context → Add one doc file or domain pack entry
- Missing constraint → Add one lint rule or test
- Missing feedback → Add one verification step
- Architecture problem → Split into two agents (only if single agent truly can't handle it)
- Scope problem → Break task into smaller pieces

Do not over-engineer the fix. One rule per mistake. Iterate.

### Step 3: Verify

After applying the fix:
1. Reproduce the original problem scenario
2. Confirm the fix prevents it
3. Confirm the fix doesn't break other things

## One Rule Per Mistake

Every time an agent makes a mistake:

1. Fix the immediate issue
2. Ask: "Could a rule prevent this forever?"
3. If yes → add the rule (lint, test, type, or documented convention)
4. If no → add context (docs, examples, domain pack entries)

Over time, the harness accumulates rules that prevent every mistake the agent has ever made. The error rate converges toward zero for known failure modes. See CC-013 in `core-zero/memories/repo/core-policies.md`.

## When to Simplify

Signs the harness is over-engineered:
- Agent spends more time on harness compliance than actual work
- Multiple redundant checks for the same thing
- Harness rules that never trigger (the model learned past them)
- Cost/time significantly higher without proportional quality gain

How to simplify:
1. Disable one component (lint rule, constraint, doc file) and benchmark
2. If no measurable quality drop → remove it permanently
3. If quality dropped → keep it, document why it's needed
4. Repeat for each suspect component

Harness entropy grows over time. Schedule periodic simplification — treat it as maintenance, not optimization. Remove harness components when the model no longer needs them.
