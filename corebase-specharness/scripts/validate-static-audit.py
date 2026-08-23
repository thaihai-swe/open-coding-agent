#!/usr/bin/env python3
"""Run the source-only lean-core static audit."""

import argparse
from pathlib import Path
import sys

SCRIPT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_ROOT))

from core._lib.doctor_checks import check_static_audit  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="", help="Installed kit root")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else SCRIPT_ROOT.parents[1]
    failures = check_static_audit(root)
    if failures:
        print("static audit failed:", file=sys.stderr)
        print("\n".join(f"- {failure}" for failure in failures), file=sys.stderr)
        return 1
    print("static audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
