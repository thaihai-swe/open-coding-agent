from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any

from ..domain.errors import ProviderError
from ..domain.models import ChatMessage, ProviderResponse, ToolCall, ToolResult
from ..domain.provider import Provider
from ..infrastructure.session_store import SessionStore
from ..tools import invoke, registry
from ..tools import permission_rules
from ..tools.permissions import AuthorizeDecision, hard_deny_reason
from ..tools.skills import build_system_message
from ..tools.task_board import PLANNING_MUTATION_NAMES, PLANNING_TOOL_NAMES, bind_session, reset_session
from ..tools.types import Risk

Authorize = Callable[[str, dict[str, Any]], AuthorizeDecision]


class QueryEngine:
    def __init__(self, provider: Provider, session: SessionStore, session_id: str, authorize: Authorize, on_event: Callable[[dict[str, Any]], None] | None = None, max_turns: int = 8) -> None:
        self.provider = provider
        self.session = session
        self.session_id = session_id
        self.authorize = authorize
        self.on_event = on_event or (lambda event: None)
        self.max_turns = max_turns
        self.history = session.load(session_id) if session_id in session.list() else []
        self._rounds_without_planning = 0

    def turn(self, prompt: str) -> ProviderResponse:
        token = bind_session(self.session_id)
        try:
            return self._turn(prompt)
        finally:
            reset_session(token)

    def _turn(self, prompt: str) -> ProviderResponse:
        self.history.append(ChatMessage("user", prompt))
        self._save()
        response: ProviderResponse | None = None
        turn_count = 0
        while turn_count < self.max_turns:
            if self._rounds_without_planning >= 3:
                self.history.append(ChatMessage("user", "<reminder>Update your todos.</reminder>"))
                self._rounds_without_planning = 0
                self._save()
            try:
                completion = self.provider.complete(self._with_system(self.history), _tool_schemas(), stream=True)
                if isinstance(completion, ProviderResponse):
                    response = completion
                    if response.message.content:
                        self.on_event({"type": "text", "content": response.message.content})
                else:
                    response = self._collect_stream(completion)
            except Exception as error:
                self._save()
                raise ProviderError(f"Provider completion failed: {error}") from error
            turn_count += 1
            self.history.append(response.message)
            self._save()
            if not response.message.tool_calls:
                self._rounds_without_planning += 1
                return replace(response, termination_reason="completed")
            hard_denied, mutated = self._run_batch(response.message.tool_calls)
            self._rounds_without_planning = 0 if mutated else self._rounds_without_planning + 1
            if hard_denied:
                return replace(response, termination_reason="completed")
        return replace(response, termination_reason="max_turns_reached")

    def _with_system(self, history: list[ChatMessage]) -> list[ChatMessage]:
        return [ChatMessage("system", build_system_message()), *history]

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

    def _run_batch(self, tool_calls: tuple[ToolCall, ...]) -> tuple[bool, bool]:
        results: list[ToolResult | None] = [None] * len(tool_calls)
        approved: list[tuple[int, ToolCall, Any]] = []
        hard_denied = False
        for index, call in enumerate(tool_calls):
            tool = registry.get(call.name)
            if tool is None:
                results[index] = ToolResult(call.id, {"error": f"Unknown tool: {call.name}"}, True)
                continue
            if not isinstance(call.arguments, dict):
                results[index] = ToolResult(call.id, {"error": "Tool arguments must be an object."}, True)
                continue
            deny_reason = hard_deny_reason(tool, call.arguments)
            if deny_reason:
                hard_denied = True
                results[index] = ToolResult(call.id, {"error": deny_reason}, True)
                continue
            if tool.risk_level in {Risk.HIGH, Risk.MEDIUM}:
                matched = permission_rules.match_rule(call.name, call.arguments)
                if matched == "allow":
                    approved.append((index, call, tool))
                    continue
                if matched == "deny":
                    self.on_event({"type": "tool_denied", "name": call.name, "arguments": call.arguments})
                    results[index] = ToolResult(call.id, {"error": "Tool execution denied by user."}, True)
                    continue
                decision = self.authorize(call.name, call.arguments)
                if decision.persist:
                    pattern = (
                        permission_rules.wildcard_pattern(call.name, call.arguments)
                        if decision.persist_pattern
                        else None
                    )
                    permission_rules.upsert_rule(
                        call.name,
                        call.arguments,
                        "allow" if decision.allow else "deny",
                        pattern=pattern,
                    )
                if not decision.allow:
                    self.on_event({"type": "tool_denied", "name": call.name, "arguments": call.arguments})
                    results[index] = ToolResult(call.id, {"error": "Tool execution denied by user."}, True)
                    continue
            approved.append((index, call, tool))
        if approved:
            self.on_event({"type": "status", "message": "running tools"})
            for _index, call, _tool in approved:
                self.on_event({"type": "tool", "name": call.name, "arguments": call.arguments})
            planning = [(index, call, tool) for index, call, tool in approved if call.name in PLANNING_TOOL_NAMES]
            others = [(index, call, tool) for index, call, tool in approved if call.name not in PLANNING_TOOL_NAMES]
            for index, call, tool in planning:
                results[index] = self._invoke_call(call, tool)
            if others:
                with ThreadPoolExecutor(max_workers=len(others)) as pool:
                    futures = [(index, pool.submit(self._invoke_call, call, tool)) for index, call, tool in others]
                for index, future in futures:
                    results[index] = future.result()
        mutated = False
        for index, call in enumerate(tool_calls):
            result = results[index]
            assert result is not None
            self.on_event({"type": "tool_result", "name": call.name, "content": result.content, "is_error": result.is_error})
            self.history.append(ChatMessage("tool", tool_result=result))
            if not result.is_error and call.name in PLANNING_MUTATION_NAMES:
                mutated = True
        self._save()
        return hard_denied, mutated

    def _invoke_call(self, call: ToolCall, tool: Any) -> ToolResult:
        try:
            result = invoke(call.name, **call.arguments, **({"bypass_permissions": True} if tool.risk_level == Risk.HIGH else {}))
            return ToolResult(call.id, result, result.get("status") == "error")
        except Exception as error:
            return ToolResult(call.id, {"error": f"Tool execution failed: {error}"}, True)

    def _save(self) -> None:
        self.session.save(self.session_id, self.history)


def _tool_schemas() -> list[dict[str, Any]]:
    return [{"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["schema"]}} for tool in registry.list_schemas()]
