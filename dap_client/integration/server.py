#!/usr/bin/env python3
"""
TCP wrapper for DAP server.

This module provides a TCP server that wraps the DAP server (stdin/stdout)
and exposes it via TCP socket for integration testing.

IMPORTANT: This wrapper is REQUIRED for DAP client communication.
The DAP server uses stdin/stdout protocol, but the DAP client expects TCP.
This wrapper bridges the two protocols.

Usage:
    python server.py --host localhost --port 5678
"""

import logging
import socket
import subprocess
import threading
import time
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DAPServerWrapper:
    """Wrapper for DAP server with TCP interface.
    
    This class bridges between:
    - DAP server (stdin/stdout protocol)
    - DAP client (TCP socket on port 5678)
    
    Without this wrapper, the DAP client cannot communicate with the DAP server.
    """

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
        self.stderr_thread: Optional[threading.Thread] = None
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.connection_count = 0
        self._lock = threading.Lock()
        
        logger.info(f"DAPServerWrapper initialized: host={host}, port={port}")
        logger.info(f"DAP server path: {self.debugger_path}")

    def start(self) -> bool:
        """Start DAP server subprocess and TCP wrapper."""
        try:
            logger.info("Starting DAP server wrapper...")
            
            # Start DAP server subprocess
            self.process = subprocess.Popen(
                [sys.executable, self.debugger_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Binary mode for DAP protocol
                bufsize=0,   # Unbuffered
            )
            logger.info(f"✅ Started DAP server subprocess (PID: {self.process.pid})")
            
            # Start stderr reader thread to capture DAP server logs
            self.stderr_thread = threading.Thread(
                target=self._read_stderr,
                daemon=True
            )
            self.stderr_thread.start()

            # Start TCP server
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(2.0)  # Shorter timeout for responsive shutdown

            self.running = True
            self.server_thread = threading.Thread(target=self._accept_connections)
            self.server_thread.daemon = True
            self.server_thread.start()

            logger.info(f"✅ TCP wrapper listening on {self.host}:{self.port}")
            logger.info("✅ Ready for DAP client connections")
            logger.info("ℹ️  DAP clients should connect to this TCP wrapper, not directly to DAP server")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start DAP server wrapper: {e}")
            logger.error("Check that:")
            logger.error("1. DAP server script exists at: %s", self.debugger_path)
            logger.error("2. Port %d is not already in use", self.port)
            logger.error("3. Python can execute the DAP server script")
            self.stop()
            return False

    def stop(self) -> None:
        """Stop DAP server wrapper and subprocess."""
        logger.info("Stopping DAP server wrapper...")
        self.running = False

        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
                logger.debug("Closed client socket")
            except Exception as e:
                logger.debug(f"Error closing client socket: {e}")
            self.client_socket = None

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
                logger.debug("Closed server socket")
            except Exception as e:
                logger.debug(f"Error closing server socket: {e}")
            self.server_socket = None

        # Terminate subprocess
        if self.process:
            try:
                logger.info("Terminating DAP server subprocess...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                    logger.info("✅ DAP server subprocess terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("DAP server subprocess did not terminate, killing...")
                    self.process.kill()
                    self.process.wait(timeout=1)
                    logger.info("✅ DAP server subprocess killed")
            except Exception as e:
                logger.error(f"Error terminating subprocess: {e}")
            finally:
                self.process = None

        # Wait for threads
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
            
        if self.stderr_thread and self.stderr_thread.is_alive():
            self.stderr_thread.join(timeout=0.5)

        logger.info(f"✅ DAP server wrapper stopped (total connections: {self.connection_count})")

    def _read_stderr(self) -> None:
        """Read and log stderr from DAP server subprocess."""
        if not self.process or not self.process.stderr:
            return
        
        try:
            while self.running and self.process:
                line = self.process.stderr.readline()
                if not line:
                    break
                line = line.decode('utf-8', errors='replace').strip()
                if line:
                    logger.info(f"[DAP Server] {line}")
        except Exception as e:
            logger.debug(f"Stderr reader error: {e}")

    def _accept_connections(self) -> None:
        """Accept incoming TCP connections."""
        logger.info("Connection acceptor thread started")
        
        while self.running and self.server_socket:
            try:
                client_socket, client_addr = self.server_socket.accept()
                client_socket.settimeout(5.0)  # Set read timeout
                
                with self._lock:
                    self.connection_count += 1
                    # Close previous connection if any
                    if self.client_socket:
                        try:
                            self.client_socket.close()
                            logger.info("Closed previous client connection")
                        except Exception:
                            pass
                    self.client_socket = client_socket

                logger.info(f"✅ Client #{self.connection_count} connected from {client_addr}")
                logger.info(f"   Starting protocol bridge: TCP:{self.port} ↔ stdin/stdout")

                # Start forwarding threads for this connection
                self._start_forwarding(client_socket, client_addr)

            except socket.timeout:
                continue  # Normal timeout, check if still running
            except OSError as e:
                if self.running:
                    logger.error(f"Socket error accepting connection: {e}")
                break  # Socket closed or error
            except Exception as e:
                if self.running:
                    logger.error(f"Unexpected error accepting connection: {e}")
                break
        
        logger.info("Connection acceptor thread stopped")

    def _start_forwarding(self, client_socket: socket.socket, client_addr: tuple) -> None:
        """Start forwarding between TCP socket and subprocess pipes."""
        client_str = f"{client_addr[0]}:{client_addr[1]}"
        logger.debug(f"Starting forwarding for {client_str}")
        
        # Thread to forward TCP -> subprocess stdin
        tcp_to_stdin = threading.Thread(
            target=self._forward_tcp_to_stdin,
            args=(client_socket, client_str),
            daemon=True,
        )
        # Thread to forward subprocess stdout -> TCP
        stdout_to_tcp = threading.Thread(
            target=self._forward_stdout_to_tcp,
            args=(client_socket, client_str),
            daemon=True,
        )

        tcp_to_stdin.start()
        stdout_to_tcp.start()

        # Monitor threads (non-blocking)
        tcp_to_stdin.join(timeout=0.5)
        stdout_to_tcp.join(timeout=0.5)
        
        logger.info(f"Client {client_str} disconnected")

    def _forward_tcp_to_stdin(self, client_socket: socket.socket, client_str: str) -> None:
        """Forward data from TCP socket to subprocess stdin."""
        logger.debug(f"Starting TCP->stdin forwarder for {client_str}")
        
        try:
            while self.running and self.process and self.process.stdin:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        logger.debug(f"TCP->stdin: Connection closed by {client_str}")
                        break  # Connection closed

                    # Log DAP requests for debugging
                    if data.startswith(b'Content-Length:'):
                        lines = data.split(b'\r\n', 3)
                        if len(lines) >= 3:
                            try:
                                content_len = int(lines[0].split(b':')[1].strip())
                                logger.debug(f"TCP->stdin: DAP request from {client_str}, length={content_len}")
                            except:
                                pass

                    # Send raw bytes to subprocess stdin
                    self.process.stdin.write(data)
                    self.process.stdin.flush()
                    
                except socket.timeout:
                    continue  # Normal timeout
                except socket.error as e:
                    logger.debug(f"TCP->stdin socket error for {client_str}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error forwarding TCP->stdin for {client_str}: {e}")
                    break
        except Exception as e:
            logger.error(f"TCP->stdin thread error for {client_str}: {e}")
        finally:
            logger.debug(f"TCP->stdin forwarder stopped for {client_str}")

    def _forward_stdout_to_tcp(self, client_socket: socket.socket, client_str: str) -> None:
        """Forward data from subprocess stdout to TCP socket."""
        logger.debug(f"Starting stdout->TCP forwarder for {client_str}")
        
        try:
            while self.running and self.process and self.process.stdout:
                try:
                    # Read raw bytes (up to 4096)
                    data = self.process.stdout.read(4096)
                    if not data:
                        logger.debug(f"stdout->TCP: Subprocess terminated or EOF for {client_str}")
                        break  # Subprocess terminated or EOF

                    # Log DAP responses for debugging
                    if data.startswith(b'Content-Length:'):
                        lines = data.split(b'\r\n', 3)
                        if len(lines) >= 3:
                            try:
                                content_len = int(lines[0].split(b':')[1].strip())
                                logger.debug(f"stdout->TCP: DAP response to {client_str}, length={content_len}")
                            except:
                                pass

                    # Send raw bytes to TCP client
                    client_socket.sendall(data)
                    
                except socket.error as e:
                    logger.debug(f"stdout->TCP socket error for {client_str}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error forwarding stdout->TCP for {client_str}: {e}")
                    break
        except Exception as e:
            logger.error(f"stdout->TCP thread error for {client_str}: {e}")
        finally:
            logger.debug(f"stdout->TCP forwarder stopped for {client_str}")

    def is_alive(self) -> bool:
        """Check if wrapper and subprocess are alive."""
        if not self.running or not self.process:
            return False
        
        # Check subprocess
        if self.process.poll() is not None:
            logger.warning(f"DAP server subprocess died with exit code: {self.process.returncode}")
            return False
        
        return True
    
    def get_status(self) -> dict:
        """Get status of wrapper."""
        with self._lock:
            client_connected = self.client_socket is not None
        
        return {
            "running": self.running,
            "subprocess_alive": self.process is not None and self.process.poll() is None,
            "client_connected": client_connected,
            "connection_count": self.connection_count,
            "host": self.host,
            "port": self.port
        }

    def wait_for_connection(self, timeout: float = 30.0) -> bool:
        """Wait for a client connection."""
        logger.info(f"Waiting for client connection (timeout: {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                if self.client_socket:
                    logger.info("✅ Client connected")
                    return True
            
            # Check if wrapper is still alive
            if not self.is_alive():
                logger.error("❌ Wrapper not alive while waiting for connection")
                return False
            
            time.sleep(0.1)
        
        logger.warning(f"⏱️  Timeout waiting for client connection after {timeout}s")
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
