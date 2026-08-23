# Implementation Plan

## Metadata
- Feature/profile: `2-permission-gate` / Complex
- Spec approved date: 2026-08-23
- Status: Draft
- Heuristics applied: `LH-001` (machine-verifiable proof commands on every seam), `LH-002` (failing tests before gate/path behavior changes)

## Lightweight Design

Brownfield change_request on the existing CLI. Feature 1 already sequential-authorizes MEDIUM/HIGH then overlaps `invoke`. This plan inserts hard deny and project-rule match ahead of that ask, switches the ask to numbered `1`–`4` with write-through to `.cda/.permission_rules/rules.json`, and moves default session/secret paths under `.cda/`.

- Approach and affected modules: deepen `src/tools/permissions.py`; add `src/tools/permission_rules.py`; retarget `QueryEngine._run_batch`, `TerminalUI.authorize`, `SessionStore` default, provider config default, `.gitignore`. No new orchestrator type, no permission-mode enum, no session-JSON permission fields, no new dependency.
- First useful slice and proof: hard deny on `invoke` + `QueryEngine.turn` (`AC-001`–`AC-009`, `AC-013`, `AC-015`–`AC-017`). Then numbered authorize + project rules (`AC-010`–`AC-012`, `AC-018`–`AC-026`, `AC-029`). Then `.cda/` defaults (`AC-027`, `AC-028`, `AC-030`).
- Key constraints or risks: hard deny is not bypassable, including by a rules-file allow. Project rules are turn-path only. Bare `invoke` stays hard deny + HIGH `bypass_permissions`. No dual-read of cwd `.sessions/` / `.secrets/` / `.permission_rules/`. Gates deferred — proof is the unittest scripts named in the spec.

## Technical Context

- Language/Version: Python 3.11+ (`StrEnum` already required). Observed 3.13.13.
- Primary Dependencies: stdlib only (`json`, `pathlib`, `concurrent.futures`, `unittest`). No new packages.
- Storage/Data: process-cwd `.cda/` is the only default local-data root. Defaults: `.cda/.permission_rules/rules.json` (JSON array of `{tool, pattern, decision}`), `.cda/.sessions/<id>.json` (`{"messages": [...]}` only), `.cda/.secrets/config.json`. `CONFIG_FILE` still overrides config.
- Target Platform: local CLI (`python3 -m src.cli`).
- Performance Goals: none beyond Feature 1 (sequential gate walk, then overlapping execute of allowed calls). Rules file is re-read per gated call (source of truth; no cache).
- Key Constraints: stdlib-first; extra tools stay; workspace bound stays; `bash` not jailed; `max_turns` default 8; missing config exit 2; cancel exit 130; live-path only (no unused permission lists, helpers, or session-JSON keys).

## Constraints
- Non-goals: `/permissions` modes, AST analysis, YOLO/auto-approve of unmatched patterns, Claude Code passthrough/eight rule sources, bash cwd jail, Session 04 hooks, new JSON event types, shell deny list on `repl`, permission fields on session JSON, project rules on bare `invoke`, auto-migration or dual-use of cwd `.sessions/` / `.secrets/` / `.permission_rules/`.
- Security/trust boundaries: deny-list + protected path/key hard deny run before ask, before handler, and before HIGH `bypass_permissions`. A project allow cannot override hard deny. Authorize stays on stdin, sequential, on the main thread. Substring deny list is an accepted teaching-demo weakness (AST is out of scope).
- Preserved behavior: extra tools registered; Feature 1 workspace bound, `glob` alias, concurrent batch, listed-order results, sibling isolation; user deny message `"Tool execution denied by user."` and `tool_denied`; env provider config; session redaction of `api_key`/`authorization`; JSON types `text`, `tool`, `tool_denied`, `error`, `status`, `tool_result`; empty first prompt line exits REPL; Ctrl+C exit 130.
- Explicit out of scope: `PermissionRouter` / mode enum types, in-memory rule cache, dual-path readers for old cwd dirs, `ToolBatchExecutor`, pytest.

## Approach

Stay inside the current layers. Presentation does not import handlers. Handlers do not import QueryEngine. Domain models stay frozen dataclasses. SessionStore stays transcript-only.

