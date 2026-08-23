from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

from ..application.query_engine import QueryEngine
from ..domain.errors import ProviderError
from ..infrastructure.providers import OpenAIProvider
from ..infrastructure.session_store import SessionStore
from .terminal_ui import TerminalUI

_UI_CONFIG_PATH = Path(".cda/ui-config.json")


def _load_ui_config() -> dict[str, object]:
    try:
        data = json.loads(_UI_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenAI-compatible coding-agent REPL")
    parser.add_argument("--session", help="Resume this session ID")
    parser.add_argument("--json", action="store_true", dest="json_mode", help="Emit structured JSON events")
    parser.add_argument("--debug", action="store_true", help="Print full exception tracebacks during errors")
    parser.add_argument("--show-tool-results", dest="show_tool_results", action="store_true", default=None, help="Show tool result output (default: on)")
    parser.add_argument("--hide-tool-results", dest="show_tool_results", action="store_false", help="Hide tool result output")
    return parser.parse_args(argv)


def _resolve_show_tool_results(cli_value: bool | None) -> bool:
    if cli_value is not None:
        return cli_value
    config = _load_ui_config()
    value = config.get("show_tool_results")
    return bool(value) if isinstance(value, bool) else True


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        provider = OpenAIProvider()
    except ProviderError as error:
        print(f"Error: {error}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 2
    store = SessionStore()
    session_id = args.session or store.create()
    show_tool_results = _resolve_show_tool_results(args.show_tool_results)
    ui = TerminalUI(json_mode=args.json_mode, show_tool_results=show_tool_results)
    engine = QueryEngine(provider, store, session_id, ui.authorize, ui.event)
    print(f"Session: {session_id}", file=sys.stderr)
    print("Enter sends. Shift+Enter adds a newline.", file=sys.stderr)
    try:
        while True:
            prompt = ui.prompt()
            if not prompt:
                return 0
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
