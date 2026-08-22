from typing import Any, Dict, List
from ..registry import Tool, registry
from ..types import TODO_STATUSES


def todo_write(todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for todo in todos:
        if todo.get("status") not in TODO_STATUSES:
            raise ValueError(f"Invalid status: {todo.get('status')}")
    return todos


TOOLS = [Tool("todo_write", "Planning", "LOW", "Updates task board", {"required": ["todos"], "properties": {"todos": {"type": "list"}}}, todo_write)]

for tool in TOOLS:
    registry.register(tool)
