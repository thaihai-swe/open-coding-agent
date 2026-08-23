import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.query_engine import QueryEngine
from src.domain.errors import ProviderError
from src.domain.models import ChatMessage, ProviderResponse, ToolCall, ToolResult
from src.domain.provider import Provider
from src.infrastructure.session_store import SessionStore
from src.tools.permissions import AuthorizeDecision
from src.tools.registry import Tool, registry
from src.tools.task_board import SYSTEM_MESSAGE


def _once(allow: bool) -> AuthorizeDecision:
    return AuthorizeDecision(allow=allow, persist=False)


class FakeProvider:
    def __init__(self, responses: list[ProviderResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[list[ChatMessage]] = []

    def complete(self, history: list[ChatMessage], tools: list[dict], stream: bool = False) -> ProviderResponse:
        self.calls.append(list(history))
        if not self.responses:
            raise ProviderError("No more responses")
        return self.responses.pop(0)


class AlwaysToolProvider:
    """Fake provider that always returns a tool call to test max_turns bounds."""
    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, history: list[ChatMessage], tools: list[dict], stream: bool = False) -> ProviderResponse:
        self.call_count += 1
        return ProviderResponse(
            ChatMessage("assistant", tool_calls=(ToolCall(f"call-{self.call_count}", "read_file", {"file_path": "nonexistent.txt"}),))
        )


class TestQueryEngine(unittest.TestCase):
    def test_direct_response_emits_text_once(self) -> None:
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "hello"))])
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True), on_event=events.append)
            response = engine.turn("Hi")

            self.assertEqual([event for event in events if event["type"] == "text"], [{"type": "text", "content": "hello"}])
            self.assertEqual([message.role for message in engine.history], ["user", "assistant"])
            self.assertEqual(response.termination_reason, "completed")

    def test_approved_tool_execution_turn(self) -> None:
        responses = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-1", "read_file", {"file_path": "nonexistent.txt"}),))),
            ProviderResponse(ChatMessage("assistant", "File read attempt finished")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True), on_event=events.append)
            response = engine.turn("Read the file")

            self.assertEqual(response.message.content, "File read attempt finished")
            self.assertEqual(response.termination_reason, "completed")
            self.assertEqual(len(engine.history), 4)
            self.assertEqual(engine.history[2].role, "tool")
            self.assertEqual(engine.history[2].tool_result.call_id, "call-1")
            self.assertEqual([event["type"] for event in events if event["type"] in {"status", "tool", "tool_result"}][:3], ["status", "tool", "tool_result"])

    def test_denied_tool_execution_turn(self) -> None:
        responses = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo bad"}),))),
            ProviderResponse(ChatMessage("assistant", "Denied acknowledged")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            # Isolate from leftover project `.cda/.permission_rules/rules.json`.
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(False), on_event=events.append)
                engine.turn("Run command")
            finally:
                os.chdir(original_cwd)

            self.assertTrue(engine.history[2].tool_result.is_error)
            self.assertEqual(engine.history[2].tool_result.content["error"], "Tool execution denied by user.")
            self.assertEqual(events[0]["type"], "tool_denied")

    def test_max_turns_reached_stops_loop(self) -> None:
        # AC-004: max_turns=2 with a provider that always requests tools stops after 2 completions
        provider = AlwaysToolProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            events = []
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True), on_event=events.append, max_turns=2)
            response = engine.turn("Infinite loop test")

            self.assertEqual(provider.call_count, 2)
            self.assertEqual(response.termination_reason, "max_turns_reached")
            self.assertTrue(bool(response.message.tool_calls))

    def test_provider_protocol_conformance(self) -> None:
        # AC-006: FakeProvider drives the engine without importing OpenAIProvider
        self.assertFalse(hasattr(FakeProvider, "__mro__") and any(cls.__name__ == "OpenAIProvider" for cls in FakeProvider.__mro__))
        self.assertTrue(callable(getattr(FakeProvider, "complete", None)))
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "ok"))])
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True))
            response = engine.turn("Hi")
            self.assertEqual(response.termination_reason, "completed")
            self.assertEqual(len(provider.calls), 1)
        import src.infrastructure.providers.openai as openai_mod
        self.assertIsNot(type(provider), openai_mod.OpenAIProvider)

    def test_unknown_tool_records_error_and_continues(self) -> None:
        # AC-004 / T-003
        responses = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-1", "not_a_real_tool", {}),))),
            ProviderResponse(ChatMessage("assistant", "recovered")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True))
            response = engine.turn("Unknown")

            self.assertTrue(engine.history[2].tool_result.is_error)
            self.assertIn("Unknown tool", str(engine.history[2].tool_result.content))
            self.assertEqual(response.message.content, "recovered")
            self.assertEqual(response.termination_reason, "completed")
            self.assertEqual(len(provider.calls), 2)

    def test_batch_history_order_when_second_finishes_first(self) -> None:
        # AC-009 / T-003
        finished: list[str] = []

        def slow(**kwargs):
            time.sleep(0.15)
            finished.append("A")
            return "A"

        def fast(**kwargs):
            finished.append("B")
            return "B"

        registry.register(Tool("slow_tool", "Execution", "LOW", "slow", {"required": [], "properties": {}}, slow))
        registry.register(Tool("fast_tool", "Execution", "LOW", "fast", {"required": [], "properties": {}}, fast))
        try:
            responses = [
                ProviderResponse(
                    ChatMessage(
                        "assistant",
                        tool_calls=(
                            ToolCall("call-a", "slow_tool", {}),
                            ToolCall("call-b", "fast_tool", {}),
                        ),
                    )
                ),
                ProviderResponse(ChatMessage("assistant", "done")),
            ]
            provider = FakeProvider(responses)
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True))
                engine.turn("Batch")

                self.assertEqual(finished, ["B", "A"])
                self.assertEqual(engine.history[2].tool_result.call_id, "call-a")
                self.assertEqual(engine.history[3].tool_result.call_id, "call-b")
        finally:
            registry.tools.pop("slow_tool", None)
            registry.tools.pop("fast_tool", None)

    def test_batch_failure_does_not_skip_sibling(self) -> None:
        # AC-010 / T-003
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "not_a_real_tool", {}),
                        ToolCall("call-2", "read_file", {"file_path": "nonexistent.txt"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "both recorded")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True))
            engine.turn("Mixed")

            self.assertEqual(engine.history[2].tool_result.call_id, "call-1")
            self.assertTrue(engine.history[2].tool_result.is_error)
            self.assertEqual(engine.history[3].tool_result.call_id, "call-2")
            self.assertIsNotNone(engine.history[3].tool_result)

    def test_next_complete_waits_for_full_batch(self) -> None:
        # AC-013 / T-003
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "read_file", {"file_path": "missing-a.txt"}),
                        ToolCall("call-2", "read_file", {"file_path": "missing-b.txt"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "after batch")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True))
            engine.turn("Wait")

            self.assertEqual(len(provider.calls), 2)
            roles = [message.role for message in provider.calls[1]]
            self.assertEqual(roles.count("tool"), 2)
            self.assertEqual(provider.calls[1][-2].tool_result.call_id, "call-1")
            self.assertEqual(provider.calls[1][-1].tool_result.call_id, "call-2")

    def test_denied_call_does_not_run_but_siblings_do(self) -> None:
        # AC-011 / T-004
        ran: list[str] = []

        def allowed(**kwargs):
            ran.append("allowed")
            return "ok"

        def denied(**kwargs):
            ran.append("denied")
            return "nope"

        registry.register(Tool("allowed_med", "File I/O", "MEDIUM", "allowed", {"required": [], "properties": {}}, allowed))
        registry.register(Tool("denied_med", "File I/O", "MEDIUM", "denied", {"required": [], "properties": {}}, denied))
        try:
            responses = [
                ProviderResponse(
                    ChatMessage(
                        "assistant",
                        tool_calls=(
                            ToolCall("call-1", "denied_med", {}),
                            ToolCall("call-2", "allowed_med", {}),
                        ),
                    )
                ),
                ProviderResponse(ChatMessage("assistant", "partial")),
            ]
            provider = FakeProvider(responses)
            events: list[dict] = []
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: _once(name != "denied_med"),
                    on_event=events.append,
                )
                engine.turn("Deny one")

                self.assertIn("tool_denied", [event["type"] for event in events])
                self.assertEqual(ran, ["allowed"])
                self.assertTrue(engine.history[2].tool_result.is_error)
                self.assertEqual(engine.history[3].tool_result.call_id, "call-2")
                self.assertFalse(engine.history[3].tool_result.is_error)
        finally:
            registry.tools.pop("allowed_med", None)
            registry.tools.pop("denied_med", None)

    def test_authorize_is_sequential_before_overlap(self) -> None:
        # AC-012 / T-004
        log: list[tuple[str, str]] = []

        def authorize(name: str, args: dict) -> AuthorizeDecision:
            log.append(("auth", name))
            return _once(True)

        def first(**kwargs):
            log.append(("run", "first_med"))
            time.sleep(0.05)
            return "1"

        def second(**kwargs):
            log.append(("run", "second_med"))
            return "2"

        registry.register(Tool("first_med", "File I/O", "MEDIUM", "first", {"required": [], "properties": {}}, first))
        registry.register(Tool("second_med", "File I/O", "MEDIUM", "second", {"required": [], "properties": {}}, second))
        try:
            responses = [
                ProviderResponse(
                    ChatMessage(
                        "assistant",
                        tool_calls=(
                            ToolCall("call-1", "first_med", {}),
                            ToolCall("call-2", "second_med", {}),
                        ),
                    )
                ),
                ProviderResponse(ChatMessage("assistant", "ok")),
            ]
            provider = FakeProvider(responses)
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(provider, store, session_id, authorize=authorize)
                engine.turn("Auth order")

                self.assertEqual([item for item in log if item[0] == "auth"], [("auth", "first_med"), ("auth", "second_med")])
                self.assertLess(log.index(("auth", "second_med")), min(i for i, item in enumerate(log) if item[0] == "run"))
        finally:
            registry.tools.pop("first_med", None)
            registry.tools.pop("second_med", None)

    def test_status_then_tool_then_tool_result_events(self) -> None:
        # AC-015 / T-004
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "read_file", {"file_path": "missing-a.txt"}),
                        ToolCall("call-2", "read_file", {"file_path": "missing-b.txt"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "after")),
        ]
        provider = FakeProvider(responses)
        events: list[dict] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True), on_event=events.append)
            engine.turn("Status")

            types = [event["type"] for event in events]
            self.assertIn("status", types)
            self.assertIn("tool", types)
            self.assertIn("tool_result", types)
            self.assertLess(types.index("status"), types.index("tool"))
            tool_indexes = [index for index, kind in enumerate(types) if kind == "tool"]
            result_indexes = [index for index, kind in enumerate(types) if kind == "tool_result"]
            self.assertEqual(len(tool_indexes), 2)
            self.assertEqual(len(result_indexes), 2)
            self.assertLess(max(tool_indexes), min(result_indexes))
            self.assertEqual(events[result_indexes[0]]["name"], "read_file")
            self.assertEqual(events[result_indexes[1]]["name"], "read_file")

    def test_hard_deny_stops_turn_before_model_retry(self) -> None:
        authorized: list[str] = []

        def authorize(name: str, args: dict) -> AuthorizeDecision:
            authorized.append(name)
            return _once(True)

        responses = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "sudo echo root"}),))
            ),
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-2", "bash", {"command": "echo root"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "retried")),
        ]
        provider = FakeProvider(responses)
        events: list[dict] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=authorize, on_event=events.append)
            response = engine.turn("Hard deny then retry")

            self.assertEqual(len(provider.calls), 1)
            self.assertEqual(authorized, [])
            self.assertEqual(response.termination_reason, "completed")
            self.assertNotIn("tool_denied", [event["type"] for event in events])
            self.assertTrue(engine.history[2].tool_result.is_error)
            self.assertIn("Blocked:", str(engine.history[2].tool_result.content))
            self.assertIn("sudo", str(engine.history[2].tool_result.content))
            self.assertEqual(len(engine.history), 3)

    def test_hard_denied_bash_skips_authorize_and_handler(self) -> None:
        # AC-008 / REQ-001, REQ-007, REQ-008, REQ-015 / T-003
        authorized: list[str] = []
        ran: list[str] = []

        def authorize(name: str, args: dict) -> AuthorizeDecision:
            authorized.append(name)
            return _once(True)

        original = registry.get("bash")
        assert original is not None

        def tracking_bash(**kwargs):
            ran.append(kwargs.get("command", ""))
            return original.handler(**kwargs)

        registry.register(
            Tool("bash", original.category, original.risk_level, original.description, original.schema, tracking_bash)
        )
        try:
            responses = [
                ProviderResponse(
                    ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "sudo id"}),))
                ),
                ProviderResponse(ChatMessage("assistant", "blocked")),
            ]
            provider = FakeProvider(responses)
            events: list[dict] = []
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(provider, store, session_id, authorize=authorize, on_event=events.append)
                engine.turn("Hard deny")

                self.assertEqual(authorized, [])
                self.assertEqual(ran, [])
                self.assertNotIn("tool_denied", [event["type"] for event in events])
                self.assertTrue(engine.history[2].tool_result.is_error)
                error_text = str(engine.history[2].tool_result.content)
                self.assertIn("Blocked:", error_text)
                self.assertIn("sudo", error_text)
        finally:
            registry.register(original)

    def test_low_read_file_does_not_authorize(self) -> None:
        # AC-009 / REQ-002 / T-003
        authorized: list[str] = []

        def authorize(name: str, args: dict) -> AuthorizeDecision:
            authorized.append(name)
            return _once(True)

        responses = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "read_file", {"file_path": "missing.txt"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "done")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=authorize)
            engine.turn("Read")

            self.assertEqual(authorized, [])
            self.assertIsNotNone(engine.history[2].tool_result)
            content = engine.history[2].tool_result.content
            self.assertNotEqual(content.get("error"), "Tool execution denied by user.")

    def test_hard_deny_then_low_sibling_keeps_order(self) -> None:
        # AC-013 / REQ-013, REQ-014 / T-003
        authorized: list[str] = []

        def authorize(name: str, args: dict) -> AuthorizeDecision:
            authorized.append(name)
            return _once(True)

        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-a", "bash", {"command": "sudo id"}),
                        ToolCall("call-b", "read_file", {"file_path": "missing.txt"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "both")),
        ]
        provider = FakeProvider(responses)
        events: list[dict] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=authorize, on_event=events.append)
            engine.turn("Mixed")

            self.assertNotIn("bash", authorized)
            self.assertEqual(engine.history[2].tool_result.call_id, "call-a")
            self.assertTrue(engine.history[2].tool_result.is_error)
            self.assertIn("Blocked:", str(engine.history[2].tool_result.content))
            self.assertEqual(engine.history[3].tool_result.call_id, "call-b")
            self.assertIsNotNone(engine.history[3].tool_result)
            self.assertNotIn("tool_denied", [event["type"] for event in events])

    def test_write_file_id_rsa_hard_denied_on_turn(self) -> None:
        # AC-015 / REQ-010, REQ-008 / T-004
        authorized: list[str] = []

        def authorize(name: str, args: dict) -> AuthorizeDecision:
            authorized.append(name)
            return _once(True)

        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(ToolCall("call-1", "write_file", {"file_path": "id_rsa", "content": "secret"}),),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "blocked")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(temp_dir)
            session_id = store.create()
            engine = QueryEngine(provider, store, session_id, authorize=authorize)
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                engine.turn("Write key")
                self.assertEqual(authorized, [])
                self.assertTrue(engine.history[2].tool_result.is_error)
                self.assertIn("Protected path blocked:", str(engine.history[2].tool_result.content))
                self.assertFalse((Path(temp_dir) / "id_rsa").exists())
            finally:
                os.chdir(cwd)

    def test_config_set_secret_hard_denied_on_turn(self) -> None:
        # AC-016 / REQ-011 / T-004
        authorized: list[str] = []
        set_values: list[tuple[str, object]] = []

        def authorize(name: str, args: dict) -> AuthorizeDecision:
            authorized.append(name)
            return _once(True)

        original = registry.get("config")
        assert original is not None

        def tracking_config(action: str, key: str, value=None):
            set_values.append((action, key, value))
            return original.handler(action, key, value)

        registry.register(
            Tool("config", original.category, original.risk_level, original.description, original.schema, tracking_config)
        )
        try:
            responses = [
                ProviderResponse(
                    ChatMessage(
                        "assistant",
                        tool_calls=(ToolCall("call-1", "config", {"action": "set", "key": "secret", "value": "n"}),),
                    )
                ),
                ProviderResponse(ChatMessage("assistant", "blocked")),
            ]
            provider = FakeProvider(responses)
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(provider, store, session_id, authorize=authorize)
                engine.turn("Set secret")

                self.assertEqual(authorized, [])
                self.assertEqual(set_values, [])
                self.assertTrue(engine.history[2].tool_result.is_error)
        finally:
            registry.register(original)


    def test_ac010_bash_allowed_once_runs_handler_with_bypass(self) -> None:
        # AC-010 / REQ-003, REQ-012 / T-005
        ran_kwargs: list[dict] = []
        original = registry.get("bash")
        assert original is not None

        def tracking_bash(**kwargs):
            ran_kwargs.append(dict(kwargs))
            return {"exit_code": 0, "stdout": "ok", "stderr": ""}

        registry.register(
            Tool("bash", original.category, original.risk_level, original.description, original.schema, tracking_bash)
        )
        try:
            responses = [
                ProviderResponse(
                    ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo safe"}),))
                ),
                ProviderResponse(ChatMessage("assistant", "done")),
            ]
            provider = FakeProvider(responses)
            with tempfile.TemporaryDirectory() as temp_dir:
                store = SessionStore(temp_dir)
                session_id = store.create()
                engine = QueryEngine(provider, store, session_id, authorize=lambda name, args: _once(True))
                engine.turn("Safe bash")

                self.assertEqual(len(ran_kwargs), 1)
                self.assertTrue(ran_kwargs[0].get("bypass_permissions"))
                self.assertFalse(engine.history[2].tool_result.is_error)
        finally:
            registry.register(original)


    def test_ac018_answer_2_persists_rule_and_runs_handler(self) -> None:
        # AC-018 / REQ-016, REQ-017, REQ-018, REQ-015 / T-006
        responses = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo ping"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "done")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: AuthorizeDecision(allow=True, persist=True),
                )
                engine.turn("Ping")

                rules_path = Path(".cda/.permission_rules/rules.json")
                self.assertTrue(rules_path.exists())
                import json
                rules = json.loads(rules_path.read_text(encoding="utf-8"))
                self.assertEqual(rules, [{"tool": "bash", "pattern": {"command": "echo ping"}, "decision": "allow"}])

                session_file = Path(".cda/.sessions") / f"{session_id}.json"
                session_data = json.loads(session_file.read_text(encoding="utf-8"))
                self.assertEqual(list(session_data.keys()), ["messages"])
            finally:
                os.chdir(cwd)

    def test_wildcard_bash_rule_skips_authorize(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                rules_path = Path(".cda/.permission_rules/rules.json")
                rules_path.parent.mkdir(parents=True, exist_ok=True)
                import json
                rules_path.write_text(
                    json.dumps([{"tool": "bash", "pattern": {"command": "cd *"}, "decision": "allow"}]),
                    encoding="utf-8",
                )

                responses = [
                    ProviderResponse(
                        ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "cd /tmp"}),))
                    ),
                    ProviderResponse(ChatMessage("assistant", "done")),
                ]
                provider = FakeProvider(responses)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()
                authorized: list[str] = []
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: (authorized.append(name) or _once(False)),
                )
                engine.turn("Change directory")

                self.assertEqual(authorized, [])
                self.assertFalse(engine.history[2].tool_result.is_error)
            finally:
                os.chdir(cwd)

    def test_answer_3_persists_wildcard_rule_and_skips_later_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()

                # Turn 1: user chooses option 3 (allow + persist + persist_pattern) for `cd project-folder`
                responses_1 = [
                    ProviderResponse(
                        ChatMessage(
                            "assistant",
                            tool_calls=(
                                ToolCall("call-1", "bash", {"command": "cd project-folder"}),
                            ),
                        )
                    ),
                    ProviderResponse(ChatMessage("assistant", "done")),
                ]
                engine_1 = QueryEngine(
                    FakeProvider(responses_1),
                    store,
                    session_id,
                    authorize=lambda name, args: AuthorizeDecision(allow=True, persist=True, persist_pattern=True),
                )
                engine_1.turn("Enter folder")

                rules_path = Path(".cda/.permission_rules/rules.json")
                self.assertTrue(rules_path.exists())
                import json
                rules = json.loads(rules_path.read_text(encoding="utf-8"))
                self.assertEqual(rules, [{"tool": "bash", "pattern": {"command": "cd *"}, "decision": "allow"}])

                # Turn 2: another session runs `cd /tmp` -> matches `cd *` rule without asking
                responses_2 = [
                    ProviderResponse(
                        ChatMessage("assistant", tool_calls=(ToolCall("call-2", "bash", {"command": "cd /tmp"}),))
                    ),
                    ProviderResponse(ChatMessage("assistant", "done 2")),
                ]
                authorized: list[str] = []
                store_2 = SessionStore(Path(".cda/.sessions"))
                session_2_id = store_2.create()
                engine_2 = QueryEngine(
                    FakeProvider(responses_2),
                    store_2,
                    session_2_id,
                    authorize=lambda name, args: (authorized.append(name) or _once(False)),
                )
                engine_2.turn("Enter tmp")

                self.assertEqual(authorized, [])
                self.assertFalse(engine_2.history[2].tool_result.is_error)
            finally:
                os.chdir(cwd)

    def test_ac019_different_session_uses_persisted_rule_without_ask(self) -> None:
        # AC-019 / REQ-003, REQ-012, REQ-018 / T-006
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                rules_path = Path(".cda/.permission_rules/rules.json")
                rules_path.parent.mkdir(parents=True, exist_ok=True)
                import json
                rules_path.write_text(
                    json.dumps([{"tool": "bash", "pattern": {"command": "echo ping"}, "decision": "allow"}]),
                    encoding="utf-8",
                )

                responses = [
                    ProviderResponse(
                        ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo ping"}),))
                    ),
                    ProviderResponse(ChatMessage("assistant", "done")),
                ]
                provider = FakeProvider(responses)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()
                authorized: list[str] = []
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: (authorized.append(name) or _once(False)),
                )
                engine.turn("Ping new session")

                self.assertEqual(authorized, [])
                self.assertFalse(engine.history[2].tool_result.is_error)
            finally:
                os.chdir(cwd)

    def test_ac020_answer_4_persists_deny_and_blocks_later_call_without_ask(self) -> None:
        # AC-020 / REQ-005, REQ-016, REQ-017, REQ-019 / T-006
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()

                # First turn: user answers 4 for write_file notes.txt
                responses_1 = [
                    ProviderResponse(
                        ChatMessage("assistant", tool_calls=(ToolCall("call-1", "write_file", {"file_path": "notes.txt", "content": "first"}),))
                    ),
                    ProviderResponse(ChatMessage("assistant", "denied")),
                ]
                events_1: list[dict] = []
                engine_1 = QueryEngine(
                    FakeProvider(responses_1),
                    store,
                    session_id,
                    authorize=lambda name, args: AuthorizeDecision(allow=False, persist=True),
                    on_event=events_1.append,
                )
                engine_1.turn("Write 1")

                rules_path = Path(".cda/.permission_rules/rules.json")
                self.assertTrue(rules_path.exists())
                import json
                rules = json.loads(rules_path.read_text(encoding="utf-8"))
                self.assertEqual(rules, [{"tool": "write_file", "pattern": {"file_path": "notes.txt"}, "decision": "deny"}])

                # Second turn: write_file notes.txt with different content
                responses_2 = [
                    ProviderResponse(
                        ChatMessage("assistant", tool_calls=(ToolCall("call-2", "write_file", {"file_path": "notes.txt", "content": "second"}),))
                    ),
                    ProviderResponse(ChatMessage("assistant", "denied again")),
                ]
                authorized: list[str] = []
                events_2: list[dict] = []
                engine_2 = QueryEngine(
                    FakeProvider(responses_2),
                    store,
                    session_id,
                    authorize=lambda name, args: (authorized.append(name) or _once(True)),
                    on_event=events_2.append,
                )
                engine_2.turn("Write 2")

                self.assertEqual(authorized, [])
                self.assertIn("tool_denied", [event["type"] for event in events_2])
                self.assertTrue(engine_2.history[6].tool_result.is_error)
                self.assertEqual(engine_2.history[6].tool_result.content["error"], "Tool execution denied by user.")
                self.assertFalse(Path("notes.txt").exists())
            finally:
                os.chdir(cwd)

    def test_ac021_answer_1_does_not_create_rules_file(self) -> None:
        # AC-021 / REQ-017 / T-006
        responses = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo once"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "done")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: AuthorizeDecision(allow=True, persist=False),
                )
                engine.turn("Ping")

                self.assertFalse(Path(".cda/.permission_rules/rules.json").exists())
            finally:
                os.chdir(cwd)

    def test_ac022_sibling_same_command_prompts_once_on_answer_2(self) -> None:
        # AC-022 / REQ-013, REQ-017 / T-006
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "bash", {"command": "echo dup"}),
                        ToolCall("call-2", "bash", {"command": "echo dup"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "done")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()
                authorized: list[str] = []
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: (authorized.append(name) or AuthorizeDecision(allow=True, persist=True)),
                )
                engine.turn("Two pings")

                self.assertEqual(authorized, ["bash"])
                self.assertFalse(engine.history[2].tool_result.is_error)
                self.assertFalse(engine.history[3].tool_result.is_error)
            finally:
                os.chdir(cwd)

    def test_ac023_rules_file_allow_cannot_override_deny_listed_sudo(self) -> None:
        # AC-023 / REQ-007, REQ-019 / T-006
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                rules_path = Path(".cda/.permission_rules/rules.json")
                rules_path.parent.mkdir(parents=True, exist_ok=True)
                import json
                rules_path.write_text(
                    json.dumps([{"tool": "bash", "pattern": {"command": "sudo id"}, "decision": "allow"}]),
                    encoding="utf-8",
                )

                responses = [
                    ProviderResponse(
                        ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "sudo id"}),))
                    ),
                    ProviderResponse(ChatMessage("assistant", "blocked")),
                ]
                provider = FakeProvider(responses)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()
                authorized: list[str] = []
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: (authorized.append(name) or _once(True)),
                )
                engine.turn("Try sudo with allow rule")

                self.assertEqual(authorized, [])
                self.assertTrue(engine.history[2].tool_result.is_error)
                self.assertIn("Blocked:", str(engine.history[2].tool_result.content))
                self.assertIn("sudo", str(engine.history[2].tool_result.content))
            finally:
                os.chdir(cwd)

    def test_ac025_invalid_rule_entry_skipped_and_valid_rule_matches(self) -> None:
        # AC-025 / REQ-018 / T-006
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                rules_path = Path(".cda/.permission_rules/rules.json")
                rules_path.parent.mkdir(parents=True, exist_ok=True)
                import json
                rules_path.write_text(
                    json.dumps([
                        {"invalid": "format"},
                        {"tool": "web_fetch", "pattern": "not-dict", "decision": "allow"},
                        {"tool": "web_fetch", "pattern": {"url": "https://example.com"}, "decision": "invalid_decision"},
                        {"tool": "web_fetch", "pattern": {"url": "https://example.com"}, "decision": "allow"},
                    ]),
                    encoding="utf-8",
                )

                responses = [
                    ProviderResponse(
                        ChatMessage("assistant", tool_calls=(ToolCall("call-1", "web_fetch", {"url": "https://example.com"}),))
                    ),
                    ProviderResponse(ChatMessage("assistant", "done")),
                ]
                provider = FakeProvider(responses)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()
                authorized: list[str] = []
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: (authorized.append(name) or _once(False)),
                )
                engine.turn("Fetch")

                self.assertEqual(authorized, [])
            finally:
                os.chdir(cwd)

    def test_ac029_rule_persists_under_dot_cda_not_cwd_root(self) -> None:
        # AC-029 / REQ-017, REQ-020 / T-006
        responses = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "bash", {"command": "echo cda"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "done")),
        ]
        provider = FakeProvider(responses)
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                store = SessionStore(Path(".cda/.sessions"))
                session_id = store.create()
                engine = QueryEngine(
                    provider,
                    store,
                    session_id,
                    authorize=lambda name, args: AuthorizeDecision(allow=True, persist=True),
                )
                engine.turn("Ping")

                self.assertTrue(Path(".cda/.permission_rules/rules.json").exists())
                self.assertFalse(Path(".permission_rules/rules.json").exists())
            finally:
                os.chdir(cwd)


