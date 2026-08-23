from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any

_RULES_PATH = Path(".cda/.permission_rules/rules.json")
_VALID_DECISIONS = frozenset({"allow", "deny"})

_PRIMARY_FIELDS: dict[str, tuple[str, ...]] = {
    "bash": ("command",),
    "powershell": ("command",),
    "write_file": ("file_path",),
    "edit_file": ("file_path",),
    "config": ("action", "key"),
    "web_fetch": ("url",),
    "repl": ("code",),
}


def _rules_path() -> Path:
    return Path.cwd() / _RULES_PATH


def primary_pattern(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    fields = _PRIMARY_FIELDS.get(name)
    if fields is not None:
        return {key: arguments.get(key) for key in fields}
    return dict(arguments)


def _is_valid_rule(entry: Any) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("tool"), str)
        and isinstance(entry.get("pattern"), dict)
        and entry.get("decision") in _VALID_DECISIONS
    )


@functools.lru_cache(maxsize=256)
def _compile_wildcard(pattern: str) -> re.Pattern[str]:
    regex = re.escape(pattern).replace(r"\*", ".*")
    return re.compile(regex)


def _field_matches(expected: Any, actual: Any) -> bool:
    if expected == actual:
        return True
    if not isinstance(expected, str) or not isinstance(actual, str) or "*" not in expected:
        return False
    return _compile_wildcard(expected).fullmatch(actual) is not None


def _pattern_matches(rule_pattern: dict[str, Any], call_pattern: dict[str, Any]) -> bool:
    if rule_pattern == call_pattern:
        return True
    if rule_pattern.keys() != call_pattern.keys():
        return False
    return all(_field_matches(rule_pattern[key], call_pattern[key]) for key in rule_pattern)


def load_rules() -> list[dict[str, Any]]:
    path = _rules_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [entry for entry in data if _is_valid_rule(entry)]


def match_rule(name: str, arguments: dict[str, Any]) -> str | None:
    pattern = primary_pattern(name, arguments)
    decision = None
    for entry in load_rules():
        if entry["tool"] == name and _pattern_matches(entry["pattern"], pattern):
            decision = entry["decision"]
    return decision


def _wildcard_value(key: str, value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return "*"
    if key == "command":
        return f"{value.split(None, 1)[0]} *"
    if key == "file_path":
        normalized = value.replace("\\", "/")
        if "/" not in normalized:
            return "*"
        parent = normalized.rsplit("/", 1)[0]
        return f"{parent}/*" if parent else "*"
    if key == "url" and "://" in value:
        scheme, rest = value.split("://", 1)
        return f"{scheme}://{rest.split('/', 1)[0]}/*"
    return "*"


def wildcard_pattern(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {key: _wildcard_value(key, value) for key, value in primary_pattern(name, arguments).items()}


def wildcard_label(name: str, arguments: dict[str, Any]) -> str:
    wild = wildcard_pattern(name, arguments)
    if name in {"bash", "powershell"}:
        cmd = str(wild.get("command") or "*")
        return cmd if cmd != "*" else f"{name} *"
    if name in {"write_file", "edit_file"}:
        path = str(wild.get("file_path") or "*")
        return f"{name} {path}"
    if name == "web_fetch":
        url = str(wild.get("url") or "*")
        return f"{name} {url}" if url != "*" else f"{name} *"
    return f"{name} *"


def upsert_rule(
    name: str,
    arguments: dict[str, Any],
    decision: str,
    pattern: dict[str, Any] | None = None,
) -> None:
    target = pattern if pattern is not None else primary_pattern(name, arguments)
    rules = load_rules()
    for index in range(len(rules) - 1, -1, -1):
        if rules[index]["tool"] == name and rules[index]["pattern"] == target:
            rules[index] = {"tool": name, "pattern": target, "decision": decision}
            break
    else:
        rules.append({"tool": name, "pattern": target, "decision": decision})
    path = _rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
