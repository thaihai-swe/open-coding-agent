from typing import Any, Dict
from .registry import Tool
from .types import PROTECTED_PATHS, Risk


def check_permission(tool: Tool, kwargs: Dict[str, Any]) -> None:
    if tool.risk_level == Risk.HIGH:
        if kwargs.get("bypass_permissions"):
            return
        raise PermissionError(f"Permission denied for high-risk tool '{tool.name}'")
    if tool.risk_level == Risk.MEDIUM:
        path = kwargs.get("file_path") or kwargs.get("key")
        if path and any(pattern in str(path) for pattern in PROTECTED_PATHS):
            raise PermissionError(f"Protected path blocked: {path}")


def validate_args(schema: Dict[str, Any], kwargs: Dict[str, Any]) -> None:
    for required in schema.get("required", []):
        if required not in kwargs:
            raise ValueError(f"Missing required argument: {required}")
    for key, value in kwargs.items():
        expected = schema.get("properties", {}).get(key, {}).get("type")
        if expected == "string" and not isinstance(value, str):
            raise TypeError(f"Argument '{key}' must be str")
        if expected == "integer" and not isinstance(value, int):
            raise TypeError(f"Argument '{key}' must be int")
        if expected == "boolean" and not isinstance(value, bool):
            raise TypeError(f"Argument '{key}' must be bool")
