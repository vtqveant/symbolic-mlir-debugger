"""Stdio connection management for DAP client"""

import json
import logging

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Any, Dict

from ..protocol import DAPRequest, DAPResponse

logger = logging.getLogger(__name__)


class DAPConnectionError(Exception):
    """Exception raised for DAP connection errors"""

    pass


class StdioConnection:
    """Manage stdio connection to DAP server via subprocess pipes"""

    def __init__(
        self,
        debugger_path: Optional[str] = None,
        timeout: int = 30,
        read_timeout: int = 10,
    ):
        """Initialize stdio connection to DAP server.

        Args:
            debugger_path: Path to DAP server script. If None, auto-detected.
            timeout: Timeout for operations in seconds
            read_timeout: Timeout for reading responses in seconds
        """
        self.debugger_path = self._resolve_debugger_path(debugger_path)
        self.timeout = timeout
        self.read_timeout = read_timeout
        self.process: Optional[subprocess.Popen] = None
        self.connected = False
        self.event_handler: Optional[Callable] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reader = threading.Event()
        self._message_queue = []
        self._queue_lock = threading.Lock()
        self._response_events = {}  # request_seq -> threading.Event
        self._response_data = {}  # request_seq -> response data
        self._next_seq = 1

    @staticmethod
    def _resolve_debugger_path(debugger_path: Optional[str]) -> str:
        """Resolve the debugger path, defaulting to auto-detection."""
        if debugger_path:
            return debugger_path

        # Auto-detect based on this file's location
        current_file = Path(__file__).resolve()
        core_dir = current_file.parent  # dap_client/core
        client_dir = core_dir.parent  # dap_client
        project_root = client_dir.parent  # symbolic-mlir-debugger
        debugger_path = project_root / "debugger" / "dap_server.py"

        if debugger_path.exists():
            return str(debugger_path)
        else:
            logger.warning(
                f"Could not auto-detect debugger path at {debugger_path}. "
                "Please specify debugger_path explicitly."
            )
            return str(debugger_path)

    def connect(self) -> bool:
        """Establish connection to DAP server by starting subprocess."""
        try:
            logger.info(f"Starting DAP server: {self.debugger_path}")
            self.process = subprocess.Popen(
                [sys.executable, self.debugger_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Binary mode for precise Content-Length reading
                bufsize=0,  # Unbuffered
            )

            # Give server time to initialize
            time.sleep(0.2)

            if self.process.poll() is not None:
                # Process terminated immediately
                _, stderr = self.process.communicate(timeout=0.5)
                error_msg = stderr.decode("utf-8", errors="replace") if stderr else "Unknown error"
                raise DAPConnectionError(f"DAP server failed to start: {error_msg}")

            self.connected = True
            logger.info("DAP server started successfully")

            # Start reader thread
            self._stop_reader.clear()
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()

            return True

        except FileNotFoundError:
            raise DAPConnectionError(f"DAP server not found: {self.debugger_path}")
        except Exception as e:
            raise DAPConnectionError(f"Failed to start DAP server: {e}")

    def disconnect(self) -> None:
        """Close connection to DAP server by terminating subprocess."""
        # Stop reader thread
        if self._reader_thread and self._reader_thread.is_alive():
            self._stop_reader.set()
            self._reader_thread.join(timeout=1.0)
            if self._reader_thread.is_alive():
                logger.warning("Reader thread did not finish in time")

        # Terminate subprocess
        if self.process:
            try:
                logger.debug("Terminating DAP server subprocess...")
                self.process.terminate()
                self.process.wait(timeout=2.0)
                logger.info("DAP server subprocess terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("DAP server subprocess did not terminate gracefully, killing...")
                try:
                    self.process.kill()
                    self.process.wait(timeout=1.0)
                    logger.info("DAP server subprocess killed")
                except Exception as kill_error:
                    logger.error(f"Failed to kill subprocess: {kill_error}")
            except Exception as e:
                logger.warning(f"Error terminating subprocess: {e}")
            finally:
                self.process = None

        self.connected = False
        logger.info("Disconnected from DAP server")

    def send(self, request: DAPRequest) -> None:
        """Send a DAP request to the server via stdin."""
        if not self.connected or not self.process or not self.process.stdin:
            raise DAPConnectionError("Not connected to DAP server")

        try:
            json_str = request.to_json()
            # DAP protocol requires Content-Length header
            message = f"Content-Length: {len(json_str)}\r\n\r\n{json_str}"
            logger.debug(f"Sending request: {json_str}")

            self.process.stdin.write(message.encode("utf-8"))
            self.process.stdin.flush()

        except BrokenPipeError:
            raise DAPConnectionError("Connection lost (broken pipe)")
        except Exception as e:
            raise DAPConnectionError(f"Failed to send request: {e}")

    def _reader_loop(self) -> None:
        """Background thread to read messages from stdout."""
        buffer = b""

        while not self._stop_reader.is_set() and self.process and self.process.stdout:
            try:
                # Read available data
                data = self.process.stdout.read(4096)
                if not data:
                    # EOF, process likely terminated
                    logger.debug("DAP server process ended (EOF)")
                    break

                buffer += data

                # Parse all complete messages from buffer
                while buffer:
                    message, remaining = self._parse_dap_message(buffer)
                    if message is None:
                        # Incomplete message, wait for more data
                        break

                    buffer = remaining
                    self._handle_message(message)

            except Exception as e:
                if not self._stop_reader.is_set():
                    logger.error(f"Error in reader loop: {e}")
                break

        logger.debug("Reader thread finished")

    def _parse_dap_message(self, buffer: bytes) -> tuple[Optional[Dict[str, Any]], bytes]:
        """Parse a DAP message from buffer.

        Returns (message_dict, remaining_buffer) or (None, buffer) if incomplete.
        """
        if not buffer:
            return None, buffer

        # Convert to string for line parsing
        text = buffer.decode("utf-8")

        # Check for Content-Length header
        if text.startswith("Content-Length:"):
            # Find first newline
            newline_pos = text.find("\n")
            if newline_pos == -1:
                return None, buffer  # Incomplete header line

            header_line = text[:newline_pos]
            # Parse length
            try:
                length = int(header_line.split(":")[1].strip())
            except (ValueError, IndexError):
                logger.error(f"Invalid Content-Length header: {header_line}")
                raise DAPConnectionError(f"Invalid Content-Length header: {header_line}")

            # Find end of headers (blank line)
            rest = text[newline_pos + 1 :]
            blank_line_end = rest.find("\n")
            if blank_line_end == -1:
                return None, buffer  # Incomplete headers

            # Skip blank line
            headers_end = newline_pos + 1 + blank_line_end + 1
            content_start = headers_end

            if len(buffer) < content_start + length:
                return None, buffer  # Not enough content

            content_bytes = buffer[content_start : content_start + length]
            try:
                content_str = content_bytes.decode("utf-8")
                message = json.loads(content_str)
                remaining = buffer[content_start + length :]
                return message, remaining
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Failed to parse DAP message content: {e}")
                raise DAPConnectionError(f"Failed to parse DAP message: {e}")

        else:
            # Try to parse as raw JSON (for backward compatibility)
            try:
                message = json.loads(text.strip())
                return message, b""
            except json.JSONDecodeError:
                return None, buffer

    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming message (response or event)."""
        msg_type = message.get("type")

        if msg_type == "response":
            request_seq = message.get("request_seq")
            if request_seq is not None:
                with self._queue_lock:
                    self._response_data[request_seq] = message
                    # Signal waiting threads
                    if request_seq in self._response_events:
                        self._response_events[request_seq].set()
            else:
                logger.warning(f"Response without request_seq: {message}")

        elif msg_type == "event":
            if self.event_handler:
                try:
                    self.event_handler(message)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
            else:
                logger.debug(f"Received event (no handler): {json.dumps(message, indent=2)}")

        else:
            logger.warning(f"Unknown message type: {msg_type}")

    def receive_response(self) -> DAPResponse:
        """Receive a DAP response from server.

        Note: This is a blocking call that waits for the next response.
        For request-response pattern, use the request() method instead.
        """
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            with self._queue_lock:
                # Check for any response in queue
                for request_seq, response_data in list(self._response_data.items()):
                    del self._response_data[request_seq]
                    response = DAPResponse.from_dict(response_data)
                    logger.debug(f"Received response: {json.dumps(response_data, indent=2)}")
                    return response

            # Wait a bit before checking again
            time.sleep(0.01)

        raise DAPConnectionError("Timeout while waiting for response")

    def request(
        self, request: DAPRequest, expect_response: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Send request and optionally wait for response."""
        # Ensure request has a unique sequence number
        if request.seq == 0:
            request.seq = self._next_seq
            self._next_seq += 1
        request_seq = request.seq

        event = threading.Event()
        with self._queue_lock:
            self._response_events[request_seq] = event

        try:
            self.send(request)

            if expect_response:
                # Wait for response with timeout
                if not event.wait(timeout=self.timeout):
                    raise DAPConnectionError(f"Timeout waiting for response to {request.command}")

                # Get response data
                with self._queue_lock:
                    if request_seq in self._response_data:
                        response_data = self._response_data.pop(request_seq)
                    else:
                        raise DAPConnectionError(
                            f"No response received for request_seq {request_seq}"
                        )

                response = DAPResponse.from_dict(response_data)
                if response.success:
                    return response.body
                else:
                    error_msg = response.message or "Unknown error"
                    raise DAPConnectionError(f"Request failed: {error_msg}")

            return None

        finally:
            # Clean up event
            with self._queue_lock:
                if request_seq in self._response_events:
                    del self._response_events[request_seq]

    def set_event_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Set handler for incoming events."""
        self.event_handler = handler

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