class TestPlanningEngine(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def _engine(self, provider, session_id="s1", authorize=None, on_event=None):
        store = SessionStore()
        if session_id not in store.list():
            Path(store.directory).mkdir(parents=True, exist_ok=True)
            store.save(session_id, [])
        return QueryEngine(
            provider,
            store,
            session_id,
            authorize=authorize or (lambda name, args: _once(True)),
            on_event=on_event,
        )

    def test_create_task_writes_session_todos_not_cwd_root(self) -> None:
        # AC-003, AC-026 / REQ-004, REQ-019 / T-003
        responses = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "create_task", {"content": "Write tests"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "created")),
        ]
        engine = self._engine(FakeProvider(responses), session_id="s1")
        engine.turn("Plan")
        path = Path(".cda/.todos/s1.json")
        self.assertTrue(path.is_file())
        self.assertFalse(Path(".cda/.todos/default.json").exists())
        self.assertFalse(Path(".todos").exists())
        self.assertFalse(Path(".tasks").exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["content"], "Write tests")
        self.assertEqual(data[0]["status"], "pending")
        result = engine.history[2].tool_result.content["result"]
        self.assertEqual(result["id"], data[0]["id"])

    def test_resume_same_session_lists_persisted_item(self) -> None:
        # AC-013 / REQ-004 / T-003
        first = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "create_task", {"content": "Write tests"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "created")),
        ]
        self._engine(FakeProvider(first), session_id="s1").turn("Create")
        listed = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-2", "list_tasks", {}),))),
            ProviderResponse(ChatMessage("assistant", "listed")),
        ]
        engine = self._engine(FakeProvider(listed), session_id="s1")
        engine.turn("List")
        payload = engine.history[-2].tool_result.content
        items = payload["result"] if isinstance(payload, dict) else payload
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["content"], "Write tests")
        self.assertTrue(Path(".cda/.todos/s1.json").is_file())
        self.assertFalse(Path(".cda/.todos/default.json").exists())

    def test_other_session_is_isolated(self) -> None:
        # AC-014 / REQ-004 / T-003
        first = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "create_task", {"content": "Write tests"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "created")),
        ]
        self._engine(FakeProvider(first), session_id="s1").turn("Create")
        before = Path(".cda/.todos/s1.json").read_text(encoding="utf-8")
        listed = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-2", "list_tasks", {}),))),
            ProviderResponse(ChatMessage("assistant", "listed")),
        ]
        engine = self._engine(FakeProvider(listed), session_id="s2")
        engine.turn("List other")
        payload = engine.history[-2].tool_result.content
        items = payload["result"] if isinstance(payload, dict) else payload
        self.assertEqual(items, [])
        self.assertEqual(Path(".cda/.todos/s1.json").read_text(encoding="utf-8"), before)
        self.assertFalse(Path(".cda/.todos/s2.json").exists())

    def test_session_json_has_no_task_board_fields(self) -> None:
        # AC-015 / REQ-005 / T-003
        responses = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "create_task", {"content": "Write tests"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "created")),
        ]
        engine = self._engine(FakeProvider(responses), session_id="s1")
        engine.turn("Plan")
        data = json.loads(Path(".cda/.sessions/s1.json").read_text(encoding="utf-8"))
        self.assertEqual(list(data.keys()), ["messages"])
        for key in ("todos", "tasks", "task_board", "board"):
            self.assertNotIn(key, data)

    def test_create_task_does_not_call_authorize(self) -> None:
        # AC-017 / REQ-001, REQ-018 / T-003
        authorized: list[str] = []
        responses = [
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "create_task", {"content": "Write tests"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "created")),
        ]
        engine = self._engine(
            FakeProvider(responses),
            session_id="s1",
            authorize=lambda name, args: (authorized.append(name) or _once(True)),
        )
        engine.turn("Plan")
        self.assertEqual(authorized, [])
        self.assertFalse(engine.history[2].tool_result.is_error)

    def test_failing_create_then_list_keeps_listed_order(self) -> None:
        # AC-025 / REQ-013, REQ-006 / T-003
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "create_task", {"content": ""}),
                        ToolCall("call-2", "list_tasks", {}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "both")),
        ]
        engine = self._engine(FakeProvider(responses), session_id="s1")
        engine.turn("Mixed")
        self.assertEqual(engine.history[2].tool_result.call_id, "call-1")
        self.assertTrue(engine.history[2].tool_result.is_error)
        self.assertEqual(engine.history[3].tool_result.call_id, "call-2")
        self.assertFalse(engine.history[3].tool_result.is_error)
        payload = engine.history[3].tool_result.content
        items = payload["result"] if isinstance(payload, dict) else payload
        self.assertEqual(items, [])

    def test_two_creates_in_one_batch_apply_in_listed_order(self) -> None:
        # AC-025 / REQ-013 / T-003
        responses = [
            ProviderResponse(
                ChatMessage(
                    "assistant",
                    tool_calls=(
                        ToolCall("call-1", "create_task", {"content": "A", "id": "a"}),
                        ToolCall("call-2", "create_task", {"content": "B", "id": "b"}),
                    ),
                )
            ),
            ProviderResponse(ChatMessage("assistant", "both")),
        ]
        engine = self._engine(FakeProvider(responses), session_id="s1")
        engine.turn("Two")
        data = json.loads(Path(".cda/.todos/s1.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in data], ["a", "b"])
        self.assertEqual(engine.history[2].tool_result.call_id, "call-1")
        self.assertEqual(engine.history[3].tool_result.call_id, "call-2")
        self.assertFalse(engine.history[2].tool_result.is_error)
        self.assertFalse(engine.history[3].tool_result.is_error)

    def test_complete_prepends_system_message_not_saved(self) -> None:
        # AC-015, AC-018 / REQ-005, REQ-016 / T-004
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "hello"))])
        engine = self._engine(provider, session_id="s1")
        engine.turn("Hi")
        self.assertTrue(provider.calls)
        first = provider.calls[0][0]
        self.assertEqual(first.role, "system")
        self.assertIn("plan before executing", first.content)
        for name in ("create_task", "list_tasks", "get_task", "claim_task", "complete_task", "cancel_task"):
            self.assertIn(name, first.content)
        self.assertNotIn("system", [message.role for message in engine.history])
        data = json.loads(Path(".cda/.sessions/s1.json").read_text(encoding="utf-8"))
        self.assertEqual(list(data.keys()), ["messages"])
        self.assertFalse(any(message.get("role") == "system" for message in data["messages"]))
        self.assertIn(SYSTEM_MESSAGE, first.content)
        self.assertIn("Skills available:\n(no skills found)", first.content)

    def test_nag_after_three_text_only_rounds(self) -> None:
        # AC-019 / REQ-017 / T-004
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", "one")),
            ProviderResponse(ChatMessage("assistant", "two")),
            ProviderResponse(ChatMessage("assistant", "three")),
            ProviderResponse(ChatMessage("assistant", "four")),
        ])
        engine = self._engine(provider, session_id="s1")
        engine.turn("1")
        engine.turn("2")
        engine.turn("3")
        engine.turn("4")
        nag = [message for message in provider.calls[3] if message.role == "user" and message.content == "<reminder>Update your todos.</reminder>"]
        self.assertEqual(len(nag), 1)
        earlier = [
            message
            for call in provider.calls[:3]
            for message in call
            if message.role == "user" and message.content == "<reminder>Update your todos.</reminder>"
        ]
        self.assertEqual(earlier, [])

    def test_successful_create_resets_nag_counter(self) -> None:
        # AC-020 / REQ-017 / T-004
        provider = FakeProvider([
            ProviderResponse(
                ChatMessage("assistant", tool_calls=(ToolCall("call-1", "create_task", {"content": "Write tests"}),))
            ),
            ProviderResponse(ChatMessage("assistant", "created")),
            ProviderResponse(ChatMessage("assistant", "one")),
            ProviderResponse(ChatMessage("assistant", "two")),
        ])
        engine = self._engine(provider, session_id="s1")
        engine.turn("Create")
        engine.turn("1")
        engine.turn("2")
        nag = [
            message
            for message in provider.calls[-1]
            if message.role == "user" and message.content == "<reminder>Update your todos.</reminder>"
        ]
        self.assertEqual(nag, [])

    def test_list_and_get_do_not_reset_nag_counter(self) -> None:
        # AC-021 / REQ-017 / T-004
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("c1", "list_tasks", {}),))),
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("c2", "get_task", {"id": "missing"}),))),
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("c3", "list_tasks", {}),))),
            ProviderResponse(ChatMessage("assistant", "four")),
        ])
        engine = self._engine(provider, session_id="s1")
        engine.turn("reads")
        nag = [
            message
            for message in provider.calls[3]
            if message.role == "user" and message.content == "<reminder>Update your todos.</reminder>"
        ]
        self.assertEqual(len(nag), 1)

    def _write_skill(self, folder: str, text: str) -> None:
        path = Path(".agents") / "skills" / folder / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_system_message_includes_skill_catalog(self) -> None:
        # AC-009 / REQ-010, REQ-011 / T-003
        self._write_skill("s1", "---\nname: s1\ndescription: First skill\n---\nOne.\n")
        self._write_skill("s2", "---\nname: s2\ndescription: Second skill\n---\nTwo.\n")
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "ok"))])
        engine = self._engine(provider, session_id="s1")
        engine.turn("Hi")
        first = provider.calls[0][0]
        self.assertEqual(first.role, "system")
        self.assertIn("You should plan before executing.", first.content)
        self.assertIn("create_task", first.content)
        self.assertIn("Skills available:", first.content)
        self.assertIn("- **s1**: First skill", first.content)
        self.assertIn("- **s2**: Second skill", first.content)
        self.assertIn("Use load_skill to get full details when needed.", first.content)

    def test_empty_catalog_shows_no_skills_found(self) -> None:
        # AC-010 / REQ-011 / T-003
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "ok"))])
        engine = self._engine(provider, session_id="s1")
        engine.turn("Hi")
        first = provider.calls[0][0]
        self.assertIn("Skills available:\n(no skills found)", first.content)

    def test_load_skill_turn_skips_authorize_and_does_not_persist_system(self) -> None:
        # AC-011, AC-012 / REQ-012, REQ-014 / T-003
        body = "---\nname: tester\ndescription: Tester\n---\nFull.\n"
        self._write_skill("tester", body)
        authorized: list[str] = []
        responses = [
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("c1", "load_skill", {"name": "tester"}),))),
            ProviderResponse(ChatMessage("assistant", "loaded")),
        ]
        engine = self._engine(
            FakeProvider(responses),
            session_id="s1",
            authorize=lambda name, args: authorized.append(name) or _once(True),
        )
        engine.turn("Load it")
        self.assertEqual(authorized, [])
        result = engine.history[2].tool_result.content
        self.assertFalse(engine.history[2].tool_result.is_error)
        self.assertEqual(result.get("result"), body)
        data = json.loads(Path(".cda/.sessions/s1.json").read_text(encoding="utf-8"))
        self.assertFalse(any(message.get("role") == "system" for message in data["messages"]))
        roles = [message.role for message in engine.history]
        self.assertEqual(roles, ["user", "assistant", "tool", "assistant"])

    def test_new_skill_appears_on_next_complete_without_restart(self) -> None:
        # AC-015 / REQ-010 / T-003
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", "one")),
            ProviderResponse(ChatMessage("assistant", "two")),
        ])
        engine = self._engine(provider, session_id="s1")
        engine.turn("first")
        self.assertIn("Skills available:\n(no skills found)", provider.calls[0][0].content)
        self._write_skill("new-skill", "---\nname: new-skill\ndescription: Fresh\n---\nHi.\n")
        engine.turn("second")
        self.assertIn("- **new-skill**: Fresh", provider.calls[1][0].content)

    def test_assembled_prompt_contains_identity_workspace_security_tools(self) -> None:
        # AC-001 / REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-007 / T-002
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "ok"))])
        engine = self._engine(provider, session_id="s1")
        engine.turn("Hi")
        first = provider.calls[0][0]
        self.assertEqual(first.role, "system")
        self.assertIn("You are a coding agent.", first.content)
        self.assertIn("Working directory:", first.content)
        self.assertIn("You should plan before executing.", first.content)
        self.assertIn("create_task", first.content)
        self.assertTrue(
            "workspace" in first.content.lower() or "working directory" in first.content.lower()
        )
        self.assertIn("- bash:", first.content)
        self.assertIn("Skills available:", first.content)
        idx_id = first.content.index("You are a coding agent.")
        idx_ws = first.content.index("Working directory:")
        idx_pl = first.content.index("You should plan before executing.")
        idx_sec = first.content.lower().index("security")
        idx_tls = first.content.index("- bash:")
        idx_skl = first.content.index("Skills available:")
        self.assertTrue(idx_id < idx_ws < idx_pl < idx_sec < idx_tls < idx_skl)

    def test_assembled_prompt_includes_agents_md(self) -> None:
        # AC-005 / REQ-009 / T-002
        Path("AGENTS.md").write_text("REPO-RULE-ALPHA", encoding="utf-8")
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "ok"))])
        engine = self._engine(provider, session_id="s1")
        engine.turn("Hi")
        first = provider.calls[0][0]
        self.assertIn("REPO-RULE-ALPHA", first.content)
        self.assertIn("AGENTS.md", first.content)

    def test_permission_rules_token_not_in_system_prompt(self) -> None:
        # AC-012 / REQ-008 / T-002
        rules_path = Path(".cda/.permission_rules/rules.json")
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(
            '[{"tool": "bash", "pattern": {"command": "UNIQUE-RULE-TOKEN"}, "decision": "allow"}]',
            encoding="utf-8",
        )
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "ok"))])
        engine = self._engine(provider, session_id="s1")
        engine.turn("Hi")
        first = provider.calls[0][0]
        self.assertNotIn("UNIQUE-RULE-TOKEN", first.content)

    def test_new_agents_md_appears_on_next_complete(self) -> None:
        # AC-013 / REQ-013 / T-002
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", "one")),
            ProviderResponse(ChatMessage("assistant", "two")),
        ])
        engine = self._engine(provider, session_id="s1")
        engine.turn("first")
        self.assertNotIn("NEW-AGENTS-BODY", provider.calls[0][0].content)
        Path("AGENTS.md").write_text("NEW-AGENTS-BODY", encoding="utf-8")
        engine.turn("second")
        self.assertIn("NEW-AGENTS-BODY", provider.calls[1][0].content)

    def test_cda_prompt_override_in_query_engine_complete(self) -> None:
        override_dir = Path(".cda") / "prompts"
        override_dir.mkdir(parents=True)
        (override_dir / "identity.md").write_text("CUSTOM-AGENT-IDENTITY", encoding="utf-8")
        provider = FakeProvider([ProviderResponse(ChatMessage("assistant", "ok"))])
        engine = self._engine(provider, session_id="s1")
        engine.turn("Hi")
        first = provider.calls[0][0]
        self.assertIn("CUSTOM-AGENT-IDENTITY", first.content)
        self.assertNotIn("You are a coding agent.", first.content)


