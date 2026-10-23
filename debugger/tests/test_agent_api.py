"""Tests for the stable agent-facing analysis API."""

import json
import subprocess
import sys
from pathlib import Path

from debugger.agent import analyze_file, analyze_text

REPO_ROOT = Path(__file__).resolve().parents[2]
CONDITIONAL = REPO_ROOT / "debugger" / "fixtures" / "conditional_branch.mlir"
ARITH_BASIC = REPO_ROOT / "debugger" / "fixtures" / "arith_basic_ops.mlir"


def test_analyze_file_reports_paths():
    report = analyze_file(CONDITIONAL, seed=0, max_paths=5)
    assert report["schema_version"] == "1.0"
    assert report["status"] == "ok"
    assert report["function"] == "max"
    assert report["paths"]
    assert report["summary"]["path_count"] == len(report["paths"])
    assert report["summary"]["seed"] == 0
    assert "compiler" in report["summary"]
    for path in report["paths"]:
        assert "inputs" in path
        assert "path_condition" in path


def test_analyze_is_deterministic_for_a_seed():
    first = analyze_file(CONDITIONAL, seed=7, max_paths=5)
    second = analyze_file(CONDITIONAL, seed=7, max_paths=5)
    assert first["paths"] == second["paths"]


def test_analyze_reports_parse_errors_without_tracebacks():
    report = analyze_text("this is not mlir", source_name="bad.mlir")
    assert report["status"] == "error"
    assert report["diagnostics"]
    assert report["diagnostics"][0]["kind"] == "parse"
    assert report["diagnostics"][0]["line"] == 1
    assert report["paths"] == []


def test_analyze_reports_unsupported_operations():
    report = analyze_file(ARITH_BASIC, seed=0, max_paths=2)
    messages = [d["message"] for d in report["diagnostics"]]
    assert any("unsupported operation" in message for message in messages), messages
    assert report["summary"]["unsupported_operations"] >= 1


def test_analyze_cli_emits_json():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "debugger",
            "analyze",
            str(CONDITIONAL),
            "--json",
            "--max-paths",
            "2",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "ok"
    assert report["function"] == "max"
    assert report["summary"]["path_count"] >= 1
