from typing import Any

from .. import task_board
from ..registry import Tool, registry


def create_task(content: str, id: str | None = None) -> dict[str, Any]:
    return task_board.create_task(content, id)


def list_tasks() -> list[dict[str, Any]]:
    return task_board.list_tasks()


def get_task(id: str) -> dict[str, Any]:
    return task_board.get_task(id)


def claim_task(id: str) -> dict[str, Any]:
    return task_board.claim_task(id)


def complete_task(id: str) -> dict[str, Any]:
    return task_board.complete_task(id)


def cancel_task(id: str) -> dict[str, Any]:
    return task_board.cancel_task(id)


TOOLS = [
    Tool(
        "create_task",
        "Planning",
        "LOW",
        "Create a pending task",
        {"required": ["content"], "properties": {"content": {"type": "string"}, "id": {"type": "string"}}},
        create_task,
    ),
    Tool("list_tasks", "Planning", "LOW", "List session tasks", {"required": [], "properties": {}}, list_tasks),
    Tool(
        "get_task",
        "Planning",
        "LOW",
        "Get one task by id",
        {"required": ["id"], "properties": {"id": {"type": "string"}}},
        get_task,
    ),
    Tool(
        "claim_task",
        "Planning",
        "LOW",
        "Claim a pending task",
        {"required": ["id"], "properties": {"id": {"type": "string"}}},
        claim_task,
    ),
    Tool(
        "complete_task",
        "Planning",
        "LOW",
        "Complete a task",
        {"required": ["id"], "properties": {"id": {"type": "string"}}},
        complete_task,
    ),
    Tool(
        "cancel_task",
        "Planning",
        "LOW",
        "Cancel and remove a task",
        {"required": ["id"], "properties": {"id": {"type": "string"}}},
        cancel_task,
    ),
]

for tool in TOOLS:
    registry.register(tool)
