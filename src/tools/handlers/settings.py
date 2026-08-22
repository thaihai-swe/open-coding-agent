from typing import Any
from ..registry import Tool, registry
from ..types import PROTECTED_KEYS, ConfigAction


def config(action: str, key: str, value: Any = None) -> Any:
    if action not in {ConfigAction.GET, ConfigAction.SET}:
        raise ValueError("action must be get or set")
    if action == ConfigAction.SET and key in PROTECTED_KEYS:
        raise PermissionError("Protected key")
    return value if action == ConfigAction.SET else "config_value"


TOOLS = [Tool("config", "Settings", "MEDIUM", "Gets or sets config", {"required": ["action", "key"], "properties": {"action": {"type": "string"}, "key": {"type": "string"}}}, config)]

for tool in TOOLS:
    registry.register(tool)
