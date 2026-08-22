from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..domain.errors import ProviderError
from ..domain.models import ChatMessage, ProviderResponse, ToolCall, ToolResult
from ..infrastructure.session_store import SessionStore
from ..tools import invoke, registry
from ..tools.types import Risk

Authorize = Callable[[str, dict[str, Any]], bool]


class QueryEngine:
    def __init__(self, provider: Any, session: SessionStore, session_id: str, authorize: Authorize, on_event: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.provider = provider
        self.session = session
        self.session_id = session_id
        self.authorize = authorize
        self.on_event = on_event or (lambda event: None)
        self.history = session.load(session_id) if session_id in session.list() else []

    def turn(self, prompt: str) -> ProviderResponse:
        self.history.append(ChatMessage("user", prompt))
        self._save()
        while True:
            try:
                completion = self.provider.complete(self.history, _tool_schemas(), stream=True)
                if isinstance(completion, ProviderResponse):
                    response = completion
                    if response.message.content:
                        self.on_event({"type": "text", "content": response.message.content})
                else:
                    response = self._collect_stream(completion)
            except Exception as error:
                self._save()
                raise ProviderError(f"Provider completion failed: {error}") from error
            self.history.append(response.message)
            self._save()
            if not response.message.tool_calls:
                return response
            for call in response.message.tool_calls:
                result = self._run_call(call)
                self.history.append(ChatMessage("tool", tool_result=result))
                self._save()

    def _collect_stream(self, deltas: Any) -> ProviderResponse:
        content = []
        tool_calls = ()
        for delta in deltas:
            if delta.content:
                content.append(delta.content)
                self.on_event({"type": "text", "content": delta.content})
            if delta.tool_calls:
                tool_calls = delta.tool_calls
        return ProviderResponse(ChatMessage("assistant", "".join(content) or None, tool_calls))

    def _run_call(self, call: ToolCall) -> ToolResult:
        tool = registry.get(call.name)
        if tool is None:
            return ToolResult(call.id, {"error": f"Unknown tool: {call.name}"}, True)
        if not isinstance(call.arguments, dict):
            return ToolResult(call.id, {"error": "Tool arguments must be an object."}, True)
        if tool.risk_level in {Risk.HIGH, Risk.MEDIUM} and not self.authorize(call.name, call.arguments):
            self.on_event({"type": "tool_denied", "name": call.name, "arguments": call.arguments})
            return ToolResult(call.id, {"error": "Tool execution denied by user."}, True)
        self.on_event({"type": "tool", "name": call.name, "arguments": call.arguments})
        try:
            result = invoke(call.name, **call.arguments, **({"bypass_permissions": True} if tool.risk_level == Risk.HIGH else {}))
            return ToolResult(call.id, result, result.get("status") == "error")
        except Exception as error:
            return ToolResult(call.id, {"error": f"Tool execution failed: {error}"}, True)

    def _save(self) -> None:
        self.session.save(self.session_id, self.history)


def _tool_schemas() -> list[dict[str, Any]]:
    return [{"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["schema"]}} for tool in registry.list_schemas()]