### Interfaces / data flow

```
TerminalUI.prompt  →  QueryEngine.turn(prompt)
                         → Provider.complete(history, schemas)
                         → _run_batch(tool_calls)  [main thread, listed order]
                              for each call:
                                unknown / bad args → error ToolResult
                                hard_deny_reason?  → error ToolResult (Blocked:/Protected…);
                                                     no authorize; no tool_denied
                                else if MEDIUM/HIGH:
                                  match_rule(cwd rules.json)?
                                    deny  → tool_denied + user-deny ToolResult
                                    allow → approved (HIGH still gets bypass on invoke)
                                    none  → TerminalUI.authorize (1–4)
                                            2/4 → upsert_rule immediately
                                            allow this call (1/2) → approved
                                            else → tool_denied + user-deny ToolResult
                                else LOW → approved
                              then Feature 1: status, tool events, ThreadPoolExecutor invoke,
                              listed-order tool_result + history + one SessionStore.save
                         → next complete only after the batch save
```

`invoke(name, **kwargs)` remains the tool public seam: `validate_args` → `check_permission` → handler.

`check_permission` consults `hard_deny_reason` **before** the HIGH `bypass_permissions` short-circuit. Bare `invoke` does **not** read project rules (REQ-012).

### Public seams (test surface)

| Seam | Observes | ACs |
| --- | --- | --- |
| `src.tools.invoke` / `check_permission` | deny list (incl. bypass and all seven patterns), HIGH-without-bypass, `repl` not on deny list, protected path/key, non-deny `echo ping` | AC-001–AC-007, AC-017 |
| `QueryEngine.turn` | no authorize on hard deny / LOW / project-rule hit; `tool_denied` only for user/project deny; sibling isolation; `2`/`4` write-through; last-wins / invalid-entry skip; session JSON has no permission fields | AC-008–AC-011, AC-013–AC-016, AC-018–AC-023, AC-025, AC-029 |
| `TerminalUI.authorize` | numbered `1`–`4` prompt text; trim; `1`/`2` allow this call; `3`/`4`/empty/`a`/`approve`/other deny this call | AC-012 |
| `SessionStore()` default + `save`/`load` | `.cda/.sessions/<id>.json`; messages-only; resume still prompts when no rules file | AC-024, AC-026, AC-027 |
| `OpenAIProvider()` missing config | error text names `.cda/.secrets/config.json` | AC-028 |
| repository `.gitignore` | contains `.cda/` | AC-030 |

Do not add mock seams. FakeProvider already drives `QueryEngine`. Rules-file tests `os.chdir` into a temp project so the public cwd path is what production uses (no injectable `rules_path` constructor).

### Key decisions

1. **Hard deny as one function, two live callers (chosen)**  
   Public function: `hard_deny_reason(tool, kwargs) -> str | None` in `src/tools/permissions.py`.  
   Order inside the function:
   1. `bash` / `powershell` `command`: case-sensitive substring against `DENY_LIST` (`rm -rf /`, `sudo`, `shutdown`, `reboot`, `mkfs`, `dd if=`, `> /dev/sda`). First match wins. Error includes `Blocked:` and the matched pattern.
   2. `config` GET: return `None` (REQ-011 — not hard-denied).
   3. `config` SET: `key in PROTECTED_KEYS` → hard deny; else `key` substring-match on `PROTECTED_PATHS` → `Protected path blocked:`.
   4. Other non-LOW tools: `file_path` or `key` substring-match on `PROTECTED_PATHS` → `Protected path blocked:` (today’s MEDIUM check, now before ask and not bypassable).
   `repl` `code` is never matched against `DENY_LIST`. LOW is never path-blocked.

   `check_permission`:
   1. `reason = hard_deny_reason(...)`; if set, `raise PermissionError(reason)` — **including when `bypass_permissions` is true**.
   2. Else HIGH without `bypass_permissions` → today’s `Permission denied for high-risk tool`.
   3. Remove the MEDIUM-only path branch (it now lives in `hard_deny_reason`).

   `QueryEngine._run_batch` calls `hard_deny_reason` **before** project-rule match and before `authorize`. Hard-denied calls become an error `ToolResult` with that reason, no `tool_denied` event, not submitted to the pool.

   Remove the `PROTECTED_KEYS` raise from `src/tools/handlers/settings.py`. After the move it is unreachable via `invoke` (dead). `PROTECTED_KEYS` stays live only inside `hard_deny_reason`.

   Deletion test: inlining the seven patterns + two protected lists in both `check_permission` and QueryEngine duplicates the live table and lets them drift. One function, two callers. Do not add a `PermissionRouter` class (one algorithm, one caller of the walk — QueryEngine).

