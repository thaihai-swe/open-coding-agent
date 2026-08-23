# Debugging Checklist

Phase 1 is a hard gate. Do not hypothesise until a red-capable command exists.

## Phase 1: Tight feedback loop

- [ ] Named one command (test, script, curl) already run at least once.
- [ ] **Red-capable**: drives the actual bug path and asserts the user's symptom.
- [ ] **Deterministic** (or pinned high-rate for flakes).
- [ ] **Fast**: seconds, not minutes.
- [ ] **Agent-runnable** without an unscripted human.
- [ ] Invocation and redacted output captured.

If no loop can be built, write `[:HALT INCONCLUSIVE]` and list what was tried.

## Phase 2: Reproduce and minimise

- [ ] Loop produces the failure the user described.
- [ ] Failure is reproducible (or high-rate for flakes).
- [ ] Repro is minimised: every remaining element is load-bearing.

## Phase 3: Hypothesise

- [ ] 3–5 ranked, falsifiable hypotheses: `If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse.`
- [ ] Ranked list shown to the user before testing (do not block if unavailable).

## Phase 4: Instrument

- [ ] Each probe maps to one Phase 3 prediction.
- [ ] One variable at a time.
- [ ] Debug logs tagged `[DEBUG-<id>]`.

## Phase 5: Fix boundary and regression proof

- [ ] Minimised repro became a failing test at a public seam, or seam absence documented.
- [ ] Original (un-minimised) loop re-run after the candidate fix.

## Phase 6: Cleanup

- [ ] All `[DEBUG-<id>]` instrumentation removed or listed for implement.
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
- Debug tag prefix (`[DEBUG-<id>]`):
- Remaining uncertainty:

## Prototype Technique

Use a prototype only to answer a named uncertainty. Do not promote it to production.

### Experiment

- Question:
- Smallest experiment / throwaway command:
- Inputs / assumptions:
- Success signal (red-capable or observable):
- Result / evidence:
- Decision enabled:
- Delete or preserve prototype:

### Safety

- Keep the prototype isolated from production modules.
- Tag temporary logs `[DEBUG-<id>]` and remove them before research exit.
- If the experiment cannot be deterministic, write `[:HALT INCONCLUSIVE]`.
