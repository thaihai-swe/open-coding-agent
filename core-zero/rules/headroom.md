# Headroom

Context compression layer for AI agents. Automatically compresses prompts, logs, files, and tool outputs using smart content-aware compressors.

## Rules
- If the Headroom MCP server is active (provides `headroom_compress`, `headroom_retrieve`, `headroom_stats` tools):
  - MUST use `headroom_compress` on any large text payloads (e.g., raw logs, test outputs, large code listings > 2,000 tokens) before presenting them or processing them, to save context space.
  - If you encounter a compressed retrieval reference hash, use `headroom_retrieve` to fetch the original content on demand if you need the full uncompressed text.
- If headroom is not available, proceed with normal behavior.

## Key Tools
- `headroom_compress(content: str)` -> Returns compressed text and a retrieval hash.
- `headroom_retrieve(hash: str)` -> Returns original text.
- `headroom_stats()` -> Shows lifetime token savings.
