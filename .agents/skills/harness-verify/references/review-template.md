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

Audit diff against repo standards and Fowler smell baseline. Run independently from Spec Review.

Smell baseline (cite hunk):
- Mysterious Name: intent unclear → rename.
- Duplicated Code: duplicate logic → extract.
- Feature Envy: reaches into external object data → move method.
- Data Clumps: fields/params traveling together → bundle into type.
- Primitive Obsession: primitive standing for domain concept → wrap type.
- Repeated Switches: duplicate switches on type → map/polymorphism.
- Shotgun Surgery: one change scatters edits → gather module.
- Speculative Generality: unrequested abstraction → delete.

Report:
- Standards findings:
- Smell findings (cite hunk):
- Result: Pass | Advisory | Fail

## Spec Alignment Review

Audit diff line-by-line against `spec.md`. Cite spec line for each finding.

Report:
- Missing/partial acceptance criteria:
- Unrequested behavior (scope creep):
- Wrong implementation of requested behavior:
- Result: Pass | Advisory | Fail

Do not merge or rerank findings across Standards and Spec axes. Present them side by side.

## Drift Review

- Drift detected: Yes | No
- Drift summary:
- Return-to-spec required: Yes | No

## Risk Review

- Security/privacy notes:
- Regression risk:
- Operational/observability risk:

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
