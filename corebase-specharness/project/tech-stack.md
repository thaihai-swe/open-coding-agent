# Project Tech Stack

Pre-filled by `/starter-init` on 2026-08-22 from repository evidence. `cli.py init` reported `detected_stacks: []` because it only looks for `pyproject.toml`, `requirements.txt`, or `setup.py`; those files are absent. The application is still Python.

## Languages & Runtimes

| Language | Version | Purpose | Package Manager |
| - | - | - | - |
| Python | App code uses `enum.StrEnum` (`src/tools/types.py`) → **3.11+**. Local interpreter observed: 3.13.13. Kit `manifest.json` / `install.sh` require **>=3.10** for the harness CLI. | Coding-agent CLI (`src/`) and CoreBase SpecHarness scripts | None declared (no `pyproject.toml`, `requirements.txt`, `setup.py`, or lockfile) |

## Frameworks

| Framework | Version | Purpose | Docs |
| - | - | - | - |
| None | — | `src/` is stdlib-only (no pytest, Pydantic, HTTP client library). | `documents/how-to-run.md` |

## Key Dependencies

| Package | Version | Purpose | Notes |
| - | - | - | - |
| (none third-party in `src/`) | — | Agent uses stdlib: `argparse`, `dataclasses`, `enum`, `json`, `pathlib`, `subprocess`, `urllib.request`, `uuid`, … | Optional kit-only: `tiktoken` in `corebase-specharness/scripts/core/_lib/token_counter.py` if installed |

## Internal Libraries & Utilities

| Module | Path | Purpose | Key Exports |
| - | - | - | - |
| QueryEngine | `src/application/query_engine.py` | Turn loop, streaming collect, tool dispatch, session save | `QueryEngine` |
| Provider protocol | `src/domain/provider.py` | LLM completion seam | `Provider.complete` |
| OpenAIProvider | `src/infrastructure/providers/openai.py` | OpenAI-compatible `/chat/completions` over stdlib urllib | `OpenAIProvider` |
| SessionStore | `src/infrastructure/session_store.py` | JSON transcripts under `.sessions/` | `create`, `save`, `load`, `list` |
| TerminalUI / CLI | `src/presentation/` | REPL, authorize prompt, JSON events | `parse_args`, `run`, `TerminalUI` |
| Tool registry | `src/tools/` | Register/invoke tools + permission checks | `registry`, `invoke`, `check_permission` |

Top-level `src/*.py` files (`cli.py`, `query_engine.py`, `session.py`, `terminal_ui.py`, `provider.py`) are re-export shims. `src/tools.py` is shadowed by the `src/tools/` package.

## External APIs

| API | Base URL | Auth | Rate Limit | SDK |
| - | - | - | - | - |
| OpenAI-compatible Chat Completions | Caller-configured `OPENAI_API_BASE` + `/chat/completions` | Bearer `OPENAI_API_KEY` | `[UNKNOWN]` | None (stdlib `urllib.request`) |

`web_search` in `src/tools/handlers/network.py` returns a stub `https://example.com/search?q=...` and does not call a search API.

## Databases & Storage

| Store | Type | Purpose | Access Pattern |
| - | - | - | - |
| `.sessions/` | JSON files (`{session_id}.json`) | Conversation history | Create/save/load; gitignored |
| `.secrets/config.json` | JSON object of string values | Provider settings | Read at provider init; **not** gitignored |

## Infrastructure & Services

| Service | Type | Purpose | Notes |
| - | - | - | - |
| None deployed | Local CLI | No CI (`.github/` absent), no Makefile, no container/runtime manifest | |

## Development Tools

| Tool | Purpose | Config File | Key Commands |
| - | - | - | - |
| stdlib `unittest` | App checks | None (each `tests/*_check.py` is a script) | Documented: `python3 tests/{provider,session,query_engine,terminal_ui,cli}_check.py`. Argv-safe equivalent that passed on 2026-08-22: `python3 -m unittest discover -s tests -p '*_check.py'` |
| `py_compile` / `compileall` | Syntax check | None | Documented: `python3 -m py_compile src/**/*.py`. Argv-safe equivalent that passed: `python3 -m compileall -q src` |
| CoreBase SpecHarness CLI | Doctor, init, verify | `corebase-specharness/project/harness-config.yaml` | `python3 corebase-specharness/scripts/core/cli.py doctor --json` |
| Lint / format / mypy | `[UNKNOWN]` — no ruff/black/mypy config in repo | `.mypy_cache/` exists locally only | No documented command |

## Environment Variables

| Variable | Purpose | Required | Default |
| - | - | - | - |
| `OPENAI_API_BASE` | Provider base URL | Yes (or JSON `openai_api_base`) | `""` |
| `OPENAI_API_KEY` | Bearer token | Yes (or JSON `openai_api_key`) | `""` |
| `OPENAI_MODEL` | Model id | Yes (or JSON `openai_model`) | `""` |
| `CONFIG_FILE` | Path to JSON config | No | `.secrets/config.json` |

Env overrides JSON when set (`tests/provider_check.py`). Missing base/key/model → `ProviderError`; CLI `run()` returns `2`.

`documents/how-to-run.md` says copy `documents/config.example.json`; that file is **absent**.

## Version Pinning Policy

- Production deps: none declared
- Dev deps: none declared
- Upgrade cadence: `[UNKNOWN]`
- Security patches: `[UNKNOWN]`
