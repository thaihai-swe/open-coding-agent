# Glossary

> Ownership: `Adopter-owned`

Project-wide vocabulary from `/starter-init` (2026-08-22). Domain/product names remain `[USER REVIEW NEEDED]`. Do not invent business terms.

## Domain Terms

| Term | Definition | Used In |
|-|-|-|
| coding-agent CLI | The product: local OpenAI-compatible REPL under `src/` | Adopter `/starter-init` 2026-08-22 |
| SpecHarness kit | Delivery/harness layer, not the product | `corebase-specharness/`, `.agents/skills/` |
| Session 02 slice | Feature `1-tool-and-execution`: terminal experience + tool dispatch, scoped by `artifacts/features/1-tool-and-execution/spec.md` | Adopter 2026-08-22 |
| workspace bound | File/search tool paths whose resolved real path is not inside process cwd are refused | `1-tool-and-execution` |
| concurrent batch | All tool calls from one assistant message may run overlapping in time; history order stays the listed order | `1-tool-and-execution` |
| period submit | Human-mode multiline prompt ends on a line that is only `.` | `1-tool-and-execution` |
| permission gate | Code-enforced deny / ask / allow decision before a tool handler runs | `2-permission-gate` |
| hard deny | A permission decision that never prompts and never runs the handler, including after Yes, “don't ask again”, `bypass_permissions`, or a project rules-file allow entry | `2-permission-gate` |
| deny list | Fixed substrings that hard-deny `bash`/`powershell` `command` values | `2-permission-gate` |
| project permission rule | User- or prompt-recorded allow/deny for one tool + primary-argument pattern, stored in `.cda/.permission_rules/rules.json` and shared by every session in that project | `2-permission-gate` |
| `.cda` | Project-local CLI data directory under process cwd: `.sessions`, `.secrets`, and `.permission_rules` | `2-permission-gate` |
| primary argument | The fields that identify a project permission pattern: `command` (bash/powershell), `file_path` (write_file/edit_file), `action`+`key` (config), `url` (web_fetch), `code` (repl), otherwise the full argument map | `2-permission-gate` |

## Technical Terms

| Term | Definition | Used In |
|-|-|-|
| QueryEngine | Orchestrates one user turn: provider complete, stream collect, tool loop, session save | `src/application/query_engine.py` |
| Provider | Protocol for `complete(messages, tools, stream)` | `src/domain/provider.py` |
| OpenAIProvider | Stdlib HTTP client for OpenAI-compatible `/chat/completions` | `src/infrastructure/providers/openai.py` |
| SessionStore | JSON transcript persistence under `.cda/.sessions/` | `src/infrastructure/session_store.py` |
| Tool registry | Singleton map of name → `Tool` (schema + handler + risk) | `src/tools/registry.py` |
| `glob` alias | Public tool name that performs the same operation as `glob_search` | `1-tool-and-execution` |
| Risk | `HIGH` / `MEDIUM` / `LOW` tool permission class | `src/tools/types.py` |
| Authorize | UI callback used when a MEDIUM/HIGH call is not hard-denied and has no matching project permission rule; numbered `1`–`4` | `src/presentation/terminal_ui.py` |
| `bypass_permissions` | Kwarg that skips the HIGH-without-approve `check_permission` branch after this call is allowed on the turn path; does not override hard deny | `src/application/query_engine.py`, `src/tools/permissions.py` |
| `.cda/.permission_rules/rules.json` | Project-level JSON array of `tool`, `pattern`, and `decision` (`allow` or `deny`); source of truth for always-allow / always-deny | `2-permission-gate` |
| Composition root | `src/presentation/cli.py` wires provider, store, UI, engine | CLI |

## Abbreviations

| Abbreviation | Expansion | Context |
|-|-|-|
| REPL | Read-eval-print loop | `python3 -m src.cli` |
| SSE | Server-sent events (`data: ` lines) | Provider streaming |
| AC | Acceptance criterion | SpecHarness artifacts |
| ADR | Architecture Decision Record | `/spec-adr` |

## Naming Conventions

| Domain Concept | Code Name | Pattern | Example |
|-|-|-|-|
| LLM vendor adapter | `*Provider` | PascalCase class in `infrastructure/providers/` | `OpenAIProvider` |
| Tool handler module | category file under `src/tools/handlers/` | snake_case | `file_io.py` |
| App unittest | `tests/*_check.py` | `*_check.py` + `unittest.main()` | `cli_check.py` |

## Forbidden Terms

| Avoid | Use Instead | Reason |
|-|-|-|
| Treating the whole `BUILDING_A_CODING_AGENT.md` as architecture | `src/`, tests, and the active feature `spec.md` | Blueprint is not a global contract; Session 02/03 are in scope only as locked in their feature specs |
| pytest as the app test runner | `unittest` `*_check.py` scripts | No pytest in this tree |

## Status & Phase Vocabulary

| Term | Meaning |
|-|-|
| Researching … Done | CoreBase SpecHarness lifecycle tokens in `corebase-specharness/project/state-machine.yaml` |
| advisory verification | `harness-config.yaml` `verification.mode: advisory`; exit 0 is not a closeout verdict |
