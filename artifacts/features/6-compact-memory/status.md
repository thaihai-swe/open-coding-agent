# Feature Status: `6-compact-memory`

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
- Input type: `new_spec`
- One-line restatement: Context compaction mechanism for coding agent conversation histories, summarizing older turns via LLM when history exceeds thresholds or on manual `/compact` slash command, preserving recent messages and storing compacted state in session transcripts.
- Artifact name requested: `6.compact-memory` (harness slug: `6-compact-memory`)
- Why now: User invoked `/spec-requirements` referencing Session 08 in `documents/BUILDING_A_CODING_AGENT.md` and https://learn.shareai.run/en/s08/.
- Profile: `Complex` (involves context summarization prompt design, QueryEngine history compaction logic, auto-triggering heuristics, `/compact` slash command, and session transcript updates).
- Changed boundaries: `src/application/query_engine.py`, `src/presentation/cli.py`, `src/tools/prompt.py` / `src/prompts/compact.md`.
- Preserved behavior: Feature 1 tool execution and event protocol; Feature 2 permission gate; Feature 3 planning tools, task board, and nag; Feature 4 skill loading and `load_skill`; Feature 5 dynamic system prompt assembly; messages-only session JSON storage.
- Risk flags: Ensuring tool-call / tool-result message pairings remain valid during truncation/compaction; ensuring prompt templates remain overridable via markdown files; preventing infinite summarization loops if provider calls fail.
- ADR conflict: None (empty log).

## Facts (not decisions)
- `QueryEngine` maintains `self.history: list[ChatMessage]` and persists to `.cda/.sessions/<session_id>.json` via `SessionStore.save()`.
- System prompt is prepended dynamically at completion time and never stored in `self.history` or session JSON.
- REPL processes slash commands starting with `/`. Currently only skills are expanded via `expand_slash_prompt()`.
- Builtin slash commands from blueprint include `/compact` (manual compaction).
- Session 08 (https://learn.shareai.run/en/s08/) introduces context summarization: split history into older turns vs recent turns (e.g. keep recent 4 messages / 2 turns), summarize older turns with a structured compaction prompt into a `<compacted-summary>...</compacted-summary>` message, and replace older messages in `history`.
- Prompt sections are stored as markdown files in `src/prompts/` and overridable via `.cda/prompts/`.

## Blockers / Decisions
- Blocker: None.
- Locked decision: Product is the coding-agent CLI (`src/`). Session 08 / s08 is an in-scope reference for this feature only.
- Locked decision: Full four-layer pipeline (L3 persist → L1 snip → L2 micro → L4 LLM summary) plus reactive compact.
- Locked decision: Invoke via builtin `/compact`, LOW `compact` tool, and auto when `auto_compact` is true.
- Locked decision: Auto trigger is message count **or** character estimate.
- Locked decision: Config is `.cda/config.json` only (hard cutover; ignore `.cda/ui-config.json`). Defaults are s08-aligned (REQ-002).
- Locked decision: L3 persist under `.cda/task_outputs/tool-results/`. Pre-L4 transcript under `.cda/.transcripts/`. Compact prompt is markdown section `compact`.
- Locked decision: L4 keep window is last `keep_recent` messages (default 4), boundary-safe. Reactive tail is 5 messages.

## Blocked Recovery
- Reason:
- Owner:
- Evidence:
- Next review at:
- Recommended handoff: /spec-plan
