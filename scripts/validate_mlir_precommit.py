#!/usr/bin/env python3
"""
Pre-commit hook for MLIR syntax validation.
Validates only staged/changed MLIR files to save time.
"""

import os
import sys
import requests
import re
import subprocess
from pathlib import Path

LSP_SERVER_URL = "https://api.niche-robotics.tech/api/v1/diagnostics"


def validate_mlir(mlir_code: str, uri: str = "file:///test.mlir") -> dict:
    """Validate MLIR code using the LSP server."""
    headers = {"Content-Type": "application/json"}
    data = {"mlir_code": mlir_code, "uri": uri}

    try:
        response = requests.post(LSP_SERVER_URL, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_staged_files():
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [f.strip() for f in result.stdout.split("\n") if f.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error getting staged files: {e}")
        return []


def validate_mlir_file(file_path: str) -> dict:
    """Validate a single .mlir file."""
    try:
        with open(file_path, "r") as f:
            mlir_code = f.read()
    except Exception as e:
        return {
            "file": file_path,
            "error": f"Could not read file: {e}",
        }

    uri = f"file://{os.path.abspath(file_path)}"
    result = validate_mlir(mlir_code, uri)

    return {
        "file": file_path,
        "diagnostics": result.get("diagnostics", []),
        "error": result.get("error"),
    }


def extract_mlir_from_python(file_path: str) -> list:
    """Extract MLIR code blocks from Python files."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return []

    mlir_blocks = []
    patterns = [r'"""([\s\S]*?)"""', r"'''([\s\S]*?)'''"]

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            mlir_code = match.group(1)
            if "module {" in mlir_code or "func.func" in mlir_code:
                line_start = content[: match.start()].count("\n") + 1
                mlir_blocks.append(
                    {
                        "code": mlir_code,
                        "line_start": line_start,
                    }
                )

    return mlir_blocks


def validate_python_file(file_path: str) -> list:
    """Validate MLIR code blocks in a Python file."""
    mlir_blocks = extract_mlir_from_python(file_path)
    results = []

    for i, block in enumerate(mlir_blocks):
        uri = (
            f"file://{os.path.abspath(file_path)}"
            f"#block_{i+1}_line_{block['line_start']}"
        )
        result = validate_mlir(block["code"], uri)

        if result.get("error") or result.get("diagnostics"):
            results.append(
                {
                    "file": file_path,
                    "line": block["line_start"],
                    "diagnostics": result.get("diagnostics", []),
                    "error": result.get("error"),
                }
            )

    return results


def main():
    """Main pre-commit validation function."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate MLIR syntax in staged files")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Validate only staged files",
    )
    parser.add_argument("files", nargs="*", help="Specific files to validate")
    args = parser.parse_args()

    # Get files to validate
    if args.staged:
        files_to_validate = get_staged_files()
        if not files_to_validate:
            print("No staged files to validate.")
            sys.exit(0)
    elif args.files:
        files_to_validate = args.files
    else:
        # Default: validate all MLIR and Python test files
        files_to_validate = []
        # Add all .mlir files
        mlir_files = list(Path(".").rglob("*.mlir"))
        mlir_files = [
            str(f)
            for f in mlir_files
            if ".venv" not in str(f) and "__pycache__" not in str(f)
        ]
        files_to_validate.extend(mlir_files)
        # Add Python test files
        python_files = [
            "debugger/tests/test_advanced_dap.py",
            "debugger/tests/test_debug.py",
            "debugger/tests/test_integration.py",
            "debugger/tests/test_interpreter.py",
            "debugger/tests/test_memory_ops.py",
            "debugger/tests/test_operations.py",
            "debugger/tests/test_parser.py",
        ]
        files_to_validate.extend([f for f in python_files if os.path.exists(f)])

    # Filter to only MLIR and Python files
    files_to_validate = [
        f for f in files_to_validate if f.endswith(".mlir") or f.endswith(".py")
    ]

    if not files_to_validate:
        print("No MLIR or Python files to validate.")
        sys.exit(0)

    print(f"🔍 Validating {len(files_to_validate)} files...")

    problems = []
    mlir_count = 0
    python_count = 0

    for file_path in sorted(files_to_validate):
        if not os.path.exists(file_path):
            print(f"  ⚠️  {file_path} (not found)")
            continue

        if file_path.endswith(".mlir"):
            mlir_count += 1
            result = validate_mlir_file(file_path)
            if result.get("error") or result.get("diagnostics"):
                problems.append(result)
                print(f"  ❌ {file_path}")
            else:
                print(f"  ✅ {file_path}")

        elif file_path.endswith(".py"):
            python_count += 1
            results = validate_python_file(file_path)
            if results:
                problems.extend(results)
                print(f"  ❌ {file_path}")
            else:
                print(f"  ✅ {file_path}")

    # Output results
    if problems:
        print("\n" + "=" * 80)
        print("❌ MLIR SYNTAX VALIDATION FAILED")
        print("=" * 80)
        print(
            f"\nSummary: Validated {mlir_count} .mlir files "
            f"and {python_count} Python files"
        )
        print(f"Found {len(problems)} files with issues:\n")

        for problem in problems:
            print(f"File: {problem['file']}")
            if "line" in problem:
                print(f"  Line: {problem['line']}")
            if problem.get("error"):
                print(f"  Error: {problem['error']}")
            if problem.get("diagnostics"):
                for diag in problem["diagnostics"]:
                    line = (
                        diag["range"]["start"]["line"] + 1 if diag.get("range") else "?"
                    )
                    char = (
                        diag["range"]["start"]["character"] + 1
                        if diag.get("range")
                        else "?"
                    )
                    print(f"  - Line {line}, Char {char}: " f"{diag.get('message')}")
            print()

        print("=" * 80)
        print("💡 Fix the syntax errors above before committing.")
        print("=" * 80)
        sys.exit(1)
    else:
        print("\n" + "=" * 80)
        print(f"✅ MLIR SYNTAX VALIDATION PASSED")
        print("=" * 80)
        print(f"Validated {mlir_count} .mlir files " f"and {python_count} Python files")
        print("All MLIR files and code blocks are syntactically valid!")
        print("=" * 80)
        sys.exit(0)


if __name__ == "__main__":
    main()
