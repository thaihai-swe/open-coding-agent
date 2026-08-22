from typing import Any
from ..registry import Tool, registry


def repl(code: str, language: str = "python", bypass_permissions: bool = False) -> Any:
    if language != "python":
        raise ValueError("Only python supported")
    exec(code, registry.repl_globals)
    return registry.repl_globals.get("result", "executed")


TOOLS = [Tool("repl", "Execution", "HIGH", "Executes stateful Python code", {"required": ["code"], "properties": {"code": {"type": "string"}}}, repl)]

for tool in TOOLS:
    registry.register(tool)
