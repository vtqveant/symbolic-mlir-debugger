#!/usr/bin/env python3
"""
Debug script to investigate hanging integration tests.
"""

import json
import subprocess
import time
import threading
import sys
from pathlib import Path


def read_stderr(pipe, prefix="[DAP stderr]"):
    """Read stderr from subprocess and print."""
    for line in pipe:
        sys.stderr.write(f"{prefix} {line}")
        sys.stderr.flush()


def send_request(proc, seq, command, arguments):
    """Send a DAP request."""
    request = {
        "seq": seq,
        "type": "request",
        "command": command,
        "arguments": arguments,
    }
    content = json.dumps(request)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    print(f"\n>>> Sending request seq={seq}, command={command}")
    print(f"Arguments: {arguments}")
    proc.stdin.write(message)
    proc.stdin.flush()
    return seq + 1


def read_message(proc):
    """Read a DAP message from stdout."""
    line = proc.stdout.readline()
    if not line:
        print("<<< No more output (process ended?)")
        return None

    print(f"<<< Header: {line.strip()}")
    if line.startswith("Content-Length:"):
        length = int(line.split(":")[1].strip())
        blank = proc.stdout.readline()
        print(f"<<< Blank line: {blank.strip()}")
        content = proc.stdout.read(length)
        print(f"<<< Content ({length} bytes): {content}")
        try:
            msg = json.loads(content)
            print(f"<<< Parsed: {json.dumps(msg, indent=2)}")
            return msg
        except json.JSONDecodeError as e:
            print(f"<<< JSON decode error: {e}")
            return None
    else:
        print(f"<<< Raw line (not Content-Length): {line}")
        try:
            msg = json.loads(line.strip())
            return msg
        except json.JSONDecodeError:
            return None


def wait_for_response(proc, expected_seq):
    """Wait for a response with matching request_seq."""
    while True:
        msg = read_message(proc)
        if msg is None:
            return None
        if msg.get("type") == "response" and msg.get("request_seq") == expected_seq:
            print(f"=== Got response for seq {expected_seq}")
            return msg
        elif msg.get("type") == "event":
            print(f"=== Ignoring event: {msg.get('event')}")
            continue
        else:
            print(f"=== Unexpected message type: {msg.get('type')}")
            continue


def main():
    """Main debug routine."""
    debugger_path = Path(__file__).parent.parent.parent / "debugger" / "dap_server.py"
    if not debugger_path.exists():
        print(f"Error: DAP server not found at {debugger_path}")
        return

    print("Starting DAP server...")
    proc = subprocess.Popen(
        ["python", str(debugger_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    # Start stderr reader thread
    stderr_thread = threading.Thread(target=read_stderr, args=(proc.stderr,))
    stderr_thread.daemon = True
    stderr_thread.start()

    time.sleep(0.5)  # Let server start

    seq = 1

    # 1. Initialize
    seq = send_request(
        proc,
        seq,
        "initialize",
        {
            "adapterID": "mlir-debugger",
            "clientID": "debug",
        },
    )
    resp = wait_for_response(proc, seq - 1)
    if not resp or not resp.get("success"):
        print("Initialize failed")
        proc.terminate()
        return

    # 2. Launch
    fixture_path = (
        Path(__file__).parent.parent.parent
        / "debugger"
        / "fixtures"
        / "simple_add.mlir"
    )
    print(f"Using fixture: {fixture_path}")
    seq = send_request(
        proc,
        seq,
        "launch",
        {
            "program": str(fixture_path),
            "noDebug": False,
            "args": ["a=5", "b=3"],
        },
    )
    resp = wait_for_response(proc, seq - 1)
    if not resp or not resp.get("success"):
        print("Launch failed")
        proc.terminate()
        return

    # 3. Set breakpoints
    print("\n=== Testing setBreakpoints ===")
    seq = send_request(
        proc,
        seq,
        "setBreakpoints",
        {
            "source": {"path": str(fixture_path)},
            "breakpoints": [{"line": 6}],
        },
    )
    print(f"Waiting for response with request_seq={seq - 1}...")
    resp = wait_for_response(proc, seq - 1)
    if resp is None:
        print("ERROR: No response received for setBreakpoints (hanging)")
        # Try to read any additional messages
        print("\nTrying to read any pending messages...")
        for _ in range(3):
            msg = read_message(proc)
            if msg is None:
                break
            print(f"Pending message: {msg}")
    else:
        print(f"setBreakpoints response: {resp}")

    # 4. Configuration done
    print("\n=== Testing configurationDone ===")
    seq = send_request(proc, seq, "configurationDone", {})
    print(f"Waiting for response with request_seq={seq - 1}...")
    resp = wait_for_response(proc, seq - 1)
    if resp is None:
        print("ERROR: No response for configurationDone")
    else:
        print(f"configurationDone response: {resp}")

    # 5. Symbolic commands (with conditional branch fixture)
    print("\n=== Testing symbolic commands ===")
    cond_fixture = (
        Path(__file__).parent.parent.parent
        / "debugger"
        / "fixtures"
        / "conditional_branch.mlir"
    )
    if cond_fixture.exists():
        # Need to launch a new session? For now just test symbolic/setMode
        seq = send_request(proc, seq, "symbolic/setMode", {"enabled": True})
        resp = wait_for_response(proc, seq - 1)
        if resp is None:
            print("ERROR: No response for symbolic/setMode")
        else:
            print(f"symbolic/setMode response: {resp}")
    else:
        print(f"Conditional branch fixture not found: {cond_fixture}")

    print("\n=== Debug complete ===")

    # Give time for any pending stderr
    time.sleep(0.5)

    proc.terminate()
    proc.wait()
    print("Process terminated")


if __name__ == "__main__":
    main()
