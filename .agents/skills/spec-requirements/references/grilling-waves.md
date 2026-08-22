# Clarification Waves

Ask only questions that can change scope, profile, design, or proof. Stop when the current wave has no blockers.

1. **Outcome:** user, problem, desired observable result.
2. **Scope:** in/out, non-goals, preserved behavior.
3. **Behavior:** happy path, edge/error path, acceptance proof.
4. **Boundary:** dependencies, contracts, security, data, migrations.
5. **Delivery:** profile, file targets, validation command, suggested handoff.

Simple features normally stop after waves 1–3. Moderate adds boundary questions. Complex continues until risks and decisions are explicit.

## Frontier-Round Protocol

Organize open questions as a **design tree**. In each round, identify every question whose prerequisites are already settled — this is the current **frontier**. Ask the entire frontier together in one numbered batch. Include a recommended answer for each question. Wait for the user's responses before computing the next round.

```
❓ Q1 — <question title>: <question body>
➡ Recommended: <your recommended answer>

❓ Q2 — <question title>: <question body>
➡ Recommended: <your recommended answer>
```

A question whose answer depends on another question still open in this round belongs to a **later round**, not this one. Each response resolves settled questions, clears their downstream blockers, and expands the frontier.

## Fact vs. Decision Split

Finding **facts** is the agent's job, not the user's.

- Discover repository facts through inspection, codebase search, or a bounded background subagent.
- Ask the user only for **decisions** that change scope, trade-offs, profile, or acceptance proof.
- Do not block a round on a fact you can look up. Run the lookup in parallel; ask the decisions that do not depend on it now.

## Inline Domain Terminology Capture

When a term is resolved during grilling, capture it immediately into `core-zero/project/glossary.md` (or the relevant `core-zero/memories/domain/<name>/glossary.md`). Do not batch terminology updates until after the session. Create the file if it does not exist; use the existing format. `core-zero/project/glossary.md` is strictly a glossary — no spec, implementation, or design content belongs there.
