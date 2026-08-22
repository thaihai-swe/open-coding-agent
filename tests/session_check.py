import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain.models import ChatMessage, ToolCall, ToolResult
from src.infrastructure.session_store import SessionStore


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


if __name__ == "__main__":
    unittest.main()
