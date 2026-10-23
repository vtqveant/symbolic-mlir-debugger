"""Agent-facing, structured feedback for MLIR programs.

This module is the stable interface for automated coding loops. It deliberately
returns JSON-serializable dictionaries and never prints analysis output to
stdout. The interactive DAP server remains the adapter for editors.
"""

from __future__ import annotations

import logging
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from .compiler import validate_mlir_text
from .interpreter.parser import MLIRParser
from .interpreter.path_explorer import PathExplorer
from .interpreter.stepper import ExecutionStepper

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"
_LINE_RE = re.compile(r"(?:line|lineno)[^0-9]*(\d+)", re.IGNORECASE)


def _diagnostic(
    kind: str,
    message: str,
    severity: str = "error",
    line: Optional[int] = None,
    operation: Optional[str] = None,
) -> Dict[str, Any]:
    diagnostic: Dict[str, Any] = {
        "severity": severity,
        "kind": kind,
        "message": message,
        "line": line,
        "operation": operation,
    }
    return diagnostic


def _line_from_exception(exc: BaseException) -> Optional[int]:
    line = getattr(exc, "line", None)
    if isinstance(line, int) and line > 0:
        return line
    match = _LINE_RE.search(str(exc))
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _base_report(source: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "program": source,
        "function": None,
        "diagnostics": [],
        "paths": [],
        "summary": {
            "path_count": 0,
            "function_count": 0,
            "truncated": False,
            "limit_reason": None,
            "seed": 0,
            "duration_ms": 0,
        },
    }


def _normalize_inputs(
    inputs: Optional[Mapping[str, Any]],
) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    if not inputs:
        return {}, None
    normalized: Dict[str, int] = {}
    for raw_key, raw_value in inputs.items():
        key = str(raw_key).lstrip("%")
        if not key:
            return None, "input name cannot be empty"
        try:
            normalized[key] = int(raw_value)
        except (TypeError, ValueError):
            return None, f"input '{key}' must be an integer, got {raw_value!r}"
    return normalized, None


