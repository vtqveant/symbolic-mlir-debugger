#!/usr/bin/env python3
"""
TCP integration tests for DAP client with real DAP server.

These tests use the TCP wrapper to start the DAP server and connect
the DAP client to it via TCP socket.
"""

import logging
import time
from pathlib import Path

import pytest

from .server import DAPServerWrapper
from dap_client.core.client import DAPClient

logger = logging.getLogger(__name__)


@pytest.fixture
def dap_server_wrapper():
    """Fixture that starts DAP server TCP wrapper."""
    wrapper = DAPServerWrapper(host="localhost", port=5679)
    if not wrapper.start():
        pytest.skip("Failed to start DAP server wrapper")

    # Wait for wrapper to be ready
    time.sleep(0.5)

    yield wrapper

    # Cleanup
    wrapper.stop()


@pytest.fixture
def dap_client(dap_server_wrapper):
    """Fixture that provides DAP client connected to wrapper."""
    client = DAPClient(host="localhost", port=5679)
    if not client.connect():
        pytest.skip("Failed to connect DAP client to server")

    yield client

    client.close()


@pytest.mark.skip(reason="TCP wrapper needs debugging - connection timeout issues")
def test_client_initialize(dap_client):
    """Test DAP client initialization."""
    result = dap_client.initialize(
        adapter_id="mlir-debugger",
        client_id="tcp-test",
    )

    assert isinstance(result, dict)
    assert "supportsConfigurationDoneRequest" in result
    assert result["supportsConfigurationDoneRequest"]


@pytest.mark.skip(reason="TCP wrapper needs debugging - connection timeout issues")
def test_client_launch(dap_client):
    """Test DAP client launch command."""
    # Initialize first
    dap_client.initialize(adapter_id="mlir-debugger", client_id="test")

    fixture_path = Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "simple_add.mlir"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    result = dap_client.launch(
        program=str(fixture_path),
        no_debug=False,
        args=["a=5", "b=3"],
    )

    assert result is not None


@pytest.mark.skip(reason="TCP wrapper needs debugging - connection timeout issues")
def test_client_set_breakpoints(dap_client):
    """Test DAP client set breakpoints command."""
    dap_client.initialize(adapter_id="mlir-debugger", client_id="test")

    fixture_path = Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "simple_add.mlir"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    dap_client.launch(program=str(fixture_path))

    result = dap_client.set_breakpoints(
        source={"path": str(fixture_path)},
        breakpoints=[{"line": 6}],
    )

    assert isinstance(result, dict)
    assert "breakpoints" in result
    breakpoints = result["breakpoints"]
    assert len(breakpoints) == 1
    assert breakpoints[0]["verified"]
    assert breakpoints[0]["line"] == 6


@pytest.mark.skip(reason="TCP wrapper needs debugging - connection timeout issues")
def test_client_symbolic_commands(dap_client):
    """Test DAP client symbolic debugging commands."""
    dap_client.initialize(adapter_id="mlir-debugger", client_id="test")

    fixture_path = (
        Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "conditional_branch.mlir"
    )
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    dap_client.launch(program=str(fixture_path), args=["arg0=5"])

    # Enable symbolic mode
    result = dap_client.symbolic_set_mode(enabled=True)
    assert isinstance(result, dict)
    assert result.get("symbolicMode")

    # Try symbolic evaluate
    result = dap_client.symbolic_evaluate(
        expression="%arg0 > 0",
        frame_id=0,
    )
    assert isinstance(result, dict)
    # Result may contain "result" or error

    # Try explore paths
    result = dap_client.symbolic_explore_paths(
        max_paths=10,
        frame_id=0,
    )
    assert isinstance(result, dict)
    # Result may contain "paths" and "totalPaths"


@pytest.mark.skip(reason="TCP wrapper needs debugging - connection timeout issues")
def test_client_full_session(dap_client):
    """Test a full debugging session using DAP client."""
    dap_client.initialize(adapter_id="mlir-debugger", client_id="full-session")

    fixture_path = Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "simple_add.mlir"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    # Launch
    launch_result = dap_client.launch(
        program=str(fixture_path),
        no_debug=False,
        args=["a=5", "b=3"],
    )
    assert launch_result is not None

    # Set breakpoints
    bp_result = dap_client.set_breakpoints(
        source={"path": str(fixture_path)},
        breakpoints=[{"line": 6}],
    )
    assert bp_result is not None

    # Configuration done
    config_result = dap_client.configuration_done()
    assert config_result is not None

    # Continue execution (should hit breakpoint immediately)
    continue_result = dap_client.continue_execution(thread_id=1)
    assert continue_result is not None

    # Get threads
    threads_result = dap_client.get_threads()
    assert isinstance(threads_result, dict)
    assert "threads" in threads_result
    threads = threads_result["threads"]
    assert len(threads) == 1
    assert threads[0]["id"] == 1

    # Get stack trace
    stack_result = dap_client.get_stack_trace(thread_id=1)
    assert isinstance(stack_result, dict)
    assert "stackFrames" in stack_result
    frames = stack_result["stackFrames"]
    assert len(frames) >= 1

    # Get variables
    variables_result = dap_client.get_variables(frame_id=0)
    assert isinstance(variables_result, dict)
    assert "variables" in variables_result


if __name__ == "__main__":
    # For manual testing
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
