from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RULES_PATH = Path(".cda/.permission_rules/rules.json")
_VALID_DECISIONS = {"allow", "deny"}


def _rules_path() -> Path:
    return Path.cwd() / _RULES_PATH


def primary_pattern(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name in {"bash", "powershell"}:
        return {"command": arguments.get("command")}
    if name in {"write_file", "edit_file"}:
        return {"file_path": arguments.get("file_path")}
    if name == "config":
        return {"action": arguments.get("action"), "key": arguments.get("key")}
    if name == "web_fetch":
        return {"url": arguments.get("url")}
    if name == "repl":
        return {"code": arguments.get("code")}
    return dict(arguments)


def _is_valid_rule(entry: Any) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("tool"), str)
        and isinstance(entry.get("pattern"), dict)
        and entry.get("decision") in _VALID_DECISIONS
    )


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
        if entry["tool"] == name and entry["pattern"] == pattern:
            decision = entry["decision"]
    return decision


def upsert_rule(name: str, arguments: dict[str, Any], decision: str) -> None:
    pattern = primary_pattern(name, arguments)
    rules = load_rules()
    replaced = False
    for index in range(len(rules) - 1, -1, -1):
        if rules[index]["tool"] == name and rules[index]["pattern"] == pattern:
            rules[index] = {"tool": name, "pattern": pattern, "decision": decision}
            replaced = True
            break
    if not replaced:
        rules.append({"tool": name, "pattern": pattern, "decision": decision})
    path = _rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
