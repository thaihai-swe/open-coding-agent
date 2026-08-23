import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.presentation.terminal_ui import TerminalUI, _edit_prompt


def _reader(chars: str):
    iterator = iter(chars)

    def _read() -> str:
        return next(iterator, "")

    return _read


def _sink():
    return lambda text: None


def _lines(*values: str):
    iterator = iter(values)

    def _input(prompt: str) -> str:
        try:
            return next(iterator)
        except StopIteration as error:
            raise EOFError from error

    return _input


class TestTerminalUI(unittest.TestCase):
    def test_single_line_prompt(self) -> None:
        ui = TerminalUI(input_fn=_lines("hello"))
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

    def test_human_prints_plain_tool_status_and_result_lines(self) -> None:
        # AC-014 / T-005
        buf = io.StringIO()
        ui = TerminalUI(output=buf, json_mode=False)
        ui.event({"type": "tool", "name": "read_file", "arguments": {"file_path": "a.txt"}})
        ui.event({"type": "status", "message": "running tools"})
        ui.event({"type": "tool_result", "name": "read_file", "content": "ok", "is_error": False})
        ui.event({"type": "error", "message": "boom"})
        output = buf.getvalue()
        self.assertIn("[tool]", output)
        self.assertIn("[status]", output)
        self.assertIn("[tool_result]", output)
        self.assertIn("Error: boom", output)
        self.assertNotIn("**", output)

    def test_json_emits_additive_event_types(self) -> None:
        # AC-016 / T-005
        buf = io.StringIO()
        ui = TerminalUI(output=buf, json_mode=True)
        events = [
            {"type": "text", "content": "# Title"},
            {"type": "tool", "name": "bash", "arguments": {}},
            {"type": "tool_denied", "name": "bash", "arguments": {}},
            {"type": "error", "message": "boom"},
            {"type": "status", "message": "running tools"},
            {"type": "tool_result", "name": "bash", "content": "ok", "is_error": False},
        ]
        for event in events:
            ui.event(event)
        lines = [json.loads(line) for line in buf.getvalue().splitlines() if line]
        self.assertEqual([item["type"] for item in lines], [event["type"] for event in events])
        self.assertEqual(lines[0]["content"], "# Title")

    def test_enter_sends_without_period(self) -> None:
        ui = TerminalUI(input_fn=_lines("hello"))
        self.assertEqual(ui.prompt(), "hello")

    def test_empty_first_line_quits(self) -> None:
        ui = TerminalUI(input_fn=_lines(""))
        self.assertEqual(ui.prompt(), "")

    def test_eof_on_empty_prompt_quits(self) -> None:
        ui = TerminalUI(input_fn=_lines())
        self.assertEqual(ui.prompt(), "")

    def test_json_mode_enter_sends(self) -> None:
        ui = TerminalUI(input_fn=_lines("hello"), json_mode=True)
        self.assertEqual(ui.prompt(), "hello")

    def test_tty_enter_submits(self) -> None:
        self.assertEqual(_edit_prompt(_reader("hello\r"), _sink()), "hello")

    def test_tty_empty_enter_quits(self) -> None:
        self.assertEqual(_edit_prompt(_reader("\r"), _sink()), "")

    def test_tty_shift_enter_modifyotherkeys_inserts_newline(self) -> None:
        self.assertEqual(_edit_prompt(_reader("hello\x1b[27;2;13~world\r"), _sink()), "hello\nworld")

    def test_tty_shift_enter_kitty_inserts_newline(self) -> None:
        self.assertEqual(_edit_prompt(_reader("hello\x1b[13;2uworld\r"), _sink()), "hello\nworld")

    def test_tty_ctrl_j_inserts_newline(self) -> None:
        self.assertEqual(_edit_prompt(_reader("hello\nworld\r"), _sink()), "hello\nworld")

    def test_human_text_renders_markdown_heading_and_bold(self) -> None:
        # AC-021 / T-008
        buf = io.StringIO()
        ui = TerminalUI(output=buf, json_mode=False)
        ui.event({"type": "text", "content": "# Title\n**bold**"})
        output = buf.getvalue()
        self.assertIn("Title", output)
        self.assertIn("bold", output)
        self.assertFalse(output.strip() in {"# Title\n**bold**", "# Title**bold**"})
        self.assertNotEqual(output, "# Title\n**bold**")

    def test_human_non_text_events_stay_plain(self) -> None:
        # AC-022 / T-008
        buf = io.StringIO()
        ui = TerminalUI(output=buf, json_mode=False)
        ui.event({"type": "tool", "name": "**bash**", "arguments": {"command": "# Title"}})
        ui.event({"type": "tool_result", "name": "bash", "content": "**ok**", "is_error": False})
        ui.event({"type": "status", "message": "**running**"})
        ui.event({"type": "error", "message": "**boom**"})
        output = buf.getvalue()
        self.assertIn("**bash**", output)
        self.assertIn("# Title", output)
        self.assertIn("**ok**", output)
        self.assertIn("**running**", output)
        self.assertIn("**boom**", output)

    def test_json_text_keeps_markdown_source(self) -> None:
        # AC-023 / T-008
        buf = io.StringIO()
        ui = TerminalUI(output=buf, json_mode=True)
        ui.event({"type": "text", "content": "# Title\n**bold**"})
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["content"], "# Title\n**bold**")


if __name__ == "__main__":
    unittest.main()



