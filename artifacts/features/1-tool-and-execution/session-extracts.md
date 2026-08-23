# Session extracts: 1-tool-and-execution

## Candidates

- [CANDIDATE] Dual `registry.register` for `glob` / `glob_search` is enough; do not add an alias map. `TOOLS = list(registry.tools.values())` is snapshotted after handler imports — keep that order.
- [CANDIDATE] Path jail belongs in `workspace.bound_path` (resolve + `is_relative_to`), not `permissions.py`. `write_file` must bind before `makedirs`.
- [CANDIDATE] Concurrent batches: sequential authorize and all UI events on the main thread; `ThreadPoolExecutor` only around `invoke`. Assemble history after `wait=True` so listed order is independent of finish order.
- [CANDIDATE] Markdown stays a private `TerminalUI._render_markdown` (ATX + `**` only). JSON dumps the original event dict.

## Post-Ship Sync

## Post-Ship Sync

- MEM-01 [PROMOTE]: core-policies.md security-sensitive path list is stale for file_io.py. Post-feature: file/search handlers now call bound_path via src/tools/workspace.py before IO. Update the security-sensitive paths paragraph. Source: STD-02 finding in review.md.
- MEM-02 [PROMOTE]: tools_check.py is the first tool-handler test under tests/. Proves that testing via invoke/registry public seam is viable for tool-handler validation without mocking QueryEngine. Source: T-001 evidence; review.md MED-02.
- MEM-03 [PROMOTE]: Dual registry.register for glob/glob_search alias works cleanly; TOOLS snapshot is evaluated at import time and order of handler imports relative to TOOLS assignment matters. Keep search imported before TOOLS = list(...). Source: plan.md risk note + review.md MED-03.

## Follow-Up

- Reopened tasks: none
- Deferred work: core-policies.md doc sync (STD-02 / MEM-01, to be completed now); optional ocr provider setup not required by this feature.
- Next required action: promote these candidates via /context-memory then confirm session transition to Done.
