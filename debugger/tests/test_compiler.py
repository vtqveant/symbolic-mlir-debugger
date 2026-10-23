"""Tests for the local-first MLIR compiler validation adapter."""

import stat
from pathlib import Path

from debugger.compiler import validate_mlir_text

VALID = """module {
  func.func @id(%a: i32) -> i32 {
    return %a : i32
  }
}
"""


def test_internal_fallback_valid():
    result = validate_mlir_text(VALID, "valid.mlir", fallback_to_internal=True)
    assert result["source"] == "internal"
    assert result["valid"] is True
    assert result["diagnostics"] == []


def test_internal_fallback_invalid():
    result = validate_mlir_text("not mlir", "bad.mlir", fallback_to_internal=True)
    assert result["source"] == "internal"
    assert result["valid"] is False
    assert result["diagnostics"]
    assert result["diagnostics"][0]["kind"] == "validation"


def test_local_tool_diagnostics_are_normalized(tmp_path: Path):
    tool = tmp_path / "fake-mlir-opt"
    tool.write_text(
        "#!/bin/sh\n" "echo 'input.mlir:2:3: error: expected operation' >&2\n" "exit 1\n"
    )
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    result = validate_mlir_text(VALID, "input.mlir", local_tool=str(tool))
    assert result["source"] == "mlir-opt"
    assert result["available"] is True
    assert result["valid"] is False
    diag = result["diagnostics"][0]
    assert diag["line"] == 2
    assert diag["severity"] == "error"
    assert "expected operation" in diag["message"]


def test_no_tool_is_not_an_error_by_default():
    result = validate_mlir_text(VALID, "valid.mlir", local_tool=None)
    if result["source"] == "unavailable":
        assert result["valid"] is True
        assert result["available"] is False
