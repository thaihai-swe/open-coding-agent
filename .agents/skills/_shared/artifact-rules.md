## Artifact Rules

- Feature artifacts live in `artifacts/features/<slug>/`
- Status file `status.md` tracks delivery phase and high-level progress
- Spec (`spec.md`) defines acceptance criteria with AC-* identifiers and problem statement
- Plan (`plan.md`) defines approach, public seams, module map, risks, and proof surfaces
- Tasks (`tasks.md`) defines granular T-NNN items (e.g., `T-001`) with status, proof commands, and AC links
- Review (`review.md`) captures findings with Two-Axis Code Review (Standards vs Spec), decision, and follow-up
- ADRs live in `core-zero/project/adr/` using `NNNN-<slug>.md`; ADR-NNN remains the logical identifier

### AC/Task Linkage & Slicing

Every acceptance criterion should be traceable to at least one task (e.g., `Covers: AC-001`). Every Done task should include fresh validation evidence or proof. Task IDs use the canonical `T-NNN` format (e.g., `T-001`); older `TASK-*` IDs are not parsed by the task graph engine.

- **Tracer bullet slices:** Prefer vertical slices cutting across all layers a task touches.
- **Expand–Contract refactors:** For wide mechanical changes, sequence as expand (add new) → migrate (batch call sites) → contract (delete old).
- **Public seams:** Tests observe behavior at declared public interfaces; do not test private implementation state.
