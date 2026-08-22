import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.presentation.terminal_ui import TerminalUI


class TestTerminalUI(unittest.TestCase):
    def test_single_line_prompt(self) -> None:
        ui = TerminalUI(input_fn=lambda prompt: "hello")
        self.assertEqual(ui.prompt(), "hello")

    def test_authorization_prompt(self) -> None:
        ui_approve = TerminalUI(input_fn=lambda prompt: "a")
        self.assertTrue(ui_approve.authorize("bash", {"command": "ls"}))

        ui_deny = TerminalUI(input_fn=lambda prompt: "d")
        self.assertFalse(ui_deny.authorize("bash", {"command": "ls"}))

    def test_json_event(self) -> None:
        buf = io.StringIO()
        ui = TerminalUI(output=buf, json_mode=True)
        ui.event({"type": "tool", "name": "bash", "arguments": {}})
        self.assertIn('"type": "tool"', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
