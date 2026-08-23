# Feature Specification

## Metadata
- Feature: `7-memory-management`
- Profile: `Complex`
- Status: `Approved`
- Owner: adopter
- Requested artifact name: `7-memory-management` (harness slug `7-memory-management`)
- References (scoped, not global architecture): Session 09 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s09/

## Problem Statement
- Who is affected, what fails, and why now: A coding-agent CLI user who works across sessions or after Feature 6 compaction loses preferences, recurring feedback, and project facts. Session JSON and compacted summaries are not a durable knowledge store. Session 09 / s09 is the next roadmap slice: persist those facts as markdown files, inject a catalog plus selected bodies into the next turn, extract new facts when a turn ends, and consolidate when the file count grows.

## Outcome
- Observable result:
  1. Persistent memories live under `.cda/memory/` as one markdown file per entry plus an index `.cda/memory/MEMORY.md`. Each file has YAML frontmatter `name`, `description`, `type` (`user` | `feedback` | `project` | `reference`) and a markdown body.
  2. Project settings for memory live in `.cda/config.json` under `memory`. Missing file or missing keys use locked defaults. Existing compact and `show_tool_results` keys are unchanged.
  3. `assemble_system_prompt()` includes a memory catalog section from `MEMORY.md` (when the index is non-empty) plus guidance to respect stored preferences. The Feature 5 section order is otherwise unchanged.
  4. At the start of each user turn, when memory is enabled, the engine selects at most `max_relevant` relevant files via a tool-less provider side-query over recent conversation plus the catalog (name + description). Side-query failure or invalid JSON falls back to keyword match on name + description. Selected file bodies are prepended to the current user request as `<relevant_memories>…</relevant_memories>` and are not written into session JSON.
  5. When a turn ends without further tool calls, and `auto_extract` is true, the engine extracts new memories from a pre-compaction snapshot of recent dialogue (last 10 messages, dialogue text capped at 4000 characters), skipping items already covered by existing name/description. New files are written and `MEMORY.md` is rebuilt. A `status` event reports how many were extracted.
  6. After extraction, when `auto_consolidate` is true and the memory file count is at least `consolidate_threshold`, the engine runs one consolidation pass: merge duplicates, drop contradicted/stale items, keep important user preferences, rewrite files, rebuild the index. A `status` event reports before/after counts.
  7. `/memory` is a builtin REPL command handled before skill expansion. It lists current entries (name, type, description) and utilization (file count vs threshold) via `status` events. It does not call `turn("/memory")`.
  8. Memory files stay inside `.cda/memory/` under process cwd. Slugs that contain path separators or `..` are sanitized. Session JSON remains `{"messages": [...]}` with no system role and no injected memory wrapper.
- Minimum useful release: US1–US6 (store + index + catalog + select/inject + extract + consolidate + `/memory` + config).

## Scope
- In scope:
  - Markdown + frontmatter store under `.cda/memory/` and rebuilt `MEMORY.md`.
  - Four types: `user`, `feedback`, `project`, `reference`.
  - Config knobs under `.cda/config.json` `memory` with locked defaults.
  - Catalog injection in the assembled system prompt.
  - Pre-turn relevant selection (LLM side-query, max 5, keyword fallback) and request-only injection.
  - Post-turn extraction from a pre-compaction snapshot; rebuild index.
  - File-count consolidation (threshold 10) after extraction.
  - Builtin `/memory` reserved before skill expansion.
  - Memory prompt section `memory` (override → bundled → fallback) for catalog guidance and extractor/consolidator/selector instructions as needed.
  - Tests for store/index, catalog, select + fallback, inject-not-persisted, extract, consolidate, `/memory`, config defaults, Feature 1–6 regression.
- Out of scope / non-goals:
  - Embeddings, vector stores, or third-party tokenizers.
  - Team / shared memory across machines.
  - Session-local memory files used as an L4 summary substitute.
  - Forked-agent extraction, four-gate Dream (24h / scan / session / lock). Teaching-version file-count gate only.
  - A write/delete memory tool in the main tool registry (engine-driven extract/write is the MVP).
  - Changing Feature 6 compact layers, `/compact`, or session JSON shape.
  - Changing Feature 5 instruction-file discovery or required section order except appending the memory catalog.
  - Parent-directory or home-directory memory paths.
