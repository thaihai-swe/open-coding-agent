import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.query_engine import QueryEngine
from src.domain.errors import ProviderError
from src.domain.models import ChatMessage, ProviderResponse, ToolCall, ToolResult
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


class TestQueryEngine(unittest.TestCase):
    def test_direct_response_emits_text_once(self) -> None:
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "hello"))])
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: True, on_event=events.append)
            engine.turn("Hi")

            self.assertEqual([event for event in events if event["type"] == "text"], [{"type": "text", "content": "hello"}])

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


if __name__ == "__main__":
    unittest.main()
