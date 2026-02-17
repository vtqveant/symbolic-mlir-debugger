"""Socket connection management for DAP client"""

import json
import logging
import select
import socket
from typing import Optional, Callable, Any, Dict

from ..protocol import DAPRequest, DAPResponse

logger = logging.getLogger(__name__)


class DAPConnectionError(Exception):
    """Exception raised for DAP connection errors"""

    pass


class DAPConnection:
    """Manage socket connection to DAP server"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5678,
        timeout: int = 30,
        read_timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.read_timeout = read_timeout
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.event_handler: Optional[Callable] = None

    def connect(self) -> bool:
        """Establish connection to DAP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to DAP server at {self.host}:{self.port}")
            return True
        except socket.timeout:
            raise DAPConnectionError(f"Connection timeout to {self.host}:{self.port}")
        except ConnectionRefusedError:
            raise DAPConnectionError(f"Connection refused by {self.host}:{self.port}")
        except Exception as e:
            raise DAPConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")

    def disconnect(self) -> None:
        """Close connection to DAP server"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
        self.socket = None
        self.connected = False
        logger.info("Disconnected from DAP server")

    def send(self, request: DAPRequest) -> None:
        """Send a DAP request to the server"""
        if not self.connected or not self.socket:
            raise DAPConnectionError("Not connected to DAP server")

        try:
            json_str = request.to_json()
            # DAP protocol requires Content-Length header
            message = f"Content-Length: {len(json_str)}\r\n\r\n{json_str}"
            logger.debug(f"Sending request: {json_str}")
            self.socket.sendall(message.encode("utf-8"))
        except socket.timeout:
            raise DAPConnectionError("Timeout while sending request")
        except Exception as e:
            raise DAPConnectionError(f"Failed to send request: {e}")

    def _receive(self, buffer_size: int = 4096) -> Optional[bytes]:
        """Receive data from server"""
        try:
            if not self.socket:
                return None

            readable, _, _ = select.select([self.socket], [], [], self.read_timeout)
            if not readable:
                return None

            data = self.socket.recv(buffer_size)
            if not data:
                return None

            return data
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"Error receiving data: {e}")
            return None

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
                # Skip this line and try to recover?
                # For now, raise error
                raise DAPConnectionError(f"Invalid Content-Length header: {header_line}")

            # Find end of headers (blank line)
            # Skip the header line and the newline
            rest = text[newline_pos + 1 :]
            # Skip possible CR before LF
            if header_line.endswith("\r"):
                # Actually newline_pos is at LF, CR is part of header_line
                pass

            # Look for blank line
            blank_line_end = rest.find("\n")
            if blank_line_end == -1:
                return None, buffer  # Incomplete headers

            # Check if blank line is just "\n" or "\r\n"
            blank_line = rest[:blank_line_end]
            if blank_line not in ("", "\r"):
                # Some servers might not send blank line? Skip anyway
                logger.debug(f"Unexpected blank line content: {blank_line!r}")

            # Skip blank line
            headers_end = newline_pos + 1 + blank_line_end + 1
            # Now we need 'length' bytes of content
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
                # Consume the entire buffer (assuming one message)
                return message, b""
            except json.JSONDecodeError:
                # Might be incomplete JSON
                return None, buffer

    def receive_response(self) -> DAPResponse:
        """Receive a DAP response from server"""
        buffer = b""

        while True:
            data = self._receive()
            if data is None:
                raise DAPConnectionError("Connection lost or timeout while waiting for response")

            buffer += data

            # Try to parse a message from buffer
            message, remaining = self._parse_dap_message(buffer)
            if message is None:
                # Incomplete message, continue reading
                if len(data) == 0:
                    raise DAPConnectionError("Connection closed by server")
                continue

            # Update buffer with remaining data
            buffer = remaining

            # Handle the message
            if "request_seq" in message:
                # This is a response
                response = DAPResponse.from_dict(message)
                logger.debug(f"Received response: {json.dumps(message, indent=2)}")
                return response

            # Handle events
            if "event" in message:
                if self.event_handler:
                    self.event_handler(message)
                else:
                    logger.debug(f"Received event (no handler): {json.dumps(message, indent=2)}")
                # Continue to read next message (looking for response)
                continue

            # Unknown message type, assume it's a response
            logger.warning(f"Unknown message type, assuming response: {message}")
            response = DAPResponse.from_dict(message)
            return response

    def request(
        self, request: DAPRequest, expect_response: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Send request and optionally wait for response"""
        self.send(request)

        if expect_response:
            response = self.receive_response()
            if response.success:
                return response.body
            else:
                error_msg = response.message or "Unknown error"
                raise DAPConnectionError(f"Request failed: {error_msg}")

        return None

    def set_event_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Set handler for incoming events"""
        self.event_handler = handler

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False
