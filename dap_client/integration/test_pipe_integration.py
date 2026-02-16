#!/usr/bin/env python3
"""
Pipe-based integration tests for DAP server.

These tests start the actual DAP server as a subprocess and communicate
via stdin/stdout using the DAP protocol (Content-Length headers).
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pytest

logger = logging.getLogger(__name__)


class DAPPipeClient:
    """Client for communicating with DAP server via pipes."""

    def __init__(self, process: subprocess.Popen):
        self.process = process
        self.seq = 0
        self.pending_responses = {}

    def send_request(
        self, command: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a DAP request and wait for response."""
        self.seq += 1
        request_seq = self.seq
        request = {
            "seq": request_seq,
            "type": "request",
            "command": command,
            "arguments": arguments or {},
        }

        # Send with Content-Length header
        content = json.dumps(request)
        message = f"Content-Length: {len(content)}\r\n\r\n{content}"
        assert self.process.stdin is not None
        self.process.stdin.write(message)
        self.process.stdin.flush()

        # Read response (skip events)
        while True:
            msg = self._read_message()
            if msg is None:
                raise RuntimeError("DAP server process ended")
            if msg.get("type") == "response" and msg.get("request_seq") == request_seq:
                return msg
            elif msg.get("type") == "event":
                # Log event, continue waiting for response
                logger.debug(f"Ignoring event: {msg.get('event')}")
                continue
            else:
                # Unexpected message type
                logger.warning(f"Unexpected message type: {msg.get('type')}")
                continue

    def _read_message(self) -> Optional[Dict[str, Any]]:
        """Read a DAP message from stdout."""
        assert self.process.stdout is not None
        # Read header line
        line = self.process.stdout.readline()
        if not line:
            return None

        if not line.startswith("Content-Length:"):
            # Try to parse as raw JSON (for testing)
            try:
                return json.loads(line.strip())
            except json.JSONDecodeError:
                raise RuntimeError(f"Invalid DAP message header: {line}")

        # Parse content length
        length = int(line.split(":")[1].strip())

        # Read blank line
        blank_line = self.process.stdout.readline()
        if blank_line not in ("\r\n", "\n"):
            # Some servers don't send blank line
            pass

        # Read content
        content = self.process.stdout.read(length)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse DAP message: {e}")

    def close(self):
        """Close the client (does not terminate process)."""
        pass


@pytest.fixture
def dap_server_process():
    """Fixture that starts DAP server subprocess."""
    debugger_path = Path(__file__).parent.parent.parent / "debugger" / "dap_server.py"
    if not debugger_path.exists():
        pytest.skip("DAP server not found")

    process = subprocess.Popen(
        ["python", str(debugger_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    # Give server time to start
    time.sleep(0.5)

    yield process

    # Cleanup
    try:
        process.terminate()
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture
def dap_client(dap_server_process):
    """Fixture that provides DAP pipe client."""
    client = DAPPipeClient(dap_server_process)
    yield client
    client.close()


def test_initialize(dap_client):
    """Test initialize command."""
    response = dap_client.send_request(
        "initialize",
        {
            "adapterID": "mlir-debugger",
            "clientID": "integration-test",
            "columnsStartAt1": True,
            "linesStartAt1": True,
            "locale": "en",
            "supportsVariableType": True,
            "supportsMemoryReferences": True,
        },
    )

    assert response["type"] == "response"
    assert response["command"] == "initialize"
    assert response["success"]
    assert "body" in response
    body = response["body"]
    assert isinstance(body, dict)
    # Check that capabilities are returned
    assert "supportsConfigurationDoneRequest" in body


def test_launch(dap_client):
    """Test launch command with a simple MLIR program."""
    # First initialize
    dap_client.send_request(
        "initialize",
        {
            "adapterID": "mlir-debugger",
            "clientID": "test",
        },
    )

    # Use existing fixture file
    fixture_path = Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "simple_add.mlir"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    response = dap_client.send_request(
        "launch",
        {
            "program": str(fixture_path),
            "noDebug": False,
            "args": ["a=5", "b=3"],
        },
    )

    assert response["type"] == "response"
    assert response["command"] == "launch"
    assert response["success"]


def test_set_breakpoints(dap_client):
    """Test setting breakpoints."""
    # Initialize and launch
    dap_client.send_request("initialize", {"adapterID": "mlir-debugger"})

    fixture_path = Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "simple_add.mlir"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    dap_client.send_request("launch", {"program": str(fixture_path)})

    # Set breakpoints
    response = dap_client.send_request(
        "setBreakpoints",
        {
            "source": {"path": str(fixture_path)},
            "breakpoints": [{"line": 6}],  # Line of arith.addi (1-indexed?)
        },
    )

    assert response["success"]
    assert "body" in response
    body = response["body"]
    assert "breakpoints" in body
    breakpoints = body["breakpoints"]
    assert len(breakpoints) == 1
    # Breakpoint line might be adjusted
    assert breakpoints[0]["verified"]


def test_configuration_done(dap_client):
    """Test configurationDone command."""
    dap_client.send_request("initialize", {"adapterID": "mlir-debugger"})

    fixture_path = Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "simple_add.mlir"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    dap_client.send_request("launch", {"program": str(fixture_path)})

    response = dap_client.send_request("configurationDone", {})
    assert response["success"]


def test_symbolic_commands(dap_client):
    """Test symbolic debugging commands."""
    dap_client.send_request("initialize", {"adapterID": "mlir-debugger"})

    fixture_path = (
        Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "conditional_branch.mlir"
    )
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    dap_client.send_request("launch", {"program": str(fixture_path), "args": ["arg0=5"]})

    # Enable symbolic mode
    response = dap_client.send_request("symbolic/setMode", {"enabled": True})
    assert response["success"]

    # Try symbolic evaluate
    response = dap_client.send_request(
        "symbolic/evaluate",
        {
            "expression": "%arg0 > 0",
            "frameId": 0,
        },
    )
    # Response may be success or error depending on implementation
    assert response["type"] == "response"

    # Try explore paths
    response = dap_client.send_request(
        "symbolic/explorePaths",
        {
            "maxPaths": 10,
            "frameId": 0,
        },
    )
    assert response["type"] == "response"


if __name__ == "__main__":
    # For manual testing
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
