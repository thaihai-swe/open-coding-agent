from typing import List
from ..registry import Tool, registry


def tool_search(query: str) -> List[str]:
    return [name for name in registry.tools if query.lower() in name.lower()]


TOOLS = [Tool("tool_search", "Discovery", "LOW", "Searches tools", {"required": ["query"], "properties": {"query": {"type": "string"}}}, tool_search)]

for tool in TOOLS:
    registry.register(tool)
