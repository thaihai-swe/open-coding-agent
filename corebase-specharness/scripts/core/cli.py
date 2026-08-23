#!/usr/bin/env python3
"""Embedded CoreBase SpecHarness command-line interface."""

import argparse
from importlib import import_module
import json
import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
scripts_root = str(_script_dir.parent)
if scripts_root not in sys.path:
    sys.path.insert(0, scripts_root)

COMMANDS = {
    "init": ("initialize CoreBase SpecHarness repository scaffolding", "core.handlers.lifecycle", "init"),
    "status": ("report feature status", "core.handlers.lifecycle", "status"),
    "context-pack": ("plan a named-skill context pack", "core.handlers.context", "context_pack"),
    "context-load": ("load named-skill context", "core.handlers.context", "context_load"),
    "context-explain": ("explain named-skill context selection", "core.handlers.context", "context_explain"),
    "status-set": ("set a feature lifecycle state", "core.handlers.envelope", "status_set"),
    "skill-enter": ("enter a named skill: load context, open session, set phase", "core.handlers.envelope", "skill_enter"),
    "skill-exit": ("exit a named skill: record handoff and set phase", "core.handlers.envelope", "skill_exit"),
    "session-start": ("start or resume a feature session", "core.handlers.sessions", "session_start"),
    "session-checkpoint": ("append a session checkpoint", "core.handlers.sessions", "session_checkpoint"),
    "session-end": ("close a feature session", "core.handlers.sessions", "session_end"),
    "task-check": ("validate tasks and list ready work", "core.handlers.tasks", "task_check"),
    "task-start": ("start an unblocked task", "core.handlers.tasks", "task_start"),
    "task-done": ("complete a task with evidence", "core.handlers.tasks", "task_done"),
    "task-block": ("block a task with a reason", "core.handlers.tasks", "task_block"),
    "phase-check": ("check phase preconditions", "core.handlers.lifecycle", "phase_check"),
    "artifact-check": ("validate feature artifacts", "core.handlers.lifecycle", "artifact_check"),
    "verify": ("run artifact checks and confirmed gates", "core.handlers.lifecycle", "verify"),
    "doctor": ("validate the embedded package", "core.harness.doctor", "doctor"),
    "gate-check": ("validate configured gates", "core.handlers.diagnostics", "gate_check"),
    "gate-list": ("list configured gates", "core.handlers.diagnostics", "gate_list"),
    "provider-list": ("list optional tool providers", "core.handlers.diagnostics", "provider_list"),
    "provider-check": ("check optional tool providers", "core.handlers.diagnostics", "provider_check"),
    "provider-run": ("run an explicitly selected provider action", "core.handlers.diagnostics", "provider_run"),
    "memory-audit": ("audit durable memory files", "core.handlers.diagnostics", "memory_audit"),
    "memory-gate": ("check memory thresholds", "core.handlers.diagnostics", "memory_gate"),
    "adr-generate": ("generate an ADR from recorded decisions", "core.handlers.diagnostics", "adr_generate"),
}


def _common(parser, *, feature=False, dry_run=False):
    parser.add_argument("--root", default="", help="Repository root")
    if feature:
        parser.add_argument("--feature", required=True, help="Feature slug")
    if dry_run:
        parser.add_argument("--dry-run", action="store_true", help="Report without modifying files")
    parser.add_argument("--json", action="store_true", help="Print JSON")


def _context_options(parser):
    _common(parser, dry_run=True)
    parser.add_argument("--feature", default="", help="Feature slug when the skill requires one")
    parser.add_argument("--task", default="", help="Active task ID when context is task-scoped")
    parser.add_argument("--skill", required=True, help="Named skill route")
    parser.add_argument("--intent", default="", help="Keywords used only inside declared route files")
    parser.add_argument("--budget", type=int, default=0, help="Context payload token budget")
    parser.add_argument("--delta-from", default="", help="Previous context-pack JSON")
    parser.add_argument(
        "--full", action="store_true",
        help="Return the complete pack; skip session auto-delta",
    )
    parser.add_argument(
        "--add-source", action="append", default=[],
        help="Repository-relative source file to include explicitly (repeatable)",
    )


def _session_options(parser, command):
    _common(parser, feature=True, dry_run=command != "session-start")
    if command == "session-start":
        parser.add_argument("--skill", required=True, help="Active named skill")
        parser.add_argument("--intent", default="", help="Session intent")
        parser.add_argument("--budget", type=int, default=0, help="Context payload token budget")
        parser.add_argument("--objective", default="", help="Session objective")
    else:
        parser.add_argument("--progress", default="", help="Progress checkpoint")
        parser.add_argument("--handoff-file", default="", help="Handoff text file")
        parser.add_argument("--next-action", default="", help="Next action")
        parser.add_argument("--blocker", action="append", default=[], help="Blocker text")
        parser.add_argument("--decision", action="append", default=[], help="Decision text")
    if command == "session-end":
        parser.add_argument("--candidate", action="append", default=[], help="Memory candidate")
        parser.add_argument("--extract-file", default="", help="Candidate extract file")


def _task_options(parser, command):
    _common(parser, feature=True, dry_run=command != "task-check")
    if command != "task-check":
        parser.add_argument("--task", required=True, help="Task ID")
        parser.add_argument("--note", default="", help="Task note or blocker")
    if command == "task-done":
        parser.add_argument("--evidence", action="append", default=[], help="Proof evidence")
        parser.add_argument("--evidence-file", default="", help="Proof evidence file")


