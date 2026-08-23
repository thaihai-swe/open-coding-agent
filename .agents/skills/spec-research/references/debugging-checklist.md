# Debugging Checklist

Phase 1 is a hard gate. Do not hypothesise until a red-capable command exists.

## Phase 1: Tight feedback loop

- [ ] Named one command (test, script, curl) that has already been run at least once.
- [ ] Command is **red-capable**: it drives the actual bug path and asserts the user's exact symptom.
- [ ] Command is **deterministic** (or, for flakes, pinned at a high reproduction rate).
- [ ] Command is **fast**: seconds, not minutes.
- [ ] Command is **agent-runnable** without an unscripted human in the loop.
- [ ] Invocation and redacted output are captured.

If no loop can be built, stop. Write `[:HALT INCONCLUSIVE]` and list what was tried.

## Phase 2: Reproduce and minimise

- [ ] Loop produces the failure the user described, not a nearby different failure.
- [ ] Failure is reproducible (or high-rate for flakes).
- [ ] Repro is minimised: every remaining element is load-bearing.

## Phase 3: Hypothesise

- [ ] 3–5 ranked, falsifiable hypotheses written as: `If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse.`
- [ ] Ranked list shown to the user before testing (do not block if the user is unavailable).

## Phase 4: Instrument

- [ ] Each probe maps to one Phase 3 prediction.
- [ ] One variable changed at a time.
- [ ] Debug logs tagged `[DEBUG-<id>]`.

## Phase 5: Fix boundary and regression proof

- [ ] Minimised repro turned into a failing test at a correct public seam, or absence of seam documented.
- [ ] Original (un-minimised) loop re-run after the candidate fix.

## Phase 6: Cleanup

- [ ] All `[DEBUG-<id>]` instrumentation removed or listed for implement to remove.
- [ ] Throwaway harness deleted or marked throwaway.

## Root Cause Record

Write this block into `analysis.md` once a cause is confirmed:

- Symptom:
- Red-capable command (invocation + redacted output):
- Minimised reproduction:
- First failing boundary:
- Ranked hypotheses (If X, then changing Y / Z):
- Evidence that confirmed or falsified each:
- Confirmed cause:
- Contributing factors:
- Fix boundary:
- Regression proof / seam:
- Debug tag prefix used (`[DEBUG-<id>]`):
- Remaining uncertainty:

## Prototype Technique

Use a prototype only to answer a named uncertainty. Do not promote a prototype into production code.

### Experiment

- Question:
- Smallest experiment / throwaway command:
- Inputs / assumptions:
- Success signal (must be red-capable or observable):
- Result / evidence:
- Decision enabled:
- Delete or preserve prototype:

### Safety

- Keep the prototype isolated from production modules.
- Tag temporary logs `[DEBUG-<id>]` and remove them before research exit.
- If the experiment cannot be made deterministic, write `[:HALT INCONCLUSIVE]`.
