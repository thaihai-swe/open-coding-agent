import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.query_engine import QueryEngine
from src.domain.errors import ProviderError
from src.domain.models import ChatMessage, ProviderResponse, ToolCall, ToolResult
from src.domain.provider import Provider
from src.infrastructure.session_store import SessionStore
from src.tools.registry import Tool, registry


class FakeProvider:
    def __init__(self, responses: list[ProviderResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[list[ChatMessage]] = []

    def complete(self, history: list[ChatMessage], tools: list[dict], stream: bool = False) -> ProviderResponse:
        self.calls.append(list(history))
        if not self.responses:
            raise ProviderError("No more responses")
        return self.responses.pop(0)


class AlwaysToolProvider:
    """Fake provider that always returns a tool call to test max_turns bounds."""
    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, history: list[ChatMessage], tools: list[dict], stream: bool = False) -> ProviderResponse:
        self.call_count += 1
        return ProviderResponse(
            ChatMessage("assistant", tool_calls=(ToolCall(f"call-{self.call_count}", "read_file", {"file_path": "nonexistent.txt"}),))
        )


class TestQueryEngine(unittest.TestCase):
    def test_direct_response_emits_text_once(self) -> None:
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "hello"))])
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True, on_event=events.append)
            response = engine.turn("Hi")

            self.assertEqual([event for event in events if event["type"] == "text"], [{"type": "text", "content": "hello"}])
            self.assertEqual([message.role for message in engine.history], ["user", "assistant"])
            self.assertEqual(response.termination_reason, "completed")

    def test_approved_tool_execution_turn(self) -> None:
        responses = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-1", "read_file", {"file_path": "nonexistent.txt"}),))),
            ProviderResponse(ChatMessage("assistant", "File read attempt finished")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True, on_event=events.append)
            response = engine.turn("Read the file")

            self.assertEqual(response.message.content, "File read attempt finished")
            self.assertEqual(response.termination_reason, "completed")
            self.assertEqual(len(engine.history), 4)
            self.assertEqual(engine.history[2].role, "tool")
            self.assertEqual(engine.history[2].tool_result.call_id, "call-1")
            self.assertEqual([event["type"] for event in events if event["type"] in {"status", "tool", "tool_result"}][:3], ["status", "tool", "tool_result"])

    def test_denied_tool_execution_turn(self) -> None:
        responses = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo bad"}),))),
            ProviderResponse(ChatMessage("assistant", "Denied acknowledged")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: False, on_event=events.append)
            engine.turn("Run command")

            self.assertTrue(engine.history[2].tool_result.is_error)
            self.assertEqual(engine.history[2].tool_result.content["error"], "Tool execution denied by user.")
            self.assertEqual(events[0]["type"], "tool_denied")

    def test_max_turns_reached_stops_loop(self) -> None:
        # AC-004: max_turns=2 with a provider that always requests tools stops after 2 completions
        provider = AlwaysToolProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True, on_event=events.append, max_turns=2)
            response = engine.turn("Infinite loop test")

            self.assertEqual(provider.call_count, 2)
            self.assertEqual(response.termination_reason, "max_turns_reached")
            self.assertTrue(bool(response.message.tool_calls))

    def test_provider_protocol_conformance(self) -> None:
        # AC-006: FakeProvider drives the engine without importing OpenAIProvider
        self.assertFalse(hasattr(FakeProvider, "__mro__") and any(cls.__name__ == "OpenAIProvider" for cls in FakeProvider.__mro__))
        self.assertTrue(callable(getattr(FakeProvider, "complete", None)))
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "ok"))])
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True)
            response = engine.turn("Hi")
            self.assertEqual(response.termination_reason, "completed")
            self.assertEqual(len(provider.calls), 1)
        import src.infrastructure.providers.openai as openai_mod
        self.assertIsNot(type(provider), openai_mod.OpenAIProvider)

    def test_unknown_tool_records_error_and_continues(self) -> None:
        # AC-004 / T-003
        responses = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-1", "not_a_real_tool", {}),))),
            ProviderResponse(ChatMessage("assistant", "recovered")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True)
            response = engine.turn("Unknown")

            self.assertTrue(engine.history[2].tool_result.is_error)
            self.assertIn("Unknown tool", str(engine.history[2].tool_result.content))
            self.assertEqual(response.message.content, "recovered")
            self.assertEqual(response.termination_reason, "completed")
            self.assertEqual(len(provider.calls), 2)

    def test_batch_history_order_when_second_finishes_first(self) -> None:
        # AC-009 / T-003
        finished: list[str] = []

        def slow(**kwargs):
            time.sleep(0.15)
            finished.append("A")
            return "A"

        def fast(**kwargs):
            finished.append("B")
            return "B"

        registry.register(Tool("slow_tool", "Execution", "LOW", "slow", {"required": [], "properties": {}}, slow))
        registry.register(Tool("fast_tool", "Execution", "LOW", "fast", {"required": [], "properties": {}}, fast))
        try:
            responses = [
                ProviderResponse(
                    ChatMessage(
                        "assistant",
                        tool_calls=(
                            ToolCall("call-a", "slow_tool", {}),
                            ToolCall("call-b", "fast_tool", {}),
                        ),
                    )
                ),
                ProviderResponse(ChatMessage("assistant", "done")),
            ]
            provider = FakeProvider(responses)
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True)
                engine.turn("Batch")

                self.assertEqual(finished, ["B", "A"])
                self.assertEqual(engine.history[2].tool_result.call_id, "call-a")
                self.assertEqual(engine.history[3].tool_result.call_id, "call-b")
        finally:
            registry.tools.pop("slow_tool", None)
            registry.tools.pop("fast_tool", None)

    def test_batch_failure_does_not_skip_sibling(self) -> None:
        # AC-010 / T-003
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "not_a_real_tool", {}),
                        ToolCall("call-2", "read_file", {"file_path": "nonexistent.txt"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "both recorded")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True)
            engine.turn("Mixed")

            self.assertEqual(engine.history[2].tool_result.call_id, "call-1")
            self.assertTrue(engine.history[2].tool_result.is_error)
            self.assertEqual(engine.history[3].tool_result.call_id, "call-2")
            self.assertIsNotNone(engine.history[3].tool_result)

    def test_next_complete_waits_for_full_batch(self) -> None:
        # AC-013 / T-003
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "read_file", {"file_path": "missing-a.txt"}),
                        ToolCall("call-2", "read_file", {"file_path": "missing-b.txt"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "after batch")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True)
            engine.turn("Wait")

            self.assertEqual(len(provider.calls), 2)
            roles = [message.role for message in provider.calls[1]]
            self.assertEqual(roles.count("tool"), 2)
            self.assertEqual(provider.calls[1][-2].tool_result.call_id, "call-1")
            self.assertEqual(provider.calls[1][-1].tool_result.call_id, "call-2")

    def test_denied_call_does_not_run_but_siblings_do(self) -> None:
        # AC-011 / T-004
        ran: list[str] = []

        def allowed(**kwargs):
            ran.append("allowed")
            return "ok"

        def denied(**kwargs):
            ran.append("denied")
            return "nope"

        registry.register(Tool("allowed_med", "File I/O", "MEDIUM", "allowed", {"required": [], "properties": {}}, allowed))
        registry.register(Tool("denied_med", "File I/O", "MEDIUM", "denied", {"required": [], "properties": {}}, denied))
        try:
            responses = [
                ProviderResponse(
                    ChatMessage(
                        "assistant",
                        tool_calls=(
                            ToolCall("call-1", "denied_med", {}),
                            ToolCall("call-2", "allowed_med", {}),
                        ),
                    )
                ),
                ProviderResponse(ChatMessage("assistant", "partial")),
            ]
            provider = FakeProvider(responses)
            events: list[dict] = []
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: name != "denied_med",
                    on_event=events.append,
                )
                engine.turn("Deny one")

                self.assertIn("tool_denied", [event["type"] for event in events])
                self.assertEqual(ran, ["allowed"])
                self.assertTrue(engine.history[2].tool_result.is_error)
                self.assertEqual(engine.history[3].tool_result.call_id, "call-2")
                self.assertFalse(engine.history[3].tool_result.is_error)
        finally:
            registry.tools.pop("allowed_med", None)
            registry.tools.pop("denied_med", None)

    def test_authorize_is_sequential_before_overlap(self) -> None:
        # AC-012 / T-004
        log: list[tuple[str, str]] = []

        def authorize(name: str, args: dict) -> bool:
            log.append(("auth", name))
            return True

        def first(**kwargs):
            log.append(("run", "first_med"))
            time.sleep(0.05)
            return "1"

        def second(**kwargs):
            log.append(("run", "second_med"))
            return "2"

        registry.register(Tool("first_med", "File I/O", "MEDIUM", "first", {"required": [], "properties": {}}, first))
        registry.register(Tool("second_med", "File I/O", "MEDIUM", "second", {"required": [], "properties": {}}, second))
        try:
            responses = [
                ProviderResponse(
                    ChatMessage(
                        "assistant",
                        tool_calls=(
                            ToolCall("call-1", "first_med", {}),
                            ToolCall("call-2", "second_med", {}),
                        ),
                    )
                ),
                ProviderResponse(ChatMessage("assistant", "ok")),
            ]
            provider = FakeProvider(responses)
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(provider, store, session_id, authorize=authorize)
                engine.turn("Auth order")

                self.assertEqual([item for item in log if item[0] == "auth"], [("auth", "first_med"), ("auth", "second_med")])
                self.assertLess(log.index(("auth", "second_med")), min(i for i, item in enumerate(log) if item[0] == "run"))
        finally:
            registry.tools.pop("first_med", None)
            registry.tools.pop("second_med", None)

    def test_status_then_tool_then_tool_result_events(self) -> None:
        # AC-015 / T-004
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "read_file", {"file_path": "missing-a.txt"}),
                        ToolCall("call-2", "read_file", {"file_path": "missing-b.txt"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "after")),
        ]
        provider = FakeProvider(responses)
        events: list[dict] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True, on_event=events.append)
            engine.turn("Status")

            types = [event["type"] for event in events]
            self.assertIn("status", types)
            self.assertIn("tool", types)
            self.assertIn("tool_result", types)
            self.assertLess(types.index("status"), types.index("tool"))
            tool_indexes = [index for index, kind in enumerate(types) if kind == "tool"]
            result_indexes = [index for index, kind in enumerate(types) if kind == "tool_result"]
            self.assertEqual(len(tool_indexes), 2)
            self.assertEqual(len(result_indexes), 2)
            self.assertLess(max(tool_indexes), min(result_indexes))
            self.assertEqual(events[result_indexes[0]]["name"], "read_file")
            self.assertEqual(events[result_indexes[1]]["name"], "read_file")


if __name__ == "__main__":
    unittest.main()


