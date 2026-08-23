# Research Analysis

## Metadata

- Feature/profile:
- Question and scope:
- Current behavior:
- Evidence sources:
- Red-capable command (bug-diagnosis only):
- Subsystem / public seam (brownfield-map only):
- Decision question (ambiguity-resolution only):

## Findings

Separate observed facts from inferences. Cite files, commands, or logs.

- Fact:
- Inference:
- Ranked hypotheses / options (if applicable):
- Confirmed cause or recommended option:

## High Risk Paths

- Boundary or dependency:
- Why it is high risk:
- Preserved contract or behavior:
- Known broken tests / security-sensitive paths:

## Open Questions

- Blocking question:
- Why it blocks:
- Owner:

## Kaizen Countermeasures

- Confirmed cause or strongest conclusion:
- Recurrence prevention:
- Remaining uncertainty:

## Recommendation & Next Step

- Single next proving step:
- Suggested handoff: `/spec-requirements` | `/spec-adr` | user

For Simple features, keep each section to one or two bullets. Do not omit the four procedure headings.

---

## Zoom-Out Prompt

Before choosing a fix or writing a spec, answer:

- What system boundary owns this behavior?
- What public seam is the correct observation point?
- What neighboring behavior must remain unchanged?
- What is the smallest safe change?
- What evidence would disprove the current hypothesis?
- If the change is a wide mechanical refactor, should it use expand -> migrate -> contract?

Record answers in `analysis.md` under `## Findings` and `## High Risk Paths`.

---

## Architecture / Design Investigation (ADI) Template

### Metadata
- Feature / topic:
- Decision question:
- Constraints:

### Abduction (Form Hypotheses)
- Candidate options (minimum 2):
- Expected seam / depth / leverage per option:

### Deduction (Predict Observable Consequences)
- Prediction for Option 1 (`If X, then Y`):
- Prediction for Option 2 (`If X, then Y`):

### Induction (Evidence & Prototype Validation)
- Prototype / experiment command:
- Observed evidence:
- Recommended option:
- Reversibility: `Easy | Moderate | Hard`
- Rejected options & why:
- Follow-up artifact: `plan | ADR | contract | none`