- Preserved behavior:
  - Feature 1: workspace bound, concurrent batch, human/JSON events.
  - Feature 2: hard deny, project rules, numbered authorize.
  - Feature 3: six planning tools, `.cda/.todos/`, 3-round nag, messages-only session JSON.
  - Feature 4: skill scan, `load_skill`, `/<skill-name>` expansion. `/memory` is reserved and is not a skill name.
  - Feature 5: dynamic system prompt, markdown overrides, system role never persisted.
  - Feature 6: four-layer compact + reactive compact + `/compact` + `compact` tool. Extraction uses a pre-compression snapshot so compact does not starve extract.

## User Stories & Journeys (Moderate/Complex)

### User Story 1 - Memory files and index (Priority: P1) 🎯 MVP
- Description: The project stores each memory as `.cda/memory/<slug>.md` with frontmatter and rebuilds `.cda/memory/MEMORY.md` whenever a memory is written. Missing directory is created on first write. Existing files are never rewritten by startup init.
- Why this priority: Every other story reads or writes this store.
- Independent Test: Temp cwd; write two memories; assert files, frontmatter, and index lines.
- Acceptance Scenarios:
  1. Given no `.cda/memory/`, When a memory named `user-preference-tabs` of type `user` is written, Then `.cda/memory/user-preference-tabs.md` exists with `name`, `description`, `type` frontmatter and the given body, and `.cda/memory/MEMORY.md` contains `- [user-preference-tabs](user-preference-tabs.md) —`.
  2. Given an existing memory file, When a second distinct memory is written, Then the index lists both names and does not contain a `MEMORY.md` self-link.
  3. Given a name containing spaces or `/`, When written, Then the filename is a sanitized slug under `.cda/memory/` and no path is created outside that directory.

### User Story 2 - Config knobs (Priority: P1) 🎯 MVP
- Description: `.cda/config.json` `memory` keys control enablement, selection cap, consolidate threshold, and auto extract/consolidate. Missing keys use defaults. Compact keys stay as Feature 6.
- Why this priority: Adopter required unified config; extract/select/consolidate read these knobs.
- Independent Test: Temp cwd with no file, partial `memory` object, and full object.
- Acceptance Scenarios:
  1. Given no `.cda/config.json` memory block, When memory settings are resolved, Then `enabled` is true, `max_relevant` is 5, `consolidate_threshold` is 10, `auto_extract` is true, `auto_consolidate` is true.
  2. Given `.cda/config.json` sets `memory.max_relevant` to 2 and omits other memory keys, When resolved, Then `max_relevant` is 2 and the other memory defaults remain.
  3. Given `memory.enabled` is false, When a turn runs, Then no relevant-memory side-query, no extract, and no consolidate run.

### User Story 3 - Catalog in the system prompt (Priority: P1) 🎯 MVP
- Description: When `MEMORY.md` is non-empty, the assembled system prompt includes the catalog and memory-use guidance. Empty or missing index omits the catalog body. Prompt text comes from section `memory` (override → bundled → fallback).
- Why this priority: s09 Path 1; the model must know which memories exist even before bodies are injected.
- Independent Test: Assemble prompt with and without an index; override `.cda/prompts/memory.md`.
- Acceptance Scenarios:
  1. Given `MEMORY.md` with one index line, When `assemble_system_prompt` runs, Then the prompt contains that line and memory-use guidance, after the skill catalog / before or with instructions.
  2. Given no memory files, When assembled, Then the prompt has no `Memories available:` catalog body (guidance-only is allowed only if the section is empty of links).
  3. Given `.cda/prompts/memory.md` contains `OVERRIDE-MEMORY-PROMPT`, When assembled with a non-empty index, Then that string appears in the system prompt.

