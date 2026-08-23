# Feature Status: 1-tool-and-execution

- Phase: Done
- Delivery profile: Complex
- Status: Active
- Active task: None
- Next step: /context-memory

## Progress
- [x] Research/spec complete
- [x] Spec approved
- [x] Plan/tasks complete (Moderate/Complex only)
- [x] Plan approved
- [ ] Implementation complete
- [ ] Validation complete

## Intake
- Input type: `change_request`
- One-line restatement: Close Session 02 gaps — dispatchable core file/shell tools plus terminal observability — against the existing coding-agent CLI.
- Artifact name requested: `1.tool-and-execution` (harness slug: `1-tool-and-execution`)
- Why now: User invoked `/spec-requirements` with Session 02 (local blueprint + https://learn.shareai.run/en/s02/) as references. Scoped override of the starter-init “blueprint out of scope” decision for this feature only.
- Analysis: `analysis.md` absent. User skipped `/spec-research`.
- ADR conflict: none (empty log).
- Domain packs: none matched beyond default project files.

## Facts (not decisions)
- Dispatch registry already exists; 16 tools registered. Core names present: `bash`, `read_file`, `write_file`, `edit_file`, `glob_search` (not `glob`).
- JSON event mode and Ctrl+C session save already exist (`tests/cli_check.py`, `tests/terminal_ui_check.py`, `src/presentation/cli.py`).
- Terminal prompt is single-line; no Markdown renderer.
- File tools have no workspace path bound; `bash` is unrestricted `shell=True`.
- Approve/deny for MEDIUM/HIGH already exists (Session 03 territory). Sequential multi-tool execution already exists.
- No tests under `tests/` for tool handlers.

## Blockers / Decisions
- Blocker:
- Locked decision: Product is the coding-agent CLI (`src/`). Session 02 sources are in-scope references for this feature.
- Locked decision: Full local Session 02 goal (dispatch + path bound + concurrent batches + multiline + Markdown + live status + JSON + cancel-preserves-session).
- Locked decision: Extra tools stay registered; contracts unchanged except path bound on file/search tools and `glob` alias.
- Locked decision: File and search tools refuse resolved real paths outside process cwd (symlink escape refused); `bash` unrestricted this slice.
- Locked decision: Public name `glob_search` remains; `glob` is an alias advertised to the provider.
- Locked decision: Concurrency-safe set = all registered tools; one assistant message = one concurrent batch; failures do not skip remaining calls; history order = listed order.
- Locked decision: Multiline submit = solo `.` line; empty first line quits; EOF submits accumulated text.
- Locked decision: Human Markdown on assistant `text` only; JSON additive `status` + `tool_result`.
- Locked decision: Authorize stays sequential before overlapping execute.

## Blocked Recovery
- Reason:
- Owner:
- Evidence:
- Next review at:
- Recommended handoff:
