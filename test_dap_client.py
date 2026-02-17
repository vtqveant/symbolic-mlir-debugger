#!/usr/bin/env python3
"""Test DAP client as an end user"""

import json
import subprocess
import time
import sys
import os


class DAPTestClient:
    def __init__(self, server_process):
        self.process = server_process
        self.seq = 0

    def send_request(self, command, arguments=None):
        """Send a DAP request"""
        self.seq += 1
        request = {
            "seq": self.seq,
            "type": "request",
            "command": command,
            "arguments": arguments or {},
        }

        content = json.dumps(request)
        message = f"Content-Length: {len(content)}\r\n\r\n{content}"
        self.process.stdin.write(message)
        self.process.stdin.flush()

        # Read response
        return self._read_response()

    def _read_response(self):
        """Read DAP response"""
        # Read header
        line = self.process.stdout.readline()
        if not line:
            return None

        if not line.startswith("Content-Length:"):
            # Try to parse as JSON directly
            try:
                return json.loads(line.strip())
            except:
                raise RuntimeError(f"Invalid header: {line}")

        length = int(line.split(":")[1].strip())

        # Read blank line
        blank = self.process.stdout.readline()

        # Read content
        content = self.process.stdout.read(length)
        return json.loads(content)

    def close(self):
        """Close client"""
        if self.process.stdin:
            self.process.stdin.close()
        if self.process.stdout:
            self.process.stdout.close()


def main():
    print("Testing DAP client as end user")
    print("=" * 50)

    # Start DAP server
    print("1. Starting DAP server...")
    server_path = os.path.join(os.path.dirname(__file__), "debugger", "dap_server.py")

    try:
        server = subprocess.Popen(
            ["python", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Give server time to start
        time.sleep(1)

        # Check if server is running
        if server.poll() is not None:
            stderr = server.stderr.read()
            print(f"Server failed to start: {stderr}")
            return False

        print("   Server started successfully")

        # Create client
        client = DAPTestClient(server)

        # Test 1: Initialize
        print("\n2. Testing initialize command...")
        try:
            response = client.send_request(
                "initialize", {"adapterID": "mlir-debugger", "clientID": "test-client"}
            )
            print(f"   Response: {response}")
        except Exception as e:
            print(f"   Error: {e}")
            return False

        # Test 2: Launch program
        print("\n3. Testing launch command...")
        try:
            response = client.send_request(
                "launch", {"program": "test_function.mlir", "noDebug": False}
            )
            print(f"   Response: {response}")
        except Exception as e:
            print(f"   Error: {e}")
            return False

        # Test 3: Set breakpoints
        print("\n4. Testing setBreakpoints command...")
        try:
            response = client.send_request(
                "setBreakpoints",
                {"source": {"path": "test_function.mlir"}, "breakpoints": [{"line": 3}]},
            )
            print(f"   Response: {response}")
        except Exception as e:
            print(f"   Error: {e}")
            return False

        # Test 4: Configuration done
        print("\n5. Testing configurationDone command...")
        try:
            response = client.send_request("configurationDone", {})
            print(f"   Response: {response}")
        except Exception as e:
            print(f"   Error: {e}")
            return False

        # Test 5: Continue execution
        print("\n6. Testing continue command...")
        try:
            response = client.send_request("continue", {"threadId": 1})
            print(f"   Response: {response}")
        except Exception as e:
            print(f"   Error: {e}")
            return False

        # Clean up
        print("\n7. Cleaning up...")
        client.close()
        server.terminate()
        server.wait()

        print("\nTest completed successfully!")
        return True

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