2. **Authorize returns `AuthorizeDecision`, not `bool` (chosen)**  
   Frozen dataclass in `src/tools/permissions.py`:

   ```python
   @dataclass(frozen=True)
   class AuthorizeDecision:
       allow: bool
       persist: bool
   ```

   `Authorize = Callable[[str, dict[str, Any]], AuthorizeDecision]`.

   `TerminalUI.authorize` prompt (human and JSON stdin, REQ-004):

   `Approve {name} {json.dumps(arguments, sort_keys=True)}? [1] Yes [2] Yes, don't ask again [3] No [4] No, don't ask again:`

   After `.strip()` (no case-fold required for digits):

   | Input | `allow` | `persist` |
   | --- | --- | --- |
   | `1` | True | False |
   | `2` | True | True |
   | `4` | False | True |
   | `3`, empty, `a`, `approve`, anything else | False | False |

   QueryEngine: if `persist`, `upsert_rule` immediately (so a later listed sibling with the same tool + primary argument sees the file — AC-022). Then `allow` → approved; else `tool_denied` + `"Tool execution denied by user."`.

   Existing `query_engine_check.py` lambdas that return `True`/`False` must return `AuthorizeDecision` in the same milestone. Helper in that test file: `_once(allow: bool) -> AuthorizeDecision`.

   AC-012 still observes allow/deny on `TerminalUI.authorize` via `.allow`. Persist is observed through the rules file (AC-018, AC-020), not a second UI seam.

3. **Project rules module (chosen: functions in `src/tools/permission_rules.py`)**  
   Default path: `Path(".cda/.permission_rules/rules.json")` (process cwd). No constructor, no cache, no path injection.

   | Function | Behavior |
   | --- | --- |
   | `primary_pattern(name, arguments) -> dict` | Exact field set from REQ-016 (`command` / `file_path` / `action`+`key` / `url` / `code` / else full map). Extra kwargs (`content`, `timeout`) are not part of the pattern. |
   | `load_rules() -> list[dict]` | Missing file → `[]`. Unreadable or non-array JSON → `[]`. Skip entries missing `tool`, whose `pattern` is not a `dict`, or whose `decision` is not `allow`/`deny`. |
   | `match_rule(name, arguments) -> str \| None` | Last valid entry whose `tool` equals `name` and whose `pattern` equals `primary_pattern(...)` (exact per-field string equality). |
   | `upsert_rule(name, arguments, decision)` | `mkdir` parents; replace the last matching valid entry or append; write a JSON array. `1`/`3` never call this. |

   QueryEngine consults `match_rule` only for MEDIUM/HIGH that are not hard-denied. LOW and hard-denied ignore JSON (REQ-019). Bare `invoke` never imports this module.

   Deletion test: skip-invalid + last-wins + replace-same-pattern is enough complexity to keep out of `_run_batch`. A `PermissionRulesStore` class would only hold the cwd path — collapse to module functions (SessionStore is a class because tests pass a directory; rules tests chdir instead).

