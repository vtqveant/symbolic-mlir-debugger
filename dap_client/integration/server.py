#!/usr/bin/env python3
"""
TCP wrapper for DAP server.

This module provides a TCP server that wraps the DAP server (stdin/stdout)
and exposes it via TCP socket for integration testing.
"""

import json
import logging
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, Callable, Any

logger = logging.getLogger(__name__)


class DAPServerWrapper:
    """Wrapper for DAP server with TCP interface."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5678,
        debugger_path: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.debugger_path = debugger_path or str(
            Path(__file__).parent.parent.parent / "debugger" / "dap_server.py"
        )
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start DAP server subprocess and TCP wrapper."""
        try:
            # Start DAP server subprocess
            self.process = subprocess.Popen(
                ["python", self.debugger_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )
            logger.info(f"Started DAP server subprocess (PID: {self.process.pid})")

            # Start TCP server
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(5.0)  # Timeout for accept

            self.running = True
            self.server_thread = threading.Thread(target=self._accept_connections)
            self.server_thread.daemon = True
            self.server_thread.start()

            logger.info(f"TCP wrapper listening on {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start DAP server wrapper: {e}")
            self.stop()
            return False

    def stop(self) -> None:
        """Stop DAP server wrapper and subprocess."""
        self.running = False

        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

        # Terminate subprocess
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    self.process.kill()
                except Exception:
                    pass
            except Exception:
                pass
            self.process = None

        # Wait for server thread
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)

        logger.info("DAP server wrapper stopped")

    def _accept_connections(self) -> None:
        """Accept incoming TCP connections."""
        while self.running and self.server_socket:
            try:
                client_socket, client_addr = self.server_socket.accept()
                logger.info(f"Client connected from {client_addr}")

                with self._lock:
                    # Close previous connection if any
                    if self.client_socket:
                        try:
                            self.client_socket.close()
                        except Exception:
                            pass
                    self.client_socket = client_socket

                # Start forwarding threads for this connection
                self._start_forwarding(client_socket)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
                break

    def _start_forwarding(self, client_socket: socket.socket) -> None:
        """Start forwarding between TCP socket and subprocess pipes."""
        # Thread to forward TCP -> subprocess stdin
        tcp_to_stdin = threading.Thread(
            target=self._forward_tcp_to_stdin,
            args=(client_socket,),
            daemon=True,
        )
        # Thread to forward subprocess stdout -> TCP
        stdout_to_tcp = threading.Thread(
            target=self._forward_stdout_to_tcp,
            args=(client_socket,),
            daemon=True,
        )

        tcp_to_stdin.start()
        stdout_to_tcp.start()

        # Wait for threads to complete (connection closed)
        tcp_to_stdin.join(timeout=0.1)
        stdout_to_tcp.join(timeout=0.1)

    def _forward_tcp_to_stdin(self, client_socket: socket.socket) -> None:
        """Forward data from TCP socket to subprocess stdin."""
        try:
            while self.running and self.process and self.process.stdin:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break  # Connection closed

                    # Send raw data to subprocess stdin
                    self.process.stdin.write(data.decode("utf-8"))
                    self.process.stdin.flush()
                except (socket.timeout, socket.error):
                    continue
                except Exception as e:
                    logger.error(f"Error forwarding TCP->stdin: {e}")
                    break
        except Exception as e:
            logger.error(f"TCP->stdin thread error: {e}")

    def _forward_stdout_to_tcp(self, client_socket: socket.socket) -> None:
        """Forward data from subprocess stdout to TCP socket."""
        try:
            while self.running and self.process and self.process.stdout:
                try:
                    line = self.process.stdout.readline()
                    if not line:
                        break  # Subprocess terminated

                    # Send to TCP client
                    client_socket.sendall(line.encode("utf-8"))
                except Exception as e:
                    logger.error(f"Error forwarding stdout->TCP: {e}")
                    break
        except Exception as e:
            logger.error(f"stdout->TCP thread error: {e}")

    def is_alive(self) -> bool:
        """Check if wrapper and subprocess are alive."""
        if not self.running or not self.process:
            return False
        return self.process.poll() is None

    def wait_for_connection(self, timeout: float = 10.0) -> bool:
        """Wait for a client connection."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self._lock:
                if self.client_socket:
                    return True
            time.sleep(0.1)
        return False


def main():
    """Command-line entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="TCP wrapper for DAP server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5678, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    wrapper = DAPServerWrapper(host=args.host, port=args.port)
    try:
        if wrapper.start():
            print(f"TCP wrapper running on {args.host}:{args.port}")
            print("Press Ctrl+C to stop")
            while wrapper.is_alive():
                time.sleep(1)
        else:
            print("Failed to start wrapper")
            return 1
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        wrapper.stop()

    return 0


if __name__ == "__main__":
    exit(main())
