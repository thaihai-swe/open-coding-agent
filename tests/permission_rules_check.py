import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools import permission_rules


class TestPermissionRuleWildcards(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def _write_rules(self, rules: list[dict]) -> None:
        path = Path(".cda/.permission_rules/rules.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rules), encoding="utf-8")

    def test_exact_command_still_matches(self) -> None:
        self._write_rules([{"tool": "bash", "pattern": {"command": "echo ping"}, "decision": "allow"}])
        self.assertEqual(permission_rules.match_rule("bash", {"command": "echo ping"}), "allow")
        self.assertIsNone(permission_rules.match_rule("bash", {"command": "echo pong"}))

    def test_star_allows_any_bash_command(self) -> None:
        self._write_rules([{"tool": "bash", "pattern": {"command": "*"}, "decision": "allow"}])
        self.assertEqual(permission_rules.match_rule("bash", {"command": "echo root"}), "allow")
        self.assertEqual(permission_rules.match_rule("bash", {"command": "cd /tmp"}), "allow")
        self.assertIsNone(permission_rules.match_rule("powershell", {"command": "echo root"}))

    def test_prefix_star_matches_cd_commands(self) -> None:
        self._write_rules([{"tool": "bash", "pattern": {"command": "cd *"}, "decision": "allow"}])
        self.assertEqual(permission_rules.match_rule("bash", {"command": "cd /tmp"}), "allow")
        self.assertEqual(permission_rules.match_rule("bash", {"command": "cd .. && ls"}), "allow")
        self.assertIsNone(permission_rules.match_rule("bash", {"command": "echo cd /tmp"}))
        self.assertIsNone(permission_rules.match_rule("bash", {"command": "ls"}))

    def test_file_path_wildcard(self) -> None:
        self._write_rules([{"tool": "write_file", "pattern": {"file_path": "src/*"}, "decision": "deny"}])
        self.assertEqual(permission_rules.match_rule("write_file", {"file_path": "src/cli.py"}), "deny")
        self.assertIsNone(permission_rules.match_rule("write_file", {"file_path": "tests/cli.py"}))

    def test_last_matching_rule_wins(self) -> None:
        self._write_rules(
            [
                {"tool": "bash", "pattern": {"command": "*"}, "decision": "allow"},
                {"tool": "bash", "pattern": {"command": "rm *"}, "decision": "deny"},
            ]
        )
        self.assertEqual(permission_rules.match_rule("bash", {"command": "echo ok"}), "allow")
        self.assertEqual(permission_rules.match_rule("bash", {"command": "rm notes.txt"}), "deny")

    def test_embedded_star_is_a_wildcard(self) -> None:
        self._write_rules(
            [{"tool": "bash", "pattern": {"command": 'find . -name "*.py"'}, "decision": "allow"}]
        )
        self.assertEqual(permission_rules.match_rule("bash", {"command": 'find . -name "*.py"'}), "allow")
        self.assertEqual(permission_rules.match_rule("bash", {"command": 'find . -name "cli.py"'}), "allow")
        self.assertIsNone(permission_rules.match_rule("bash", {"command": 'find . -name "cli.txt"'}))

    def test_upsert_still_writes_exact_pattern(self) -> None:
        permission_rules.upsert_rule("bash", {"command": "echo ping"}, "allow")
        rules = json.loads(Path(".cda/.permission_rules/rules.json").read_text(encoding="utf-8"))
        self.assertEqual(rules, [{"tool": "bash", "pattern": {"command": "echo ping"}, "decision": "allow"}])

    def test_wildcard_pattern_derives_command_file_and_url(self) -> None:
        self.assertEqual(
            permission_rules.wildcard_pattern("bash", {"command": "cd project-folder"}),
            {"command": "cd *"},
        )
        self.assertEqual(
            permission_rules.wildcard_pattern("powershell", {"command": "ls"}),
            {"command": "ls *"},
        )
        self.assertEqual(
            permission_rules.wildcard_pattern("write_file", {"file_path": "src/cli.py", "content": "x"}),
            {"file_path": "src/*"},
        )
        self.assertEqual(
            permission_rules.wildcard_pattern("edit_file", {"file_path": "notes.txt"}),
            {"file_path": "*"},
        )
        self.assertEqual(
            permission_rules.wildcard_pattern("web_fetch", {"url": "https://example.com/docs/page"}),
            {"url": "https://example.com/*"},
        )
        self.assertEqual(
            permission_rules.wildcard_pattern("config", {"action": "set", "key": "theme"}),
            {"action": "*", "key": "*"},
        )

    def test_wildcard_label_uses_primary_field(self) -> None:
        self.assertEqual(permission_rules.wildcard_label("bash", {"command": "cd project-folder"}), "cd *")
        self.assertEqual(permission_rules.wildcard_label("bash", {}), "bash *")
        self.assertEqual(permission_rules.wildcard_label("write_file", {"file_path": "src/cli.py"}), "write_file src/*")
        self.assertEqual(permission_rules.wildcard_label("write_file", {"file_path": "notes.txt"}), "write_file *")
        self.assertEqual(
            permission_rules.wildcard_label("web_fetch", {"url": "https://example.com/docs/page"}),
            "web_fetch https://example.com/*",
        )
        self.assertEqual(permission_rules.wildcard_label("config", {"action": "set", "key": "theme"}), "config *")

    def test_upsert_rule_writes_explicit_wildcard_pattern(self) -> None:
        pattern = permission_rules.wildcard_pattern("bash", {"command": "cd project-folder"})
        permission_rules.upsert_rule("bash", {"command": "cd project-folder"}, "allow", pattern=pattern)
        rules = json.loads(Path(".cda/.permission_rules/rules.json").read_text(encoding="utf-8"))
        self.assertEqual(rules, [{"tool": "bash", "pattern": {"command": "cd *"}, "decision": "allow"}])
        self.assertEqual(permission_rules.match_rule("bash", {"command": "cd /tmp"}), "allow")
        self.assertIsNone(permission_rules.match_rule("bash", {"command": "echo ping"}))

    def test_ensure_default_rules_writes_baseline_when_missing(self) -> None:
        target = Path(".cda/.permission_rules/rules.json")
        self.assertFalse(target.exists())
        created = permission_rules.ensure_default_rules(Path.cwd())
        self.assertEqual(created, Path.cwd() / target)
        self.assertTrue(target.is_file())
        rules = json.loads(target.read_text(encoding="utf-8"))
        self.assertTrue(any(rule.get("pattern") == {"command": "*sudo*"} for rule in rules))
        self.assertTrue(all(rule.get("decision") == "deny" for rule in rules))

    def test_ensure_default_rules_does_not_overwrite_existing(self) -> None:
        existing = [{"tool": "bash", "pattern": {"command": "echo ping"}, "decision": "allow"}]
        self._write_rules(existing)
        permission_rules.ensure_default_rules(Path.cwd())
        rules = json.loads(Path(".cda/.permission_rules/rules.json").read_text(encoding="utf-8"))
        self.assertEqual(rules, existing)


if __name__ == "__main__":
    unittest.main()
