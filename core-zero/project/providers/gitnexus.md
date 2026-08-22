# Provider: gitnexus

repo: https://github.com/abhigyanpatwari/GitNexus

## Setup

```bash
npm install -g gitnexus
gitnexus analyze && gitnexus setup
```

After setup, set `providers.code-intelligence.active: gitnexus` in `tool-providers.md`.

## Stale Index

```bash
npx gitnexus analyze
```

## Tool Mapping

| #   | Capability Intent         | Tool call                                                          |
| - | - | - |
| 1   | Explore / query concept   | `gitnexus_query({query: "concept"})`                               |
| 2   | Symbol context            | `gitnexus_context({name: "symbolName"})`                           |
| 3   | Impact — upstream callers | `gitnexus_impact({target: "symbolName", direction: "upstream"})`   |
| 4   | Impact — downstream deps  | `gitnexus_impact({target: "symbolName", direction: "downstream"})` |
| 5   | Summarize file or module  | `gitnexus_context({name: "moduleName"})` + summarize the result    |
| 6   | Detect changed symbols    | `gitnexus_detect_changes()`                                        |
| 7   | Safe rename               | `gitnexus_rename({from: "oldName", to: "newName"})`                |
| 8   | Codebase overview         | Resource: `gitnexus://repo/<repo-name>/context`                    |
| 9   | All functional clusters   | Resource: `gitnexus://repo/<repo-name>/clusters`                   |
| 10  | All execution flows       | Resource: `gitnexus://repo/<repo-name>/processes`                  |
| 11  | Single execution trace    | Resource: `gitnexus://repo/<repo-name>/process/{name}`             |

## Skill Files (from your agent config dir)

| Task                                         | Skill file                                                             |
| - | - |
| Understand architecture / "How does X work?" | `<agent-config-dir>/skills/gitnexus/gitnexus-exploring/SKILL.md`       |
| Blast radius / "What breaks if I change X?"  | `<agent-config-dir>/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?"             | `<agent-config-dir>/skills/gitnexus/gitnexus-debugging/SKILL.md`       |
| Rename / extract / split / refactor          | `<agent-config-dir>/skills/gitnexus/gitnexus-refactoring/SKILL.md`     |
| Tools, resources, schema reference           | `<agent-config-dir>/skills/gitnexus/gitnexus-guide/SKILL.md`           |
| Index, status, clean, wiki CLI               | `<agent-config-dir>/skills/gitnexus/gitnexus-cli/SKILL.md`             |
