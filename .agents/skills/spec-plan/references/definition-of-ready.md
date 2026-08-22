# Definition of Ready

A feature may enter implementation when:
- Profile is recorded and artifact depth matches it.
- Scope, non-goals, and preserved behavior are clear.
- Every required AC has a proof method at a declared public seam.
- Module map defines single responsibility, dependency direction, public seam, and split/co-location rationale per path.
- Design-it-Twice alternatives are recorded when two interface shapes were viable.
- Plan, tasks, dependency order, and AC mapping pass validation.
- Tasks are tracer-bullet slices, or an expand-contract sequence is explicit for a wide refactor.
- Simple: compact plan/task artifacts contain expected files, one executable task, and a validation command.
- No blocking open question or `[:HALT` marker remains.
