import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.query_engine import QueryEngine
from src.domain.errors import ProviderError
from src.domain.models import ChatMessage, ProviderResponse, ToolCall, ToolResult
from src.domain.provider import Provider
from src.infrastructure.session_store import SessionStore


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
            self.assertEqual(events[0]["type"], "tool")

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


if __name__ == "__main__":
    unittest.main()
