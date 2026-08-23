from __future__ import annotations

import json
import re
from pathlib import Path

from ..domain.models import ChatMessage, ToolResult

TOOL_RESULT_PLACEHOLDER = "[Earlier tool result compacted. Re-run if needed.]"
SNIP_PLACEHOLDER = "[snipped {n} messages from conversation middle]"
PERSISTED_MARKER = "<persisted-output"
PERSIST_DIR = Path(".cda/task_outputs/tool-results")


def estimate_history_chars(messages: list[ChatMessage]) -> int:
    total = 0
    for message in messages:
        if message.content:
            total += len(message.content)
        if message.tool_result is not None:
            total += len(_serialize_tool_content(message.tool_result.content))
    return total


def sanitize_filename(name: str) -> str:
    cleaned = name.replace("\\", "/").split("/")[-1]
    cleaned = cleaned.replace("..", "")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", cleaned)
    return cleaned or "output"


def find_safe_boundary(messages: list[ChatMessage], index: int) -> int:
    if index <= 0:
        return 0
    if index >= len(messages):
        return len(messages)
    if _is_tool_result(messages[index]) and _has_tool_calls(messages[index - 1]):
        return index - 1
    return index


def tool_result_budget(
    messages: list[ChatMessage],
    max_bytes: int = 200000,
    preview_chars: int = 2000,
    persist_dir: Path | str | None = None,
) -> list[ChatMessage]:
    if not messages:
        return list(messages)
    last_index = _last_tool_batch_start(messages)
    if last_index is None:
        return list(messages)

    batch = list(range(last_index, len(messages)))
    tool_indexes = [i for i in batch if _is_tool_result(messages[i])]
    if not tool_indexes:
        return list(messages)

    sizes = {i: len(_serialize_tool_content(messages[i].tool_result.content).encode("utf-8")) for i in tool_indexes}
    total = sum(sizes.values())
    if total <= max_bytes:
        return list(messages)

    out = list(messages)
    target = Path.cwd() / PERSIST_DIR if persist_dir is None else Path(persist_dir)
    target.mkdir(parents=True, exist_ok=True)
    ranked = sorted(tool_indexes, key=lambda i: sizes[i], reverse=True)
    for index in ranked:
        if total <= max_bytes:
            break
        result = out[index].tool_result
        assert result is not None
        raw = _serialize_tool_content(result.content)
        filename = sanitize_filename(result.call_id) + ".txt"
        path = target / filename
        path.write_text(raw, encoding="utf-8")
        preview = raw[:preview_chars]
        marker = f'{PERSISTED_MARKER} path="{path}">\n{preview}\n</persisted-output>'
        out[index] = ChatMessage(out[index].role, out[index].content, out[index].tool_calls, ToolResult(result.call_id, marker, result.is_error))
        total -= sizes[index]
        total += len(marker.encode("utf-8"))
    return out


def snip_compact(messages: list[ChatMessage], max_messages: int = 50, keep_head: int = 3) -> list[ChatMessage]:
    if len(messages) <= max_messages:
        return list(messages)
    keep_head = max(keep_head, 0)
    tail_budget = max(max_messages - keep_head - 1, 0)
    head_end = min(keep_head, len(messages))
    if head_end > 0 and _has_tool_calls(messages[head_end - 1]):
        while head_end < len(messages) and _is_tool_result(messages[head_end]):
            head_end += 1
    tail_start = max(head_end, len(messages) - tail_budget)
    tail_start = find_safe_boundary(messages, tail_start)
    if tail_start <= head_end:
        return list(messages)
    snipped = tail_start - head_end
    placeholder = ChatMessage("user", SNIP_PLACEHOLDER.format(n=snipped))
    return [*messages[:head_end], placeholder, *messages[tail_start:]]


def micro_compact(messages: list[ChatMessage], keep_recent_results: int = 3) -> list[ChatMessage]:
    tool_indexes = [i for i, message in enumerate(messages) if _is_tool_result(message)]
    if len(tool_indexes) <= keep_recent_results:
        return list(messages)
    keep = set(tool_indexes[-keep_recent_results:])
    out = list(messages)
    for index in tool_indexes:
        if index in keep:
            continue
        result = out[index].tool_result
        assert result is not None
        body = _serialize_tool_content(result.content)
        if len(body) <= 120:
            continue
        out[index] = ChatMessage(out[index].role, out[index].content, out[index].tool_calls, ToolResult(result.call_id, TOOL_RESULT_PLACEHOLDER, result.is_error))
    return out


def _last_tool_batch_start(messages: list[ChatMessage]) -> int | None:
    last_tool = None
    for index in range(len(messages) - 1, -1, -1):
        if _is_tool_result(messages[index]):
            last_tool = index
            break
    if last_tool is None:
        return None
    start = last_tool
    while start > 0 and _is_tool_result(messages[start - 1]):
        start -= 1
    return start


def _has_tool_calls(message: ChatMessage) -> bool:
    return bool(message.tool_calls)


def _is_tool_result(message: ChatMessage) -> bool:
    return message.tool_result is not None


def _serialize_tool_content(content: object) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False)
    except TypeError:
        return str(content)
