"""Command-line entry point for the Symbolic MLIR Debugger.

Usage:
    python -m debugger analyze <program.mlir> [--json]
    python -m debugger dap
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List, Optional

from .agent import analyze_file


def _parse_inputs(items: Optional[List[str]]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"invalid --input '{item}'; expected NAME=VALUE")
        name, raw = item.split("=", 1)
        name = name.lstrip("%").strip()
        if not name:
            raise ValueError(f"invalid --input '{item}'; input name is empty")
        try:
            result[name] = int(raw, 0)
        except ValueError as exc:
            raise ValueError(f"invalid integer for input '{name}': {raw!r}") from exc
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m debugger",
        description="Structured feedback and DAP debugging for MLIR programs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser(
        "analyze",
        help="analyze an MLIR program and emit structured feedback",
        description=(
            "Parse and symbolically explore an MLIR program. Emits actionable diagnostics "
            "and feasible paths as JSON with --json."
        ),
    )
    analyze.add_argument("program", help="path to the .mlir file")
    analyze.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="concrete input for a function argument (repeatable, integer values)",
    )
    analyze.add_argument(
        "--max-paths",
        type=int,
        default=10,
        help="maximum number of feasible paths to explore (default: 10)",
    )
    analyze.add_argument(
        "--seed",
        type=int,
        default=0,
        help="deterministic exploration seed (default: 0)",
    )
    analyze.add_argument(
        "--json",
        action="store_true",
        help="emit the complete feedback report as JSON",
    )

    sub.add_parser(
        "dap",
        help="run the stdio Debug Adapter Protocol server",
        description="Run the interactive DAP server (normally launched by dap_client).",
    )
    return parser


def _print_human(report: Dict[str, object]) -> None:
    print(f"status:   {report.get('status')}")
    print(f"program:  {report.get('program')}")
    print(f"function: {report.get('function') or '(none)'}")
    summary = report.get("summary") or {}
    print(
        "paths:    {path_count} (truncated: {truncated}, seed: {seed})".format(
            path_count=summary.get("path_count", 0),
            truncated=summary.get("truncated", False),
            seed=summary.get("seed", 0),
        )
    )
    diagnostics = report.get("diagnostics") or []
    if diagnostics:
        print("diagnostics:")
        for diagnostic in diagnostics:
            location = ""
            if diagnostic.get("line"):
                location = f" line {diagnostic['line']}"
            operation = ""
            if diagnostic.get("operation"):
                operation = f" [{diagnostic['operation']}]"
            print(
                "  - {severity}/{kind}{location}{operation}: {message}".format(
                    severity=diagnostic.get("severity"),
                    kind=diagnostic.get("kind"),
                    location=location,
                    operation=operation,
                    message=diagnostic.get("message"),
                )
            )
    for path in (report.get("paths") or [])[:5]:
        print(
            "  path {index}: inputs={inputs} return={return_value}".format(
                index=path.get("index"),
                inputs=path.get("inputs"),
                return_value=path.get("return_value"),
            )
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "dap":
        from .dap_server import main as dap_main

        dap_main()
        return 0

    try:
        inputs = _parse_inputs(args.input)
    except ValueError as exc:
        parser.error(str(exc))

    report = analyze_file(
        args.program,
        inputs=inputs,
        max_paths=args.max_paths,
        seed=args.seed,
    )

    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_human(report)

    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
