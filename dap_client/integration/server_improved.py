#!/usr/bin/env python3
"""
Enhanced TCP wrapper for DAP server with improved error handling and logging.

This module provides a TCP server that wraps the DAP server (stdin/stdout)
and exposes it via TCP socket for integration testing.
"""

import logging
import socket
import subprocess
import threading
import time
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dap_wrapper.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Configuration for DAP server wrapper."""
    host: str = "localhost"
    port: int = 5678
    debugger_path: Optional[str] = None
    connection_timeout: float = 30.0
    read_timeout: float = 5.0
    max_retries: int = 3
    health_check_interval: float = 10.0
    buffer_size: int = 4096
    
    def __post_init__(self):
        if self.debugger_path is None:
            self.debugger_path = str(
                Path(__file__).parent.parent.parent / "debugger" / "dap_server.py"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EnhancedDAPServerWrapper:
    """Enhanced wrapper for DAP server with TCP interface."""
    
    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.health_thread: Optional[threading.Thread] = None
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.connection_count = 0
        self.error_count = 0
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None
        
    def start(self) -> bool:
        """Start DAP server subprocess and TCP wrapper with retries."""
        logger.info(f"Starting DAP server wrapper with config: {self.config.to_dict()}")
        
        for attempt in range(self.config.max_retries):
            try:
                if self._start_internal():
                    self._start_time = time.time()
                    logger.info(f"DAP server wrapper started successfully on attempt {attempt + 1}")
                    return True
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    logger.info(f"Retrying in 2 seconds...")
                    time.sleep(2)
                    self._cleanup_failed_start()
        
        logger.error(f"Failed to start DAP server wrapper after {self.config.max_retries} attempts")
        return False
    
    def _start_internal(self) -> bool:
        """Internal startup logic."""
        # Start DAP server subprocess
        self.process = subprocess.Popen(
            [sys.executable, self.config.debugger_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # Binary mode for DAP protocol
            bufsize=0,   # Unbuffered
        )
        
        # Start stderr reader thread
        stderr_thread = threading.Thread(
            target=self._read_stderr,
            daemon=True
        )
        stderr_thread.start()
        
        logger.info(f"Started DAP server subprocess (PID: {self.process.pid})")
        
        # Start TCP server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.config.host, self.config.port))
        self.server_socket.listen(1)
        self.server_socket.settimeout(2.0)  # Shorter timeout for responsive shutdown
        
        self.running = True
        
        # Start server thread
        self.server_thread = threading.Thread(
            target=self._accept_connections,
            daemon=True
        )
        self.server_thread.start()
        
        # Start health check thread
        self.health_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_thread.start()
        
        logger.info(f"TCP wrapper listening on {self.config.host}:{self.config.port}")
        logger.info(f"Wrapper PID: {self.process.pid}, Ready for connections")
        
        return True
    
    def _cleanup_failed_start(self):
        """Cleanup after failed startup attempt."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1)
            except:
                pass
            self.process = None
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        self.running = False
    
    def stop(self) -> None:
        """Stop DAP server wrapper and subprocess gracefully."""
        logger.info("Stopping DAP server wrapper...")
        self.running = False
        
        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception as e:
                logger.debug(f"Error closing client socket: {e}")
            self.client_socket = None
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
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
                    logger.info("DAP server subprocess terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("DAP server subprocess did not terminate, killing...")
                    self.process.kill()
                    self.process.wait(timeout=1)
                    logger.info("DAP server subprocess killed")
            except Exception as e:
                logger.error(f"Error terminating subprocess: {e}")
            finally:
                self.process = None
        
        # Calculate uptime
        if self._start_time:
            uptime = time.time() - self._start_time
            logger.info(f"Wrapper uptime: {uptime:.1f} seconds, "
                       f"Connections: {self.connection_count}, "
                       f"Errors: {self.error_count}")
        
        logger.info("DAP server wrapper stopped")
    
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
                client_socket.settimeout(self.config.read_timeout)
                
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
                
                logger.info(f"Client #{self.connection_count} connected from {client_addr}")
                
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
                    self.error_count += 1
                break
        
        logger.info("Connection acceptor thread stopped")
    
    def _start_forwarding(self, client_socket: socket.socket, client_addr: tuple) -> None:
        """Start forwarding between TCP socket and subprocess pipes."""
        logger.debug(f"Starting forwarding for {client_addr}")
        
        # Thread to forward TCP -> subprocess stdin
        tcp_to_stdin = threading.Thread(
            target=self._forward_tcp_to_stdin,
            args=(client_socket, client_addr),
            daemon=True,
        )
        
        # Thread to forward subprocess stdout -> TCP
        stdout_to_tcp = threading.Thread(
            target=self._forward_stdout_to_tcp,
            args=(client_socket, client_addr),
            daemon=True,
        )
        
        tcp_to_stdin.start()
        stdout_to_tcp.start()
        
        # Monitor threads
        tcp_to_stdin.join(timeout=0.5)
        stdout_to_tcp.join(timeout=0.5)
        
        logger.debug(f"Forwarding threads completed for {client_addr}")
    
    def _forward_tcp_to_stdin(self, client_socket: socket.socket, client_addr: tuple) -> None:
        """Forward data from TCP socket to subprocess stdin."""
        client_str = f"{client_addr[0]}:{client_addr[1]}"
        logger.debug(f"Starting TCP->stdin forwarder for {client_str}")
        
        try:
            while self.running and self.process and self.process.stdin:
                try:
                    data = client_socket.recv(self.config.buffer_size)
                    if not data:
                        logger.debug(f"TCP->stdin: Connection closed by {client_str}")
                        break
                    
                    # Log first few bytes of each message (DAP Content-Length header)
                    if data.startswith(b'Content-Length:'):
                        lines = data.split(b'\r\n', 3)
                        if len(lines) >= 3:
                            try:
                                content_len = int(lines[0].split(b':')[1].strip())
                                logger.debug(f"TCP->stdin: DAP message, length={content_len}")
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
                    logger.error(f"TCP->stdin error for {client_str}: {e}")
                    self.error_count += 1
                    break
                    
        except Exception as e:
            logger.error(f"TCP->stdin thread error for {client_str}: {e}")
            self.error_count += 1
        finally:
            logger.debug(f"TCP->stdin forwarder stopped for {client_str}")
    
    def _forward_stdout_to_tcp(self, client_socket: socket.socket, client_addr: tuple) -> None:
        """Forward data from subprocess stdout to TCP socket."""
        client_str = f"{client_addr[0]}:{client_addr[1]}"
        logger.debug(f"Starting stdout->TCP forwarder for {client_str}")
        
        try:
            while self.running and self.process and self.process.stdout:
                try:
                    # Read raw bytes
                    data = self.process.stdout.read(self.config.buffer_size)
                    if not data:
                        logger.debug(f"stdout->TCP: Subprocess terminated or EOF for {client_str}")
                        break
                    
                    # Log DAP responses
                    if data.startswith(b'Content-Length:'):
                        lines = data.split(b'\r\n', 3)
                        if len(lines) >= 3:
                            try:
                                content_len = int(lines[0].split(b':')[1].strip())
                                logger.debug(f"stdout->TCP: DAP response, length={content_len}")
                            except:
                                pass
                    
                    # Send raw bytes to TCP client
                    client_socket.sendall(data)
                    
                except socket.error as e:
                    logger.debug(f"stdout->TCP socket error for {client_str}: {e}")
                    break
                except Exception as e:
                    logger.error(f"stdout->TCP error for {client_str}: {e}")
                    self.error_count += 1
                    break
                    
        except Exception as e:
            logger.error(f"stdout->TCP thread error for {client_str}: {e}")
            self.error_count += 1
        finally:
            logger.debug(f"stdout->TCP forwarder stopped for {client_str}")
    
    def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        logger.debug("Health check thread started")
        
        while self.running:
            time.sleep(self.config.health_check_interval)
            
            # Check subprocess
            if self.process and self.process.poll() is not None:
                logger.error(f"DAP server subprocess died with exit code: {self.process.returncode}")
                self.running = False
                break
            
            # Log status
            with self._lock:
                client_connected = self.client_socket is not None
            
            logger.debug(f"Health check: running={self.running}, "
                        f"subprocess_alive={self.process is not None and self.process.poll() is None}, "
                        f"client_connected={client_connected}")
        
        logger.debug("Health check thread stopped")
    
    def is_alive(self) -> bool:
        """Check if wrapper and subprocess are alive."""
        if not self.running or not self.process:
            return False
        
        # Check subprocess
        if self.process.poll() is not None:
            return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of wrapper."""
        with self._lock:
            client_connected = self.client_socket is not None
        
        return {
            "running": self.running,
            "subprocess_alive": self.process is not None and self.process.poll() is None,
            "client_connected": client_connected,
            "connection_count": self.connection_count,
            "error_count": self.error_count,
            "uptime_seconds": time.time() - self._start_time if self._start_time else 0,
            "config": self.config.to_dict()
        }
    
    def wait_for_connection(self, timeout: float = None) -> bool:
        """Wait for a client connection."""
        if timeout is None:
            timeout = self.config.connection_timeout
        
        logger.info(f"Waiting for client connection (timeout: {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                if self.client_socket:
                    logger.info("Client connected")
                    return True
            
            if not self.is_alive():
                logger.error("Wrapper not alive while waiting for connection")
                return False
            
            time.sleep(0.1)
        
        logger.warning(f"Timeout waiting for client connection after {timeout}s")
        return False


def main():
    """Command-line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enhanced TCP wrapper for DAP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --host localhost --port 5678
  %(prog)s --host 0.0.0.0 --port 9999 --debug
  %(prog)s --config-file wrapper_config.json
        """
    )
    
    parser.add_argument("--host", default="localhost", 
                       help="Host to bind to (default: localhost)")
    parser.add_argument("--port", type=int, default=5678,
                       help="Port to bind to (default: 5678)")
    parser.add_argument("--debugger-path", 
                       help="Path to DAP server script (default: auto-detected)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    parser.add_argument("--log-file", default="dap_wrapper.log",
                       help="Log file path (default: dap_wrapper.log)")
    parser.add_argument("--connection-timeout", type=float, default=30.0,
                       help="Connection timeout in seconds (default: 30)")
    parser.add_argument("--config-file",
                       help="JSON configuration file (overrides command line)")
    
    args = parser.parse_args()
    
    # Load config from file if specified
    config = ServerConfig()
    if args.config_file:
        try:
            with open(args.config_file, 'r') as f:
                file_config = json.load(f)
                for key, value in file_config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
        except Exception as e:
            logger.error(f"Failed to load config file {args.config_file}: {e}")
            return 1
    
    # Override with command line args
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.debugger_path:
        config.debugger_path = args.debugger_path
    if args.connection_timeout:
        config.connection_timeout = args.connection_timeout
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.getLogger().setLevel(log_level)
    
    # Update file handler
    for handler in logging.getLogger().handlers:
        if isinstance(handler