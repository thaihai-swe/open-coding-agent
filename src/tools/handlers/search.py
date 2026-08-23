import glob
import os
import re
from typing import Any

from ..registry import Tool, registry
from ..workspace import bound_path


def _inside_workspace(path: str) -> bool:
    try:
        bound_path(path)
        return True
    except ValueError:
        return False


def glob_search(pattern: str, path: str = ".") -> list[str]:
    root = bound_path(path)
    matches = [item for item in glob.glob(os.path.join(str(root), pattern), recursive=True) if _inside_workspace(item)]
    matches.sort(key=lambda item: os.path.getmtime(item) if os.path.exists(item) else 0, reverse=True)
    return matches[:100]


def grep_search(pattern: str, path: str = ".", glob_pattern: str = "", output_mode: str = "content", head_limit: int = 250) -> Any:
    root = bound_path(path)
    expression, results = re.compile(pattern), []
    for walk_root, _, files in os.walk(str(root)):
        for filename in files:
            file_path = os.path.join(walk_root, filename)
            if not _inside_workspace(file_path):
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                    for index, line in enumerate(file, 1):
                        if expression.search(line):
                            if output_mode == "files_with_matches":
                                results.append(file_path)
                                break
                            results.append(f"{file_path}:{index}:{line.strip()}")
                            if len(results) >= head_limit:
                                return results
            except OSError:
                pass
    return results[:head_limit]


_GLOB_SCHEMA = {"required": ["pattern"], "properties": {"pattern": {"type": "string"}}}
_GLOB_DESCRIPTION = "Finds files matching pattern"

TOOLS = [
    Tool("glob_search", "Search", "LOW", _GLOB_DESCRIPTION, _GLOB_SCHEMA, glob_search),
    Tool("glob", "Search", "LOW", _GLOB_DESCRIPTION, _GLOB_SCHEMA, glob_search),  # T-001 / AC-002 / AC-003
    Tool("grep_search", "Search", "LOW", "Regex search files", {"required": ["pattern"], "properties": {"pattern": {"type": "string"}}}, grep_search),
]

for tool in TOOLS:
    registry.register(tool)
