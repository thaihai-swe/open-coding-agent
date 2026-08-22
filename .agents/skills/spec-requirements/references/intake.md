# Requirements Intake

Capture only decisions needed to classify and route the feature.

## Intake Summary

- Input type: `new_spec | change_request | maintenance | harness_improvement`
- One-line restatement:
- Profile: `Simple | Moderate | Complex`
- Why now:
- Primary user/outcome:
- Changed boundaries / public seams:
- Preserved behavior:
- Risk flags: `none` or list
- Known constraints:
- Blocking unknowns:
- Next action:

## Fact vs Decision Split

- Discover repository facts (stack, files, existing tests) through inspection or subagents.
- Ask the adopter only for domain, trade-off, and scope decisions using the frontier-round protocol.

## Profile Heuristic

- Simple: one AC, one or two files, obvious behavior, no public contract risk.
- Moderate: multiple files, normal design choice, or several scenarios.
- Complex: uncertainty, migration, public contract, security, performance, or multiple components. Prompt user through proposal and Design-it-Twice.