4. **`.cda/` defaults (chosen: change the three default strings; no compatibility shim)**  
   - `SessionStore.__init__` default directory: `.cda/.sessions` (still `mkdir(parents=True)`).
   - `OpenAIProvider` / `_load_config` default: `.cda/.secrets/config.json`. Missing-config `ProviderError` text names that path (replace `.secrets/config.json`).
   - `CONFIG_FILE` override unchanged.
   - `.gitignore`: add `.cda/`. Leave the existing `.sessions/` line (covers leftover Feature 1 dirs; AC-030 only requires `.cda/` present).
   - `documents/how-to-run.md`: document `.cda/.secrets/config.json` (the runbook still points at a dead path otherwise).
   - Do not read or write cwd `.sessions/`, `.secrets/`, or `.permission_rules/`. Do not migrate.

   Tests that need the default layout `os.chdir` into a temp directory (same pattern as `tests/tools_check.py`). Tests that pass `SessionStore(temp_dir)` keep an explicit directory and do not create `.cda/` unless they chdir.

5. **HIGH `bypass_permissions` on the turn path**  
   Unchanged injection in `_invoke_call` after this call is allowed (answer `1`/`2` or matching project allow). Hard-denied calls never reach `_invoke_call`. `bypass_permissions` does not skip `hard_deny_reason`.

6. **No new JSON event type**  
   Hard deny → existing `tool_result` with `is_error` and the `Blocked:` / `Protected path blocked:` text. User deny and project deny → existing `tool_denied`.

### Module map

| Path | Public seam | Responsibility | Depends on | Split / co-locate |
| --- | --- | --- | --- | --- |
| `src/tools/types.py` | `DENY_LIST`, existing `PROTECTED_*` | Permission constants only | none | Co-locate with `PROTECTED_PATHS` / `PROTECTED_KEYS` |
| `src/tools/permissions.py` | `hard_deny_reason`, `check_permission`, `AuthorizeDecision` | In-process hard deny + HIGH bypass + ask result type | `types`, `registry.Tool` | Deepen existing gate; do not add file IO |
| `src/tools/permission_rules.py` **new** | `primary_pattern`, `load_rules`, `match_rule`, `upsert_rule` | Cwd JSON array as source of truth | stdlib `json`/`pathlib` | Split from `permissions.py`: different change reason (disk vs in-process) |
| `src/tools/handlers/settings.py` | `config` handler | GET/SET without a second protected-key raise | `registry`, `ConfigAction` | Remove dead `PROTECTED_KEYS` branch |
| `src/tools/__init__.py` | `invoke` | Unchanged order: validate → `check_permission` → handler | `permissions` | Do not consult project rules |
| `src/application/query_engine.py` | `QueryEngine.turn` / `_run_batch` | Hard deny → match_rule → authorize; persist `2`/`4`; Feature 1 pool | `hard_deny_reason`, `permission_rules`, `invoke` | Keep the walk as methods, not a router type |
| `src/presentation/terminal_ui.py` | `authorize` | Numbered `1`–`4` prompt; return `AuthorizeDecision` | `AuthorizeDecision` | Presentation may import this type only, not handlers |
| `src/infrastructure/session_store.py` | `SessionStore()` default | Transcripts under `.cda/.sessions` | stdlib | No permission fields |
| `src/infrastructure/providers/openai.py` | `_load_config` default + error text | `.cda/.secrets/config.json` | stdlib | `CONFIG_FILE` still wins |
| `src/presentation/cli.py` | `run` | Unchanged composition (`SessionStore()`, `ui.authorize`) | engine, UI | Touch only if a proof fails |
| `.gitignore` | `.cda/` entry | Ignore local CLI data | n/a | Add; do not invent extra ignore rules |
| `documents/how-to-run.md` | default config path | Point operators at `.cda/.secrets/config.json` | n/a | Path move is user-visible |
| `tests/tools_check.py` | `invoke` | AC-001–AC-007, AC-017; patch `subprocess.run` so deny-listed bash never starts | `invoke` | Extend Feature 1 file |
| `tests/query_engine_check.py` | `QueryEngine.turn` | AC-008–AC-011, AC-013–AC-016, AC-018–AC-023, AC-025, AC-029; chdir for `.cda/` proofs; update bool lambdas | FakeProvider, `AuthorizeDecision` | Extend; do not rewrite FakeProvider |
| `tests/terminal_ui_check.py` | `TerminalUI.authorize` | AC-012 | scripted `input_fn` | Replace `a`/`d` assertions |
| `tests/session_check.py` | `SessionStore` | AC-024, AC-026, AC-027 | chdir + default ctor | Extend |
| `tests/provider_check.py` | missing default config | AC-028 | no `CONFIG_FILE` | Extend |
| `tests/cli_check.py` | `.gitignore` | AC-030 | read repo `.gitignore` | Extend |

