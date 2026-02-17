#!/usr/bin/env python3
"""
TCP wrapper for DAP server.

This module provides a TCP server that wraps the DAP server (stdin/stdout)
and exposes it via TCP socket for integration testing.

The wrapper:
1. Starts the DAP server as a subprocess
2. Listens on a TCP port (default: 5678)
3. Forwards data between TCP socket and subprocess stdin/stdout

This is required because the DAP server uses stdin/stdout (stdio mode)
while the DAP client expects to connect via TCP.
"""

import argparse
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DAPServerWrapper:
    """Wrapper for DAP server with TCP interface.

    This class bridges the gap between the DAP server's stdio interface
    and the DAP client's TCP interface.
    """

    # Default configuration
    DEFAULT_PORT = 5678
    DEFAULT_HOST = "localhost"
    DEFAULT_DEBUGGER_PATH = None  # Will auto-detect
    CONNECTION_TIMEOUT = 5.0
    PROCESS_TERMINATE_TIMEOUT = 2.0
    PROCESS_KILL_TIMEOUT = 1.0
    FORWARD_BUFFER_SIZE = 4096

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        debugger_path: Optional[str] = DEFAULT_DEBUGGER_PATH,
    ):
        """Initialize the DAP server wrapper.

        Args:
            host: Host to bind to (default: localhost)
            port: TCP port to listen on (default: 5678)
            debugger_path: Path to DAP server script. If None, will auto-detect.
        """
        self.host = host
        self.port = port
        self.debugger_path = self._resolve_debugger_path(debugger_path)
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self._lock = threading.Lock()
        self._client_connected = False
        self._connections_handled = 0

    @staticmethod
    def _resolve_debugger_path(debugger_path: Optional[str]) -> str:
        """Resolve the debugger path, defaulting to auto-detection."""
        if debugger_path:
            return debugger_path

        # Auto-detect based on this file's location
        current_file = Path(__file__).resolve()
        integration_dir = current_file.parent
        client_dir = integration_dir.parent
        project_root = client_dir.parent
        debugger_path = project_root / "debugger" / "dap_server.py"

        if debugger_path.exists():
            return str(debugger_path)
        else:
            logger.warning(
                f"Could not auto-detect debugger path at {debugger_path}. "
                "Please specify debugger_path explicitly."
            )
            return str(debugger_path)

    def start(self) -> bool:
        """Start DAP server subprocess and TCP wrapper.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting DAP server wrapper on {self.host}:{self.port}")

            # Start DAP server subprocess
            logger.debug(f"Starting DAP server: {self.debugger_path}")
            self.process = subprocess.Popen(
                [sys.executable, self.debugger_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Binary mode
                bufsize=0,  # Unbuffered
            )
            logger.info(f"✓ DAP server subprocess started (PID: {self.process.pid})")

            # Validate subprocess is running
            time.sleep(0.2)  # Give it a moment to initialize
            if self.process.poll() is not None:
                logger.error(f"✗ DAP server subprocess terminated immediately")
                # Try to read stderr
                _, stderr = self.process.communicate(timeout=0.5)
                if stderr:
                    logger.error(f"DAP server stderr: {stderr.decode('utf-8', errors='replace')}")
                return False

            # Start TCP server
            logger.debug("Starting TCP server socket")
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.setblocking(False)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(self.CONNECTION_TIMEOUT)

            logger.info(f"✓ TCP wrapper listening on {self.host}:{self.port}")

            # Start accepting connections
            self.running = True
            self.server_thread = threading.Thread(target=self._accept_connections)
            self.server_thread.daemon = True
            self.server_thread.start()

            logger.info("✓ DAP server wrapper started successfully")
            return True

        except FileExistsError:
            logger.error(f"✗ DAP server script not found: {self.debugger_path}")
            return False
        except PermissionError:
            logger.error(f"✗ Permission denied when binding to {self.host}:{self.port}")
            return False
        except socket.error as e:
            logger.error(f"✗ Socket error starting wrapper: {e}")
            self.stop()
            return False
        except Exception as e:
            logger.error(f"✗ Failed to start DAP server wrapper: {e}")
            self.stop()
            return False

    def stop(self) -> None:
        """Stop DAP server wrapper and subprocess.

        This method gracefully shuts down the wrapper and its subprocess.
        """
        logger.info("Stopping DAP server wrapper...")

        # Mark as not running
        was_running = self.running
        self.running = False

        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
                logger.debug("Client socket closed")
            except Exception as e:
                logger.warning(f"Error closing client socket: {e}")
            finally:
                self.client_socket = None
                self._client_connected = False

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
                logger.debug("Server socket closed")
            except Exception as e:
                logger.warning(f"Error closing server socket: {e}")
            finally:
                self.server_socket = None

        # Terminate subprocess
        if self.process:
            try:
                logger.debug("Terminating DAP server subprocess...")
                self.process.terminate()
                self.process.wait(timeout=self.PROCESS_TERMINATE_TIMEOUT)
                logger.info("✓ DAP server subprocess terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("DAP server subprocess did not terminate gracefully, killing...")
                try:
                    self.process.kill()
                    self.process.wait(timeout=self.PROCESS_KILL_TIMEOUT)
                    logger.info("✓ DAP server subprocess killed")
                except Exception as kill_error:
                    logger.error(f"✗ Failed to kill subprocess: {kill_error}")
            except Exception as e:
                logger.warning(f"Error terminating subprocess: {e}")
            finally:
                self.process = None

        # Wait for server thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
            if self.server_thread.is_alive():
                logger.warning("Server thread did not finish in time")

        logger.info("✓ DAP server wrapper stopped")

    def _accept_connections(self) -> None:
        """Accept incoming TCP connections and handle them."""
        logger.debug(f"Acceptance thread started")

        while self.running:
            try:
                self.server_socket.settimeout(self.CONNECTION_TIMEOUT)
                client_socket, client_addr = self.server_socket.accept()
                logger.info(f"✓ Client connected from {client_addr}")

                with self._lock:
                    # Close previous connection if any
                    if self.client_socket:
                        try:
                            self.client_socket.close()
                        except Exception:
                            pass
                    self.client_socket = client_socket
                    self._client_connected = True
                    self._connections_handled += 1

                # Start forwarding threads for this connection
                self._start_forwarding(client_socket)

            except socket.timeout:
                continue
            except socket.error as e:
                if self.running:
                    logger.error(f"✗ Socket error accepting connection: {e}")
                break
            except Exception as e:
                if self.running:
                    logger.error(f"✗ Error accepting connection: {e}")
                break

        logger.debug("Acceptance thread finished")

    def _start_forwarding(self, client_socket: socket.socket) -> None:
        """Start forwarding between TCP socket and subprocess pipes.

        Creates two daemon threads:
        1. TCP -> subprocess stdin
        2. subprocess stdout -> TCP
        """
        logger.debug("Starting forwarding threads")

        # Thread to forward TCP -> subprocess stdin
        tcp_to_stdin = threading.Thread(
            target=self._forward_tcp_to_stdin,
            args=(client_socket,),
            daemon=True,
            name="TCP->stdin"
        )
        # Thread to forward subprocess stdout -> TCP
        stdout_to_tcp = threading.Thread(
            target=self._forward_stdout_to_tcp,
            args=(client_socket,),
            daemon=True,
            name="stdout->TCP"
        )

        tcp_to_stdin.start()
        stdout_to_tcp.start()

        logger.debug(f"Forwarding threads started: {tcp_to_stdin.name}, {stdout_to_tcp.name}")

        # Wait for threads to complete (connection closed)
        tcp_to_stdin.join(timeout=0.1)
        stdout_to_tcp.join(timeout=0.1)

        logger.debug("Forwarding threads finished")

    def _forward_tcp_to_stdin(self, client_socket: socket.socket) -> None:
        """Forward data from TCP socket to subprocess stdin.

        This thread runs in a daemon thread and will be terminated when
        the wrapper is stopped. It handles socket timeouts gracefully.
        """
        logger.debug(f"TCP->stdin forwarding thread started")

        try:
            while self.running and self.process and self.process.stdin:
                try:
                    data = client_socket.recv(self.FORWARD_BUFFER_SIZE)
                    if not data:
                        logger.debug("TCP connection closed, terminating forwarding")
                        break

                    # Send raw bytes to subprocess stdin
                    self.process.stdin.write(data)
                    self.process.stdin.flush()

                except socket.timeout:
                    continue
                except socket.error as e:
                    if self.running:
                        logger.debug(f"Socket error in TCP->stdin: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error in TCP->stdin thread: {e}")
                    break

        except Exception as e:
            logger.error(f"TCP->stdin thread error: {e}")
        finally:
            logger.debug("TCP->stdin forwarding thread finished")

    def _forward_stdout_to_tcp(self, client_socket: socket.socket) -> None:
        """Forward data from subprocess stdout to TCP socket.

        This thread runs in a daemon thread and will be terminated when
        the wrapper is stopped. It handles subprocess EOF and errors gracefully.
        """
        logger.debug(f"stdout->TCP forwarding thread started")

        try:
            while self.running and self.process and self.process.stdout:
                try:
                    # Read raw bytes (up to buffer size)
                    data = self.process.stdout.read(self.FORWARD_BUFFER_SIZE)
                    if not data:
                        logger.debug("Subprocess terminated or EOF, terminating forwarding")
                        break

                    # Send raw bytes to TCP client
                    client_socket.sendall(data)

                except Exception as e:
                    if self.running:
                        logger.debug(f"Error in stdout->TCP: {e}")
                    break

        except Exception as e:
            logger.error(f"stdout->TCP thread error: {e}")
        finally:
            logger.debug("stdout->TCP forwarding thread finished")

    def is_alive(self) -> bool:
        """Check if wrapper and subprocess are alive.

        Returns:
            True if running, False otherwise
        """
        if not self.running or not self.process:
            return False
        return self.process.poll() is None

    def wait_for_connection(self, timeout: float = 10.0) -> bool:
        """Wait for a client connection.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if a client connected, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self._lock:
                if self._client_connected:
                    return True
            time.sleep(0.1)
        return False

    def get_connections_handled(self) -> int:
        """Get the number of connections handled.

        Returns:
            Number of connections handled
        """
        with self._lock:
            return self._connections_handled


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="TCP wrapper for DAP server. Exposes stdin/stdout DAP server via TCP."
    )
    parser.add_argument(
        "--host",
        default=DAPServerWrapper.DEFAULT_HOST,
        help=f"Host to bind to (default: {DAPServerWrapper.DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DAPServerWrapper.DEFAULT_PORT,
        help=f"Port to bind to (default: {DAPServerWrapper.DEFAULT_PORT})",
    )
    parser.add_argument(
        "--debugger-path",
        help="Path to DAP server script (auto-detected if not specified)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    wrapper = DAPServerWrapper(
        host=args.host,
        port=args.port,
        debugger_path=args.debugger_path,
    )

    try:
        if wrapper.start():
            print(f"✓ TCP wrapper running on {args.host}:{args.port}")
            print(f"  DAP server PID: {wrapper.process.pid}")
            print(f"  Connections handled: 0")
            print("\nUse the DAP client to connect to this wrapper.")
            print("Press Ctrl+C to stop the wrapper\n")

            while wrapper.is_alive():
                time.sleep(1)
        else:
            print("✗ Failed to start DAP server wrapper")
            print("\nCheck the logs above for error details.")
            return 1

    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        wrapper.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
