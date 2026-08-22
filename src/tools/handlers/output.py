from typing import Any
from ..registry import Tool, registry


def structured_output(data: Any) -> Any:
    if not isinstance(data, (dict, list)):
        raise TypeError("data must be dict or list")
    return data


TOOLS = [Tool("structured_output", "Output", "LOW", "Returns JSON output", {"required": ["data"], "properties": {}}, structured_output)]

for tool in TOOLS:
    registry.register(tool)
