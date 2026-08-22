# Project Tech Stack

> Source: Phase A Archaeology Sweep (2026-04-08)
> Ownership: Adopter-owned

## Languages & Runtimes

| Language | Version | Purpose | Package Manager |
| - | - | - | - |
| Python | `>=3.11` (tested on 3.13.13; uses `enum.StrEnum`) | Core coding agent application, CLI, tests | `pip` (stdlib-only; no manifest) |

## Frameworks

| Framework | Version | Purpose | Docs |
| - | - | - | - |
| None (standard library) | Python 3.13 stdlib | Application, HTTP client, test runner, CLI parsing | https://docs.python.org/3/ |

## Key Dependencies

| Package | Version | Purpose | Notes |
| - | - | - | - |
| `urllib.request` | stdlib | Outbound HTTP POST and SSE parsing for OpenAI chat completions | Zero third-party HTTP dependencies |
| `dataclasses` | stdlib | Domain message, response, and tool models | Replaced blueprint's Pydantic spec |
| `subprocess` | stdlib | `bash` and `powershell` tool execution | Runs under `shell=True` |
| `unittest` | stdlib | Test runner and assertions (`tests/*_check.py`) | No pytest configured |
| `argparse` | stdlib | CLI argument parsing (`src/presentation/cli.py`) | `--session`, `--json`, `--debug` |

## Internal Libraries & Utilities

| Module | Path | Purpose | Key Exports |
| - | - | - | - |
| Tool Registry | `src/tools/registry.py` | Tool dataclass and singleton registry | `Tool`, `ToolRegistry`, `registry` |
| Permissions | `src/tools/permissions.py` | Permission checking, protected path matching, argument validator | `check_permission`, `validate_args` |
| Domain Models | `src/domain/models/` | Immutable message, response, delta, call, and result models | `ChatMessage`, `ProviderResponse`, `StreamDelta`, `ToolCall`, `ToolResult` |
| OpenAI Provider | `src/infrastructure/providers/openai.py` | Standard HTTP / SSE client for `/chat/completions` | `OpenAIProvider`, `ProviderError` |
| Session Store | `src/infrastructure/session_store.py` | JSON session persistence with credential redaction | `SessionStore` |
| Query Engine | `src/application/query_engine.py` | Multi-turn agent loop with authorize callback and tool invoke | `QueryEngine` |
| Terminal UI | `src/presentation/terminal_ui.py` | Interactive prompt, authorization UX, event renderer | `TerminalUI` |
| CLI | `src/presentation/cli.py` | Main CLI runner and argument parsing | `run`, `parse_args` |
| Root Facades | `src/*.py` | Backward-compatible flat import shims | Re-exports from subpackages |

## External APIs

| API | Base URL | Auth | Rate Limit | SDK |
| - | - | - | - | - |
| OpenAI-compatible Chat Completions | Configurable via `OPENAI_API_BASE` or `.secrets/config.json` | `Bearer <OPENAI_API_KEY>` | Provider-dependent | Raw stdlib `urllib.request` |

## Databases & Storage

| Store | Type | Purpose | Access Pattern |
| - | - | - | - |
| Local Disk (`.sessions/<id>.json`) | Flat JSON files | Conversation history persistence across turns and sessions | Read/write via `SessionStore` with sensitive key redaction |
| Local Config (`.secrets/config.json`) | JSON file | Local API credentials and endpoint configuration | Read via `_load_config()` with fallback to environment |

## Infrastructure & Services

| Service | Type | Purpose | Notes |
| - | - | - | - |
| None | Local execution only | CLI runs entirely on local machine | No cloud infrastructure or daemon required |

## Development Tools

| Tool | Purpose | Config File | Key Commands |
| - | - | - | - |
| `unittest` | Unit test suite | None (runs via python discovery) | `python3 -m unittest discover -s tests -p "*_check.py"` |
| `py_compile` | Syntax / bytecode verification | None | `python3 -m py_compile src/cli.py src/presentation/cli.py` |

## Environment Variables

| Variable | Purpose | Required | Default |
| - | - | - | - |
| `OPENAI_API_BASE` | Base URL for OpenAI-compatible endpoint | Yes (if not in config file) | None |
| `OPENAI_API_KEY` | Bearer API token | Yes (if not in config file) | None |
| `OPENAI_MODEL` | Target model name | Yes (if not in config file) | None |
| `CONFIG_FILE` | Path to JSON config file | No | `.secrets/config.json` |

## Version Pinning Policy

- Production deps: Stdlib only; Python `>=3.11` required (uses `enum.StrEnum`).
- Dev deps: None configured.
- Upgrade cadence: `[USER REVIEW NEEDED]`
- Security patches: `[USER REVIEW NEEDED]`
