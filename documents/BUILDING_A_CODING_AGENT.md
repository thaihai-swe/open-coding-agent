# Building a Coding Agent CLI from Scratch: Python Master Blueprint

A comprehensive, production-grade guide and 20-step progressive implementation roadmap for building an AI coding agent CLI in **Python** from scratch. This blueprint synthesizes architectural patterns from Claude Code, Claw Code, Learn Claude Code (ShareAI), and Cordum control-plane security research.

---

## 1. System Architecture & Component Design

The agent harness uses a modular Python architecture (`src/`) where high-level orchestration, state management, security policy evaluation, and tool execution are isolated into single-responsibility modules.

```
                    User Terminal (repl / CLI Args)
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │   bootstrap_graph.py     │  (7-stage bootstrap pipeline)
                     └────────────┬─────────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │     runtime.py       │  (Input tokenization & prompt routing)
                       └──────────┬───────────┘
                                  │
      ┌───────────────────────────┴───────────────────────────┐
      ▼                                                       ▼
┌─────────────┐                                     ┌───────────────────┐
│ commands.py │ (15 Slash Commands + 27 CLI subcmds)│  query_engine.py  │
└─────────────┘                                     └─────────┬─────────┘
                                                              │ (Turn loop & events)
                                                              ▼
                                                    ┌───────────────────┐
                                                    │   tool_pool.py    │ (Max 15 tools in prompt)
                                                    └─────────┬─────────┘
                                                              │
                                                              ▼
                                                    ┌───────────────────┐
                                                    │     tools.py      │ (19 Pydantic tool specs)
                                                    └─────────┬─────────┘
                                                              │
                                                              ▼
                                                    ┌───────────────────┐
                                                    │   permissions.py  │ (PermissionPolicy & DenyList)
                                                    └───────────────────┘
```

### 1.1 Core Python Subsystems

* **`bootstrap_graph`**: Executes a 7-stage deterministic startup pipeline:
  1. `Prefetch`: Warms config caches and loads reference snapshots.
  2. `Warning Handler`: Attaches global warning filters to suppress noisy library output.
  3. `CLI Parser`: Fast-path check for simple flags (e.g. `--version`), then parses CLI arguments.
  4. `Setup + Commands Parallel Load`: Concurrently loads env vars, MCP servers, and command registry.
  5. `Deferred Init`: Lazy-loads heavy modules (e.g., OpenTelemetry, gRPC).
  6. `Mode Routing`: Directs execution mode (`local`, `remote`, `ssh`, `teleport`, `direct-connect`, `deep-link`).
  7. `Query Engine Submit Loop`: Hands control over to the interactive repl turn loop.
* **`provider_abstraction`**: OpenAI-standard API client abstraction layer supporting Anthropic, OpenAI, Azure OpenAI, Ollama, OpenRouter, and local OpenAI-compatible endpoints with streaming tool calls, structured outputs, automatic retries, and fallback chains.
* **`terminal_ui`**: Terminal UI engine providing real-time Markdown rendering, live tool/status output streaming, interactive permission prompts, accessible screen-reader/high-contrast fallback modes, structured JSON export formatting, and graceful signal handling (Ctrl+C cleanup without state loss).
* **`query_engine`**: Stateful conversation orchestrator enforcing limits (`max_turns=8`, `max_budget_tokens=2000`, `compact_after_turns=12`). Manages concurrent-safe tool execution, Ctrl+C cancellation signals without losing state, and yields real-time SSE stream events (`message_start`, `command_match`, `tool_match`, `permission_denial`, `message_delta`, `message_stop`).
* **`runtime`**: Dispatches raw user input through prompt routing, returning matched command/tool objects.
* **`commands`**: Slash command registry and execution pipeline backed by structured command metadata.
* **`tools` & `tool_pool`**: Tool input schema validation, tool execution dispatch, and prompt tool filtering (capping visible tools in prompt, handling simple mode).
* **`permissions`**: Multi-layer security engine combining prompt-level tool hiding, AST-level command safety checks, policy modes, and interactive user prompts.
* **`session_store` & `transcript`**: Persistence layer using immutable message snapshots with context boundary markers and dual compaction.
* **`mcp_client`**: Model Context Protocol client managing stdio, SSE, HTTP, WebSocket, SDK, and proxy transports with server namespacing.

