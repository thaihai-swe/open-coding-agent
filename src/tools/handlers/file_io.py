import os
from typing import Any, Dict

from ..registry import Tool, registry
from ..types import Status
from ..workspace import bound_path


def read_file(file_path: str, offset: int = 1, limit: int = 2000, pages: str = "") -> str:
    """Read and return a numbered range of lines from a file."""
    file_path = str(bound_path(file_path))
    with open(file_path, "r", encoding="utf-8", errors="replace") as file:
        lines = file.readlines()
    selected = lines[offset - 1 : offset - 1 + limit]
    return "".join(f"{index + offset}: {line}" for index, line in enumerate(selected))


def write_file(file_path: str, content: str) -> Dict[str, Any]:
    target = bound_path(file_path)
    os.makedirs(target.parent, exist_ok=True)
    with open(target, "w", encoding="utf-8") as file:
        file.write(content)
    return {"status": Status.SUCCESS, "file_path": file_path, "bytes": len(content)}


def edit_file(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> Dict[str, Any]:
    file_path = str(bound_path(file_path))
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    count = content.count(old_string)
    if count == 0:
        raise ValueError("old_string not found in file")
    if count > 1 and not replace_all:
        raise ValueError("old_string appears multiple times; set replace_all=True")
    new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(new_content)
    return {"status": Status.SUCCESS, "replacements": count if replace_all else 1}


TOOLS = [
    Tool("read_file", "File I/O", "LOW", "Reads file contents", {"required": ["file_path"], "properties": {"file_path": {"type": "string"}}}, read_file),
    Tool("write_file", "File I/O", "MEDIUM", "Writes content to file", {"required": ["file_path", "content"], "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}}, write_file),
    Tool("edit_file", "File I/O", "MEDIUM", "Edits content in file", {"required": ["file_path", "old_string", "new_string"], "properties": {"file_path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}}, edit_file),
]

for tool in TOOLS:
    registry.register(tool)
