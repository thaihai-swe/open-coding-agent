from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(".cda/config.json")

DEFAULT_COMPACT_CONFIG: dict[str, Any] = {
    "auto_compact": True,
    "max_messages": 50,
    "max_chars": 80000,
    "keep_head": 3,
    "keep_recent": 4,
    "keep_recent_tool_results": 3,
    "tool_result_max_bytes": 200000,
    "persist_preview_chars": 2000,
    "reactive_retries": 1,
    "compact_fail_retries": 3,
}

DEFAULT_CONFIG: dict[str, Any] = {
    "show_tool_results": True,
    "compact": dict(DEFAULT_COMPACT_CONFIG),
}


def ensure_default_config(cwd: Path | str | None = None) -> Path:
    root = Path.cwd() if cwd is None else Path(cwd)
    target = root / CONFIG_PATH
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "show_tool_results": DEFAULT_CONFIG["show_tool_results"],
        "compact": dict(DEFAULT_COMPACT_CONFIG),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def load_config(cwd: Path | str | None = None) -> dict[str, Any]:
    root = Path.cwd() if cwd is None else Path(cwd)
    target = root / CONFIG_PATH
    try:
        if not target.is_file():
            return {}
        data = json.loads(target.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_compact_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved = dict(DEFAULT_COMPACT_CONFIG)
    if config:
        compact_user = config.get("compact")
        if isinstance(compact_user, dict):
            for key, val in compact_user.items():
                if key in resolved and val is not None:
                    resolved[key] = val
    return resolved


def resolve_show_tool_results(cli_value: bool | None, cwd: Path | str | None = None) -> bool:
    if cli_value is not None:
        return cli_value
    cfg = load_config(cwd)
    val = cfg.get("show_tool_results")
    return bool(val) if isinstance(val, bool) else True
