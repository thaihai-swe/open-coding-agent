# Session Extracts: 4-skills

## Candidate Lessons
- [CANDIDATE] `invoke(name, /, **kwargs)`: In Python tools registries, when `invoke` passes tool parameters via `**kwargs`, the tool name parameter MUST be positional-only (`/`). Otherwise, any tool with a parameter named `name` (like `load_skill(name: str)`) causes `TypeError: invoke() got multiple values for argument 'name'`.
- [CANDIDATE] Stdlib frontmatter parsing: When YAML frontmatter needs to be parsed in a stdlib-only environment, splitting on `---` and doing regex/string key-value extraction for known scalar fields (`name`, `description`, `when_to_use`) avoids dragging heavy external dependencies like PyYAML into minimal agent CLI cores.
- [CANDIDATE] Two-level knowledge injection: Level 1 (catalog in system prompt per turn) gives awareness of available skills without token bloat; Level 2 (full content via `tool_result` on `load_skill`) loads domain instructions into history only when specifically requested.
