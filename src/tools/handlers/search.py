import glob
import os
import re
from typing import Any, List
from ..registry import Tool, registry


def glob_search(pattern: str, path: str = ".") -> List[str]:
    matches = glob.glob(os.path.join(path, pattern), recursive=True)
    matches.sort(key=lambda item: os.path.getmtime(item) if os.path.exists(item) else 0, reverse=True)
    return matches[:100]


def grep_search(pattern: str, path: str = ".", glob_pattern: str = "", output_mode: str = "content", head_limit: int = 250) -> Any:
    expression, results = re.compile(pattern), []
    for root, _, files in os.walk(path):
        for filename in files:
            file_path = os.path.join(root, filename)
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


TOOLS = [
    Tool("glob_search", "Search", "LOW", "Finds files matching pattern", {"required": ["pattern"], "properties": {"pattern": {"type": "string"}}}, glob_search),
    Tool("grep_search", "Search", "LOW", "Regex search files", {"required": ["pattern"], "properties": {"pattern": {"type": "string"}}}, grep_search),
]

for tool in TOOLS:
    registry.register(tool)
