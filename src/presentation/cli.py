from __future__ import annotations

import argparse
import sys
import traceback

from ..application.query_engine import QueryEngine
from ..domain.errors import ProviderError
from ..infrastructure.providers import OpenAIProvider
from ..infrastructure.session_store import SessionStore
from .terminal_ui import TerminalUI


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenAI-compatible coding-agent REPL")
    parser.add_argument("--session", help="Resume this session ID")
    parser.add_argument("--json", action="store_true", dest="json_mode", help="Emit structured JSON events")
    parser.add_argument("--debug", action="store_true", help="Print full exception tracebacks during errors")
    return parser.parse_args(argv)


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
    ui = TerminalUI(json_mode=args.json_mode)
    engine = QueryEngine(provider, store, session_id, ui.authorize, ui.event)
    print(f"Session: {session_id}", file=sys.stderr)
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
