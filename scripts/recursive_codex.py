#!/usr/bin/env python3
"""Unified command line entry point for Recursive Codex."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_project import audit


def main() -> int:
    parser = argparse.ArgumentParser(prog="recursive-codex", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    audit_parser = subcommands.add_parser("audit", help="audit project state and record graph")
    audit_parser.add_argument("root", nargs="?", default=".", type=Path)
    audit_parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"AUDIT {report['status'].upper()} {args.root.resolve()}")
        print(json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        for error in report["errors"]:
            print(f"ERROR: {error}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