### User Story 4 - Relevant selection and request injection (Priority: P1) 🎯 MVP
- Description: At the start of a user turn, a tool-less side-query receives recent user text (up to 3 recent user messages, 2000 characters) and a numbered catalog. It returns a JSON array of indices, capped at `max_relevant`. Invalid/failed response uses keyword overlap on name+description. Selected bodies are prepended to the outgoing user message as `<relevant_memories>…</relevant_memories>` and are not saved to session JSON.
- Why this priority: s09 Path 2; this is how a later session recalls tabs vs spaces.
- Independent Test: FakeProvider returns `[0]`; another FakeProvider raises; inspect request messages vs `engine.history` vs session JSON.
- Acceptance Scenarios:
  1. Given two memories and a FakeProvider selector that returns `[0]`, When `turn` calls `complete()` for the user message, Then the first `complete()` user content contains `<relevant_memories>`, the first memory body, and `</relevant_memories>`, and `engine.history` user content does not contain that wrapper.
  2. Given the selector `complete()` raises, When the turn runs, Then keyword fallback may select files whose name or description shares a token longer than 3 characters with recent user text, still capped at `max_relevant`, and the turn still completes.
  3. Given no memories, When the turn runs, Then no selector `complete()` is made and the user history message is unchanged.

### User Story 5 - Post-turn extract and consolidate (Priority: P1) 🎯 MVP
- Description: After a turn that ends without a tool-call loop continuation, extract runs on a snapshot taken before cheap/L4 compact. Extractor returns `[{name, type, description, body}]` or `[]`. Valid new items are written. Then if file count ≥ `consolidate_threshold`, consolidate replaces the set (except `MEMORY.md`) with the returned list. Extractor/consolidator use no tools. Failures leave existing files intact and do not fail the user turn.
- Why this priority: Users rarely say “remember this”; extraction is the write path. Consolidation keeps the store bounded.
- Independent Test: FakeProvider extractor returns one item; consolidator returns a shorter list at threshold; failure cases.
- Acceptance Scenarios:
  1. Given a finished text-only turn and extractor JSON `[{"name":"user-preference-tabs","type":"user","description":"tabs","body":"Use tabs"}]`, When the turn returns, Then that file exists, `MEMORY.md` lists it, and a `status` event mentions `extracted` and `1`.
  2. Given extractor returns `[]` or already-covered content, When the turn returns, Then no new memory file is added.
  3. Given 10 existing memories and `consolidate_threshold` 10, When extract finishes and consolidator returns 3 items, Then exactly those 3 memory files remain (plus rebuilt `MEMORY.md`) and a `status` event mentions `consolidated`.
  4. Given the extractor `complete()` raises, When the turn returns, Then the user-visible reply still succeeded and the memory directory is unchanged.
  5. Given `auto_extract` false, When a text-only turn ends, Then no extractor `complete()` runs.

### User Story 6 - /memory builtin (Priority: P1) 🎯 MVP
- Description: The human types `/memory` and sees the catalog plus counts. `/memory` is not a skill name and does not start a model turn.
- Why this priority: Blueprint slash command; operators need a no-LLM inspection path.
- Independent Test: CLI slash test with two files on disk.
- Acceptance Scenarios:
  1. Given two memory files, When REPL input is `/memory`, Then `turn` is not called with `/memory`, no `Unknown skill: /memory` error is emitted, and at least one `status` event lists both names and the file count.
  2. Given a skill named something other than `memory`, When the user types `/<skill-name>`, Then Feature 4 expansion still occurs.

