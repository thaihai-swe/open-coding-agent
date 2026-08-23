# Learned Heuristics

## Purpose

Append-only ledger of evidence-backed operational heuristics discovered during feature delivery and debugging in this repository. Managed via `/context-memory`.

## Entry Template

<!-- Format for appending new LH-NNN entries:
### LH-<NNN>: <Concise Rule Title>
- Trigger: <When does this heuristic apply?>
- Working heuristic: <Concrete rule or guidance to follow>
- Evidence: <Observable failure or feature experience that proved this>
- Confidence: High | Moderate
- Last reviewed: YYYY-MM-DD
- Promote to stronger rule? Yes | No
-->

## Heuristics

### LH-001: Task validation proof must be machine-verifiable
- Trigger:
  - Defining completion criteria in `tasks.md` or verifying feature implementation.
- Working heuristic:
  - Every task must specify a concrete command or test file that runs and exits 0 as its validation proof, rather than vague human descriptions.
- Evidence:
  - Tasks with subjective or unexecutable proof criteria lead to missed edge cases and unverified completions.
- Confidence: High
- Last reviewed: 2026-06-24
- Promote to stronger rule? No

### LH-002: Isolate regression with a focused test before fixing
- Trigger:
  - Investigating a bug or regression report.
- Working heuristic:
  - Write a failing test reproducing the exact defect before modifying production code. Once the fix is applied, verify that the test passes.
- Evidence:
  - Speculative fixes without reproduction tests frequently introduce secondary regressions or mask root causes.
- Confidence: High
- Last reviewed: 2026-06-24
- Promote to stronger rule? No
