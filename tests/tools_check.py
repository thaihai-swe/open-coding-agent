import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools import invoke, registry


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

