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

## Technical Terms

| Term | Definition | Used In |
|-|-|-|
| QueryEngine | Orchestrates one user turn: provider complete, stream collect, tool loop, session save | `src/application/query_engine.py` |
| Provider | Protocol for `complete(messages, tools, stream)` | `src/domain/provider.py` |
| OpenAIProvider | Stdlib HTTP client for OpenAI-compatible `/chat/completions` | `src/infrastructure/providers/openai.py` |
| SessionStore | JSON transcript persistence under `.sessions/` | `src/infrastructure/session_store.py` |
| Tool registry | Singleton map of name → `Tool` (schema + handler + risk) | `src/tools/registry.py` |
| `glob` alias | Public tool name that performs the same operation as `glob_search` | `1-tool-and-execution` |
| Risk | `HIGH` / `MEDIUM` / `LOW` tool permission class | `src/tools/types.py` |
| Authorize | UI callback that must return true before MEDIUM/HIGH `invoke` | `src/presentation/terminal_ui.py` |
| `bypass_permissions` | Kwarg that skips HIGH `check_permission`; QueryEngine sets it after approve | `src/application/query_engine.py`, `src/tools/permissions.py` |
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
| Treating the whole `BUILDING_A_CODING_AGENT.md` as architecture | `src/`, tests, and the active feature `spec.md` | Blueprint is not a global contract; Session 02 is in scope only as locked in `1-tool-and-execution` |
| pytest as the app test runner | `unittest` `*_check.py` scripts | No pytest in this tree |

## Status & Phase Vocabulary

| Term | Meaning |
|-|-|
| Researching … Done | CoreBase SpecHarness lifecycle tokens in `corebase-specharness/project/state-machine.yaml` |
| advisory verification | `harness-config.yaml` `verification.mode: advisory`; exit 0 is not a closeout verdict |
