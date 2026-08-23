from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..domain.errors import ProviderError
from ..domain.models import ChatMessage, ProviderResponse, ToolCall, ToolResult
from ..domain.provider import Provider
from ..infrastructure.session_store import SessionStore, _redact
from ..tools import invoke, registry
from ..tools import permission_rules
from ..tools.compact import (
    estimate_history_chars,
    find_safe_boundary,
    micro_compact,
    snip_compact,
    tool_result_budget,
)
from ..tools.config import load_config, resolve_compact_config, resolve_memory_config
from ..tools.memory import (
    consolidate_memories,
    extract_memories,
    format_relevant_memories,
    select_relevant_memories,
)
from ..tools.permissions import AuthorizeDecision, hard_deny_reason
from ..tools.prompt import assemble_system_prompt, load_prompt_section
from ..tools.task_board import PLANNING_MUTATION_NAMES, PLANNING_TOOL_NAMES, bind_session, reset_session
from ..tools.types import Risk

Authorize = Callable[[str, dict[str, Any]], AuthorizeDecision]


class QueryEngine:
    def __init__(
        self,
        provider: Provider,
        session: SessionStore,
        session_id: str,
        authorize: Authorize,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        max_turns: int = 8,
    ) -> None:
        self.provider = provider
        self.session = session
        self.session_id = session_id
        self.authorize = authorize
        self.on_event = on_event or (lambda event: None)
        self.max_turns = max_turns
        self.history = session.load(session_id) if session_id in session.list() else []
        self._rounds_without_planning = 0
        self._consecutive_compact_failures = 0
        raw_cfg = load_config()
        self.config = resolve_compact_config(raw_cfg)
        self.memory_config = resolve_memory_config(raw_cfg)

    def turn(self, prompt: str) -> ProviderResponse:
        token = bind_session(self.session_id)
        try:
            return self._turn(prompt)
        finally:
            reset_session(token)

    def manual_compact(self) -> bool:
        return self.compact_history()

    def compact_history(self, keep_recent: int | None = None) -> bool:
        if self._consecutive_compact_failures >= self.config.get("compact_fail_retries", 3):
            return False
        keep = self.config.get("keep_recent", 4) if keep_recent is None else keep_recent
        tail_start = max(0, len(self.history) - keep)
        tail_start = find_safe_boundary(self.history, tail_start)
        if tail_start <= 0:
            return False
        self.on_event({"type": "status", "message": "compacting context"})
        self._write_transcript_snapshot()
        summary = self._summarize_messages(self.history[:tail_start])
        if not summary:
            self._consecutive_compact_failures += 1
            return False
        self._consecutive_compact_failures = 0
        summary_msg = ChatMessage("user", f"<compacted-summary>\n{summary}\n</compacted-summary>")
        self.history = [summary_msg, *self.history[tail_start:]]
        self._save()
        self.on_event({"type": "status", "message": "context compacted"})
        return True

    def reactive_compact(self, tail_count: int = 5) -> bool:
        if self._consecutive_compact_failures >= self.config.get("compact_fail_retries", 3):
            return False
        tail_start = max(0, len(self.history) - tail_count)
        tail_start = find_safe_boundary(self.history, tail_start)
        if tail_start <= 0:
            return False
        self.on_event({"type": "status", "message": "reactive compacting context"})
        self._write_transcript_snapshot()
        summary = self._summarize_messages(self.history[:tail_start])
        if not summary:
            self._consecutive_compact_failures += 1
            return False
        self._consecutive_compact_failures = 0
        summary_msg = ChatMessage("user", f"<compacted-summary>\n{summary}\n</compacted-summary>")
        self.history = [summary_msg, *self.history[tail_start:]]
        self._save()
        self.on_event({"type": "status", "message": "context compacted"})
        return True

    def _summarize_messages(self, messages_to_summarize: list[ChatMessage]) -> str | None:
        compact_prompt = load_prompt_section("compact")
        prompt_msgs = [ChatMessage("system", compact_prompt), *messages_to_summarize]
        try:
            res = self.provider.complete(prompt_msgs, tools=[], stream=False)
            if isinstance(res, ProviderResponse):
                return res.message.content or None
            collected = []
            for delta in res:
                if delta.content:
                    collected.append(delta.content)
            return "".join(collected).strip() or None
        except Exception:
            return None

    def _write_transcript_snapshot(self) -> None:
        transcripts_dir = Path(".cda/.transcripts")
        try:
            transcripts_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            path = transcripts_dir / f"{self.session_id}-{ts}.jsonl"
            lines = [json.dumps(_redact(asdict(m)), ensure_ascii=False) for m in self.history]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            pass

    def _apply_pre_complete_compaction(self) -> None:
        if not self.config.get("auto_compact", True):
            return
        self.history = tool_result_budget(
            self.history,
            max_bytes=self.config.get("tool_result_max_bytes", 200000),
            preview_chars=self.config.get("persist_preview_chars", 2000),
        )
        self.history = snip_compact(
            self.history,
            max_messages=self.config.get("max_messages", 50),
            keep_head=self.config.get("keep_head", 3),
        )
        self.history = micro_compact(
            self.history,
            keep_recent_results=self.config.get("keep_recent_tool_results", 3),
        )
        if (
            len(self.history) > self.config.get("max_messages", 50)
            or estimate_history_chars(self.history) > self.config.get("max_chars", 80000)
        ):
            self.compact_history()

    def _turn(self, prompt: str) -> ProviderResponse:
        self.history.append(ChatMessage("user", prompt))
        self._save()

        relevant_content = ""
        if self.memory_config.get("enabled", True):
            selected_files = select_relevant_memories(
                self.provider,
                self.history,
                max_items=self.memory_config.get("max_relevant", 5),
            )
            relevant_content = format_relevant_memories(selected_files)

        response: ProviderResponse | None = None
        turn_count = 0
        reactive_retries_used = 0
        max_reactive_retries = self.config.get("reactive_retries", 1)
        pre_compress = list(self.history)

        while turn_count < self.max_turns:
            if self._rounds_without_planning >= 3:
                self.history.append(ChatMessage("user", "<reminder>Update your todos.</reminder>"))
                self._rounds_without_planning = 0
                self._save()

            pre_compress = list(self.history)
            self._apply_pre_complete_compaction()

            request_history = list(self.history)
            if relevant_content:
                for i in reversed(range(len(request_history))):
                    if request_history[i].role == "user" and request_history[i].content:
                        orig = request_history[i].content or ""
                        request_history[i] = replace(
                            request_history[i],
                            content=f"{relevant_content}\n\n{orig}",
                        )
                        break

            while True:
                try:
                    completion = self.provider.complete(self._with_system(request_history), _tool_schemas(), stream=True)
                    if isinstance(completion, ProviderResponse):
                        response = completion
                        if response.message.content:
                            self.on_event({"type": "text", "content": response.message.content})
                    else:
                        response = self._collect_stream(completion)
                    break
                except ProviderError as error:
                    err_lower = str(error).lower()
                    if (
                        "prompt_too_long" in err_lower
                        or "context length" in err_lower
                        or "413" in err_lower
                    ):
                        if reactive_retries_used < max_reactive_retries:
                            reactive_retries_used += 1
                            if self.reactive_compact(tail_count=5):
                                request_history = list(self.history)
                                if relevant_content:
                                    for i in reversed(range(len(request_history))):
                                        if request_history[i].role == "user" and request_history[i].content:
                                            orig = request_history[i].content or ""
                                            request_history[i] = replace(
                                                request_history[i],
                                                content=f"{relevant_content}\n\n{orig}",
                                            )
                                            break
                                continue
                    self._save()
                    raise
                except Exception as error:
                    self._save()
                    raise ProviderError(f"Provider completion failed: {error}") from error

            turn_count += 1
            self.history.append(response.message)
            self._save()
            if not response.message.tool_calls:
                self._rounds_without_planning += 1
                self._post_turn_memory(pre_compress)
                return replace(response, termination_reason="completed")
            hard_denied, mutated = self._run_batch(response.message.tool_calls)
            self._rounds_without_planning = 0 if mutated else self._rounds_without_planning + 1
            if hard_denied:
                self._post_turn_memory(pre_compress)
                return replace(response, termination_reason="completed")
            if any(call.name == "compact" for call in response.message.tool_calls):
                self._post_turn_memory(pre_compress)
                return replace(response, termination_reason="completed")
        self._post_turn_memory(pre_compress)
        return replace(response, termination_reason="max_turns_reached")

    def _post_turn_memory(self, snapshot: list[ChatMessage]) -> None:
        if not self.memory_config.get("enabled", True):
            return
        if self.memory_config.get("auto_extract", True):
            try:
                count = extract_memories(self.provider, snapshot)
                if count > 0:
                    self.on_event({"type": "status", "message": f"extracted {count} new memories"})
            except Exception:
                pass
        if self.memory_config.get("auto_consolidate", True):
            try:
                threshold = self.memory_config.get("consolidate_threshold", 10)
                old_c, new_c = consolidate_memories(self.provider, threshold=threshold)
                if old_c >= threshold:
                    self.on_event({"type": "status", "message": f"consolidated memories: {old_c} -> {new_c}"})
            except Exception:
                pass

    def _with_system(self, history: list[ChatMessage]) -> list[ChatMessage]:
        return [ChatMessage("system", assemble_system_prompt()), *history]

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
            if not result.is_error and call.name == "compact":
                self.compact_history()
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
