import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch

from src.tools import invoke, registry
from src.tools.permissions import AuthorizeDecision, AuthorizeOption


class TestAuthorizeOption(unittest.TestCase):
    def test_from_response_maps_each_option(self) -> None:
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.ALLOW_ONCE),
            AuthorizeDecision(allow=True, persist=False),
        )
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.ALLOW_ALWAYS),
            AuthorizeDecision(allow=True, persist=True),
        )
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.DENY_ONCE),
            AuthorizeDecision(allow=False, persist=False),
        )
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.DENY_ALWAYS),
            AuthorizeDecision(allow=False, persist=True),
        )

    def test_from_response_unknown_is_deny_once(self) -> None:
        for bad in ("", "a", "approve", "other", "yes", "no"):
            with self.subTest(bad=bad):
                self.assertEqual(
                    AuthorizeDecision.from_response(bad),
                    AuthorizeDecision(allow=False, persist=False),
                )


class TestPermissionGateHardDeny(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    @patch("subprocess.run")
    def test_bash_sudo_hard_denied_with_bypass_and_no_subprocess(self, mock_run) -> None:
        # AC-001 / REQ-006, REQ-007, REQ-015 / T-001
        result = invoke("bash", command="sudo rm -rf /tmp/x", bypass_permissions=True)
        self.assertEqual(result.get("status"), "error")
        error_msg = str(result.get("error"))
        self.assertIn("Blocked:", error_msg)
        self.assertIn("sudo", error_msg)
        mock_run.assert_not_called()

    def test_powershell_shutdown_hard_denied(self) -> None:
        # AC-002 / REQ-006, REQ-007 / T-001
        result = invoke("powershell", command="shutdown /s", bypass_permissions=True)
        self.assertEqual(result.get("status"), "error")
        error_msg = str(result.get("error"))
        self.assertIn("Blocked:", error_msg)
        self.assertIn("shutdown", error_msg)

    def test_bash_non_deny_with_bypass_succeeds(self) -> None:
        # AC-003 / REQ-006 / T-001
        result = invoke("bash", command="echo ping", bypass_permissions=True)
        self.assertNotEqual(result.get("status"), "error")
        self.assertIn("ping", result["result"]["stdout"])

    def test_bash_without_bypass_permission_denied(self) -> None:
        # AC-004 / REQ-012 / T-001
        result = invoke("bash", command="echo ping")
        self.assertEqual(result.get("status"), "error")
        self.assertIn("Permission denied for high-risk tool", str(result.get("error")))

    def test_repl_code_with_sudo_not_deny_listed(self) -> None:
        # AC-005 / REQ-009 / T-001
        result = invoke("repl", code="sudo = 1", bypass_permissions=True)
        self.assertNotEqual(result.get("status"), "error")
        self.assertNotIn("Blocked:", str(result))

    @patch("subprocess.run")
    def test_all_seven_deny_list_patterns_blocked(self, mock_run) -> None:
        # AC-017 / REQ-006, REQ-015 / T-001
        patterns = (
            "rm -rf /",
            "sudo",
            "shutdown",
            "reboot",
            "mkfs",
            "dd if=",
            "> /dev/sda",
        )
        for pattern in patterns:
            with self.subTest(pattern=pattern):
                cmd = f"echo safe && {pattern} /var"
                result = invoke("bash", command=cmd, bypass_permissions=True)
                self.assertEqual(result.get("status"), "error")
                error_msg = str(result.get("error"))
                self.assertIn("Blocked:", error_msg)
                self.assertIn(pattern, error_msg)
        mock_run.assert_not_called()

    def test_write_file_env_hard_denied_not_written(self) -> None:
        # AC-006 / REQ-010 / T-002
        result = invoke("write_file", file_path=".env", content="x")
        self.assertEqual(result.get("status"), "error")
        self.assertIn("Protected path blocked:", str(result.get("error")))
        self.assertFalse(Path(".env").exists())

    def test_config_set_protected_key_hard_denied(self) -> None:
        # AC-007 / REQ-011 / T-002
        result = invoke("config", action="set", key="secret", value="n")
        self.assertEqual(result.get("status"), "error")

    def test_config_get_protected_key_not_hard_denied(self) -> None:
        # AC-007 / REQ-011 / T-002
        result = invoke("config", action="get", key="secret")
        self.assertEqual(result.get("status"), "success")

    def test_config_set_protected_path_key_hard_denied(self) -> None:
        # AC-006 / REQ-010 / T-002
        result = invoke("config", action="set", key=".gitconfig", value="n")
        self.assertEqual(result.get("status"), "error")
        self.assertIn("Protected path blocked:", str(result.get("error")))


class TestToolsDispatch(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)
        Path("hello.txt").write_text("hello\n", encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def test_read_file_in_cwd(self) -> None:
        # AC-001 / T-001
        result = invoke("read_file", file_path="hello.txt")
        self.assertNotEqual(result.get("status"), "error")
        self.assertIn("hello", str(result.get("result")))

    def test_write_and_edit_file_in_cwd(self) -> None:
        # AC-001 / T-001
        written = invoke("write_file", file_path="note.txt", content="alpha")
        self.assertNotEqual(written.get("status"), "error")
        self.assertEqual(Path("note.txt").read_text(encoding="utf-8"), "alpha")
        edited = invoke("edit_file", file_path="note.txt", old_string="alpha", new_string="beta")
        self.assertNotEqual(edited.get("status"), "error")
        self.assertEqual(Path("note.txt").read_text(encoding="utf-8"), "beta")

    def test_bash_in_cwd(self) -> None:
        # AC-001 / T-001
        result = invoke("bash", command="echo ping", bypass_permissions=True)
        self.assertNotEqual(result.get("status"), "error")
        self.assertIn("ping", result["result"]["stdout"])

    def test_glob_and_glob_search_same_matches(self) -> None:
        # AC-002 / T-001
        glob_search = invoke("glob_search", pattern="*.txt")
        glob_alias = invoke("glob", pattern="*.txt")
        self.assertNotEqual(glob_search.get("status"), "error")
        self.assertNotEqual(glob_alias.get("status"), "error")
        self.assertEqual(set(glob_search["result"]), set(glob_alias["result"]))
        self.assertTrue(any(str(item).endswith("hello.txt") for item in glob_search["result"]))

    def test_schemas_include_glob_and_glob_search(self) -> None:
        # AC-003 / T-001
        names = {item["name"] for item in registry.list_schemas()}
        self.assertIn("glob", names)
        self.assertIn("glob_search", names)

    def test_extra_grep_search_still_registered(self) -> None:
        # AC-005 / T-001
        names = {item["name"] for item in registry.list_schemas()}
        self.assertIn("grep_search", names)
        result = invoke("grep_search", pattern="hello")
        self.assertNotEqual(result.get("status"), "error")
        self.assertTrue(any("hello" in str(item) for item in result["result"]))


class TestWorkspaceBound(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        base = Path(self._temp.name)
        self.project = base / "proj"
        self.project.mkdir()
        self.secret = base / "secret.txt"
        self.secret.write_text("outside-secret\n", encoding="utf-8")
        os.chdir(self.project)
        Path("hello.txt").write_text("hello\n", encoding="utf-8")
        Path("escape.txt").symlink_to(self.secret)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def test_file_and_search_refuse_parent_path(self) -> None:
        # AC-006 / T-002
        escape = f"../{self.secret.name}"
        write_escape = "../should-not-write.txt"
        for name, kwargs in (
            ("read_file", {"file_path": escape}),
            ("write_file", {"file_path": write_escape, "content": "nope"}),
            ("edit_file", {"file_path": escape, "old_string": "outside-secret", "new_string": "changed"}),
            ("glob_search", {"pattern": "*.txt", "path": ".."}),
            ("glob", {"pattern": "*.txt", "path": ".."}),
            ("grep_search", {"pattern": "outside-secret", "path": ".."}),
        ):
            with self.subTest(name=name):
                result = invoke(name, **kwargs)
                self.assertEqual(result.get("status"), "error", result)
        self.assertEqual(self.secret.read_text(encoding="utf-8"), "outside-secret\n")
        self.assertFalse((self.project.parent / "should-not-write.txt").exists())

    def test_symlink_escape_is_refused(self) -> None:
        # AC-006 / T-002
        result = invoke("read_file", file_path="escape.txt")
        self.assertEqual(result.get("status"), "error")
        self.assertNotIn("outside-secret", str(result))

    def test_in_cwd_paths_still_succeed(self) -> None:
        # AC-007 / T-002
        self.assertNotEqual(invoke("read_file", file_path="hello.txt").get("status"), "error")
        self.assertNotEqual(invoke("write_file", file_path="note.txt", content="alpha").get("status"), "error")
        self.assertNotEqual(
            invoke("edit_file", file_path="note.txt", old_string="alpha", new_string="beta").get("status"),
            "error",
        )
        self.assertNotEqual(invoke("glob_search", pattern="*.txt").get("status"), "error")
        self.assertNotEqual(invoke("glob", pattern="*.txt").get("status"), "error")
        self.assertNotEqual(invoke("grep_search", pattern="hello").get("status"), "error")

    def test_bash_is_not_workspace_jailed(self) -> None:
        # AC-008 / T-002
        result = invoke("bash", command=f"cat {self.secret}", bypass_permissions=True)
        self.assertNotEqual(result.get("status"), "error")
        self.assertIn("outside-secret", result["result"]["stdout"])


if __name__ == "__main__":
    unittest.main()

