#!/usr/bin/env python3
"""Hermetic MLIR validation for CI.

Uses a local ``mlir-opt`` when available. If it is not installed, the in-tree
parser provides a best-effort syntax check and the job stays non-blocking unless
``--strict`` is passed. No network service is contacted.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from debugger.compiler import find_local_mlir_opt, validate_mlir_file, validate_mlir_text  # noqa: E402

_MLIR_BLOCK_RE = re.compile(r"(\"\"\"|''')(.*?)\1", re.DOTALL)


def _extract_python_blocks(path: Path) -> List[Dict[str, Any]]:
    content = path.read_text(encoding="utf-8")
    blocks = []
    for match in _MLIR_BLOCK_RE.finditer(content):
        code = match.group(2)
        if "module {" in code or "func.func" in code:
            blocks.append(
                {
                    "code": code,
                    "line": content[: match.start()].count("\n") + 1,
                }
            )
    return blocks


def _format_diag(diag: Dict[str, Any]) -> str:
    location = f"line {diag['line']}: " if diag.get("line") else ""
    return f"    {diag.get('severity', 'error')}: {location}{diag.get('message', '')}"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail when the in-tree fallback reports errors (requires no mlir-opt)",
    )
    args = parser.parse_args(argv)

    tool = find_local_mlir_opt()
    if tool:
        print(f"Using local MLIR tool: {tool}")
    elif not args.strict:
        print(
            "No local mlir-opt found. Skipping build-time MLIR validation; "
            "pass --strict to force the in-tree parser fallback."
        )
        return 0
    else:
        print("No local mlir-opt found; strict in-tree parser fallback enabled.")

    problems: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    mlir_files = [
        p
        for p in REPO_ROOT.rglob("*.mlir")
        if ".venv" not in p.parts and "__pycache__" not in p.parts
    ]

    print(f"Validating {len(mlir_files)} .mlir files...")
    for path in sorted(mlir_files):
        result = validate_mlir_file(path, fallback_to_internal=True)
        errors = [d for d in result["diagnostics"] if d.get("severity") == "error"]
        if not errors:
            print(f"  [OK]   {path.relative_to(REPO_ROOT)}")
            continue
        record = {"file": str(path.relative_to(REPO_ROOT)), "diagnostics": result["diagnostics"]}
        if result["source"] == "internal" and not args.strict:
            warnings.append(record)
            print(f"  [WARN] {path.relative_to(REPO_ROOT)} (in-tree parser)")
        else:
            problems.append(record)
            print(f"  [FAIL] {path.relative_to(REPO_ROOT)}")

    python_files = [
        REPO_ROOT / "debugger/tests/test_advanced_dap.py",
        REPO_ROOT / "debugger/tests/test_debug.py",
        REPO_ROOT / "debugger/tests/test_integration.py",
        REPO_ROOT / "debugger/tests/test_interpreter.py",
        REPO_ROOT / "debugger/tests/test_memory_ops.py",
        REPO_ROOT / "debugger/tests/test_operations.py",
        REPO_ROOT / "debugger/tests/test_parser.py",
    ]
    print(f"\nValidating embedded MLIR in {len(python_files)} Python files...")
    for path in python_files:
        if not path.exists():
            print(f"  [WARN] {path.relative_to(REPO_ROOT)} (not found)")
            continue
        file_errors = []
        for block in _extract_python_blocks(path):
            result = validate_mlir_text(
                block["code"],
                f"{path}:block_line_{block['line']}",
                fallback_to_internal=True,
            )
            errors = [d for d in result["diagnostics"] if d.get("severity") == "error"]
            if not errors:
                continue
            record = {
                "file": str(path.relative_to(REPO_ROOT)),
                "line": block["line"],
                "diagnostics": result["diagnostics"],
            }
            if result["source"] == "internal" and not args.strict:
                warnings.append(record)
            else:
                file_errors.append(record)
        if file_errors:
            problems.extend(file_errors)
            print(f"  [FAIL] {path.relative_to(REPO_ROOT)}")
        else:
            print(f"  [OK]   {path.relative_to(REPO_ROOT)}")

    if warnings:
        print(f"\n{len(warnings)} best-effort warning(s) from the in-tree parser:")
        for record in warnings[:20]:
            print(f"  {record['file']}")
            for diag in record["diagnostics"]:
                if diag.get("severity") == "error":
                    print(_format_diag(diag))

    if problems:
        print("\n" + "=" * 80)
        print("MLIR SYNTAX VALIDATION FAILED")
        print("=" * 80)
        for record in problems:
            print(f"\nFile: {record['file']}")
            if record.get("line"):
                print(f"  Line: {record['line']}")
            for diag in record["diagnostics"]:
                print(_format_diag(diag))
        sys.exit(1)

    print("\nMLIR syntax validation completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