---

## 2. The Built-in Agent Tools Specification

Every tool is defined using Python `dataclasses` and `Pydantic` models for input validation.

| #   | Tool Name          | Category      | Risk Level | Description & Key Parameters                                                                                                                                                      |
| --- | ------------------ | ------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `bash`             | Shell         | **HIGH**   | Executes shell commands in a sandbox. Params: `command` (str), `timeout` (ms, max 600000), `description` (str), `run_in_background` (bool), `dangerously_disable_sandbox` (bool). |
| 2   | `read_file`        | File I/O      | **LOW**    | Reads text, images, PDFs, or notebooks. Params: `file_path` (str), `offset` (int), `limit` (int), `pages` (str). Formats output with `cat -n` line numbers.                       |
| 3   | `write_file`       | File I/O      | **MEDIUM** | Overwrites or creates files. Params: `file_path` (str), `content` (str). Returns `structured_patch` and `git_diff`.                                                               |
| 4   | `edit_file`        | File I/O      | **MEDIUM** | String replacement. Params: `file_path` (str), `old_string` (str), `new_string` (str), `replace_all` (bool). Fails if `old_string` is non-unique (unless `replace_all=True`).     |
| 5   | `glob_search`      | Search        | **LOW**    | Fast file pattern matching. Params: `pattern` (str), `path` (str). Results sorted by modification date, truncated at 100 entries.                                                 |
| 6   | `grep_search`      | Search        | **LOW**    | Regex search via `ripgrep`. Params: `pattern` (str), `path` (str), `glob` (str), `output_mode` (`content` \| `files_with_matches` \| `count`), `head_limit` (default 250).        |
| 7   | `web_fetch`         | Network       | **MEDIUM** | Scrapes external URL content. Params: `url` (str), `prompt` (str). Subject to network permission rules.                                                                           |
| 8   | `web_search`        | Network       | **LOW**    | Performs web search. Params: `query` (str), `allowed_domains` (list[str]).                                                                                                        |
| 9   | `todo_write`        | Planning      | **LOW**    | Manages internal task list. Params: `todos` (list of `{id, content, status, priority}`). Statuses: `pending`, `in_progress`, `completed`.                                         |
| 10  | `skill`            | Agent         | **LOW**    | Loads dynamic domain workflows. Params: `skill` (str), `args` (dict).                                                                                                             |
| 12  | `tool_search`       | Discovery     | **LOW**    | Searches deferred tools not currently in context. Params: `query` (str, e.g. `select:read_file,edit_file` or `+slack`).                                                           |
| 15  | `send_user_message`  | Communication | **LOW**    | Sends message to user. Params: `message` (str), `attachments` (list), `status` (`normal` \| `proactive`).                                                                         |
| 16  | `config`           | Settings      | **MEDIUM** | Reads or modifies runtime settings. Params: `action` (`get` \| `set`), `key` (str), `value` (any).                                                                                |
| 17  | `structured_output` | Output        | **LOW**    | Returns structured JSON to caller. Params: `data` (dict/list).                                                                                                                    |
| 18  | `repl`             | Execution     | **HIGH**   | Stateful code interpreter execution. Params: `language` (str), `code` (str). Maintains state between calls.                                                                       |
| 19  | `powershell`       | Shell         | **HIGH**   | Windows-native shell execution (conditional on Windows platform). Params: `command` (str), `timeout` (ms).                                                                        |
---

## 3. Command System & Categorization

The command surface consists of **15 interactive slash commands** inside the repl and **27 CLI subcommands** invoked directly from the shell (42 total operations).

