# Feature Status: `5-system-prompt`

- Phase: Implementing
- Delivery profile: `Complex`
- Status: `Active`
- Active task: `None`
- Next step: /harness-verify

## Progress
- [x] Research/spec complete
- [x] Spec approved
- [x] Plan/tasks complete (Moderate/Complex only)
- [x] Plan approved
- [x] Implementation complete
- [ ] Validation complete

## Intake
- Input type: `change_request`
- One-line restatement: Dynamic runtime system prompt assembly combining agent identity, workspace context, security & permission policies, active tools & planning instructions, skill catalog, and local instruction files (`AGENTS.md` / `CLAUDE.md`) with deterministic context caching.
- Artifact name requested: `5.system-prompt` (harness slug: `5-system-prompt`)
- Why now: User invoked `/spec-requirements` referencing Session 10 in `documents/BUILDING_A_CODING_AGENT.md` and https://learn.shareai.run/en/s10/.
- Profile: `Complex` (refactors system message composition across QueryEngine, tools, skills, and file instructions; touches prompt caching, security policies, and instruction discovery).
- Changed boundaries: Dynamic prompt assembler module `src/prompt/` (or `src/tools/prompt.py`), `QueryEngine._with_system`, system prompt composition.
- Preserved behavior: Feature 1 workspace bounds & tool dispatch; Feature 2 permission gate & rules; Feature 3 task planning tools, board, & 3-round nag; Feature 4 skill catalog format, `load_skill`, & REPL slash commands; session JSON transcripts remain messages-only (system message never persisted).
- Risk flags: Ensuring prompt caching does not prevent hot-reloading when `AGENTS.md` or skills change; preventing prompt bloat if instruction files are oversized.
- ADR conflict: None (empty log).

## Facts (not decisions)
- Current system message in `src/tools/skills.py` combines `src.tools.task_board.SYSTEM_MESSAGE` and `format_catalog(skills)`.
- `QueryEngine._with_system` attaches this string as `ChatMessage("system", ...)` dynamically on every `complete()`.
- System messages are never persisted to `.cda/.sessions/<id>.json`.
- `AGENTS.md` exists at repository root.
- Teaching s10 (https://learn.shareai.run/en/s10/) uses topic-keyed sections (`identity`, `tools`, `workspace`, `memory`/instructions), on-demand assembly `assemble_system_prompt(context)`, and deterministic JSON context key caching `get_system_prompt(context)`.

## Blockers / Decisions
- Blocker:
- Locked decision: Product is the coding-agent CLI (`src/`). Stdlib Python 3.11+ only. Session 10 is an in-scope reference for this feature.
- Locked decision: System message is dynamic and never persisted into `.cda/.sessions/<id>.json`.

## Blocked Recovery
- Reason:
- Owner:
- Evidence:
- Next review at:
- Recommended handoff:
