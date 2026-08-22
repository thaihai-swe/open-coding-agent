from __future__ import annotations

import json
from typing import Any
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from ..domain.models import ChatMessage, ToolCall, ToolResult


class SessionStore:
    def __init__(self, directory: str | Path = ".sessions") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def create(self) -> str:
        return uuid4().hex

    def list(self) -> list[str]:
        return sorted(path.stem for path in self.directory.glob("*.json"))

    def save(self, session_id: str, history: list[ChatMessage]) -> None:
        path = self.directory / f"{session_id}.json"
        path.write_text(json.dumps({"messages": [_encode(message) for message in history]}, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, session_id: str) -> list[ChatMessage]:
        path = self.directory / f"{session_id}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [_decode(message) for message in data["messages"]]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise ValueError(f"Cannot load session '{session_id}': {error}") from error


def _encode(message: ChatMessage) -> dict:
    return _redact(asdict(message))


def _decode(data: dict) -> ChatMessage:
    calls = tuple(ToolCall(**call) for call in data.get("tool_calls", []))
    result = data.get("tool_result")
    return ChatMessage(data["role"], data.get("content"), calls, ToolResult(**result) if result else None)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items() if "api_key" not in key.lower() and "authorization" not in key.lower()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