### 3.1 15 Interactive Slash Commands

| Command        | Arguments        | Resume Compatible? | Description                                                                          |
| -------------- | ---------------- | ------------------ | ------------------------------------------------------------------------------------ |
| `/help`        | none             | No                 | Displays available slash commands and descriptions.                                  |
| `/status`      | none             | Yes                | Shows turns completed, active model, and token usage summary.                        |
| `/compact`     | none             | Yes                | Forces manual context compaction (preserves recent 4 messages).                      |
| `/model`       | `[model_id]`     | No                 | Views or switches active LLM model immediately.                                      |
| `/permissions` | `[mode]`         | No                 | Views or changes permission mode (`ReadOnly`, `WorkspaceWrite`, `DangerFullAccess`). |
| `/clear`       | `[--confirm]`    | Yes                | Resets conversation context window while retaining session ID.                       |
| `/cost`        | none             | Yes                | Displays precise token costs formatted in `$X.XXXX`.                                 |
| `/resume`      | `<path>`         | No                 | Restores conversation state from a saved session file.                               |
| `/config`      | `[subcommand]`   | Yes                | Views/edits runtime config (`env`, `hooks`, `model`).                                |
| `/memory`      | none             | Yes                | Displays persistent memory entries and utilization.                                  |
| `/init`        | none             | Yes                | Re-scans working directory and reloads `CLAUDE.md`.                                  |
| `/diff`        | none             | Yes                | Shows uncommitted working directory git changes.                                     |
| `/version`     | none             | Yes                | Displays framework version and active runtime environment.                           |
| `/export`      | `[file_path]`    | Yes                | Exports full transcript and tool calls to file.                                      |
| `/session`     | `[list\|switch]` | No                 | Lists active sessions or switches between concurrent sessions.                       |

### 3.2 CommandGraph Taxonomy
Commands are categorized into a frozen dataclass `CommandGraph`:
* **`builtins`**: Core session commands (`/help`, `/status`, `/compact`, `/clear`, `/cost`, `/version`, `/diff`).
* **`plugin_like`**: configurable extension commands (`/model`, `/permissions`, `/config`, `/export`, `/session`).
* **`skill_like`**: Multi-step composite workflows (`/resume`, `/memory`, `/init`).

---

## 4. Query Engine & Turn Orchestration

The `QueryEnginePort` manages turn cycles, event generation, and budget enforcement.

```python
@dataclass
class QueryEngineconfig:
    max_turns: int = 8
    max_budget_tokens: int = 2000
    compact_after_turns: int = 12
    structured_output: bool = False
    structured_retry_limit: int = 2
```

### 4.1 Execution Loop & Event Protocol
1. User prompt submitted via `submit_message()` or streamed via `stream_submit_message()`.
2. Engine invokes LLM client API with accumulated `mutable_messages` and `ToolPool` (max 15 tools).
3. Response parsed:
   * If text response -> yield `message_delta` -> yield `message_stop` with `stop_reason="completed"`.
   * If slash command -> yield `command_match` -> execute command handler.
   * If tool call -> check `permissions.py`. If denied -> yield `permission_denial`. If allowed -> yield `tool_match` -> execute tool -> append `ToolResult` to history -> loop turn.
4. Termination triggers: `completed`, `max_turns_reached` (turn counter >= 8), or `max_budget_reached` (tokens >= 2000).

---

## 5. Control Plane & Security Engine

Security is enforced through multi-tier permission checking, protected file rules, and inbound tool output scanning.

### 5.1 Graduated Permission Modes
* **`plan` (`ReadOnly`)**: Analysis mode. File writes and shell executions are strictly blocked.
* **`default` (`WorkspaceWrite`)**: Standard developer mode. Workspace file I/O auto-approved; shell commands prompt user.
* **`acceptEdits`**: Workspace file edits auto-approved; non-workspace and shell commands prompt user.
* **`auto`**: Classifier-assisted auto-approval. Tool calls evaluated against ML/rule classifier; high-risk operations prompt user.
* **`bypassPermissions` (`DangerFullAccess`)**: Skips all prompts. Used only in isolated cloud containers.