Dependency direction (unchanged, inward):

```
presentation → application → tools / domain / infrastructure
permissions.py → types (no file IO)
permission_rules.py → stdlib only
QueryEngine → permissions.hard_deny_reason + permission_rules + invoke
handlers.shell / settings → registry (not the deny list)
permission_rules ↛ invoke   (bare invoke must not import it)
```

### Non-functional considerations

- NFR-001 hard deny not bypassable: `hard_deny_reason` before bypass short-circuit and before `match_rule`. Proof AC-001, AC-002, AC-008, AC-017, AC-023.
- NFR-002 no dead permission code: `DENY_LIST` / `PROTECTED_*` only consumed by `hard_deny_reason`; rules functions only consumed by `_run_batch`; session JSON encoder stays messages-only. Proof AC-001, AC-008, AC-015, AC-017, AC-018, AC-019, AC-026. Disconnecting any of those consults fails the named AC.
- NFR-003 JSON event types unchanged. Proof AC-008, AC-011, AC-014, AC-020.
- NFR-004 sequential gates then overlap; stdin not concurrent. Proof AC-013, AC-014, AC-022.
- NFR-005 workspace bound and extra tools unchanged. Proof AC-003, AC-009 plus existing `tools_check` bound cases.
- NFR-006 user-editable rules file; messages-only sessions; default secrets path. Proof AC-018–AC-021, AC-024–AC-029.
- NFR-007 `.cda/` gitignored. Proof AC-030.

## Alternatives Considered

| Option | Depth / seam / blast radius | Chosen? | Why rejected or kept |
| --- | --- | --- | --- |
| Shared `hard_deny_reason` + `check_permission` first | One table; `invoke` and `turn` cannot drift | Yes | Live-path requirement (REQ-015) |
| Duplicate deny list in QueryEngine and `check_permission` | Two copies | No | Drift; one list can become dead |
| `PermissionRouter` class | Shallow wrapper around `_run_batch` | No | One caller — deletion test fails |
| Keep handler `PROTECTED_KEYS` raise **and** gate check | Second copy after `invoke` | No | Unreachable via `invoke` = dead code |
| `AuthorizeDecision(allow, persist)` | Named 4-way result; UI + engine share it | Yes | QueryEngine must distinguish `1` vs `2` and `3` vs `4` |
| Keep `Authorize -> bool` | Cannot persist `2`/`4` | No | Spec US5 |
| `Authorize -> str` (raw `1`–`4`) | Mapping lives only in QueryEngine; AC-012 is allow/deny on UI | No | Splits the 1–4 contract across two files; UI tests would re-encode allow/deny |
| `(bool, bool)` tuple | No new type | No | Positional; same blast radius as the dataclass with worse locality |
| `src/tools/permission_rules.py` functions | JSON skip-invalid / last-wins / upsert behind four names | Yes | File is the source of truth; complexity does not belong in `_run_batch` |
| Fold rules into `SessionStore` / session JSON | One file on disk | No | Spec forbids permission fields on session JSON; rules are project-level |
| `PermissionRulesStore(path)` class | Test-injected path | No | Hypothetical seam; tests chdir like `tools_check.py` |
| Inline JSON in QueryEngine | One less file | No | Invalid-entry / last-wins / upsert would bloat `_run_batch` |
| Dual-read old cwd `.sessions/` / `.secrets/` | Compat | No | Spec: Feature 1 defaults superseded; no auto-migration |
| Shared `CdaRoot` helper | One constant module | No | Three default strings, each locked by an AC — YAGNI |
| Cache rules in QueryEngine memory | Skip disk on siblings | No | File is source of truth (user edit, AC-022 sibling after `2`) |
| `/spec-adr` for dataclass vs string | Hard-to-reverse platform choice | No | Both stdlib; reversible in one milestone. Revisit via `/spec-adr` only if a second persistence backend appears |

