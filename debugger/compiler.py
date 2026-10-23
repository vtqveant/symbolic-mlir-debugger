"""Local-first MLIR validation adapters.

The default path invokes a local ``mlir-opt`` when available and falls back to
the in-tree parser for a best-effort syntax check. Remote validation is opt-in
via an explicit endpoint; no network call happens by default.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

_LOCATION_RE = re.compile(
    r"^(?P<file>.*?):(?P<line>\d+):(?P<column>\d+):\s+"
    r"(?P<severity>error|warning|note):\s+(?P<message>.*)$"
)
_GENERIC_RE = re.compile(r"^(?P<severity>error|warning|note):\s+(?P<message>.*)$")
_LINE_RE = re.compile(r"(?:line|lineno)[^0-9]*(\d+)", re.IGNORECASE)

_TOOL_NAMES = ("mlir-opt", "mlir-opt-18", "mlir-opt-17", "mlir-opt-16", "mlir-opt-15")


def find_local_mlir_opt() -> Optional[str]:
    """Return the configured/available ``mlir-opt`` executable, if any."""
    configured = os.environ.get("SMD_MLIR_OPT")
    if configured:
        return configured if Path(configured).exists() or shutil.which(configured) else None
    for name in _TOOL_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _diagnostic(
    message: str,
    severity: str = "error",
    line: Optional[int] = None,
    source: str = "unknown",
) -> Dict[str, Any]:
    return {
        "severity": severity if severity in ("error", "warning", "info") else "error",
        "kind": "validation",
        "message": message,
        "line": line,
        "operation": None,
        "source": source,
    }


def _parse_tool_output(stderr: str, stdout: str, source: str) -> List[Dict[str, Any]]:
    diagnostics: List[Dict[str, Any]] = []
    for line in (stderr + "\n" + stdout).splitlines():
        line = line.strip()
        if not line:
            continue
        match = _LOCATION_RE.match(line)
        if match:
            severity = "warning" if match.group("severity") in ("warning", "note") else "error"
            diagnostics.append(
                _diagnostic(
                    match.group("message"),
                    severity=severity,
                    line=int(match.group("line")),
                    source=source,
                )
            )
            continue
        match = _GENERIC_RE.match(line)
        if match:
            severity = "warning" if match.group("severity") in ("warning", "note") else "error"
            diagnostics.append(
                _diagnostic(match.group("message"), severity=severity, source=source)
            )
    return diagnostics


def _validate_with_tool(tool: str, text: str, timeout: int) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as handle:
        handle.write(text)
        path = Path(handle.name)
    try:
        commands = [
            [tool, "--allow-unregistered-dialect", str(path)],
            [tool, str(path)],
        ]
        last_result = None
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            last_result = result
            if result.returncode == 0 or "unknown argument" not in result.stderr.lower():
                break
        assert last_result is not None
        diagnostics = _parse_tool_output(
            last_result.stderr or "", last_result.stdout or "", "mlir-opt"
        )
        if last_result.returncode != 0 and not diagnostics:
            diagnostics.append(
                _diagnostic(
                    f"mlir-opt failed with exit code {last_result.returncode}",
                    source="mlir-opt",
                )
            )
        return {
            "valid": not any(d["severity"] == "error" for d in diagnostics),
            "source": "mlir-opt",
            "available": True,
            "tool": tool,
            "diagnostics": diagnostics,
        }
    except subprocess.TimeoutExpired:
        return {
            "valid": False,
            "source": "mlir-opt",
            "available": True,
            "tool": tool,
            "diagnostics": [_diagnostic("mlir-opt validation timed out", source="mlir-opt")],
        }
    except OSError as exc:
        return {
            "valid": False,
            "source": "mlir-opt",
            "available": True,
            "tool": tool,
            "diagnostics": [_diagnostic(f"could not run mlir-opt: {exc}", source="mlir-opt")],
        }
    finally:
        path.unlink(missing_ok=True)


def _validate_internal(text: str) -> Dict[str, Any]:
    from .interpreter.parser import MLIRParser

    try:
        MLIRParser().parse_string(text)
        return {
            "valid": True,
            "source": "internal",
            "available": True,
            "tool": None,
            "diagnostics": [],
        }
    except Exception as exc:  # noqa: BLE001 - converted to a diagnostic
        match = _LINE_RE.search(str(exc))
        line = int(match.group(1)) if match else None
        return {
            "valid": False,
            "source": "internal",
            "available": True,
            "tool": None,
            "diagnostics": [_diagnostic(str(exc), line=line, source="internal")],
        }


def _validate_remote(text: str, filename: str, endpoint: str, timeout: int) -> Dict[str, Any]:
    try:
        import requests
    except ImportError:
        return {
            "valid": False,
            "source": "remote",
            "available": False,
            "tool": endpoint,
            "diagnostics": [
                _diagnostic("requests is required for remote validation", source="remote")
            ],
        }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "textDocument/diagnostic",
        "params": {
            "textDocument": {
                "uri": f"file:///{filename}",
                "languageId": "mlir",
                "version": 1,
                "text": text,
            }
        },
    }
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")
        result = response.json()
        items = result.get("result", {}).get("items", [])
        diagnostics = []
        for item in items:
            severity = "warning" if item.get("severity", 1) != 1 else "error"
            line = None
            if item.get("range"):
                line = item["range"]["start"]["line"] + 1
            diagnostics.append(
                _diagnostic(item.get("message", "validation error"), severity, line, "remote")
            )
        return {
            "valid": not any(d["severity"] == "error" for d in diagnostics),
            "source": "remote",
            "available": True,
            "tool": endpoint,
            "diagnostics": diagnostics,
        }
    except Exception as exc:  # noqa: BLE001 - converted to a diagnostic
        return {
            "valid": False,
            "source": "remote",
            "available": False,
            "tool": endpoint,
            "diagnostics": [_diagnostic(f"remote validation failed: {exc}", source="remote")],
        }


def validate_mlir_text(
    text: str,
    filename: str = "<memory>",
    *,
    local_tool: Optional[str] = None,
    endpoint: Optional[str] = None,
    fallback_to_internal: bool = False,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Validate MLIR text, local-first.

    Order: explicit/auto-detected local ``mlir-opt``, optional explicit remote
    endpoint, then the in-tree parser only when ``fallback_to_internal`` is true.
    """
    if endpoint:
        return _validate_remote(text, filename, endpoint, timeout)

    tool = local_tool or find_local_mlir_opt()
    if tool:
        return _validate_with_tool(tool, text, timeout)

    if fallback_to_internal:
        return _validate_internal(text)

    return {
        "valid": True,
        "source": "unavailable",
        "available": False,
        "tool": None,
        "diagnostics": [],
    }


def validate_mlir_file(
    path: Union[str, Path],
    *,
    local_tool: Optional[str] = None,
    endpoint: Optional[str] = None,
    fallback_to_internal: bool = False,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Validate an MLIR file using :func:`validate_mlir_text`."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "valid": False,
            "source": "io",
            "available": False,
            "tool": None,
            "diagnostics": [_diagnostic(f"cannot read {path}: {exc}", source="io")],
        }
    return validate_mlir_text(
        text,
        str(path),
        local_tool=local_tool,
        endpoint=endpoint,
        fallback_to_internal=fallback_to_internal,
        timeout=timeout,
    )