### 5.2 Defensive Guardrails
1. **Tool Registry Filter**: Filters denied tools before constructing the prompt, preventing the model from knowing blocked tools exist.
2. **Per-Call Permission Verification**: Validates invocations against rule sets (tool name, parameters, path patterns) before execution.
3. **AST-Level Command Analysis**: Analyzes command ASTs (e.g. for shell execution) to reject dangerous patterns (recursion bombs, unauthorized privilege escalation, TTY manipulation) prior to policy approval.
4. **Protected File Paths**: Rejects file operations targeting sensitive paths (`.gitconfig`, `.bashrc`, `.zshrc`, `.env`, SSH keys).
5. **Inbound Prompt-Injection Scanner**: Scans raw outputs from fetched URLs, shell output, and file reads before appending them to history.

---

## 6. Context & Memory Subsystem

### 6.1 System Prompt Assembly & Boundaries
System prompts are built at runtime by discovering workspace instruction files in order:
1. `.claude/CLAUDE.md`
2. `CLAUDE.local.md`
3. `CLAUDE.md` (root directory upwards to parent directories)

**Hard Rules**:
* `MAX_INSTRUCTION_FILE_CHARS = 4000` (max characters per file).
* `MAX_TOTAL_INSTRUCTION_CHARS = 12000` (max total system instruction length).
* Content hash deduplication prevents duplicate instruction injection across monorepos.

### 6.2 Dual Compaction & History Architecture
* **Engine Compaction**: Triggers when context utilization hits configured limits. Inserts a compaction boundary marker, preserves recent conversation turns, and summarizes older turns (extracting key files, current focus, and remaining work).
* **TranscriptStore Compaction**: Secondary buffer compaction ensuring persistent logs remain bounded.
* **Background Memory ("Dreaming")**: Idle-time background pass that consolidates session history, prunes outdated context, and maintains project memory files.

---

## 7. Model Context Protocol (MCP) Integration

External systems integrate via MCP standards:
* **6 Transport Types**: `Stdio`, `SSE`, `HTTP`, `WebSocket`, `SDK`, `ClaudeAiProxy`.
* **Deterministic Tool Namespacing**: `mcp__{normalized_server}__{tool_name}` (e.g. `mcp__postgres__select_query`).
* **config Hashing**: 64-bit FNV-1a hash algorithm (`0xcbf29ce484222325` seed basis) for deduplicating server instances across config files.
* **config Priority Merging**: `~/.claude/settings.json` (User) < `.claude/settings.json` (Project) < `.claude/settings.local.json` (Local Override).

---

## 8. Extension Points

Extension points let users adapt the CLI without modifying its core agent loop.

* **Custom Agents**: Reusable specialist sub-agents defined by Markdown prompts, roles, allowed tools, and isolation requirements.
* **skills**: Parameterized Markdown workflows that add domain knowledge or compose common actions into discoverable commands.
* **Hooks**: configurable lifecycle actions before and after tool execution for linting, logging, notifications, and policy checks.
* **Plugins**: Installable packages that can contribute tools, commands, skills, terminal UI elements, and integrations.
* **MCP Capabilities**: Beyond MCP tools, support MCP resources (readable external context) and prompts (reusable server-provided templates).
* **Instruction Composition**: Allow instruction files to import shared instructions while retaining local project overrides and strict content limits.

---

## 9. 20-Session Progressive Implementation Roadmap

This 20-step roadmap guides you from a basic 100-line script (`s01`) to a complete production harness (`s20`).

```
Tools & Execution          (s01 – s04)
Planning & Coordination    (s05 – s07, s10, s11)
Memory Management          (s08 – s09)
Concurrency & Scheduling   (s13 – s14)
Multi-Agent Platform       (s12, s15 – s20)
```

