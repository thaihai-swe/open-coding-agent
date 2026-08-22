from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Tool:
    name: str
    category: str
    risk_level: str
    description: str
    schema: Dict[str, Any]
    handler: Callable[..., Any]


class ToolRegistry:
    def __init__(self) -> None:
        self.tools: Dict[str, Tool] = {}
        self.repl_globals: Dict[str, Any] = {}

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_schemas(self) -> List[Dict[str, Any]]:
        return [{"name": tool.name, "category": tool.category, "risk_level": tool.risk_level, "description": tool.description, "schema": tool.schema} for tool in self.tools.values()]


registry = ToolRegistry()
