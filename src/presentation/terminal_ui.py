from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any


class TerminalUI:
    def __init__(self, input_fn: Callable[[str], str] = input, output=None, json_mode: bool = False) -> None:
        self.input_fn = input_fn
        self.output = output or sys.stdout
        self.json_mode = json_mode

    def prompt(self) -> str:
        return self.input_fn("> ")

    def authorize(self, name: str, arguments: dict[str, Any]) -> bool:
        response = self.input_fn(f"Approve {name} {json.dumps(arguments, sort_keys=True)}? [A]pprove/[D]eny: ").strip().lower()
        return response in {"a", "approve"}

    def event(self, event: dict[str, Any]) -> None:
        if self.json_mode:
            self._write(json.dumps(event, default=str))
            return
        if event["type"] == "text":
            self.output.write(event["content"])
            self.output.flush()
        elif event["type"] in {"tool", "tool_denied"}:
            self._write(f"[{event['type']}] {event['name']} {json.dumps(event['arguments'], sort_keys=True)}")
        elif event["type"] == "error":
            self._write(f"Error: {event['message']}")

    def _write(self, message: str) -> None:
        self.output.write(message + "\n")
        self.output.flush()