### Milestone Schedule

#### Session 01: Provider Foundation & Minimal Agent Loop
* **Goal**: Define a provider-neutral, OpenAI-standard chat and tool-calling interface; implement an initial OpenAI-compatible provider and a minimal repl that sends messages, executes tool calls, and appends results to history.

#### Session 02: Terminal Experience & Tool Registry
* **Goal**: Build an accessible terminal renderer with multiline input, Markdown rendering, live status/tool output, JSON output mode, and cleanup that preserves session state after cancellation; create a dispatch table for core tools (`read_file`, `write_file`, `edit_file`, `bash`, `glob`).

#### Session 03: Permission Gate
* **Goal**: Implement permission checks intercepting high-risk operations (e.g. `bash`) to request user confirmation (`[A]pprove/[D]eny`).

#### Session 04: Lifecycle Hooks
* **Goal**: Add lifecycle event hooks (`pre_tool_call`, `post_tool_call`, `on_error`) for logging, telemetry, and auditing.

#### Session 05: Explicit Planning Subsystem
* **Goal**: Implement task list tools allowing the agent to create and update structured plan states.

#### Session 06: Isolated Sub-Agents
* **Goal**: Enable the main agent to launch child sub-agents with clean, isolated context windows.

#### Session 07: Dynamic skill Loading
* **Goal**: Add skill tools to load external domain instructions dynamically into context when needed.

#### Session 08: Context Compaction
* **Goal**: Implement context summarization triggering after extended turns while preserving recent history.

#### Session 09: Persistent Memory System
* **Goal**: Build persistent project memory surviving session clears and transcript compactions.

#### Session 10: Dynamic System Prompt Assembly
* **Goal**: Assemble system prompts at runtime combining instruction files (`AGENTS.md`), active tools, skill definitions, and security policies.

#### Session 11: Error Recovery & Retry Classifier
* **Goal**: Classify tool execution errors (syntax error, missing argument, non-zero return code) and construct feedback prompts for self-correction.

#### Session 12: Structured Task Board
* **Goal**: Build task graph management tools (`TaskCreate`, `TaskUpdate`, `TaskStop`) to orchestrate multi-step engineering goals.

#### Session 13: Non-Blocking Background Tasks
* **Goal**: Support background command execution with asynchronous process polling and notification events.

#### Session 14: Cron Task Scheduler
* **Goal**: Add harness-managed scheduled execution for periodic background checks.

#### Session 15: Agent Teams & Mailboxes
* **Goal**: Support multi-agent teams with dedicated message mailboxes and process isolation.

#### Session 16: Inter-Agent Communication Protocol
* **Goal**: Standardize structured message passing contracts between agent team members.

#### Session 17: Autonomous Task Claiming
* **Goal**: Allow idle background agents to scan the task board and claim pending tasks autonomously.

#### Session 18: Git Worktree Isolation
* **Goal**: Implement worktree management to give parallel sub-agents isolated filesystem directories.

#### Session 19: MCP Tool Client Bridge
* **Goal**: Build full MCP client supporting stdio and HTTP/SSE transport discovery with explicit tool namespacing.

#### Session 20: Multi-Provider Production Harness & Evaluation
* **Goal**: Assemble all subsystems into a production-hardened CLI with OpenAI-standard multi-provider abstractions, full terminal UX streaming, structured JSON output options, automated retry/fallback mechanisms, and end-to-end evaluation suites.

---

## 10. Verification & Evaluation Strategy

To verify the agent as it is built:
1. **Unit Testing (`pytest`)**: Test Pydantic schemas, permission deny-lists, context summarization, and prompt assembly.
2. **Mock Tool Evals**: Test tool call handling using mock LLM responses without invoking real API endpoints.
3. **End-to-End Task Evaluation**: Run benchmark coding tasks (e.g. refactoring a script, fixing a failing test, creating a feature branch) to evaluate autonomy and self-correction.
