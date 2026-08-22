# Glossary

> Ownership: `Adopter-owned`
> Technical terms pre-filled from code (2026-04-08). Product/domain terms remain `[USER REVIEW NEEDED]`.

This is the project-wide vocabulary seed. Domain-specific vocabulary belongs
in `core-zero/memories/domain/glossary.md`, which is an optional replaceable
domain pack rather than a second project glossary.

## Domain Terms

| Term | Definition | Used In |
|-|-|-|
| `[USER REVIEW NEEDED]` | Product/business language not stated by the adopter | `[UNKNOWN]` |

## Technical Terms

| Term | Definition | Used In |
|-|-|-|
| QueryEngine | Application loop: persist user turn, stream provider completion, run authorized tools, persist again | `src/application/query_engine.py` |
| OpenAIProvider | Stdlib HTTP + SSE client for `{api_base}/chat/completions`; not the official OpenAI SDK | `src/infrastructure/providers/openai.py` |
| SessionStore | JSON persistence of chat history under `.sessions/<id>.json` with key redaction | `src/infrastructure/session_store.py` |
| authorize | Interactive approve/deny callback invoked for HIGH and MEDIUM tools | `src/presentation/terminal_ui.py`, `QueryEngine._run_call` |
| bypass_permissions | Kwarg that skips the HIGH-risk gate inside `check_permission` | `src/tools/permissions.py`, `query_engine.py` |
| ProviderError | Domain error for missing config, bad JSON, HTTP failures, or invalid provider payloads | `src/domain/errors.py` |
| tool_denied | Event type emitted when the user denies a tool; turn continues with an error ToolResult | `QueryEngine`, `TerminalUI` |
| Risk | HIGH / MEDIUM / LOW classification on each registered tool | `src/tools/types.py` |
| shim | Flat `src/*.py` re-export of a layered module; not a second implementation | `src/cli.py`, `src/provider.py`, etc. |
| PROTECTED_PATHS | Substring list blocking some MEDIUM file/config writes: `.gitconfig`, `.bashrc`, `.zshrc`, `.env`, `id_rsa` | `src/tools/types.py` |

## Abbreviations

| Abbreviation | Expansion | Context |
|-|-|-|
| SSE | Server-Sent Events | Provider streaming (`data: ...`, `[DONE]`) |
| REPL | Read-Eval-Print Loop | Interactive `python3 -m src.cli` session |
| CLI | Command-Line Interface | `src/presentation/cli.py` |

## Naming Conventions

| Domain Concept | Code Name | Pattern | Example |
|-|-|-|-|
| Chat turn message | `ChatMessage` | PascalCase frozen dataclass | `ChatMessage("user", prompt)` |
| Tool invocation | `ToolCall` | PascalCase frozen dataclass | `ToolCall(id, name, arguments)` |
| Tool outcome | `ToolResult` | PascalCase frozen dataclass | `ToolResult(call_id, content, is_error)` |
| Provider stream chunk | `StreamDelta` | PascalCase frozen dataclass | `StreamDelta(content=..., done=False)` |

## Forbidden Terms

| Avoid | Use Instead | Reason |
|-|-|-|
| "this repo is CoreZero" | "this repo is a coding-agent CLI; CoreZero is the installed harness" | Kit seed language is not product identity |
| Treat `BUILDING_A_CODING_AGENT.md` as implemented | Cite `src/` + tests | Blueprint is a roadmap |

## Status & Phase Vocabulary

| Term | Meaning |
|-|-|
| Researching | Brownfield mapping / `/spec-research` in progress |
| ResearchComplete | Analysis artifact accepted |
| Specifying | `/spec-requirements` in progress |
| SpecApproved | Spec accepted |
| Planning | `/spec-plan` in progress |
| TaskPlanning | `/spec-tasks` in progress |
| PlanApproved | Plan and tasks accepted |
| Implementing | `/spec-implement` in progress |
| Verifying | `/harness-verify` in progress |
| Done | Closeout complete |

<!-- The kit uses these phases by default: Researching, ResearchComplete, Specifying, SpecApproved, Planning, TaskPlanning, PlanApproved, Implementing, Verifying, Done -->