## Requirements (Moderate/Complex)
- `REQ-001`: Persistent memories are stored only under process-cwd `.cda/memory/`. Each entry is `<slug>.md` with YAML frontmatter keys `name`, `description`, `type` and a markdown body. `type` is one of `user`, `feedback`, `project`, `reference`. Priority: Must. Validation: memory unit tests. Linked story: US1.
- `REQ-002`: Writing a memory sanitizes `name` to a slug (lowercase, spaces and `/` to `-`, reject `..` and path separators in the final filename) and rebuilds `.cda/memory/MEMORY.md` as one line per file excluding the index itself: `- [<name>](<filename>) — <description>`. Priority: Must. Validation: memory unit tests. Linked story: US1.
- `REQ-003`: Default memory settings are `enabled=true`, `max_relevant=5`, `consolidate_threshold=10`, `auto_extract=true`, `auto_consolidate=true`. They live under `.cda/config.json` `memory`. Missing file or keys use these defaults. Compact defaults from Feature 6 are unchanged. Priority: Must. Validation: config tests. Linked story: US2.
- `REQ-004`: When `enabled` is false, skip relevant selection, request injection, extract, and consolidate. `/memory` still lists on-disk files. Priority: Must. Validation: `query_engine_check.py`, `cli_check.py`. Linked story: US2, US6.
- `REQ-005`: `assemble_system_prompt()` includes the `memory` prompt section. If `MEMORY.md` is non-empty, the catalog text is present in the system message. System role is still not persisted. Priority: Must. Validation: `tools_check.py`. Linked story: US3.
- `REQ-006`: Memory prompt resolution uses `load_prompt_section("memory")` (override `.cda/prompts/memory.md`, then `src/prompts/memory.md`, then inline fallback). Priority: Must. Validation: `tools_check.py`. Linked story: US3.
- `REQ-007`: At the start of each user `turn`, if enabled and at least one memory file exists, run a tool-less selector `complete()` with recent user text (≤3 user messages, ≤2000 characters) and a numbered catalog. Parse a JSON integer array; keep valid indices in range; cap at `max_relevant`. On any failure, keyword-match tokens longer than 3 characters against name+description, same cap. Priority: Must. Validation: `query_engine_check.py`. Linked story: US4.
- `REQ-008`: Selected memory file full texts are prepended only on the provider request for that turn, wrapped in `<relevant_memories>` / `</relevant_memories>`. `QueryEngine.history` and `.cda/.sessions/<id>.json` do not contain that wrapper. Priority: Must. Validation: `query_engine_check.py`. Linked story: US4.
- `REQ-009`: Before cheap/L4 compact in a turn, snapshot history for extraction. When the turn ends without scheduling another tool batch, if `auto_extract` and enabled, run a tool-less extractor `complete()` over the last 10 snapshot messages, dialogue capped at 4000 characters, including existing name+description to avoid duplicates. Write only items that have non-empty `description` and `body`. Emit `status` mentioning `extracted` and the count when count > 0. Extractor failure is swallowed for the user turn. Priority: Must. Validation: `query_engine_check.py`. Linked story: US5.
- `REQ-010`: After a successful extract attempt (including zero new items), if `auto_consolidate` and enabled and `len(memory files) >= consolidate_threshold`, run one tool-less consolidator `complete()`. On a valid non-empty JSON array, replace all `.cda/memory/*.md` except `MEMORY.md` with the returned items and rebuild the index. On failure or unparsable output, leave files unchanged. Emit `status` mentioning `consolidated` on success. Priority: Must. Validation: `query_engine_check.py`. Linked story: US5.
- `REQ-011`: `/memory` is a builtin REPL command handled before Feature 4 skill expansion. It does not call `turn("/memory")`. It emits `status` listing each memory name and the file count. Unknown `/name` that is not `/memory` or `/compact` stays Feature 4 behavior. Priority: Must. Validation: `cli_check.py`. Linked story: US6.
- `REQ-012`: Selector, extractor, and consolidator `complete()` calls register no tools. They must not recurse into extract/select/consolidate. Priority: Must. Validation: `query_engine_check.py`. Linked story: US4, US5.
- `REQ-013`: `src/` remains Python 3.11+ stdlib only. Feature 1–6 public behavior is unchanged except the added memory catalog section, request-only injection, post-turn extract/consolidate, reserved `/memory`, and new `memory` config keys. Priority: Must. Validation: full `*_check.py` suite. Linked story: US1–US6.

