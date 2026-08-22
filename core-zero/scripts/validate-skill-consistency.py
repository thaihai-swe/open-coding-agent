#!/usr/bin/env python3
"""Validate the shipped direct-skill contracts and canonical route registry."""

import argparse
from pathlib import Path
import re
import sys

SCRIPT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_ROOT))

from core._lib.doctor_checks import (  # noqa: E402
    COMMAND_RE,
    check_context_routes,
    check_skill_contracts,
)
from core._lib.routing_metadata import load_routes, normalize_writes  # noqa: E402


def route_warnings(root, routes):
    """Return advisory route-contract findings without failing validation."""
    warnings = []
    by_name = {row.get("skill"): row for row in routes if row.get("skill")}
    written = {
        item["path"]
        for row in routes
        for item in normalize_writes(row)
        if item["kind"] == "file"
    }
    for row in routes:
        label = row.get("skill") or "unnamed"
        skill_path = Path(root) / "skills" / label / "SKILL.md"
        if skill_path.is_file():
            text = skill_path.read_text(encoding="utf-8", errors="ignore")
            for write in normalize_writes(row):
                filename = Path(write["path"]).name
                if write["kind"] == "file" and write["path"] not in text and filename not in text:
                    warnings.append(
                        f"context route {label} writes {write['path']} but SKILL.md never mentions it"
                    )
        for prerequisite in row.get("prerequisites", []) or []:
            if prerequisite in written:
                continue
            upstream = [
                name for name, other in by_name.items()
                if prerequisite in (other.get("feature_artifacts") or [])
            ]
            if not upstream:
                warnings.append(
                    f"context route {label} prerequisite {prerequisite} has no upstream producer"
                )
    return warnings


def validate(root):
    routes = load_routes(root).get("skills", [])
    errors = check_context_routes(root) + check_skill_contracts(root)
    warnings = route_warnings(root, routes)
    command_names = set()
    cli_text = (root / "core-zero/scripts/core/cli.py").read_text(encoding="utf-8")
    command_names.update(re.findall(r'"([a-z][a-z0-9-]+)":\s*\(', cli_text))
    for path in sorted((root / "skills").rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for command in COMMAND_RE.findall(text):
            if command.endswith("-"):
                continue
            if command not in command_names:
                errors.append(f"{path}: unknown CLI command '{command}'")
    return errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="", help="Installed kit root")
    parser.add_argument(
        "--warnings-as-errors", action="store_true",
        help="Exit non-zero when advisory route checks emit warnings",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else SCRIPT_ROOT.parents[1]
    errors, warnings = validate(root)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if errors:
        print("skill consistency validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    if args.warnings_as_errors and warnings:
        print(f"skill consistency warnings ({len(warnings)}):", file=sys.stderr)
        return 1
    print(f"validated {len(list((root / 'skills').glob('*/SKILL.md')))} direct skills and canonical routes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
