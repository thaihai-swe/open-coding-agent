from __future__ import annotations

import argparse
import sys
import traceback

from ..application.query_engine import QueryEngine
from ..domain.errors import ProviderError
from ..infrastructure.providers import OpenAIProvider
from ..infrastructure.session_store import SessionStore
from ..tools.config import ensure_default_config, resolve_show_tool_results
from ..tools.permission_rules import ensure_default_rules
from ..tools.skills import expand_slash_prompt
from .terminal_ui import TerminalUI


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenAI-compatible coding-agent REPL")
    parser.add_argument("--session", help="Resume this session ID")
    parser.add_argument("--json", action="store_true", dest="json_mode", help="Emit structured JSON events")
    parser.add_argument("--debug", action="store_true", help="Print full exception tracebacks during errors")
    parser.add_argument("--show-tool-results", dest="show_tool_results", action="store_true", default=None, help="Show tool result output (default: on)")
    parser.add_argument("--hide-tool-results", dest="show_tool_results", action="store_false", help="Hide tool result output")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_default_config()
    ensure_default_rules()
    try:
        provider = OpenAIProvider()
    except ProviderError as error:
        print(f"Error: {error}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 2
    store = SessionStore()
    session_id = args.session or store.create()
    show_tool_results = resolve_show_tool_results(args.show_tool_results)
    ui = TerminalUI(json_mode=args.json_mode, show_tool_results=show_tool_results)
    engine = QueryEngine(provider, store, session_id, ui.authorize, ui.event)
    print(f"Session: {session_id}", file=sys.stderr)
    print("Enter sends. Shift+Enter adds a newline.", file=sys.stderr)
    try:
        while True:
            prompt = ui.prompt()
            if not prompt:
                return 0
            if prompt == "/compact" or prompt.startswith("/compact "):
                compacted = engine.manual_compact()
                if compacted:
                    ui.event({"type": "status", "message": "Context compacted."})
                else:
                    ui.event({"type": "status", "message": "Nothing to compact or compaction limit reached."})
                continue
            if prompt.startswith("/"):
                expanded, err = expand_slash_prompt(prompt)
                if err:
                    ui.event({"type": "error", "message": err})
                    continue
                prompt = expanded
            try:
                engine.turn(prompt)
                if not args.json_mode:
                    print()
            except Exception as error:
                ui.event({"type": "error", "message": str(error)})
                if args.debug:
                    traceback.print_exc()
    except KeyboardInterrupt:
        engine._save()
        print("\nSession preserved.", file=sys.stderr)
        return 130
