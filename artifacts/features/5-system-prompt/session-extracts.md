# Session Extracts: `5-system-prompt`

## Candidate Lessons

- `[CANDIDATE]` Pure stdlib prompt assembly: Composing topic-keyed fragments (`Identity`, `Workspace`, `Planning`, `Security`, `Tools`, `Skills`, `Instructions`) via `\n\n.join()` with stdlib string formatting is cleaner, faster (<1ms), and more maintainable than monolithic strings or third-party template engines.
- `[CANDIDATE]` Instruction file bounding: When injecting local repo markdown (`AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`), enforce per-file (4000 chars) and overall section (12000 chars) budgets and SHA-256 deduplication to protect against context exhaustion and duplicate file symlinks.
- `[CANDIDATE]` Dynamic prompt freshness: Assembling the system message on each `complete()` without persistence in session JSON transcripts enables real-time responsiveness to mid-session edits of `AGENTS.md` and `SKILL.md` while keeping transcripts clean.
- `[CANDIDATE]` Backward compatibility delegation: Delegating legacy `skills.build_system_message` to the new `prompt.assemble_system_prompt` preserves existing callers without circular imports or duplicated assembly logic.
