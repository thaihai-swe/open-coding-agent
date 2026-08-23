from __future__ import annotations

import contextvars
import json
import uuid
from pathlib import Path
from typing import Any

from .types import TODO_STATUSES

PLANNING_TOOL_NAMES = frozenset({
    "create_task",
    "list_tasks",
    "get_task",
    "claim_task",
    "complete_task",
    "cancel_task",
})
PLANNING_MUTATION_NAMES = frozenset({
    "create_task",
    "claim_task",
    "complete_task",
    "cancel_task",
})
PLANNING_BOARD_NAMES = PLANNING_MUTATION_NAMES | frozenset({"list_tasks"})
SYSTEM_MESSAGE = (
    "You should plan before executing. Tools: create_task, list_tasks, get_task, "
    "claim_task, complete_task, cancel_task."
)
_MARKERS = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}
_SESSION: contextvars.ContextVar[str] = contextvars.ContextVar("todo_session_id", default="default")


def bind_session(session_id: str) -> contextvars.Token[str]:
    return _SESSION.set(session_id)


def reset_session(token: contextvars.Token[str]) -> None:
    _SESSION.reset(token)


def current_session_id() -> str:
    return _SESSION.get()


def _todos_path() -> Path:
    return Path.cwd() / ".cda" / ".todos" / f"{current_session_id()}.json"


def _public(item: dict[str, Any]) -> dict[str, Any]:
    return {"id": item["id"], "content": item["content"], "status": item["status"]}


def _valid_item(entry: Any) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("id"), str)
        and bool(entry.get("id"))
        and isinstance(entry.get("content"), str)
        and bool(entry.get("content"))
        and entry.get("status") in TODO_STATUSES
    )


def load_tasks() -> list[dict[str, Any]]:
    path = _todos_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [_public(entry) for entry in data if _valid_item(entry)]


def save_tasks(items: list[dict[str, Any]]) -> None:
    # ponytail: no file lock — QueryEngine runs planning tools on the main thread
    path = _todos_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([_public(item) for item in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def create_task(content: str, id: str | None = None) -> dict[str, Any]:
    text = content.strip() if isinstance(content, str) else ""
    if not text:
        raise ValueError("content must be a non-empty string")
    items = load_tasks()
    task_id = id.strip() if isinstance(id, str) else ""
    if id is None:
        task_id = uuid.uuid4().hex
    elif not task_id:
        raise ValueError("id must be a non-empty string")
    elif any(item["id"] == task_id for item in items):
        raise ValueError(f"Duplicate task id: {task_id}")
    item = {"id": task_id, "content": text, "status": "pending"}
    items.append(item)
    save_tasks(items)
    return {**_public(item), "tasks": items}


def list_tasks() -> list[dict[str, Any]]:
    return load_tasks()


def _lookup(items: list[dict[str, Any]], id: str) -> tuple[int, dict[str, Any]]:
    for index, item in enumerate(items):
        if item["id"] == id:
            return index, item
    raise ValueError(f"Unknown task: {id}")


def get_task(id: str) -> dict[str, Any]:
    return _lookup(load_tasks(), id)[1]


def claim_task(id: str) -> dict[str, Any]:
    items = load_tasks()
    index, item = _lookup(items, id)
    if item["status"] != "pending":
        raise ValueError(f"Cannot claim task in status {item['status']}")
    item = {**item, "status": "in_progress"}
    items[index] = item
    save_tasks(items)
    return {**_public(item), "tasks": items}


def complete_task(id: str) -> dict[str, Any]:
    items = load_tasks()
    index, item = _lookup(items, id)
    if item["status"] not in {"pending", "in_progress"}:
        raise ValueError(f"Cannot complete task in status {item['status']}")
    item = {**item, "status": "completed"}
    items[index] = item
    save_tasks(items)
    return {**_public(item), "tasks": items}


def cancel_task(id: str) -> dict[str, Any]:
    items = load_tasks()
    index, _item = _lookup(items, id)
    del items[index]
    save_tasks(items)
    return {"id": id, "tasks": items}


def format_board(items: list[dict[str, Any]]) -> str:
    lines = ["## Current Tasks"]
    for item in items:
        marker = _MARKERS.get(str(item.get("status")), "[ ]")
        lines.append(f"  {marker} {item.get('id', '')} {item.get('content', '')}")
    return "\n".join(lines)
