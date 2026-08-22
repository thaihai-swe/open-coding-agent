# Verification Review

## Metadata

- Feature slug: 
- Date: 
- Status: 

## Decision

- Decision: Pass | Pass with Follow-Up Debt | Fail
- Release recommendation:
- Short summary:

## Findings

List findings first. If there are no findings, say `No findings.`

- Finding ID:
  Severity: High | Medium | Low
  Area:
  Evidence:
  Why it matters:
  Recommended action:

## Evidence Review

- Fresh automated evidence reviewed:
- Fresh manual evidence reviewed:
- Stale or missing evidence:

## AC-to-Proof Mapping

| AC-ID | Task-ID | Proof evidence | Pass/Fail |
|---|---|---|---|
| | | | |

## Design Conformance

| Design element | Evidence location | Pass/Fail |
|---|---|---|
| | | |

## Security Audit

- Findings:
- Evidence:
- Result: Pass | Follow-Up | Fail

## Dropped Behavior

- Behavior reviewed:
- Result: None | Accepted | Reopened
- Evidence:

## Standards Review

Procedure-only. Audit the diff against repo standards and the smell baseline. Run independently from Spec Review. Repo documented rules always override the smell baseline. Baseline smells are judgement calls, never hard violations. Skip smells tooling already enforces.

Fowler smell baseline (cite the hunk):
- Mysterious Name: a name that does not reveal intent. Fix: rename.
- Duplicated Code: the same logic shape in more than one hunk. Fix: extract and call from both.
- Feature Envy: a method that reaches into another object's data more than its own. Fix: move the method.
- Data Clumps: the same fields or params travelling together repeatedly. Fix: bundle into a type.
- Primitive Obsession: a primitive standing in for a domain concept. Fix: give it a small type.
- Repeated Switches: the same switch on the same type in multiple places. Fix: polymorphism or one shared map.
- Shotgun Surgery: one change forces scattered edits across many files. Fix: gather into one module.
- Speculative Generality: abstraction or parameters added for needs the spec does not have. Fix: delete.

Report:
- Standards findings:
- Smell findings (judgement calls, cite hunk):
- Result: Pass | Advisory | Fail

## Spec Alignment Review

Procedure-only. Audit the diff line-by-line against `spec.md`. Run independently from Standards Review. Cite the spec line for each finding.

Report:
- Missing or partial acceptance criteria:
- Unrequested behavior (scope creep):
- Requirements that look implemented but the implementation looks wrong:
- Result: Pass | Advisory | Fail

Do not merge or rerank findings across Standards and Spec axes. Present them side by side.

## Drift Review

- Drift detected: Yes | No
- Drift summary:
- Return-to-spec required: Yes | No

## Risk Review

- Security or privacy notes:
- Regression risk:
- Operational or observability risk:

## Provider Review

- Provider command:
- Provider status:
- Provider findings summary:

## Capabilities Used / Deferred

- Used optional helpers:
- Deferred optional helpers:
- Why deferred:

## Follow-Up

- Reopened tasks:
- Deferred work:
- Next required action:
