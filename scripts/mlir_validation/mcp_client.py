#!/usr/bin/env python3
"""
MCP client for MLIR validation.
Communicates with MCP server via SSE (MCP protocol 2024-11-05).
"""

import json
import requests
import time
import threading
import queue
from typing import Dict, Any, Optional, Tuple


class SSEClient:
    """Simple SSE client for parsing Server-Sent Events."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, verify: bool = True):
        self.url = url
        self.headers = headers or {}
        self.verify = verify
        self.response = None
        self.event_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        """Start reading SSE stream in background thread."""
        self.thread = threading.Thread(target=self._read_stream, daemon=True)
        self.thread.start()

    def _read_stream(self):
        """Read SSE stream and parse events."""
        try:
            self.response = requests.get(
                self.url,
                headers=self.headers,
                stream=True,
                timeout=30.0,
                verify=self.verify,
            )

            if self.response.status_code != 200:
                self.event_queue.put(("error", f"HTTP {self.response.status_code}"))
                return

            buffer = ""
            for line in self.response.iter_lines(decode_unicode=True):
                if self.stop_event.is_set():
                    break

                if not line:
                    if buffer:
                        self._parse_event(buffer)
                        buffer = ""
                    continue

                buffer += line + "\n"

        except Exception as e:
            self.event_queue.put(("error", str(e)))

    def _parse_event(self, event_text: str):
        """Parse SSE event text."""
        lines = event_text.strip().split("\n")
        event_type = "message"
        data = ""

        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:]  # Remove 'event: '
            elif line.startswith("data: "):
                data = line[6:]  # Remove 'data: '

        if data:
            self.event_queue.put((event_type, data))

    def get_event(self, timeout: float = 30.0) -> Optional[Tuple[str, str]]:
        """Get next event from queue."""
        try:
            return self.event_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        """Stop the SSE client."""
        self.stop_event.set()
        if self.response:
            self.response.close()
        if self.thread:
            self.thread.join(timeout=1.0)


class MCPClient:
    """Client for MCP server communication via SSE (2024-11-05 protocol)."""

    def __init__(
        self,
        base_url: str = "https://mcp.eventflow.ru/mcp",
        verify: bool = True,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.sse_url = f"{self.base_url}/sse"
        self.post_url = None
        self.session_id = None
        self.sse_client = None
        self.pending_requests = {}  # request_id -> response queue
        self.verify = verify
        self.max_retries = max_retries
        self.initialized = False
        self.protocol_version = "2025-11-25"

    def _read_sse_response(self, response, expected_id):
        """Read SSE stream from response and find JSON-RPC response with matching ID."""
        buffer = ""
        for line in response.iter_lines(decode_unicode=True):
            if line:
                buffer += line + "\n"
            else:
                if buffer:
                    # Parse SSE event
                    lines = buffer.strip().split("\n")
                    event_type = "message"
                    data = ""
                    for line_str in lines:
                        if line_str.startswith("event: "):
                            event_type = line_str[7:]
                        elif line_str.startswith("data: "):
                            data = line_str[6:]
                    if data and event_type == "message":
                        try:
                            message = json.loads(data)
                            if "id" in message and message["id"] == expected_id:
                                return message
                        except json.JSONDecodeError:
                            pass
                    buffer = ""
        # If we get here, no matching response found
        raise RuntimeError(f"No response found for request ID {expected_id}")

    def _connect(self):
        """Ensure connected to MCP server using Streamable HTTP transport."""
        if self.initialized:
            return

        # For new transport, POST endpoint is the base URL
        self.post_url = self.base_url

        # Initialize MCP session
        self._initialize_session()

    def _initialize_session(self):
        """Initialize MCP session with server using Streamable HTTP transport."""
        if self.initialized:
            return

        # Prepare initialize request
        initialize_id = int(time.time() * 1000)
        initialize_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "mlir-validation-client", "version": "1.0.0"},
                "rootUri": None,
                "initializationOptions": None,
            },
            "id": initialize_id,
        }

        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": self.protocol_version,
        }

        try:
            # Send initialize request
            if self.post_url is None:
                raise RuntimeError("Not connected to MCP server")
            post_url = self.post_url
            response = requests.post(
                post_url,
                json=initialize_request,
                headers=headers,
                timeout=30.0,
                verify=self.verify,
                stream=True,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Initialize request failed: HTTP {response.status_code}: {response.text}"
                )

            # Extract session ID from headers
            session_id = response.headers.get("Mcp-Session-Id")
            if not session_id:
                raise RuntimeError("No Mcp-Session-Id header in response")
            self.session_id = session_id

            # Read SSE stream for initialize response
            result = self._read_sse_response(response, initialize_id)
            if "error" in result:
                raise RuntimeError(f"Initialize error: {result['error']}")

            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {},
            }
            notification_headers = headers.copy()
            notification_headers["MCP-Session-Id"] = session_id
            # Remove Accept header for notification (server expects 202)
            notification_headers["Accept"] = "application/json"

            notification_response = requests.post(
                post_url,
                json=initialized_notification,
                headers=notification_headers,
                timeout=30.0,
                verify=self.verify,
            )

            if notification_response.status_code != 202:
                print(
                    f"Warning: Initialized notification failed: "
                    f"HTTP {notification_response.status_code}"
                )

            self.initialized = True
            print(f"MCP session initialized with protocol version {self.protocol_version}")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize MCP session: {e}")

    def _listen_for_messages(self):
        """Listen for message events and route to pending requests."""
        while True:
            if self.sse_client is None:
                break

            event = self.sse_client.get_event(timeout=1.0)
            if event is None:
                continue

            event_type, data = event
            if event_type == "message":
                try:
                    message = json.loads(data)
                    if "id" in message and message["id"] in self.pending_requests:
                        # This is a response to a pending request
                        q = self.pending_requests.pop(message["id"])
                        q.put(message)
                except json.JSONDecodeError:
                    pass
            elif event_type == "error":
                # Propagate error to all pending requests
                for q in self.pending_requests.values():
                    q.put({"error": {"message": data}})
                break

    def _make_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a JSON-RPC request to MCP server using Streamable HTTP transport."""
        # Ensure connected
        self._connect()

        last_error = None
        for attempt in range(self.max_retries):
            # Generate request ID
            request_id = int(time.time() * 1000) + attempt  # ensure uniqueness

            # Prepare JSON-RPC request
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": request_id,
            }

            headers = {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
                "MCP-Protocol-Version": self.protocol_version,
            }
            if self.session_id:
                headers["MCP-Session-Id"] = self.session_id

            try:
                # Send request
                if self.post_url is None:
                    return {"error": "Not connected to MCP server"}
                post_url = self.post_url
                response = requests.post(
                    post_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                    verify=self.verify,
                    stream=True,
                )

                if response.status_code != 200:
                    # HTTP error, don't retry
                    return {"error": f"HTTP {response.status_code}: {response.text}"}

                # Read SSE response
                try:
                    result = self._read_sse_response(response, request_id)
                    if "error" in result:
                        # Server returned JSON-RPC error
                        return {"error": result["error"]}
                    return result.get("result", {})
                except RuntimeError as e:
                    last_error = str(e)
                    continue  # retry

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                last_error = str(e)
                # Exponential backoff
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)  # 1, 2, 4 seconds
                continue
            except Exception as e:
                # Other errors, don't retry
                return {"error": str(e)}

        # All retries exhausted
        return {"error": f"Request failed after {self.max_retries} attempts: {last_error}"}

    def validate_mlir(self, mlir_code: str, uri: str = "file:///test.mlir") -> Dict[str, Any]:
        """
        Validate MLIR code using MCP server via SSE.
        """
        return self._make_request(
            "tools/call",
            {
                "name": "validate_mlir",
                "arguments": {"mlir_code": mlir_code, "uri": uri},
            },
        )

    def check_mlir_syntax(self, mlir_code: str, uri: str = "file:///test.mlir") -> Dict[str, Any]:
        """
        Check MLIR syntax using MCP server.
        """
        return self._make_request(
            "tools/call",
            {
                "name": "check_mlir_syntax",
                "arguments": {"mlir_code": mlir_code, "uri": uri},
            },
        )

    def test_connection(self) -> bool:
        """Test connection to MCP server using Streamable HTTP transport."""
        try:
            # Try POST to MCP endpoint with minimal request
            headers = {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
                "MCP-Protocol-Version": self.protocol_version,
            }
            # Send simple initialize request (may fail but shows server reachable)
            dummy_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {},
                },
                "id": 1,
            }
            response = requests.post(
                self.base_url,
                json=dummy_request,
                headers=headers,
                timeout=5.0,
                verify=self.verify,
            )
            # Any response other than 404/network error indicates server is reachable
            status_ok = response.status_code != 404
            response.close()
            return status_ok
        except Exception:
            return False

    def close(self):
        """Close connection to MCP server."""
        if self.sse_client:
            self.sse_client.stop()
            self.sse_client = None


# Example usage
if __name__ == "__main__":
    # Test the client
    client = MCPClient(verify=False)

    # Test connection
    print("Testing MCP server connection...")
    if client.test_connection():
        print("✓ Connected to MCP server")
    else:
        print("✗ Failed to connect to MCP server")
        exit(1)

    # Test MLIR validation
    test_mlir = """module {
  func.func @main() -> i32 {
    %c1 = arith.constant 1 : i32
    %c2 = arith.constant 2 : i32
    %sum = arith.addi %c1, %c2 : i32
    return %sum : i32
  }
}"""

    print("\nTesting MLIR validation...")
    result = client.validate_mlir(test_mlir)

    if "error" in result:
        print(f"✗ Validation error: {result['error']}")
    else:
        print("✓ Validation successful")
        if "diagnostics" in result and result["diagnostics"]:
            print(f"  Found {len(result['diagnostics'])} diagnostics")
            for diag in result["diagnostics"]:
                print(f"  - {diag.get('message', 'Unknown diagnostic')}")
        else:
            print("  No diagnostics found (code is valid)")

    client.close()