def _parser():
    parser = argparse.ArgumentParser(prog="corebase-specharness", description="CoreBase SpecHarness local workflow operations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, (help_text, _, _) in COMMANDS.items():
        sub = subparsers.add_parser(command, help=help_text)
        if command == "init":
            _common(sub, dry_run=True)
        elif command == "status":
            _common(sub, dry_run=True)
            sub.add_argument("--feature", default="", help="Feature slug")
            sub.add_argument("--next", action="store_true", help="Report valid next handoffs without choosing one")
        elif command in {"context-pack", "context-load", "context-explain", "skill-enter"}:
            _context_options(sub)
            if command == "skill-enter":
                sub.add_argument("--objective", default="", help="Session objective")
        elif command == "status-set":
            _common(sub, feature=True, dry_run=True)
            sub.add_argument("--phase", required=True, help="status.md lifecycle token")
            sub.add_argument("--next-step", default="", help="Next step recorded in status.md")
            sub.add_argument("--verification-override", action="store_true", help="Authorize Done with an explicit audited override")
            sub.add_argument("--override-reason", default="", help="Required reason for a verification override")
        elif command == "skill-exit":
            _common(sub, dry_run=True)
            sub.add_argument("--feature", default="", help="Feature slug when the skill requires one")
            sub.add_argument("--skill", required=True, help="Named skill route")
            sub.add_argument("--phase", default="", help="Exit lifecycle token; defaults to the route exit state")
            sub.add_argument("--handoff", default="", help="Suggested next skill")
            sub.add_argument("--progress", default="", help="Progress checkpoint")
            sub.add_argument("--handoff-file", default="", help="Handoff text file")
            sub.add_argument("--next-action", default="", help="Next action")
            sub.add_argument("--blocker", action="append", default=[], help="Blocker text")
            sub.add_argument("--decision", action="append", default=[], help="Decision text")
            sub.add_argument("--verification-override", action="store_true", help="Authorize Done with an explicit audited override")
            sub.add_argument("--override-reason", default="", help="Required reason for a verification override")
        elif command.startswith("session-"):
            _session_options(sub, command)
        elif command.startswith("task-"):
            _task_options(sub, command)
        elif command == "phase-check":
            _common(sub, feature=True, dry_run=True)
            target = sub.add_mutually_exclusive_group(required=True)
            target.add_argument("--phase", help="Target phase")
            target.add_argument("--skill", help="Skill whose route declares the target phase")
        elif command == "artifact-check":
            _common(sub, feature=True)
            sub.add_argument("--phase", default="", help="Optional artifact phase")
            sub.add_argument("--skill", default="", help="Skill whose route declares the artifact file set")
            sub.add_argument("--trace", action="store_true", help="Include traceability")
        elif command == "verify":
            _common(sub, feature=True, dry_run=True)
            sub.add_argument("--phase", default="", help="Target phase when --skill is omitted; defaults to Verify")
            sub.add_argument("--skill", default="", help="Skill whose route declares readiness and structure")
            sub.add_argument(
                "--fast", action="store_true",
                help="Skip gates whose optional paths do not match git-changed files",
            )
        elif command == "doctor":
            _common(sub)
        elif command in {"gate-check", "gate-list"}:
            _common(sub)
            if command == "gate-check":
                sub.add_argument(
                    "--fast", action="store_true",
                    help="Skip gates whose optional paths do not match git-changed files",
                )
        elif command == "provider-list":
            _common(sub)
        elif command == "provider-check":
            _common(sub)
            sub.add_argument("--category", choices=("review", "code-intelligence"), default="")
        elif command == "provider-run":
            _common(sub, dry_run=True)
            sub.add_argument("--category", required=True, choices=("review", "code-intelligence"))
            sub.add_argument("--action", default="", help="Declared provider action; defaults by category")
            sub.add_argument("--feature", default="", help="Feature slug for provider evidence")
        elif command in {"memory-audit", "memory-gate"}:
            _common(sub)
            sub.add_argument("--mode", default="advisory", choices=("advisory", "warn", "block"))
        elif command == "adr-generate":
            _common(sub, dry_run=True)
            sub.add_argument("--feature", default="", help="Feature slug when the ADR is feature-bound")
            sub.add_argument("--title", default="", help="ADR title")
            sub.add_argument("--decision", action="append", default=[], help="Decision text")
            sub.add_argument(
                "--reversibility",
                default="Moderate",
                choices=("Easy", "Moderate", "Hard"),
                help="Reversibility recorded on the ADR log entry",
            )
    return parser


def _run(args):
    _, module_name, handler_name = COMMANDS[args.command]
    return getattr(import_module(module_name), handler_name)(args)


def _normalize(command, value):
    value = value or {}
    return {
        "command": command,
        "status": value.get("status", "ok"),
        "feature": value.get("feature", ""),
        "artifacts": value.get("artifacts", []),
        "findings": value.get("findings", []),
        "warnings": value.get("warnings", []),
        "errors": value.get("errors", []),
        "next_action": value.get("next_action", ""),
        "details": value.get("details", {}),
    }


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        result = _normalize(args.command, _run(args))
    except Exception as exc:
        result = _normalize(args.command, {"status": "failed", "errors": [str(exc)]})
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for warning in result["warnings"]:
            print(f"WARN: {warning}", file=sys.stderr)
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result["status"] in {"ok", "deferred"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
