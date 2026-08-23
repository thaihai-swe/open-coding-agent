from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from .registry import Tool
from .types import ConfigAction, DENY_LIST, PROTECTED_KEYS, PROTECTED_PATHS, Risk

_SCHEMA_TYPES = {"string": str, "integer": int, "boolean": bool}


class AuthorizeOption(StrEnum):
    ALLOW_ONCE = "1"
    ALLOW_ALWAYS = "2"
    ALLOW_PATTERN = "3"
    DENY_ONCE = "4"
    DENY_ALWAYS = "5"
    DENY_PATTERN = "6"

    @property
    def allow(self) -> bool:
        return self in _ALLOW_OPTIONS

    @property
    def persist(self) -> bool:
        return self in _PERSIST_OPTIONS

    @property
    def persist_pattern(self) -> bool:
        return self in _PERSIST_PATTERN_OPTIONS


_ALLOW_OPTIONS = frozenset({
    AuthorizeOption.ALLOW_ONCE,
    AuthorizeOption.ALLOW_ALWAYS,
    AuthorizeOption.ALLOW_PATTERN,
})
_PERSIST_OPTIONS = frozenset({
    AuthorizeOption.ALLOW_ALWAYS,
    AuthorizeOption.ALLOW_PATTERN,
    AuthorizeOption.DENY_ALWAYS,
    AuthorizeOption.DENY_PATTERN,
})
_PERSIST_PATTERN_OPTIONS = frozenset({
    AuthorizeOption.ALLOW_PATTERN,
    AuthorizeOption.DENY_PATTERN,
})


@dataclass(frozen=True)
class AuthorizeDecision:
    allow: bool
    persist: bool = False
    persist_pattern: bool = False

    @classmethod
    def from_response(cls, response: str) -> AuthorizeDecision:
        try:
            option = AuthorizeOption(response)
        except ValueError:
            return cls(allow=False)
        return cls(
            allow=option.allow,
            persist=option.persist,
            persist_pattern=option.persist_pattern,
        )


def _matches_any_pattern(value: Any, patterns: tuple[str, ...]) -> bool:
    text = str(value or "")
    return any(pat in text for pat in patterns)


def hard_deny_reason(tool: Tool, kwargs: dict[str, Any]) -> str | None:
    if tool.name in ("bash", "powershell"):
        command = str(kwargs.get("command") or "")
        for pattern in DENY_LIST:
            if pattern in command:
                return f"Blocked: {pattern}"

    if tool.name == "config":
        if kwargs.get("action") == ConfigAction.GET:
            return None
        key = kwargs.get("key")
        if key in PROTECTED_KEYS:
            return f"Protected key blocked: {key}"
        if key and _matches_any_pattern(key, PROTECTED_PATHS):
            return f"Protected path blocked: {key}"
        return None

    if tool.risk_level != Risk.LOW:
        path = kwargs.get("file_path") or kwargs.get("key")
        if path and _matches_any_pattern(path, PROTECTED_PATHS):
            return f"Protected path blocked: {path}"
    return None


def check_permission(tool: Tool, kwargs: dict[str, Any]) -> None:
    reason = hard_deny_reason(tool, kwargs)
    if reason:
        raise PermissionError(reason)
    if tool.risk_level == Risk.HIGH and not kwargs.get("bypass_permissions"):
        raise PermissionError(f"Permission denied for high-risk tool '{tool.name}'")


def validate_args(schema: dict[str, Any], kwargs: dict[str, Any]) -> None:
    for required in schema.get("required", []):
        if required not in kwargs:
            raise ValueError(f"Missing required argument: {required}")
    properties = schema.get("properties", {})
    for key, value in kwargs.items():
        expected = properties.get(key, {}).get("type")
        py_type = _SCHEMA_TYPES.get(expected)
        if py_type is not None and not isinstance(value, py_type):
            raise TypeError(f"Argument '{key}' must be {py_type.__name__}")
