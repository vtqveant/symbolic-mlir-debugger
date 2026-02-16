"""Socket connection management for DAP client"""

import json
import logging
import select
import socket
from typing import Optional, Callable, Any, Dict

from dap_client.protocol import DAPRequest, DAPResponse

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
            raise DAPConnectionError(
                f"Failed to connect to {self.host}:{self.port}: {e}"
            )

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
            logger.debug(f"Sending request: {json_str}")
            self.socket.sendall(json_str.encode("utf-8"))
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

    def receive_response(self) -> DAPResponse:
        """Receive a DAP response from server"""
        buffer = b""

        while True:
            data = self._receive()
            if data is None:
                raise DAPConnectionError(
                    "Connection lost or timeout while waiting for response"
                )

            buffer += data

            try:
                # Try to parse JSON from buffer
                json_str = buffer.decode("utf-8").strip()
                # Check if we have a complete JSON message
                # DAP messages are JSON objects that may span multiple packets
                obj = json.loads(json_str)

                if "request_seq" in obj:
                    # This is a response
                    response = DAPResponse.from_dict(obj)
                    logger.debug(f"Received response: {json.dumps(obj, indent=2)}")
                    return response

                # Handle events differently
                if "event" in obj:
                    if self.event_handler:
                        self.event_handler(obj)
                    else:
                        logger.debug(
                            f"Received event (no handler): {json.dumps(obj, indent=2)}"
                        )

                # For now, assume it's a response
                response = DAPResponse.from_dict(obj)
                return response

            except json.JSONDecodeError:
                # Incomplete JSON, continue reading
                if len(data) == 0:
                    raise DAPConnectionError("Connection closed by server")
                continue

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