## Acceptance Criteria
- `AC-001`: Given a write of name `user-preference-tabs`, type `user`, description `tabs not spaces`, body `Use tabs.`, When the store is read, Then `.cda/memory/user-preference-tabs.md` has those frontmatter fields and body, and `MEMORY.md` contains `- [user-preference-tabs](user-preference-tabs.md) — tabs not spaces`. Covers REQ-001, REQ-002. Proof: `python3 tests/tools_check.py`.
- `AC-002`: Given a write with name `bad/../x`, When the store writes, Then the created file’s resolved path is inside `.cda/memory/` and no file is created outside process cwd. Covers REQ-002. Proof: `python3 tests/tools_check.py`.
- `AC-003`: Given no `memory` block in `.cda/config.json`, When memory settings are resolved, Then they match REQ-003 defaults and compact defaults still match Feature 6 REQ-002. Covers REQ-003. Proof: `python3 tests/tools_check.py`.
- `AC-004`: Given `.cda/config.json` `{"memory": {"max_relevant": 2}}`, When resolved, Then `max_relevant` is 2 and `consolidate_threshold` is 10. Covers REQ-003. Proof: `python3 tests/tools_check.py`.
- `AC-005`: Given `memory.enabled` false and at least one memory file, When `turn` runs a text-only prompt, Then no selector/extractor/consolidator `complete()` is invoked. Covers REQ-004, REQ-012. Proof: `python3 tests/query_engine_check.py`.
- `AC-006`: Given a non-empty `MEMORY.md`, When `assemble_system_prompt` runs, Then the system text contains an index line from that file. Covers REQ-005. Proof: `python3 tests/tools_check.py`.
- `AC-007`: Given no memory files, When `assemble_system_prompt` runs, Then there is no memory index bullet line of the form `- [` pointing at a `.md` memory file. Covers REQ-005. Proof: `python3 tests/tools_check.py`.
- `AC-008`: Given `.cda/prompts/memory.md` body `OVERRIDE-MEMORY-PROMPT` and a non-empty index, When assembled, Then the system prompt contains `OVERRIDE-MEMORY-PROMPT`. Covers REQ-006. Proof: `python3 tests/tools_check.py`.
- `AC-009`: Given two memories and a selector response whose text contains `[0]`, When `turn` issues the user-turn `complete()`, Then that request’s user content contains `<relevant_memories>` and the first file body, and `engine.history` for that user message does not contain `<relevant_memories>`. Covers REQ-007, REQ-008. Proof: `python3 tests/query_engine_check.py`.
- `AC-010`: Given a selector `complete()` that raises, a memory whose description contains `tabs`, and user prompt `remember I like tabs`, When `turn` runs, Then the request user content contains that memory body or, if keyword fallback selects none, the turn still completes without error. Covers REQ-007. Proof: `python3 tests/query_engine_check.py`.
- `AC-011`: Given L4/cheap compact would run in the same turn, When extract runs, Then it is called with a snapshot captured before those compact layers mutate history. Covers REQ-009. Proof: `python3 tests/query_engine_check.py`.
- `AC-012`: Given extractor content a JSON array with one valid item, When a text-only turn ends, Then that memory file exists, `MEMORY.md` lists it, and a `status` event message contains `extracted` (case-insensitive) and `1`. Covers REQ-009. Proof: `python3 tests/query_engine_check.py`.
- `AC-013`: Given extractor returns `[]`, When the turn ends, Then the memory file count is unchanged. Covers REQ-009. Proof: `python3 tests/query_engine_check.py`.
- `AC-014`: Given 10 memory files and consolidator JSON of 3 valid items, When the turn’s extract/consolidate path runs, Then exactly 3 memory entry files remain, `MEMORY.md` has 3 link lines, and a `status` event contains `consolidated` (case-insensitive). Covers REQ-010. Proof: `python3 tests/query_engine_check.py`.
- `AC-015`: Given consolidator `complete()` raises, When the path runs at threshold, Then existing memory files are unchanged and the user turn still returns a normal assistant message. Covers REQ-010. Proof: `python3 tests/query_engine_check.py`.
- `AC-016`: Given REPL input `/memory` with two on-disk memories, When `run()` handles it, Then `turn` is not called with `/memory` and a `status` event lists both names. Covers REQ-011. Proof: `python3 tests/cli_check.py`.
- `AC-017`: Given a skill `code-review`, When REPL input is `/code-review`, Then Feature 4 expansion still occurs. Covers REQ-011, REQ-013. Proof: `python3 tests/cli_check.py`.
- `AC-018`: Given selector/extractor/consolidator `complete()` calls, When inspected, Then each was invoked with empty tools. Covers REQ-012. Proof: `python3 tests/query_engine_check.py`.
- `AC-019`: Given L4 completed in a session that also extracted a memory, When session JSON is loaded, Then top-level keys are only `messages` and no message has `role=system` or `<relevant_memories>`. Covers REQ-008, REQ-013. Proof: `python3 tests/query_engine_check.py`.
- `AC-020`: Given existing Feature 1–6 suites plus new tests, When `python3 -m unittest discover -s tests -p '*_check.py'` runs, Then all tests pass. Covers REQ-013. Proof: `python3 -m unittest discover -s tests -p '*_check.py'`.

