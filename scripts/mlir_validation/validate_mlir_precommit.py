#!/usr/bin/env python3
"""Pre-commit MLIR validation using local tools, never a network service."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from debugger.compiler import find_local_mlir_opt, validate_mlir_file, validate_mlir_text  # noqa: E402

_MLIR_BLOCK_RE = re.compile(r"(\"\"\"|''')(.*?)\1", re.DOTALL)


def get_staged_files() -> List[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.CalledProcessError as exc:
        print(f"Error getting staged files: {exc}")
        return []


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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="validate staged files")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="use the in-tree parser as a blocking fallback when mlir-opt is missing",
    )
    parser.add_argument("files", nargs="*", help="specific files to validate")
    args = parser.parse_args(argv)

    if args.files:
        files = args.files
    elif args.staged:
        files = get_staged_files()
    else:
        files = [str(p.relative_to(REPO_ROOT)) for p in REPO_ROOT.rglob("*.mlir")]

    files = [f for f in files if f.endswith(".mlir") or f.endswith(".py")]
    if not files:
        print("No MLIR or Python files to validate.")
        return 0

    tool = find_local_mlir_opt()
    if tool:
        print(f"Using local MLIR tool: {tool}")
    elif not args.strict:
        print(
            "No local mlir-opt found. MLIR validation skipped; "
            "install mlir-opt or pass --strict to use the in-tree parser."
        )
        return 0
    else:
        print("No local mlir-opt found; strict in-tree parser fallback enabled.")

    problems: List[Dict[str, Any]] = []
    for raw in sorted(files):
        path = (REPO_ROOT / raw).resolve()
        if not path.exists():
            print(f"  [WARN] {raw} (not found)")
            continue

        if path.suffix == ".mlir":
            result = validate_mlir_file(path, fallback_to_internal=True)
            errors = [d for d in result["diagnostics"] if d.get("severity") == "error"]
            if errors and (result["source"] != "internal" or args.strict):
                problems.append({"file": raw, "diagnostics": result["diagnostics"]})
                print(f"  [FAIL] {raw}")
            elif errors:
                print(f"  [WARN] {raw} (in-tree parser)")
            else:
                print(f"  [OK]   {raw}")
        elif path.suffix == ".py":
            file_problems = []
            for block in _extract_python_blocks(path):
                result = validate_mlir_text(
                    block["code"],
                    f"{raw}:block_line_{block['line']}",
                    fallback_to_internal=True,
                )
                errors = [d for d in result["diagnostics"] if d.get("severity") == "error"]
                if not errors:
                    continue
                record = {
                    "file": raw,
                    "line": block["line"],
                    "diagnostics": result["diagnostics"],
                }
                if result["source"] == "internal" and not args.strict:
                    print(f"  [WARN] {raw}:{block['line']} (in-tree parser)")
                else:
                    file_problems.append(record)
            if file_problems:
                problems.extend(file_problems)
                print(f"  [FAIL] {raw}")
            else:
                print(f"  [OK]   {raw}")

    if problems:
        print("\nMLIR SYNTAX VALIDATION FAILED")
        for record in problems:
            print(f"\nFile: {record['file']}")
            if record.get("line"):
                print(f"  Line: {record['line']}")
            for diag in record["diagnostics"]:
                location = f"line {diag['line']}: " if diag.get("line") else ""
                print(f"  {diag.get('severity', 'error')}: {location}{diag.get('message', '')}")
        return 1
    print("\nMLIR syntax validation completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
