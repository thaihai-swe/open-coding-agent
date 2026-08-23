from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Dict, Optional
from .registry import Tool
from .types import ConfigAction, DENY_LIST, PROTECTED_KEYS, PROTECTED_PATHS, Risk


class AuthorizeOption(StrEnum):
    ALLOW_ONCE = "1"
    ALLOW_ALWAYS = "2"
    DENY_ONCE = "3"
    DENY_ALWAYS = "4"

    @property
    def allow(self) -> bool:
        return self in {AuthorizeOption.ALLOW_ONCE, AuthorizeOption.ALLOW_ALWAYS}

    @property
    def persist(self) -> bool:
        return self in {AuthorizeOption.ALLOW_ALWAYS, AuthorizeOption.DENY_ALWAYS}


@dataclass(frozen=True)
class AuthorizeDecision:
    allow: bool
    persist: bool = False

    @classmethod
    def from_response(cls, response: str) -> AuthorizeDecision:
        try:
            option = AuthorizeOption(response)
        except ValueError:
            return cls(allow=False, persist=False)
        return cls(allow=option.allow, persist=option.persist)


def hard_deny_reason(tool: Tool, kwargs: Dict[str, Any]) -> Optional[str]:
    # T-001 / AC-001, AC-002, AC-017: deny-list on bash/powershell command only.
    if tool.name in ("bash", "powershell"):
        command = str(kwargs.get("command") or "")
        for pattern in DENY_LIST:
            if pattern in command:
                return f"Blocked: {pattern}"
    # T-002 / AC-006, AC-007: protected path/key. GET is never hard-denied.
    if tool.name == "config":
        if kwargs.get("action") == ConfigAction.GET:
            return None
        key = kwargs.get("key")
        if key in PROTECTED_KEYS:
            return f"Protected key blocked: {key}"
        if key and any(pattern in str(key) for pattern in PROTECTED_PATHS):
            return f"Protected path blocked: {key}"
        return None
    if tool.risk_level != Risk.LOW:
        path = kwargs.get("file_path") or kwargs.get("key")
        if path and any(pattern in str(path) for pattern in PROTECTED_PATHS):
            return f"Protected path blocked: {path}"
    return None


def check_permission(tool: Tool, kwargs: Dict[str, Any]) -> None:
    reason = hard_deny_reason(tool, kwargs)
    if reason:
        raise PermissionError(reason)
    if tool.risk_level == Risk.HIGH:
        if kwargs.get("bypass_permissions"):
            return
        raise PermissionError(f"Permission denied for high-risk tool '{tool.name}'")


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
