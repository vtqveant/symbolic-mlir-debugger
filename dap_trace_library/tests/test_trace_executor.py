"""Regression tests for the trace execution adapter."""

from pathlib import Path

from dap_trace_library.execution.trace_executor import TraceExecutor

REPO_ROOT = Path(__file__).resolve().parents[2]
SIMPLE_ADD = REPO_ROOT / "debugger" / "fixtures" / "simple_add.mlir"


def _trace(program: str, command: str = "disconnect") -> dict:
    return {
        "name": "trace-executor-smoke",
        "program": program,
        "session": [
            {
                "command": "initialize",
                "arguments": {
                    "adapter_id": "mlir-debugger",
                    "client_id": "trace-executor-test",
                },
                "expect": {"success": True},
            },
            {
                "command": "launch",
                "arguments": {"program": program, "noDebug": False},
                "expect": {"success": True},
            },
            {
                "command": "configurationDone",
                "arguments": {},
                "expect": {"success": True},
            },
            {
                "command": command,
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True},
            },
        ],
    }


def test_trace_executor_uses_dap_client():
    result = TraceExecutor(timeout=30).execute_trace(_trace(str(SIMPLE_ADD)), "valid trace")
    assert result["success"] is True, result
    assert result["returncode"] == 0
    assert result["command"] == "dap_client.runner.test_runner.TestRunner"
    assert len(result["steps"]) == 4


def test_trace_executor_reports_step_errors():
    result = TraceExecutor(timeout=30).execute_trace(
        _trace(str(SIMPLE_ADD), command="not-a-real-dap-command"),
        "invalid command",
    )
    assert result["success"] is False
    assert result["returncode"] == 1
    assert result["error_messages"]
