import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.session_store import SessionStore
from src.presentation.cli import parse_args, run


class TestCli(unittest.TestCase):
    def test_args(self) -> None:
        args = parse_args(["--session", "session-1", "--json"])
        self.assertEqual(args.session, "session-1")
        self.assertTrue(args.json_mode)
        self.assertFalse(args.debug)

    def test_debug_arg(self) -> None:
        self.assertTrue(parse_args(["--debug"]).debug)

    def test_missing_configuration_is_actionable(self) -> None:
        with patch.dict(os.environ, {"CONFIG_FILE": "/tmp/nonexistent-openai-config.json"}, clear=True):
            self.assertEqual(run([]), 2)

    def test_keyboard_interrupt_saves_session_and_exits_130(self) -> None:
        # AC-017 / T-006
        class FakeProvider:
            def complete(self, history, tools, stream=False):
                raise AssertionError("turn should not run")

        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            with (
                patch("src.presentation.cli.OpenAIProvider", return_value=FakeProvider()),
                patch("src.presentation.cli.SessionStore", return_value=store),
                patch("src.presentation.cli.TerminalUI") as ui_cls,
            ):
                ui_cls.return_value.prompt.side_effect = KeyboardInterrupt
                code = run([])
            self.assertEqual(code, 130)
            self.assertTrue(any(Path(temp_dir).glob("*.json")))

    def test_ac030_gitignore_contains_cda_entry(self) -> None:
        # AC-030 / REQ-021 / T-008
        gitignore = Path(__file__).resolve().parent.parent / ".gitignore"
        self.assertIn(".cda/", gitignore.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

