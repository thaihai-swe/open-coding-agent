import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.query_engine import QueryEngine
from src.domain.errors import ProviderError
from src.domain.models import ChatMessage, ProviderResponse, ToolCall, ToolResult
from src.infrastructure.session_store import SessionStore
from src.tools.permissions import AuthorizeDecision


class FakeProvider:
    def __init__(self, responses: list[ProviderResponse]) -> None:
        self.responses = list(responses)

    def complete(self, history: list[ChatMessage], tools: list[dict], stream: bool = False) -> ProviderResponse:
        if not self.responses:
            raise ProviderError("No more responses")
        return self.responses.pop(0)


class TestSession(unittest.TestCase):
    def test_session_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            history = [ChatMessage("user", "run bash"), ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo 1"}),)), ChatMessage("tool", tool_result=ToolResult("call-1", {"output": "1"}))]
            store.save(session_id, history)

            session_file = Path(temp_dir) / f"{session_id}.json"
            content = session_file.read_text(encoding="utf-8")
            self.assertNotIn("secret", content)
            self.assertNotIn("OPENAI_API_KEY", content)

            loaded = store.load(session_id)
            self.assertEqual(loaded, history)
            self.assertIn(session_id, store.list())

    def test_default_store_writes_under_cda_sessions(self) -> None:
        # AC-027 / REQ-020 / T-007
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                store = SessionStore()
                session_id = store.create()
                store.save(session_id, [ChatMessage("user", "hi")])
                self.assertTrue((Path(".cda/.sessions") / f"{session_id}.json").exists())
                self.assertFalse((Path(".sessions") / f"{session_id}.json").exists())
            finally:
                os.chdir(cwd)

    def test_messages_only_session_without_rules_still_prompts(self) -> None:
        # AC-024 / REQ-018 / T-007
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                store = SessionStore()
                session_id = store.create()
                store.save(session_id, [ChatMessage("user", "hi"), ChatMessage("assistant", "ok")])
                loaded = store.load(session_id)
                self.assertEqual([message.role for message in loaded], ["user", "assistant"])
                self.assertFalse(Path(".cda/.permission_rules/rules.json").exists())

                authorized: list[str] = []
                responses = [
                    ProviderResponse(
                        ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo ping"}),))
                    ),
                    ProviderResponse(ChatMessage("assistant", "done")),
                ]
                engine = QueryEngine(
                    FakeProvider(responses),
                    store,
                    session_id,
                    authorize=lambda name, args: (authorized.append(name) or AuthorizeDecision(allow=True, persist=False)),
                )
                engine.turn("Ping")
                self.assertEqual(authorized, ["bash"])
            finally:
                os.chdir(cwd)

    def test_later_save_does_not_add_permission_fields_or_change_rules(self) -> None:
        # AC-026 / REQ-018 / T-007
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                rules_path = Path(".cda/.permission_rules/rules.json")
                rules_path.parent.mkdir(parents=True, exist_ok=True)
                original_rules = [{"tool": "bash", "pattern": {"command": "echo ping"}, "decision": "allow"}]
                rules_path.write_text(json.dumps(original_rules), encoding="utf-8")

                store = SessionStore()
                session_id = store.create()
                store.save(session_id, [ChatMessage("user", "hi")])
                store.save(session_id, [ChatMessage("user", "hi"), ChatMessage("assistant", "ok")])

                session_data = json.loads((Path(".cda/.sessions") / f"{session_id}.json").read_text(encoding="utf-8"))
                self.assertEqual(list(session_data.keys()), ["messages"])
                self.assertEqual(json.loads(rules_path.read_text(encoding="utf-8")), original_rules)
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
