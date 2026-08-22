# Zoom-Out Prompt

Before choosing a fix or writing a spec, answer:

- What system boundary owns this behavior?
- What public seam is the correct observation point?
- What neighboring behavior must remain unchanged?
- What is the smallest safe change?
- What evidence would disprove the current hypothesis?
- If the change is a wide mechanical refactor, should it use expand → migrate → contract?

Record the answers in `analysis.md` under `## Findings` and `## High Risk Paths`.