def _analyze_path(
    path: Path,
    source: str,
    inputs: Optional[Mapping[str, Any]] = None,
    max_paths: int = 10,
    seed: Optional[int] = 0,
) -> Dict[str, Any]:
    report = _base_report(source)
    report["summary"]["seed"] = seed if seed is not None else 0
    start = time.monotonic()

    if max_paths < 0:
        report["status"] = "error"
        report["diagnostics"].append(_diagnostic("limit", "max_paths must be non-negative"))
        return report

    concrete_inputs, input_error = _normalize_inputs(inputs)
    if input_error:
        report["status"] = "error"
        report["diagnostics"].append(_diagnostic("input", input_error))
        return report

    # Compiler validation is local-first and optional. The agent still uses the
    # in-tree parser below, so a missing mlir-opt never blocks analysis.
    try:
        source_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report["status"] = "error"
        report["diagnostics"].append(_diagnostic("io", f"cannot read file: {exc}"))
        return report
    compiler_report = validate_mlir_text(source_text, source, fallback_to_internal=False)
    report["summary"]["compiler"] = {
        "source": compiler_report.get("source"),
        "available": compiler_report.get("available", False),
        "tool": compiler_report.get("tool"),
    }
    report["diagnostics"].extend(compiler_report.get("diagnostics", []))

    # Parse so malformed MLIR is reported as a parse diagnostic rather than an
    # opaque stepper/execution failure.
    try:
        functions = MLIRParser().parse_file(str(path))
    except Exception as exc:  # noqa: BLE001 - converted into a diagnostic
        report["status"] = "error"
        report["diagnostics"].append(_diagnostic("parse", str(exc), line=_line_from_exception(exc)))
        report["summary"]["duration_ms"] = round((time.monotonic() - start) * 1000, 2)
        return report

    report["summary"]["function_count"] = len(functions)
    if not functions:
        report["status"] = "error"
        report["diagnostics"].append(_diagnostic("parse", "no functions found in the module"))
        report["summary"]["duration_ms"] = round((time.monotonic() - start) * 1000, 2)
        return report

    try:
        stepper = ExecutionStepper(str(path), concrete_inputs=concrete_inputs or {})
    except Exception as exc:  # noqa: BLE001 - converted into a diagnostic
        report["status"] = "error"
        report["diagnostics"].append(
            _diagnostic("execution", str(exc), line=_line_from_exception(exc))
        )
        report["summary"]["duration_ms"] = round((time.monotonic() - start) * 1000, 2)
        return report

    report["function"] = stepper.func_name
    explorer = PathExplorer(stepper)
    try:
        paths = explorer.explore(max_paths=max_paths, seed=seed)
    except Exception as exc:  # noqa: BLE001 - converted into a diagnostic
        paths = []
        report["diagnostics"].append(_diagnostic("path", str(exc), line=_line_from_exception(exc)))

    if explorer.last_error:
        report["diagnostics"].append(_diagnostic("path", explorer.last_error))

    normalized_paths = []
    for index, path_info in enumerate(paths):
        normalized_paths.append(
            {
                "index": path_info.get("path_id", index),
                "inputs": path_info.get("inputs", {}),
                "path_condition": path_info.get("path_condition", []),
                "return_value": path_info.get("return_value"),
                "depth": path_info.get("depth", 0),
            }
        )
    report["paths"] = normalized_paths

    unsupported = list(getattr(stepper.interpreter, "unsupported_operations", []) or [])
    for record in unsupported:
        operation = record.get("operation", "?")
        report["diagnostics"].append(
            _diagnostic(
                "execution",
                f"unsupported operation '{operation}'; the reported results may be incomplete",
                severity="warning",
                line=record.get("line") or None,
                operation=operation,
            )
        )

    info = explorer.last_info or {}
    truncated = bool(info.get("truncated"))
    limit_reason = info.get("reason")
    report["summary"]["path_count"] = len(normalized_paths)
    report["summary"]["truncated"] = truncated
    report["summary"]["limit_reason"] = limit_reason
    report["summary"]["unsupported_operations"] = len(unsupported)

    if truncated:
        report["diagnostics"].append(
            _diagnostic(
                "limit",
                f"path exploration stopped early ({limit_reason or 'limit'}); "
                "results may be incomplete",
                severity="warning",
            )
        )
    if not normalized_paths and not report["diagnostics"]:
        report["diagnostics"].append(
            _diagnostic(
                "path",
                "no feasible completed paths were found for the program",
                severity="warning",
            )
        )

    if any(d["severity"] == "error" for d in report["diagnostics"]):
        report["status"] = "error"
    report["summary"]["duration_ms"] = round((time.monotonic() - start) * 1000, 2)
    return report


def analyze_file(
    path: Union[str, Path],
    inputs: Optional[Mapping[str, Any]] = None,
    max_paths: int = 10,
    seed: Optional[int] = 0,
) -> Dict[str, Any]:
    """Analyze an MLIR file and return a structured feedback report."""
    source_path = Path(path)
    if not source_path.exists():
        report = _base_report(str(path))
        report["status"] = "error"
        report["diagnostics"].append(_diagnostic("io", f"file not found: {source_path}"))
        return report
    try:
        source_path.read_text(encoding="utf-8")
    except OSError as exc:
        report = _base_report(str(path))
        report["status"] = "error"
        report["diagnostics"].append(_diagnostic("io", f"cannot read file: {exc}"))
        return report
    return _analyze_path(source_path, str(path), inputs, max_paths, seed)


def analyze_text(
    text: str,
    source_name: str = "<memory>",
    inputs: Optional[Mapping[str, Any]] = None,
    max_paths: int = 10,
    seed: Optional[int] = 0,
) -> Dict[str, Any]:
    """Analyze MLIR text and return a structured feedback report."""
    with tempfile.TemporaryDirectory(prefix="smlir-agent-") as tmpdir:
        path = Path(tmpdir) / "program.mlir"
        path.write_text(text, encoding="utf-8")
        return _analyze_path(path, source_name, inputs, max_paths, seed)
