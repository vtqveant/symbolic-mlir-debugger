#!/usr/bin/env python3
"""
MLIR validation script for CI pipeline.
Validates all MLIR files and embedded MLIR code in the repository.
"""

import os
import sys
import json
import requests
import glob
import re

LSP_SERVER_URL = "https://api.niche-robotics.tech/api/v1/diagnostics"


def validate_mlir(mlir_code: str, uri: str = "file:///test.mlir") -> dict:
    """Validate MLIR code using the LSP server."""
    headers = {"Content-Type": "application/json"}
    data = {"mlir_code": mlir_code, "uri": uri}

    try:
        response = requests.post(LSP_SERVER_URL, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def validate_mlir_file(file_path: str) -> dict:
    """Validate a single .mlir file."""
    with open(file_path, "r") as f:
        mlir_code = f.read()

    uri = f"file://{os.path.abspath(file_path)}"
    result = validate_mlir(mlir_code, uri)

    return {
        "file": file_path,
        "diagnostics": result.get("diagnostics", []),
        "error": result.get("error"),
    }


def extract_mlir_from_python(file_path: str) -> list:
    """Extract MLIR code blocks from Python files."""
    with open(file_path, "r") as f:
        content = f.read()

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
        uri = f"file://{os.path.abspath(file_path)}" f"#block_{i+1}_line_{block['line_start']}"
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
    """Main validation function."""
    problems = []

    # Validate .mlir files
    mlir_files = glob.glob("**/*.mlir", recursive=True)
    mlir_files = [f for f in mlir_files if ".venv" not in f and "__pycache__" not in f]

    print(f"Validating {len(mlir_files)} .mlir files...")
    for mlir_file in sorted(mlir_files):
        result = validate_mlir_file(mlir_file)
        if result.get("error") or result.get("diagnostics"):
            problems.append(result)
            print(f"  [FAIL] {mlir_file}")
        else:
            print(f"  [OK]   {mlir_file}")

    # Validate Python test files
    python_files = [
        "debugger/tests/test_advanced_dap.py",
        "debugger/tests/test_debug.py",
        "debugger/tests/test_integration.py",
        "debugger/tests/test_interpreter.py",
        "debugger/tests/test_memory_ops.py",
        "debugger/tests/test_operations.py",
        "debugger/tests/test_parser.py",
    ]

    print(f"\nValidating {len(python_files)} Python files for embedded MLIR...")
    for py_file in python_files:
        if os.path.exists(py_file):
            results = validate_python_file(py_file)
            if results:
                problems.extend(results)
                print(f"  [FAIL] {py_file}")
            else:
                print(f"  [OK]   {py_file}")
        else:
            print(f"  [WARN] {py_file} (not found)")

    # Output results
    if problems:
        print("\n" + "=" * 80)
        print("MLIR SYNTAX VALIDATION FAILED")
        print("=" * 80)

        for problem in problems:
            print(f"\nFile: {problem['file']}")
            if "line" in problem:
                print(f"  Line: {problem['line']}")
            if problem.get("error"):
                print(f"  Error: {problem['error']}")
            if problem.get("diagnostics"):
                for diag in problem["diagnostics"]:
                    line = diag["range"]["start"]["line"] + 1 if diag.get("range") else "?"
                    char = diag["range"]["start"]["character"] + 1 if diag.get("range") else "?"
                    print(f"  - Line {line}, Char {char}: " f"{diag.get('message')}")

        # Save detailed report
        with open("mlir_validation_report.json", "w") as f:
            json.dump(problems, f, indent=2)

        print("\nDetailed report saved to: mlir_validation_report.json")
        sys.exit(1)
    else:
        print("\n" + "=" * 80)
        print("ALL MLIR FILES AND CODE BLOCKS ARE SYNTACTICALLY VALID!")
        print("=" * 80)
        sys.exit(0)


if __name__ == "__main__":
    main()
