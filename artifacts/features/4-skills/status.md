# Feature Status: 4-skills

- Phase: Implementing
- Delivery profile: Complex
- Status: Active
- Active task: None
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
- One-line restatement: Replace stub `skill` with two-level on-demand skill loading (catalog in the system message + full SKILL.md via `load_skill`) and REPL `/<skill-name>` invocation.
- Artifact name requested: `4.skills` (harness slug: `4-skills`)
- Why now: User invoked `/spec-requirements` with Session 07 as a reference and asked for skill loading like Codex / Claude. Scoped override of the starter-init “blueprint out of scope” decision for this feature only.
- Analysis: `analysis.md` absent. User skipped `/spec-research`.
- ADR conflict: none (empty log).
- Domain packs: none matched beyond default project files.

## Facts (not decisions)
- `skill` is already registered: category Agent, risk LOW, required arg `skill` (string). Handler returns `"Loaded skill known"` only when `skill == "known"`; any other name is `Unknown skill: {name}`. Optional `args` is accepted in the function signature but is not in the schema. No tests.
- QueryEngine prepends Feature 3 `SYSTEM_MESSAGE` (`plan before executing` + the six planning tool names) on every `complete()`. That message is not stored in session JSON.
- Session files stay `{"messages": [...]}` under `.cda/.sessions/`. Feature 2 locked: no extra fields on session JSON.
- Feature 1: extra tools stay registered; concurrent batch; listed-order results. Feature 2: hard deny / project rules / numbered authorize. A LOW skill tool skips authorize.
- Product-sense: CoreBase SpecHarness skills under `.agents/skills/` are delivery-kit, not runtime agent features. Adopter explicitly chose to scan that same tree as-is so every SKILL.md is cataloged (including spec-* / design / harness-*).
- Teaching s07 (https://learn.shareai.run/en/s07/): scan cwd `skills/<dir>/SKILL.md`; parse YAML frontmatter `name`/`description`; inject catalog into SYSTEM; `load_skill(name)` returns full SKILL.md via `tool_result`. Unknown name returns `Skill not found: {name}`. Extra files via existing file/bash tools. Loop unchanged.
- `src/` is stdlib-only. PyYAML is present in this environment but is not an approved `src/` dependency.
- `skill-enter` expected `skills/_shared/status-template.md`; this tree keeps the template at `.agents/skills/_shared/status-template.md`. Status was seeded from that template so work could proceed. A cwd `skills/` directory must not be created for the harness template because project runtime skills live under `.agents/skills/`.

## Blockers / Decisions
- Blocker:
- Locked decision: Product is the coding-agent CLI (`src/`). Session 07 page is an in-scope reference for this feature only, not a global architecture contract.
- Locked decision: Public tool is `load_skill(name: str)` only. Unregister stub `skill`. Unknown name is a tool error containing `Skill not found: <name>`.
- Locked decision: Scan project cwd `.agents/skills/` and global `~/.agents/skills/`. Include every SKILL.md found. Project name wins on collision. Missing/unreadable packages are skipped.
- Locked decision: Scan on every provider `complete()`. Catalog is appended to the Feature 3 planning system message. Empty catalog is `(no skills found)`. System message is not stored in session JSON.
- Locked decision: Stdlib-only frontmatter. Fields: `name`, `description`, `when_to_use`. Missing name → directory name. Missing description → first markdown heading or first non-empty line.
- Locked decision: REPL slash `/<skill-name> [args]` for every cataloged skill expands that skill’s SKILL.md plus trailing args into a turn. Unknown `/name` reports `Unknown skill: /<name>` and does not call `QueryEngine.turn`.
- Locked decision: Extra `references/` / `scripts/` / `assets/` are not auto-injected. The model may later `read_file` / `bash` them. No `allowed-tools`, fork, or model override.

## Blocked Recovery
- Reason:
- Owner:
- Evidence:
- Next review at:
- Recommended handoff: `/spec-plan`