class TestCompactionEngine(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = os.getcwd()
        self._temp = tempfile.TemporaryDirectory()
        os.chdir(self._temp.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._temp.cleanup()

    def _engine(self, provider, session_id: str = "s1", on_event=None, config: dict | None = None) -> QueryEngine:
        store = SessionStore(Path(".cda/.sessions"))
        engine = QueryEngine(
            provider,
            store,
            session_id,
            authorize=lambda name, args: _once(True),
            on_event=on_event or (lambda event: None),
        )
        if config is not None:
            engine.config.update(config)
        return engine

    def test_ac009_ac010_auto_compact_triggered_by_chars(self) -> None:
        # AC-009, AC-010 / REQ-003, REQ-004, REQ-008 / T-002
        long_content = "Z" * 500
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", "SUM-BODY")),  # summarizer response
            ProviderResponse(ChatMessage("assistant", "Final text after compact")),
        ])
        events = []
        engine = self._engine(provider, on_event=events.append, config={"max_chars": 300, "keep_recent": 2})
        engine.history = [
            ChatMessage("user", long_content),
            ChatMessage("assistant", "short"),
            ChatMessage("user", "recent1"),
            ChatMessage("assistant", "recent2"),
        ]
        res = engine.turn("new turn")
        # Summarizer was called with tools=[]
        self.assertEqual(len(provider.calls), 2)
        # Summarizer request has no tools
        # History[0] now contains <compacted-summary>
        self.assertEqual(engine.history[0].role, "user")
        self.assertIn("<compacted-summary>", engine.history[0].content)
        self.assertIn("SUM-BODY", engine.history[0].content)
        self.assertIn("</compacted-summary>", engine.history[0].content)
        # Transcripts directory exists
        transcripts = list(Path(".cda/.transcripts").glob("*.jsonl"))
        self.assertTrue(transcripts)
        # AC-021: status event emitted with compact
        status_events = [e for e in events if e.get("type") == "status" and "compact" in e.get("message", "").lower()]
        self.assertTrue(status_events)

    def test_ac012_session_json_contains_compacted_messages_without_system(self) -> None:
        # AC-012 / REQ-008, REQ-015 / T-002
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", "SUMMARY")),
            ProviderResponse(ChatMessage("assistant", "reply")),
        ])
        engine = self._engine(provider, config={"max_chars": 100, "keep_recent": 1})
        engine.history = [
            ChatMessage("user", "A" * 200),
            ChatMessage("assistant", "B" * 200),
        ]
        engine.turn("hello")
        session_file = Path(".cda/.sessions/s1.json")
        self.assertTrue(session_file.is_file())
        data = json.loads(session_file.read_text(encoding="utf-8"))
        self.assertEqual(list(data.keys()), ["messages"])
        self.assertFalse(any(m.get("role") == "system" for m in data["messages"]))
        self.assertEqual(data["messages"][0]["role"], "user")
        self.assertIn("<compacted-summary>", data["messages"][0]["content"])

    def test_ac015_compact_tool_invocation_runs_compact_and_ends_turn(self) -> None:
        # AC-015 / REQ-010 / T-002
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", tool_calls=(ToolCall("call-c", "compact", {}),))),
            ProviderResponse(ChatMessage("assistant", "SUMMARY-TEXT")),
        ])
        engine = self._engine(provider, config={"keep_recent": 1})
        engine.history = [
            ChatMessage("user", "msg1"),
            ChatMessage("assistant", "msg2"),
        ]
        res = engine.turn("please compact")
        self.assertEqual(res.termination_reason, "completed")
        self.assertEqual(engine.history[0].role, "user")
        self.assertIn("<compacted-summary>", engine.history[0].content)

    def test_ac016_auto_compact_false_disables_auto_compaction(self) -> None:
        # AC-016 / REQ-011 / T-002
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", "direct reply")),
        ])
        engine = self._engine(provider, config={"auto_compact": False, "max_chars": 50})
        engine.history = [ChatMessage("user", "X" * 500)]
        res = engine.turn("hi")
        self.assertEqual(len(provider.calls), 1)
        self.assertNotIn("<compacted-summary>", str(engine.history[0].content))

    def test_ac017_reactive_compact_recovers_from_prompt_too_long(self) -> None:
        # AC-017 / REQ-012 / T-002
        class OverflowThenSucceedProvider:
            def __init__(self) -> None:
                self.calls = []
                self.attempt = 0

            def complete(self, history, tools, stream=False):
                self.calls.append(list(history))
                self.attempt += 1
                if self.attempt == 1:
                    raise ProviderError("Provider HTTP 413: prompt_too_long context length exceeded")
                if self.attempt == 2:
                    # Summarizer call during reactive compact
                    return ProviderResponse(ChatMessage("assistant", "REACTIVE-SUMMARY"))
                return ProviderResponse(ChatMessage("assistant", "Success after reactive compact"))

        provider = OverflowThenSucceedProvider()
        engine = self._engine(provider, config={"reactive_retries": 1})
        engine.history = [
            ChatMessage("user", "old1"),
            ChatMessage("assistant", "old2"),
            ChatMessage("user", "old3"),
            ChatMessage("assistant", "old4"),
            ChatMessage("user", "old5"),
            ChatMessage("assistant", "old6"),
        ]
        res = engine.turn("turn causing overflow")
        self.assertEqual(res.message.content, "Success after reactive compact")
        self.assertEqual(engine.history[0].role, "user")
        self.assertIn("REACTIVE-SUMMARY", engine.history[0].content)

    def test_ac018_reactive_compact_propagates_when_retries_exhausted(self) -> None:
        # AC-018 / REQ-012 / T-002
        class AlwaysOverflowProvider:
            def __init__(self) -> None:
                self.calls = []

            def complete(self, history, tools, stream=False):
                self.calls.append(list(history))
                if len(tools) == 0:
                    return ProviderResponse(ChatMessage("assistant", "SUMMARY"))
                raise ProviderError("HTTP 413 prompt_too_long")

        provider = AlwaysOverflowProvider()
        engine = self._engine(provider, config={"reactive_retries": 1})
        engine.history = [ChatMessage("user", f"m{i}") for i in range(10)]
        with self.assertRaises(ProviderError):
            engine.turn("overflow")

    def test_ac019_circuit_breaker_stops_after_consecutive_summarizer_failures(self) -> None:
        # AC-019 / REQ-013 / T-002
        class FailingSummarizerProvider:
            def __init__(self) -> None:
                self.calls = []

            def complete(self, history, tools, stream=False):
                self.calls.append(list(history))
                if len(tools) == 0:
                    raise ProviderError("Summarizer down")
                return ProviderResponse(ChatMessage("assistant", "normal reply"))

        provider = FailingSummarizerProvider()
        engine = self._engine(provider, config={"max_chars": 50, "compact_fail_retries": 3, "keep_recent": 1})
        engine.history = [ChatMessage("user", "Z" * 200)]
        # First turn triggers compact attempt (failure 1)
        engine.turn("t1")
        self.assertEqual(engine._consecutive_compact_failures, 1)
        # Second turn triggers compact attempt (failure 2)
        engine.turn("t2")
        self.assertEqual(engine._consecutive_compact_failures, 2)
        # Third turn triggers compact attempt (failure 3)
        engine.turn("t3")
        self.assertEqual(engine._consecutive_compact_failures, 3)
        # Fourth turn: circuit breaker prevents summarizer call
        calls_before = len([c for c in provider.calls if len(c) > 0])
        engine.turn("t4")
        # History is not wiped with empty summary
        self.assertFalse(any("<compacted-summary>" in (m.content or "") for m in engine.history))

    def test_ac020_cda_compact_prompt_override_used_in_summarizer(self) -> None:
        # AC-020 / REQ-014 / T-002
        override_dir = Path(".cda") / "prompts"
        override_dir.mkdir(parents=True)
        (override_dir / "compact.md").write_text("CUSTOM-COMPACT-INSTRUCTIONS", encoding="utf-8")
        provider = FakeProvider([
            ProviderResponse(ChatMessage("assistant", "SUM")),
            ProviderResponse(ChatMessage("assistant", "ok")),
        ])
        engine = self._engine(provider, config={"max_chars": 50, "keep_recent": 1})
        engine.history = [ChatMessage("user", "Y" * 200)]
        engine.turn("compact me")
        summarizer_call = provider.calls[0]
        self.assertEqual(summarizer_call[0].role, "system")
        self.assertIn("CUSTOM-COMPACT-INSTRUCTIONS", summarizer_call[0].content)


if __name__ == "__main__":
    unittest.main()


