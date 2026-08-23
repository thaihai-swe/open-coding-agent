from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(".cda/config.json")
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "default_config.json"


def load_default_config() -> dict[str, Any]:
    try:
        data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


DEFAULT_CONFIG: dict[str, Any] = load_default_config()
DEFAULT_COMPACT_CONFIG: dict[str, Any] = dict(DEFAULT_CONFIG.get("compact") or {})
DEFAULT_MEMORY_CONFIG: dict[str, Any] = dict(DEFAULT_CONFIG.get("memory") or {})


def ensure_default_config(cwd: Path | str | None = None) -> Path:
    root = Path.cwd() if cwd is None else Path(cwd)
    target = root / CONFIG_PATH
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = load_default_config()
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


def resolve_memory_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved = dict(DEFAULT_MEMORY_CONFIG)
    if config:
        memory_user = config.get("memory")
        if isinstance(memory_user, dict):
            for key, val in memory_user.items():
                if key in resolved and val is not None:
                    resolved[key] = val
    return resolved


def resolve_show_tool_results(cli_value: bool | None, cwd: Path | str | None = None) -> bool:
    if cli_value is not None:
        return cli_value
    cfg = load_config(cwd)
    val = cfg.get("show_tool_results")
    return bool(val) if isinstance(val, bool) else True
