import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch

from src.tools import invoke, registry
from src.tools.permissions import AuthorizeDecision, AuthorizeOption
from src.tools.prompt import (
    FALLBACK_SECTIONS,
    INSTRUCTION_FILENAMES,
    MAX_FILE_CHARS,
    MAX_TOTAL_INSTRUCTION_CHARS,
    assemble_system_prompt,
    discover_instructions,
    format_security_section,
    format_tools_section,
    load_prompt_section,
)
from src.tools.skills import (
    build_system_message,
    expand_slash_prompt,
    format_catalog,
    load_skill_content,
    parse_frontmatter,
    scan_skills,
)
from src.tools.task_board import SYSTEM_MESSAGE


class TestAuthorizeOption(unittest.TestCase):
    def test_from_response_maps_each_option(self) -> None:
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.ALLOW_ONCE),
            AuthorizeDecision(allow=True, persist=False, persist_pattern=False),
        )
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.ALLOW_ALWAYS),
            AuthorizeDecision(allow=True, persist=True, persist_pattern=False),
        )
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.ALLOW_PATTERN),
            AuthorizeDecision(allow=True, persist=True, persist_pattern=True),
        )
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.DENY_ONCE),
            AuthorizeDecision(allow=False, persist=False, persist_pattern=False),
        )
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.DENY_ALWAYS),
            AuthorizeDecision(allow=False, persist=True, persist_pattern=False),
        )
        self.assertEqual(
            AuthorizeDecision.from_response(AuthorizeOption.DENY_PATTERN),
            AuthorizeDecision(allow=False, persist=True, persist_pattern=True),
        )

    def test_from_response_unknown_is_deny_once(self) -> None:
        for bad in ("", "a", "approve", "other", "yes", "no", "7"):
            with self.subTest(bad=bad):
                self.assertEqual(
                    AuthorizeDecision.from_response(bad),
                    AuthorizeDecision(allow=False, persist=False, persist_pattern=False),
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


class TestPlanningBoard(unittest.TestCase):
    PLANNING = (
        "create_task",
        "list_tasks",
        "get_task",
        "claim_task",
        "complete_task",
        "cancel_task",
    )

    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def test_six_planning_tools_registered_and_todo_write_gone(self) -> None:
        # AC-001 / REQ-001, REQ-002 / T-001
        names = {item["name"] for item in registry.list_schemas()}
        self.assertNotIn("todo_write", names)
        self.assertIsNone(registry.get("todo_write"))
        for name in self.PLANNING:
            tool = registry.get(name)
            self.assertIsNotNone(tool, name)
            self.assertEqual(tool.category, "Planning")
            self.assertEqual(tool.risk_level, "LOW")
        self.assertIn("grep_search", names)

    def test_todo_write_invoke_is_unknown(self) -> None:
        # AC-002 / REQ-002 / T-001
        result = invoke("todo_write", todos=[])
        self.assertEqual(result.get("status"), "error")
        self.assertIn("Unknown tool", str(result.get("error")))

    def test_create_task_persists_pending_to_default_json(self) -> None:
        # AC-003 / REQ-003, REQ-004, REQ-006 / T-001
        result = invoke("create_task", content="Write tests")
        self.assertEqual(result.get("status"), "success", result)
        payload = result["result"]
        self.assertTrue(payload["id"])
        self.assertEqual(payload["content"], "Write tests")
        self.assertEqual(payload["status"], "pending")
        self.assertIsInstance(payload["tasks"], list)
        path = Path(".cda/.todos/default.json")
        self.assertTrue(path.is_file())
        self.assertFalse(Path(".todos").exists())
        self.assertFalse(Path(".tasks").exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data, [{"id": payload["id"], "content": "Write tests", "status": "pending"}])
        self.assertEqual(payload["tasks"], data)

    def test_list_and_get_task(self) -> None:
        # AC-004 / REQ-007, REQ-008 / T-001
        created = invoke("create_task", content="Write tests")["result"]
        listed = invoke("list_tasks")
        self.assertEqual(listed.get("status"), "success", listed)
        self.assertEqual(
            listed["result"],
            [{"id": created["id"], "content": "Write tests", "status": "pending"}],
        )
        got = invoke("get_task", id=created["id"])
        self.assertEqual(got.get("status"), "success", got)
        self.assertEqual(got["result"], {"id": created["id"], "content": "Write tests", "status": "pending"})
        self.assertNotIn("tasks", got["result"])

    def test_empty_or_missing_content_is_error(self) -> None:
        # AC-011 / REQ-006 / T-001
        missing = invoke("create_task")
        self.assertEqual(missing.get("status"), "error")
        empty = invoke("create_task", content="")
        self.assertEqual(empty.get("status"), "error")
        blank = invoke("create_task", content="   ")
        self.assertEqual(blank.get("status"), "error")
        self.assertFalse(Path(".cda/.todos/default.json").exists())

    def test_missing_or_invalid_file_is_empty_list(self) -> None:
        # AC-016 / REQ-004 / T-001
        missing = invoke("list_tasks")
        self.assertEqual(missing.get("status"), "success", missing)
        self.assertEqual(missing["result"], [])
        path = Path(".cda/.todos/default.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"not": "an array"}', encoding="utf-8")
        invalid = invoke("list_tasks")
        self.assertEqual(invalid.get("status"), "success", invalid)
        self.assertEqual(invalid["result"], [])

    def _todos_file(self) -> Path:
        return Path(".cda/.todos/default.json")

    def _disk(self) -> list:
        path = self._todos_file()
        if not path.is_file():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def test_unknown_id_is_error_and_unchanged(self) -> None:
        # AC-005 / REQ-008, REQ-009, REQ-010, REQ-011 / T-002
        created = invoke("create_task", content="Write tests")["result"]
        before = self._disk()
        for name in ("get_task", "claim_task", "complete_task", "cancel_task"):
            with self.subTest(name=name):
                result = invoke(name, id="missing-id")
                self.assertEqual(result.get("status"), "error", result)
                self.assertEqual(self._disk(), before)
        self.assertEqual(created["id"] in {item["id"] for item in before}, True)

    def test_claim_then_complete_stays_on_board(self) -> None:
        # AC-006 / REQ-009, REQ-010 / T-002
        task_id = invoke("create_task", content="Write tests")["result"]["id"]
        claimed = invoke("claim_task", id=task_id)
        self.assertEqual(claimed.get("status"), "success", claimed)
        self.assertEqual(claimed["result"]["status"], "in_progress")
        self.assertEqual(self._disk()[0]["status"], "in_progress")
        done = invoke("complete_task", id=task_id)
        self.assertEqual(done.get("status"), "success", done)
        self.assertEqual(done["result"]["status"], "completed")
        self.assertEqual(self._disk(), [{"id": task_id, "content": "Write tests", "status": "completed"}])

    def test_complete_pending_without_claim(self) -> None:
        # AC-007 / REQ-010 / T-002
        task_id = invoke("create_task", content="Write tests")["result"]["id"]
        done = invoke("complete_task", id=task_id)
        self.assertEqual(done.get("status"), "success", done)
        self.assertEqual(self._disk()[0]["status"], "completed")

    def test_illegal_claim_and_complete_do_not_mutate(self) -> None:
        # AC-008 / REQ-009, REQ-010 / T-002
        task_id = invoke("create_task", content="Write tests")["result"]["id"]
        invoke("claim_task", id=task_id)
        again = invoke("claim_task", id=task_id)
        self.assertEqual(again.get("status"), "error", again)
        self.assertEqual(self._disk()[0]["status"], "in_progress")
        invoke("complete_task", id=task_id)
        complete_again = invoke("complete_task", id=task_id)
        self.assertEqual(complete_again.get("status"), "error", complete_again)
        claim_done = invoke("claim_task", id=task_id)
        self.assertEqual(claim_done.get("status"), "error", claim_done)
        self.assertEqual(self._disk()[0]["status"], "completed")

    def test_two_claims_both_in_progress(self) -> None:
        # AC-009 / REQ-009, REQ-012 / T-002
        first = invoke("create_task", content="A")["result"]["id"]
        second = invoke("create_task", content="B")["result"]["id"]
        self.assertEqual(invoke("claim_task", id=first).get("status"), "success")
        self.assertEqual(invoke("claim_task", id=second).get("status"), "success")
        statuses = {item["id"]: item["status"] for item in self._disk()}
        self.assertEqual(statuses[first], "in_progress")
        self.assertEqual(statuses[second], "in_progress")

    def test_cancel_removes_pending_and_completed(self) -> None:
        # AC-010 / REQ-011 / T-002
        pending_id = invoke("create_task", content="pending item")["result"]["id"]
        done_id = invoke("create_task", content="done item")["result"]["id"]
        invoke("complete_task", id=done_id)
        self.assertEqual(invoke("cancel_task", id=pending_id).get("status"), "success")
        ids = {item["id"] for item in self._disk()}
        self.assertNotIn(pending_id, ids)
        self.assertIn(done_id, ids)
        cancelled = invoke("cancel_task", id=done_id)
        self.assertEqual(cancelled.get("status"), "success", cancelled)
        self.assertEqual(self._disk(), [])
        self.assertEqual(cancelled["result"]["id"], done_id)
        self.assertEqual(cancelled["result"]["tasks"], [])

    def test_duplicate_id_on_create_is_error(self) -> None:
        # AC-012 / REQ-006 / T-002
        created = invoke("create_task", content="original", id="t1")
        self.assertEqual(created.get("status"), "success", created)
        dup = invoke("create_task", content="new content", id="t1")
        self.assertEqual(dup.get("status"), "error", dup)
        self.assertEqual(self._disk(), [{"id": "t1", "content": "original", "status": "pending"}])


class TestSkillDiscovery(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)
        self.project = Path(self._temp.name) / ".agents" / "skills"
        self.global_root = Path(self._temp.name) / "home" / ".agents" / "skills"

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def _write_skill(self, root: Path, folder: str, text: str) -> Path:
        path = root / folder / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_scan_project_skill_with_frontmatter(self) -> None:
        # AC-001 / REQ-001, REQ-002, REQ-003 / T-001
        body = "---\nname: my-skill\ndescription: A custom skill\n---\nDo the work.\n"
        self._write_skill(self.project, "my-skill", body)
        skills = scan_skills(project_root=self.project, global_root=self.global_root)
        self.assertIn("my-skill", skills)
        self.assertEqual(skills["my-skill"]["name"], "my-skill")
        self.assertEqual(skills["my-skill"]["description"], "A custom skill")
        self.assertEqual(skills["my-skill"]["content"], body)

    def test_project_skill_overrides_global(self) -> None:
        # AC-002 / REQ-005 / T-001
        self._write_skill(
            self.global_root,
            "shared",
            "---\nname: shared\ndescription: Global copy\n---\nGlobal body.\n",
        )
        project_body = "---\nname: shared\ndescription: Project copy\n---\nProject body.\n"
        self._write_skill(self.project, "shared", project_body)
        skills = scan_skills(project_root=self.project, global_root=self.global_root)
        self.assertEqual(skills["shared"]["description"], "Project copy")
        self.assertEqual(skills["shared"]["content"], project_body)

    def test_missing_frontmatter_uses_folder_and_heading(self) -> None:
        # AC-003 / REQ-004 / T-001
        self._write_skill(self.project, "docs", "# Document Helper\n\nHelp with docs.\n")
        skills = scan_skills(project_root=self.project, global_root=self.global_root)
        self.assertEqual(skills["docs"]["name"], "docs")
        self.assertEqual(skills["docs"]["description"], "Document Helper")

    def test_parse_frontmatter_when_to_use_and_quotes(self) -> None:
        # REQ-003 / T-001
        meta, body = parse_frontmatter(
            '---\nname: "sql-style"\ndescription: \'SQL guide\'\nwhen_to_use: writing queries\n---\nBody.\n',
            "fallback",
        )
        self.assertEqual(meta["name"], "sql-style")
        self.assertEqual(meta["description"], "SQL guide")
        self.assertEqual(meta["when_to_use"], "writing queries")
        self.assertEqual(body, "Body.\n")

    def test_skip_directory_without_skill_md(self) -> None:
        # REQ-002 / T-001
        (self.project / "empty").mkdir(parents=True)
        skills = scan_skills(project_root=self.project, global_root=self.global_root)
        self.assertEqual(skills, {})

    def test_format_catalog_empty_and_named(self) -> None:
        # REQ-011 / T-001
        self.assertEqual(format_catalog({}), "Skills available:\n(no skills found)")
        text = format_catalog(
            {
                "pdf": {"name": "pdf", "description": "PDF helper", "when_to_use": "reading PDFs"},
                "sql": {"name": "sql", "description": "SQL style"},
            }
        )
        self.assertIn("Skills available:", text)
        self.assertIn("- **pdf**: PDF helper (when to use: reading PDFs)", text)
        self.assertIn("- **sql**: SQL style", text)
        self.assertIn("Use load_skill to get full details when needed.", text)

    def test_load_skill_content_and_build_system_message(self) -> None:
        # REQ-007, REQ-010 / T-001
        body = "---\nname: tester\ndescription: Tester\n---\nFull text.\n"
        self._write_skill(self.project, "tester", body)
        skills = scan_skills(project_root=self.project, global_root=self.global_root)
        self.assertEqual(load_skill_content("tester", skills), body)
        with self.assertRaises(ValueError) as raised:
            load_skill_content("missing-skill", skills)
        self.assertIn("Skill not found: missing-skill", str(raised.exception))
        message = build_system_message(skills)
        self.assertIn(SYSTEM_MESSAGE, message)
        self.assertIn("Skills available:", message)
        self.assertIn("- **tester**: Tester", message)

    def test_expand_slash_prompt(self) -> None:
        # REQ-013 / T-001
        skills = {"code-review": {"name": "code-review", "content": "BODY"}}
        expanded, error = expand_slash_prompt("/code-review please check line 10", skills)
        self.assertIsNone(error)
        self.assertEqual(expanded, '<skill name="code-review">\nBODY\n</skill>\nplease check line 10')
        bare, bare_error = expand_slash_prompt("/code-review", skills)
        self.assertIsNone(bare_error)
        self.assertEqual(bare, '<skill name="code-review">\nBODY\n</skill>')
        missing, missing_error = expand_slash_prompt("/foo", skills)
        self.assertIsNone(missing)
        self.assertEqual(missing_error, "Unknown skill: /foo")
        passthrough, passthrough_error = expand_slash_prompt("hello", skills)
        self.assertEqual(passthrough, "hello")
        self.assertIsNone(passthrough_error)

    def test_load_skill_tool_registered_and_old_skill_stub_removed(self) -> None:
        # AC-004 / REQ-006, REQ-009, REQ-014 / T-002
        tool = registry.get("load_skill")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.category, "Agent")
        self.assertEqual(tool.risk_level, "LOW")
        self.assertEqual(tool.schema.get("required"), ["name"])
        self.assertEqual(tool.schema.get("properties", {}).get("name", {}).get("type"), "string")
        self.assertIsNone(registry.get("skill"))

    def test_invoke_load_skill_success(self) -> None:
        # AC-005 / REQ-007 / T-002
        body = "---\nname: tester\ndescription: Tester\n---\nFull content of tester.\n"
        self._write_skill(self.project, "tester", body)
        res = invoke("load_skill", name="tester")
        self.assertEqual(res.get("status"), "success", res)
        self.assertEqual(res.get("result"), body)

    def test_invoke_load_skill_missing_error(self) -> None:
        # AC-006 / REQ-008 / T-002
        res = invoke("load_skill", name="missing-skill")
        self.assertEqual(res.get("status"), "error", res)
        self.assertIn("Skill not found: missing-skill", str(res.get("error")))

    def test_invoke_load_skill_path_traversal_safe(self) -> None:
        # AC-007 / REQ-007, REQ-008 / T-002
        res = invoke("load_skill", name="../../etc/passwd")
        self.assertEqual(res.get("status"), "error", res)
        self.assertIn("Skill not found: ../../etc/passwd", str(res.get("error")))

    def test_invoke_old_skill_stub_returns_unknown_tool(self) -> None:
        # AC-008 / REQ-009 / T-002
        res = invoke("skill", skill="known")
        self.assertEqual(res.get("status"), "error", res)
        self.assertIn("Unknown tool: skill", str(res.get("error")))


class TestPromptAssembler(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def test_discover_instructions_order_and_content(self) -> None:
        # AC-005, AC-016 / REQ-009 / T-001
        Path("CLAUDE.md").write_text("CLAUDE content", encoding="utf-8")
        Path("AGENTS.md").write_text("AGENTS content", encoding="utf-8")
        instructions = discover_instructions(Path.cwd())
        names = [name for name, _ in instructions]
        self.assertEqual(names, ["AGENTS.md", "CLAUDE.md"])
        self.assertEqual(instructions[0], ("AGENTS.md", "AGENTS content"))
        self.assertEqual(instructions[1], ("CLAUDE.md", "CLAUDE content"))

    def test_discover_instructions_empty_when_no_files(self) -> None:
        # AC-006 / REQ-012 / T-001
        instructions = discover_instructions(Path.cwd())
        self.assertEqual(instructions, [])

    def test_discover_instructions_deduplicates_identical_content(self) -> None:
        # AC-007 / REQ-010 / T-001
        Path("AGENTS.md").write_text("DUP-BODY", encoding="utf-8")
        Path("CLAUDE.md").write_text("DUP-BODY", encoding="utf-8")
        instructions = discover_instructions(Path.cwd())
        self.assertEqual(len(instructions), 1)
        self.assertEqual(instructions[0], ("AGENTS.md", "DUP-BODY"))

    def test_discover_instructions_per_file_capping_4000(self) -> None:
        # AC-008 / REQ-011 / T-001
        long_body = "A" * 5000
        Path("AGENTS.md").write_text(long_body, encoding="utf-8")
        instructions = discover_instructions(Path.cwd())
        self.assertEqual(len(instructions), 1)
        filename, body = instructions[0]
        self.assertEqual(filename, "AGENTS.md")
        self.assertTrue(body.startswith("A" * 4000))
        self.assertIn("TRUNCATED", body)
        # Ensure raw file text portion is at most 4000
        self.assertEqual(body[:4000], "A" * 4000)

    def test_discover_instructions_total_capping_12000(self) -> None:
        # AC-009 / REQ-011 / T-001
        Path("AGENTS.md").write_text("A" * 4000, encoding="utf-8")
        Path("CLAUDE.md").write_text("B" * 4000, encoding="utf-8")
        Path("CLAUDE.local.md").write_text("C" * 5000, encoding="utf-8")
        instructions = discover_instructions(Path.cwd())
        self.assertEqual(len(instructions), 3)
        # First two kept in full (4000 each)
        self.assertEqual(instructions[0][1], "A" * 4000)
        self.assertEqual(instructions[1][1], "B" * 4000)
        # Third file capped to remaining 4000 budget
        self.assertTrue(instructions[2][1].startswith("C" * 4000))
        self.assertIn("TRUNCATED", instructions[2][1])

    def test_discover_instructions_unreadable_file_skipped_without_crash(self) -> None:
        # AC-017 / REQ-009 / T-001
        # Create unreadable non-utf8 binary file
        Path("AGENTS.md").write_bytes(b"\xff\xfe\x00\x00\x80\x90")
        Path("CLAUDE.md").write_text("Valid claude", encoding="utf-8")
        instructions = discover_instructions(Path.cwd())
        self.assertEqual(len(instructions), 1)
        self.assertEqual(instructions[0], ("CLAUDE.md", "Valid claude"))

    def test_format_tools_section_lists_names_and_no_properties(self) -> None:
        # AC-010 / REQ-007 / T-001
        text = format_tools_section()
        self.assertIn("- bash:", text)
        self.assertIn("- load_skill:", text)
        self.assertIn("- create_task:", text)
        self.assertNotIn('"properties"', text)

    def test_format_security_section_mentions_policies(self) -> None:
        # AC-011 / REQ-008 / T-001
        text = format_security_section()
        self.assertTrue(
            "working directory" in text.lower()
            or "workspace" in text.lower()
        )
        self.assertTrue("deny" in text.lower() or "blocked" in text.lower())
        self.assertTrue("protected" in text.lower())
        self.assertTrue("approval" in text.lower() or "authorization" in text.lower())

    def test_assemble_system_prompt_structure_and_order(self) -> None:
        # AC-004, AC-005, AC-006 / REQ-002, REQ-003, REQ-004, REQ-005 / T-001
        Path("AGENTS.md").write_text("REPO-RULE-ALPHA", encoding="utf-8")
        prompt = assemble_system_prompt(cwd=Path.cwd())
        
        # Verify identity
        self.assertIn("You are a coding agent.", prompt)
        # Verify workspace
        resolved_cwd = str(Path.cwd().resolve())
        self.assertIn(f"Working directory: {resolved_cwd}", prompt)
        # Verify Feature 3 planning
        self.assertIn(SYSTEM_MESSAGE, prompt)
        # Verify Security
        self.assertIn("Security & Permission Policies:", prompt)
        # Verify Tools
        self.assertIn("Available tools:", prompt)
        # Verify Skills
        self.assertIn("Skills available:", prompt)
        # Verify Instructions
        self.assertIn("Instructions:", prompt)
        self.assertIn("### AGENTS.md", prompt)
        self.assertIn("REPO-RULE-ALPHA", prompt)

        # Verify ordering: Identity -> Workspace -> Planning -> Security -> Tools -> Skills -> Instructions
        idx_id = prompt.index("You are a coding agent.")
        idx_ws = prompt.index("Working directory:")
        idx_pl = prompt.index(SYSTEM_MESSAGE)
        idx_sec = prompt.index("Security & Permission Policies:")
        idx_tls = prompt.index("Available tools:")
        idx_skl = prompt.index("Skills available:")
        idx_ins = prompt.index("Instructions:")
        self.assertTrue(idx_id < idx_ws < idx_pl < idx_sec < idx_tls < idx_skl < idx_ins)

    def test_assemble_system_prompt_omits_instruction_section_when_empty(self) -> None:
        # AC-006 / REQ-012 / T-001
        prompt = assemble_system_prompt(cwd=Path.cwd())
        self.assertNotIn("Instructions:", prompt)
        self.assertNotIn("### AGENTS.md", prompt)

    def test_load_prompt_section_uses_bundled_defaults(self) -> None:
        self.assertEqual(
            load_prompt_section("identity", Path.cwd()),
            "You are a coding agent. Act, don't explain.",
        )
        self.assertEqual(load_prompt_section("planning", Path.cwd()), SYSTEM_MESSAGE)
        self.assertIn("Security & Permission Policies:", load_prompt_section("security", Path.cwd()))

    def test_load_prompt_section_prefers_project_override(self) -> None:
        override_dir = Path(".cda") / "prompts"
        override_dir.mkdir(parents=True)
        (override_dir / "identity.md").write_text("OVERRIDE-IDENTITY\n", encoding="utf-8")
        (override_dir / "planning.md").write_text("OVERRIDE-PLANNING", encoding="utf-8")
        (override_dir / "security.md").write_text("OVERRIDE-SECURITY", encoding="utf-8")
        self.assertEqual(load_prompt_section("identity", Path.cwd()), "OVERRIDE-IDENTITY")
        self.assertEqual(load_prompt_section("planning", Path.cwd()), "OVERRIDE-PLANNING")
        self.assertEqual(load_prompt_section("security", Path.cwd()), "OVERRIDE-SECURITY")
        prompt = assemble_system_prompt(cwd=Path.cwd())
        self.assertIn("OVERRIDE-IDENTITY", prompt)
        self.assertIn("OVERRIDE-PLANNING", prompt)
        self.assertIn("OVERRIDE-SECURITY", prompt)
        self.assertNotIn("You are a coding agent.", prompt)

    def test_load_prompt_section_unreadable_override_falls_back(self) -> None:
        override_dir = Path(".cda") / "prompts"
        override_dir.mkdir(parents=True)
        (override_dir / "identity.md").write_bytes(b"\xff\xfe\x00\x00")
        self.assertEqual(
            load_prompt_section("identity", Path.cwd()),
            "You are a coding agent. Act, don't explain.",
        )

    def test_load_prompt_section_empty_override_falls_back(self) -> None:
        override_dir = Path(".cda") / "prompts"
        override_dir.mkdir(parents=True)
        (override_dir / "identity.md").write_text("\n", encoding="utf-8")
        self.assertEqual(
            load_prompt_section("identity", Path.cwd()),
            FALLBACK_SECTIONS["identity"],
        )

    def test_load_prompt_section_unknown_name_is_empty(self) -> None:
        self.assertEqual(load_prompt_section("not-a-section", Path.cwd()), "")

    def test_prompt_override_appears_on_next_assemble_without_restart(self) -> None:
        first = assemble_system_prompt(cwd=Path.cwd())
        self.assertIn("You are a coding agent.", first)
        override_dir = Path(".cda") / "prompts"
        override_dir.mkdir(parents=True)
        (override_dir / "identity.md").write_text("MID-SESSION-IDENTITY", encoding="utf-8")
        second = assemble_system_prompt(cwd=Path.cwd())
        self.assertIn("MID-SESSION-IDENTITY", second)
        self.assertNotIn("You are a coding agent.", second)


class TestCompactConfig(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def test_ac001_missing_config_uses_defaults(self) -> None:
        from src.tools.config import load_config, resolve_compact_config, resolve_show_tool_results

        self.assertEqual(load_config(Path.cwd()), {})
        compact = resolve_compact_config(load_config(Path.cwd()))
        self.assertTrue(resolve_show_tool_results(None, Path.cwd()))
        self.assertTrue(compact["auto_compact"])
        self.assertEqual(compact["max_messages"], 50)
        self.assertEqual(compact["max_chars"], 80000)
        self.assertEqual(compact["keep_head"], 3)
        self.assertEqual(compact["keep_recent"], 4)
        self.assertEqual(compact["keep_recent_tool_results"], 3)
        self.assertEqual(compact["tool_result_max_bytes"], 200000)
        self.assertEqual(compact["persist_preview_chars"], 2000)
        self.assertEqual(compact["reactive_retries"], 1)
        self.assertEqual(compact["compact_fail_retries"], 3)

    def test_ac002_config_json_overrides_selected_keys(self) -> None:
        from src.tools.config import load_config, resolve_compact_config, resolve_show_tool_results

        Path(".cda").mkdir()
        Path(".cda/config.json").write_text(
            json.dumps({"show_tool_results": False, "compact": {"max_messages": 10}}),
            encoding="utf-8",
        )
        cfg = load_config(Path.cwd())
        compact = resolve_compact_config(cfg)
        self.assertFalse(resolve_show_tool_results(None, Path.cwd()))
        self.assertEqual(compact["max_messages"], 10)
        self.assertEqual(compact["max_chars"], 80000)

    def test_ensure_default_config_writes_best_defaults_when_missing(self) -> None:
        from src.tools.config import DEFAULT_CONFIG, DEFAULT_COMPACT_CONFIG, ensure_default_config, load_config

        target = Path.cwd() / ".cda" / "config.json"
        self.assertFalse(target.exists())
        created = ensure_default_config(Path.cwd())
        self.assertEqual(created, target)
        self.assertTrue(target.is_file())
        cfg = load_config(Path.cwd())
        self.assertEqual(cfg["show_tool_results"], DEFAULT_CONFIG["show_tool_results"])
        self.assertEqual(cfg["compact"], DEFAULT_COMPACT_CONFIG)

    def test_ensure_default_config_does_not_overwrite_existing(self) -> None:
        from src.tools.config import ensure_default_config, load_config

        Path(".cda").mkdir()
        Path(".cda/config.json").write_text(
            json.dumps({"show_tool_results": False, "compact": {"max_messages": 10}}),
            encoding="utf-8",
        )
        ensure_default_config(Path.cwd())
        cfg = load_config(Path.cwd())
        self.assertFalse(cfg["show_tool_results"])
        self.assertEqual(cfg["compact"]["max_messages"], 10)

    def test_ac020_compact_prompt_bundled_and_override(self) -> None:
        bundled = load_prompt_section("compact", Path.cwd())
        self.assertTrue(bundled)
        override_dir = Path(".cda") / "prompts"
        override_dir.mkdir(parents=True)
        (override_dir / "compact.md").write_text("OVERRIDE-COMPACT-PROMPT", encoding="utf-8")
        self.assertEqual(load_prompt_section("compact", Path.cwd()), "OVERRIDE-COMPACT-PROMPT")


class TestCompactTransformers(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def test_ac004_tool_result_budget_persists_large_outputs(self) -> None:
        from src.domain.models import ChatMessage, ToolResult
        from src.tools.compact import tool_result_budget

        huge = "X" * 250000
        history = [
            ChatMessage("user", "read it"),
            ChatMessage("assistant", "ok"),
            ChatMessage("tool", tool_result=ToolResult("call-1", huge)),
        ]
        out = tool_result_budget(history, max_bytes=200000, preview_chars=2000, persist_dir=Path(".cda/task_outputs/tool-results"))
        files = list(Path(".cda/task_outputs/tool-results").glob("*"))
        self.assertTrue(files)
        body = out[-1].tool_result.content
        self.assertIn("<persisted-output", body)
        preview = body.split(">", 1)[1].split("</persisted-output>", 1)[0].strip()
        self.assertLessEqual(len(preview), 2000)

    def test_ac005_snip_compact_keeps_head_and_placeholder(self) -> None:
        from src.domain.models import ChatMessage
        from src.tools.compact import snip_compact

        history = [ChatMessage("user", f"m{i}") for i in range(60)]
        out = snip_compact(history, max_messages=50, keep_head=3)
        self.assertEqual(len(out), 50)
        self.assertEqual([m.content for m in out[:3]], ["m0", "m1", "m2"])
        self.assertEqual(out[3].role, "user")
        self.assertEqual(out[3].content, "[snipped 11 messages from conversation middle]")

    def test_ac006_snip_does_not_split_tool_pair(self) -> None:
        from src.domain.models import ChatMessage, ToolCall, ToolResult
        from src.tools.compact import snip_compact

        history = [ChatMessage("user", f"m{i}") for i in range(48)]
        history.append(ChatMessage("assistant", None, (ToolCall("c1", "bash", {"command": "echo"}),)))
        history.append(ChatMessage("tool", tool_result=ToolResult("c1", "ok")))
        out = snip_compact(history, max_messages=50, keep_head=3)
        roles = [(m.role, bool(m.tool_calls), m.tool_result is not None) for m in out]
        for i, (role, has_calls, has_result) in enumerate(roles):
            if has_result:
                self.assertFalse(i == 0)
                prev = roles[i - 1]
                if prev[1]:
                    self.assertTrue(True)
        assistant_indexes = [i for i, item in enumerate(out) if item.tool_calls]
        for index in assistant_indexes:
            self.assertLess(index + 1, len(out))
            self.assertIsNotNone(out[index + 1].tool_result)

    def test_ac007_micro_compact_placeholders_old_results(self) -> None:
        from src.domain.models import ChatMessage, ToolResult
        from src.tools.compact import TOOL_RESULT_PLACEHOLDER, micro_compact

        history = []
        for i in range(5):
            history.append(ChatMessage("tool", tool_result=ToolResult(f"c{i}", "Y" * 200)))
        out = micro_compact(history, keep_recent_results=3)
        self.assertEqual(out[0].tool_result.content, TOOL_RESULT_PLACEHOLDER)
        self.assertEqual(out[1].tool_result.content, TOOL_RESULT_PLACEHOLDER)
        self.assertEqual(out[2].tool_result.content, "Y" * 200)
        self.assertEqual(out[3].tool_result.content, "Y" * 200)
        self.assertEqual(out[4].tool_result.content, "Y" * 200)

    def test_ac008_cheap_layers_noop_under_thresholds(self) -> None:
        from src.domain.models import ChatMessage, ToolResult
        from src.tools.compact import micro_compact, snip_compact, tool_result_budget

        history = [
            ChatMessage("user", "hi"),
            ChatMessage("assistant", "ok"),
            ChatMessage("tool", tool_result=ToolResult("c1", "short")),
        ]
        self.assertEqual(tool_result_budget(history, max_bytes=200000), history)
        self.assertEqual(snip_compact(history, max_messages=50), history)
        self.assertEqual(micro_compact(history, keep_recent_results=3), history)

    def test_ac011_safe_boundary_slides_off_orphaned_tool_result(self) -> None:
        from src.domain.models import ChatMessage, ToolCall, ToolResult
        from src.tools.compact import find_safe_boundary

        history = [
            ChatMessage("user", "do"),
            ChatMessage("assistant", None, (ToolCall("c1", "bash", {"command": "echo"}),)),
            ChatMessage("tool", tool_result=ToolResult("c1", "ok")),
            ChatMessage("user", "next"),
        ]
        self.assertEqual(find_safe_boundary(history, 2), 1)

    def test_ac024_persist_sanitizes_traversal_call_id(self) -> None:
        from src.domain.models import ChatMessage, ToolResult
        from src.tools.compact import sanitize_filename, tool_result_budget

        self.assertNotIn("..", sanitize_filename("../etc/passwd"))
        self.assertNotIn("/", sanitize_filename("a/b/c"))
        huge = "Z" * 250000
        history = [ChatMessage("tool", tool_result=ToolResult("../evil/id", huge))]
        persist = Path(".cda/task_outputs/tool-results")
        tool_result_budget(history, max_bytes=200000, persist_dir=persist)
        written = list(persist.glob("*"))
        self.assertTrue(written)
        for path in written:
            self.assertEqual(path.parent.resolve(), persist.resolve())
            self.assertNotIn("..", path.name)


class TestMemoryStorageAndPrompts(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def test_ac001_write_memory_file_and_rebuild_index(self) -> None:
        from src.tools.memory import list_memory_files, read_memory_index, write_memory_file

        path = write_memory_file(
            "user-preference-tabs",
            "user",
            "tabs not spaces",
            "Use tabs.",
            Path.cwd(),
        )
        self.assertEqual(path.name, "user-preference-tabs.md")
        self.assertTrue(path.is_file())
        self.assertEqual(path.parent.resolve(), (Path.cwd() / ".cda" / "memory").resolve())
        text = path.read_text(encoding="utf-8")
        self.assertIn("name: user-preference-tabs", text)
        self.assertIn("description: tabs not spaces", text)
        self.assertIn("type: user", text)
        self.assertIn("Use tabs.", text)
        index = read_memory_index(Path.cwd())
        self.assertIn("- [user-preference-tabs](user-preference-tabs.md) — tabs not spaces", index)
        memories = list_memory_files(Path.cwd())
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].name, "user-preference-tabs")
        self.assertEqual(memories[0].type, "user")

    def test_ac002_sanitize_slug_stays_inside_memory_dir(self) -> None:
        from src.tools.memory import sanitize_slug, write_memory_file

        path = write_memory_file("bad/../x", "user", "unsafe", "body", Path.cwd())
        memory_dir = (Path.cwd() / ".cda" / "memory").resolve()
        self.assertTrue(path.resolve().is_relative_to(memory_dir))
        self.assertNotIn("..", path.name)
        self.assertNotIn("/", path.name)
        self.assertTrue(path.name.endswith(".md"))
        slug = sanitize_slug("bad/../x")
        self.assertNotIn("..", slug)
        self.assertNotIn("/", slug)

    def test_ac003_missing_memory_block_uses_defaults(self) -> None:
        from src.tools.config import (
            DEFAULT_COMPACT_CONFIG,
            DEFAULT_MEMORY_CONFIG,
            load_config,
            resolve_compact_config,
            resolve_memory_config,
        )

        self.assertEqual(load_config(Path.cwd()), {})
        memory = resolve_memory_config(load_config(Path.cwd()))
        compact = resolve_compact_config(load_config(Path.cwd()))
        self.assertEqual(memory, DEFAULT_MEMORY_CONFIG)
        self.assertTrue(memory["enabled"])
        self.assertEqual(memory["max_relevant"], 5)
        self.assertEqual(memory["consolidate_threshold"], 10)
        self.assertTrue(memory["auto_extract"])
        self.assertTrue(memory["auto_consolidate"])
        self.assertEqual(compact["max_messages"], DEFAULT_COMPACT_CONFIG["max_messages"])

    def test_ac004_partial_memory_override_keeps_other_defaults(self) -> None:
        from src.tools.config import load_config, resolve_memory_config

        Path(".cda").mkdir()
        Path(".cda/config.json").write_text(
            json.dumps({"memory": {"max_relevant": 2}}),
            encoding="utf-8",
        )
        memory = resolve_memory_config(load_config(Path.cwd()))
        self.assertEqual(memory["max_relevant"], 2)
        self.assertEqual(memory["consolidate_threshold"], 10)
        self.assertTrue(memory["enabled"])

    def test_ensure_default_config_includes_memory_block(self) -> None:
        from src.tools.config import DEFAULT_MEMORY_CONFIG, ensure_default_config, load_config

        created = ensure_default_config(Path.cwd())
        cfg = load_config(Path.cwd())
        self.assertEqual(created, Path.cwd() / ".cda" / "config.json")
        self.assertEqual(cfg["memory"], DEFAULT_MEMORY_CONFIG)

    def test_default_config_json_is_source_of_startup_payload(self) -> None:
        from src.tools.config import DEFAULT_CONFIG_PATH, ensure_default_config, load_default_config

        bundled = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(load_default_config(), bundled)
        created = ensure_default_config(Path.cwd())
        written = json.loads(created.read_text(encoding="utf-8"))
        self.assertEqual(written, bundled)

    def test_ac006_nonempty_index_appears_in_system_prompt(self) -> None:
        from src.tools.memory import write_memory_file

        write_memory_file("user-preference-tabs", "user", "tabs not spaces", "Use tabs.", Path.cwd())
        prompt = assemble_system_prompt(cwd=Path.cwd())
        self.assertIn("- [user-preference-tabs](user-preference-tabs.md) — tabs not spaces", prompt)

    def test_ac007_empty_index_omits_memory_bullets(self) -> None:
        prompt = assemble_system_prompt(cwd=Path.cwd())
        self.assertNotIn("- [", prompt)
        self.assertNotRegex(prompt, r"- \[.+\]\(.+\.md\)")

    def test_ac008_memory_prompt_override_appears_when_index_present(self) -> None:
        from src.tools.memory import write_memory_file

        write_memory_file("user-preference-tabs", "user", "tabs not spaces", "Use tabs.", Path.cwd())
        override_dir = Path(".cda") / "prompts"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "memory.md").write_text("OVERRIDE-MEMORY-PROMPT\n{catalog}", encoding="utf-8")
        prompt = assemble_system_prompt(cwd=Path.cwd())
        self.assertIn("OVERRIDE-MEMORY-PROMPT", prompt)
        self.assertIn("- [user-preference-tabs](user-preference-tabs.md) — tabs not spaces", prompt)


if __name__ == "__main__":
    unittest.main()


