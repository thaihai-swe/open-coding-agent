import json
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

    def test_cli_initializes_default_config_json_on_startup_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                config_file = Path(temp_dir) / ".cda" / "config.json"
                self.assertFalse(config_file.exists())
                with (
                    patch("src.presentation.cli.OpenAIProvider"),
                    patch("src.presentation.cli.SessionStore"),
                    patch("src.presentation.cli.QueryEngine"),
                    patch("src.presentation.cli.TerminalUI") as ui_cls,
                ):
                    ui_cls.return_value.prompt.return_value = ""
                    code = run([])
                    self.assertEqual(code, 0)
                self.assertTrue(config_file.is_file())
                data = json.loads(config_file.read_text(encoding="utf-8"))
                self.assertTrue(data.get("show_tool_results"))
                self.assertIn("compact", data)
                self.assertEqual(data["compact"].get("max_messages"), 50)
                self.assertIn("memory", data)
                self.assertTrue(data["memory"].get("enabled"))
                self.assertEqual(data["memory"].get("max_relevant"), 5)
                self.assertEqual(data["memory"].get("consolidate_threshold"), 10)
                rules_file = Path(temp_dir) / ".cda" / ".permission_rules" / "rules.json"
                self.assertTrue(rules_file.is_file())
                rules = json.loads(rules_file.read_text(encoding="utf-8"))
                self.assertTrue(any(rule.get("pattern") == {"command": "*sudo*"} for rule in rules))
            finally:
                os.chdir(cwd)

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

    def test_ac003_ui_config_json_ignored_config_json_used(self) -> None:
        from src.tools.config import resolve_show_tool_results

        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                Path(".cda").mkdir()
                Path(".cda/ui-config.json").write_text('{"show_tool_results": false}', encoding="utf-8")
                self.assertTrue(resolve_show_tool_results(None, Path(temp_dir)))
                Path(".cda/config.json").write_text('{"show_tool_results": false}', encoding="utf-8")
                self.assertFalse(resolve_show_tool_results(None, Path(temp_dir)))
            finally:
                os.chdir(cwd)

    def test_ac013_compact_slash_does_not_call_turn(self) -> None:
        class MockEngine:
            def __init__(self) -> None:
                self.prompts: list[str] = []
                self.compact_calls = 0

            def turn(self, prompt: str):
                self.prompts.append(prompt)

            def manual_compact(self) -> bool:
                self.compact_calls += 1
                return True

        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                mock_engine = MockEngine()
                events: list[dict] = []
                with (
                    patch("src.presentation.cli.OpenAIProvider"),
                    patch("src.presentation.cli.SessionStore"),
                    patch("src.presentation.cli.QueryEngine", return_value=mock_engine),
                    patch("src.presentation.cli.TerminalUI") as ui_cls,
                ):
                    ui_mock = ui_cls.return_value
                    ui_mock.prompt.side_effect = ["/compact", ""]
                    ui_mock.event.side_effect = events.append
                    code = run([])
                    self.assertEqual(code, 0)
                self.assertEqual(mock_engine.compact_calls, 1)
                self.assertEqual(mock_engine.prompts, [])
                self.assertFalse(any("Unknown skill: /compact" in e.get("message", "") for e in events))
            finally:
                os.chdir(cwd)

    def test_ac014_skill_slash_still_expands(self) -> None:
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
                skill_path.write_text("BODY", encoding="utf-8")
                mock_engine = MockEngine()
                with (
                    patch("src.presentation.cli.OpenAIProvider"),
                    patch("src.presentation.cli.SessionStore"),
                    patch("src.presentation.cli.QueryEngine", return_value=mock_engine),
                    patch("src.presentation.cli.TerminalUI") as ui_cls,
                ):
                    ui_mock = ui_cls.return_value
                    ui_mock.prompt.side_effect = ["/code-review", ""]
                    code = run([])
                    self.assertEqual(code, 0)
                self.assertEqual(mock_engine.prompts, ['<skill name="code-review">\nBODY\n</skill>'])
            finally:
                os.chdir(cwd)

    def test_ac016_memory_slash_lists_entries_without_turn(self) -> None:
        from src.tools.memory import write_memory_file

        class MockEngine:
            def __init__(self) -> None:
                self.prompts: list[str] = []

            def turn(self, prompt: str):
                self.prompts.append(prompt)

        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                write_memory_file("user-preference-tabs", "user", "tabs not spaces", "Use tabs.", Path.cwd())
                write_memory_file("project-auth", "project", "auth rewrite", "Auth is compliance-driven.", Path.cwd())
                mock_engine = MockEngine()
                events: list[dict] = []
                with (
                    patch("src.presentation.cli.OpenAIProvider"),
                    patch("src.presentation.cli.SessionStore"),
                    patch("src.presentation.cli.QueryEngine", return_value=mock_engine),
                    patch("src.presentation.cli.TerminalUI") as ui_cls,
                ):
                    ui_mock = ui_cls.return_value
                    ui_mock.prompt.side_effect = ["/memory", ""]
                    ui_mock.event.side_effect = events.append
                    code = run([])
                    self.assertEqual(code, 0)
                self.assertEqual(mock_engine.prompts, [])
                self.assertFalse(any("Unknown skill: /memory" in e.get("message", "") for e in events))
                status = [e for e in events if e.get("type") == "status"]
                self.assertTrue(status)
                joined = "\n".join(e.get("message", "") for e in status)
                self.assertIn("user-preference-tabs", joined)
                self.assertIn("project-auth", joined)
                self.assertIn("2", joined)
            finally:
                os.chdir(cwd)

    def test_ac017_other_skill_slash_still_expands(self) -> None:
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
                skill_path.write_text("BODY", encoding="utf-8")
                mock_engine = MockEngine()
                with (
                    patch("src.presentation.cli.OpenAIProvider"),
                    patch("src.presentation.cli.SessionStore"),
                    patch("src.presentation.cli.QueryEngine", return_value=mock_engine),
                    patch("src.presentation.cli.TerminalUI") as ui_cls,
                ):
                    ui_mock = ui_cls.return_value
                    ui_mock.prompt.side_effect = ["/code-review", ""]
                    code = run([])
                    self.assertEqual(code, 0)
                self.assertEqual(mock_engine.prompts, ['<skill name="code-review">\nBODY\n</skill>'])
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()

