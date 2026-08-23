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

    def test_slash_command_expansion_and_unknown_handling(self) -> None:
        # AC-013, AC-014, AC-016, AC-017 / REQ-013 / T-004
        class MockEngine:
            def __init__(self) -> None:
                self.prompts: list[str] = []

            def turn(self, prompt: str):
                self.prompts.append(prompt)

        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                skill_path = Path(".agents") / "skills" / "code-review" / "SKILL.md"
                skill_path.parent.mkdir(parents=True, exist_ok=True)
                skill_path.write_text("BODY OF CODE REVIEW", encoding="utf-8")

                mock_engine = MockEngine()
                events: list[dict] = []
                ui_prompts = [
                    "/code-review please check line 10",
                    "/code-review",
                    "/nonexistent-skill",
                    "normal prompt",
                    "",
                ]

                with (
                    patch("src.presentation.cli.OpenAIProvider"),
                    patch("src.presentation.cli.SessionStore"),
                    patch("src.presentation.cli.QueryEngine", return_value=mock_engine),
                    patch("src.presentation.cli.TerminalUI") as ui_cls,
                ):
                    ui_mock = ui_cls.return_value
                    ui_mock.prompt.side_effect = ui_prompts
                    ui_mock.event.side_effect = events.append

                    code = run([])
                    self.assertEqual(code, 0)

                # AC-013: /code-review with args
                self.assertEqual(len(mock_engine.prompts), 3)
                self.assertEqual(
                    mock_engine.prompts[0],
                    '<skill name="code-review">\nBODY OF CODE REVIEW\n</skill>\nplease check line 10',
                )
                # AC-016: /code-review without args
                self.assertEqual(
                    mock_engine.prompts[1],
                    '<skill name="code-review">\nBODY OF CODE REVIEW\n</skill>',
                )
                # AC-017: normal prompt passthrough
                self.assertEqual(mock_engine.prompts[2], "normal prompt")

                # AC-014: unknown slash command emits error event
                error_events = [e for e in events if e.get("type") == "error"]
                self.assertTrue(any("Unknown skill: /nonexistent-skill" in e.get("message", "") for e in error_events))
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()