## Success Criteria (Measurable Outcomes)
- `SC-001`: After a user states a preference in session A, session B’s first `complete()` can include that preference via catalog and/or `<relevant_memories>` without the preference remaining only in session A’s transcript.
- `SC-002`: A user can type `/memory` and see names and a file count with no model turn.
- `SC-003`: When memory file count reaches the threshold, a successful consolidate pass leaves fewer or equal files and a rebuilt index; a failed pass leaves the previous files.
- `SC-004`: Extract and select failures never abort the user-visible turn.
- `SC-005`: Zero third-party dependencies added to `src/`. Session JSON shape is unchanged.

## Constraints and Risk
- Constraints:
  - NFR-001 Stdlib-only `src/` (Python 3.11+). Linked ACs: AC-020.
  - NFR-002 Session JSON remains `{"messages": [...]}` with no system role and no injected memory wrapper. Linked ACs: AC-009, AC-019.
  - NFR-003 Memory paths stay under process cwd `.cda/memory/`. Linked ACs: AC-001, AC-002.
  - NFR-004 Side-queries are tool-less and must not recurse. Linked ACs: AC-018.
  - NFR-005 User turn succeeds if extract/select/consolidate fail. Linked ACs: AC-010, AC-015.
  - NFR-006 Feature 6 compact still runs; extract uses pre-compact snapshot. Linked ACs: AC-011, AC-019.
- Dependencies/touchpoints: `QueryEngine.turn` / `_with_system`, `assemble_system_prompt` / `load_prompt_section`, `.cda/config.json`, CLI slash loop, `SessionStore`, `TerminalUI` events, `tests/cli_check.py`, `tests/query_engine_check.py`, `tests/tools_check.py`.
- Risks and mitigations:
  - Risk: Extra provider calls per turn (select + extract). Mitigation: skip when disabled or no files (select); extract only on natural turn end; failures are non-fatal.
  - Risk: Extractor invents junk memories. Mitigation: require description+body; pass existing catalog; consolidator prunes at threshold.
  - Risk: `/memory` collides with a skill named `memory`. Mitigation: builtin wins; spec forbids treating `/memory` as a skill.
  - Risk: Consolidation deletes useful files on bad JSON. Mitigation: replace only on valid non-empty parse; else no-op.
- Open questions (blocking only): none.

## Decisions
- Locked decisions:
  - Session 09 / s09 is an in-scope reference for this feature only, not a global architecture contract.
  - Storage: `.cda/memory/` (not workspace-root `.memory/`).
  - Full s09 paths: catalog in system prompt + relevant side-query inject + post-turn extract + file-count consolidate.
  - Selection: LLM side-query first, keyword fallback; cap `max_relevant=5`.
  - Consolidate gate: file count ≥ 10 (not four-gate Dream).
  - Config: `.cda/config.json` `memory` keys; Feature 6 compact block unchanged.
  - `/memory` builtin before skill expansion; no main-registry write-memory tool in MVP.
  - Injection is request-only; not persisted in history or session JSON.
  - Extract from pre-compression snapshot of last 10 messages, 4000-char dialogue cap.
  - Prompt section name: `memory`.
  - Status events for extract/consolidate/`/memory`; no new required event `type`.
  - Out: embeddings, team memory, session-memory-as-summary, forked agents, four-gate Dream.
- Related `ADR-*`: none.
