# Prototype Technique

Use a prototype only to answer a named uncertainty. Do not promote a prototype into production code.

## Experiment

- Question:
- Smallest experiment / throwaway command:
- Inputs / assumptions:
- Success signal (must be red-capable or observable):
- Result / evidence:
- Decision enabled:
- Delete or preserve prototype:

## Safety

- Keep the prototype isolated from production modules.
- Tag temporary logs `[DEBUG-<id>]` and remove them before research exit.
- If the experiment cannot be made deterministic, write `[:HALT INCONCLUSIVE]`.
