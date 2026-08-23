# Missing Features Audit

Based on `documents/BUILDING_A_CODING_AGENT.md` compared against the current codebase (`src/` and completed feature artifacts 1 through 7), here are all the defined features, subsystems, tools, and commands that have **not been implemented yet**:

---

### 1. Missing Core Subsystems & Architecture (Sections 1, 4, 5, 7, 8)
- **`bootstrap_graph` (7-stage startup pipeline)**:
  - Deterministic startup pipeline: `Prefetch`, `Warning Handler`, `CLI Parser`, `Setup + Commands Parallel Load`, `Deferred Init`, `Mode Routing`, and `Query Engine Submit Loop`.
  - Execution modes (`remote`, `ssh`, `teleport`, `direct-connect`, `deep-link`).
- **`tool_pool`**:
  - Dynamic tool prompt cap (max 15 tools visible in context prompt at once) and simple-mode tool filtering.
- **Model Context Protocol (MCP) Client (Section 7 / Session 19)**:
  - 6 MCP transport implementations (`Stdio`, `SSE`, `HTTP`, `WebSocket`, `SDK`, `ClaudeAiProxy`).
  - Deterministic tool namespacing (`mcp__{server}__{tool}`) and 64-bit FNV-1a config deduplication hashing.
  - Hierarchical MCP config merging (`~/.claude/` < `.claude/` < `.claude/settings.local.json`).
  - MCP Resources (readable external context) and MCP Prompts (reusable server-provided templates).
- **Lifecycle Event Hooks (Section 8 / Session 04)**:
  - Pre- and post-tool call interception hooks (`pre_tool_call`, `post_tool_call`, `on_error`) for linting, auditing, and telemetry.
- **Graduated Security Engine / Permission Modes (Section 5.1)**:
  - Permission modes: `plan` (`ReadOnly`), `acceptEdits`, `auto` (classifier-assisted auto-approval). *(Current implementation supports per-call interactive authorization prompts + `.cda/.permission_rules/rules.json` allow/deny rules).*
  - **AST-level Command Safety Analysis**: Shell AST scanning for fork bombs, privilege escalation, or unsafe escapes.
  - **Inbound Prompt-Injection Scanner**: Automated sanitization/scanning of fetched web URLs and shell output before history injection.

---

### 2. Missing Interactive Slash Commands & CLI Subcommands (Section 3)

Out of **15 interactive slash commands**, only `/compact` and `/memory` (plus dynamic `/skill-name` expansion) are currently implemented in the REPL.

**Missing Slash Commands (13/15):**
1. `/help` — Displays available slash commands and usage descriptions.
2. `/status` — Displays completed turns, active model, and token usage summary.
3. `/model [model_id]` — Real-time model inspection and runtime model switching.
4. `/permissions [mode]` — View or switch active permission mode (`ReadOnly`, `WorkspaceWrite`, `DangerFullAccess`).
5. `/clear [--confirm]` — Clears context window while retaining current session ID.
6. `/cost` — Displays token consumption and exact dollar cost (`$X.XXXX`).
7. `/resume <path>` — Restores conversation state from an explicit saved session file.
8. `/config [subcommand]` — Dynamic view/edit of runtime config (`env`, `hooks`, `model`).
9. `/init` — Re-scans working directory and reloads instruction files.
10. `/diff` — Shows uncommitted git changes directly in terminal.
11. `/version` — Displays agent framework version and active runtime environment.
12. `/export [file_path]` — Exports full transcript and tool calls to structured file.
13. `/session [list|switch]` — Interactive multi-session manager.

**Missing 27 CLI Subcommands & `CommandGraph` taxonomy**:
- Categorization into frozen `CommandGraph` dataclass (`builtins`, `plugin_like`, `skill_like`).
- Standalone CLI command execution outside REPL (e.g. `cda diff`, `cda config set`, etc.).

---

### 3. Missing Tools & Tool Capabilities (Section 2)
- **`todo_write`**: The monolithic batch plan tool from Section 2 was superseded by the 6-tool task board (`create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`), but the exact spec `{id, content, status, priority}` from Section 2 is not present.
- **`read_file` Multi-Format Support**: Missing PDF, notebook (`.ipynb`), and image extraction (currently reads plain UTF-8 text only).
- **`write_file` Diff Return**: Missing return of `structured_patch` and `git_diff` in tool result.
- **`bash` & `powershell` Background Execution**: `run_in_background` flag and `dangerously_disable_sandbox` parameters are not implemented.
- **`web_search` Allowed Domains**: `allowed_domains` filter parameter is not implemented (currently placeholder).

---

### 4. Missing Roadmap Milestones (Section 9)

The completed features cover roadmap milestones **s01–s03, s05, s07–s10**. The following roadmap milestones remain unimplemented:

- **Session 04 — Lifecycle Hooks**:
  - Add lifecycle event hooks (`pre_tool_call`, `post_tool_call`, `on_error`) for logging, telemetry, and auditing.
- **Session 11 — Error Recovery & Retry Classifier**:
  - Structured classification of tool execution failures (syntax error, missing argument, non-zero return code) and automated feedback prompt construction for self-correction.
- **Session 19 — MCP Tool Client Bridge**:
  - Full MCP client supporting stdio and HTTP/SSE transport discovery with explicit tool namespacing.
- **Session 20 — Production Multi-Provider Abstraction & Evaluation**:
  - Provider adapters (Anthropic, Azure OpenAI, Ollama, OpenRouter) with automated retry/fallback chains and end-to-end evaluation suites.
