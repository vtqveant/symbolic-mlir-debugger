"""Tests that the trace validator uses the shared dap_client schema."""

from dap_trace_library.validation.trace_validator import TraceValidator


def _trace(command="disconnect"):
    return {
        "name": "validator-smoke",
        "program": "debugger/fixtures/simple_add.mlir",
        "session": [
            {
                "command": "initialize",
                "arguments": {"adapter_id": "mlir-debugger"},
                "expect": {"success": True},
            },
            {
                "command": "launch",
                "arguments": {"program": "debugger/fixtures/simple_add.mlir"},
                "expect": {"success": True},
            },
            {
                "command": command,
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True},
            },
        ],
    }


def test_valid_trace_uses_shared_schema():
    validator = TraceValidator()
    assert validator.valid_commands
    result = validator.validate_trace(_trace())
    assert result["valid"] is True
    assert result["errors"] == []


def test_unknown_command_is_a_schema_error():
    result = TraceValidator().validate_trace(_trace("not-a-command"))
    assert result["valid"] is False
    assert any("Schema validation error" in e for e in result["errors"])


def test_missing_expect_is_a_warning():
    trace = _trace()
    trace["session"][0].pop("expect")
    result = TraceValidator().validate_trace(trace)
    assert result["valid"] is True
    assert any("expect" in w for w in result["warnings"])