No `/spec-adr` this slice: deny/ask/allow shape, `.cda/` root, and project-file persistence are locked in `spec.md`. Remaining choices are Ponytail stdlib vs extra types.

## Complexity Tracking

| Violation / Shortcut | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| New `permission_rules.py` | Skip-invalid, last-wins, upsert, mkdir | Inlining into QueryEngine hides a second persistence contract next to the turn loop |
| `AuthorizeDecision` type instead of `bool` | `2`/`4` must persist without a second callback | Bool cannot represent four outcomes; a side-channel callback is a second seam |
| `hard_deny_reason` called from both `check_permission` and QueryEngine | Bare `invoke` and `turn` are both live | Asking first then failing is the bug this feature closes |
| `os.chdir` in rules/default-path tests instead of injected paths | Public seam is process cwd | A `rules_path=` argument would be a test-only constructor |
| Substring deny list (case-sensitive) | Spec / teaching list | AST is an explicit non-goal |
| Accepted: default config path break with no migration | Adopter grouped data under `.cda/` | Dual-read would keep a dead cwd `.secrets/` path live |
| `ponytail:` no in-memory rule cache | File is source of truth; N is tiny | Cache would ignore user edits mid-process and sibling `2` |

Technical risk of gate order + persist-before-sibling is specified in REQ-013/REQ-017, not unverified — no halt to `/spec-research`.

## Delivery

Ordered milestone roadmap (tracer slices; each leaves unittest proof). Update existing bool `authorize` lambdas in the same slice that changes the `Authorize` type so the suite never depends on a dual bool/decision adapter.

1. **P1 hard deny** — `DENY_LIST`; `hard_deny_reason`; `check_permission` before bypass; drop settings.py duplicate; QueryEngine skip authorize on hard deny (still bool authorize until slice 2, **or** land `AuthorizeDecision` with `persist=False` here if that is a smaller diff). Covers AC-001–AC-009, AC-013, AC-015–AC-017. Proof: `python3 tests/tools_check.py`, `python3 tests/query_engine_check.py`.
2. **P1 ask + project rules** — `AuthorizeDecision`; numbered `TerminalUI.authorize`; `permission_rules.py`; `_run_batch` match → ask → upsert. Covers AC-010–AC-012, AC-014, AC-018–AC-023, AC-025, AC-029. Proof: `python3 tests/terminal_ui_check.py`, `python3 tests/query_engine_check.py`.
3. **P1 `.cda/` data root** — SessionStore default, provider default + error text, `.gitignore`, `how-to-run.md`. Covers AC-024, AC-026–AC-028, AC-030. Proof: `python3 tests/session_check.py`, `python3 tests/provider_check.py`, `python3 tests/cli_check.py`.
4. **Regression pack** — `python3 -m compileall -q src` and `python3 -m unittest discover -s tests -p '*_check.py'`.

Rollback or migration: revert the listed files. No schema migration. Existing cwd `.sessions/` and `.secrets/` files are left in place and unused. Operators must point `CONFIG_FILE` at an old config or copy it to `.cda/.secrets/config.json`.

Open risks:

- Substring deny list is bypassable (`sudo` vs `SuDo`, `rm -rf /` vs `rm -rf /*`). Accepted; AST is out of scope.
- `sudo` as a substring blocks benign commands that mention the token. Accepted; list is exact and short.
- User-edited project allow can always-allow non-hard-denied HIGH commands for every session in that cwd. Hard deny still wins.
- Exact primary-argument match: `echo ping` allow does not cover `echo pong`. Accepted (Q1).
- Moving default config breaks Feature 1 how-to-run with no auto-migration. Mitigation: `CONFIG_FILE`; error text names the new path; this plan updates `documents/how-to-run.md`.
- `corebase-specharness/project/architecture.md` and `product-sense.md` still describe cwd `.sessions/` / `.secrets/`. Out of this skill; update via `/context-memory` if requested.
- `upsert_rule` / `SessionStore.save` IO errors abort the turn (no extra handler). Same as today’s session save.
- Verification gates still deferred; these commands are proof, not closeout.

Next step: execute `/spec-tasks` to build the executable task graph.
