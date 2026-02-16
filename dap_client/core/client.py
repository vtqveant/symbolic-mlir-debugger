"""Main DAP client class"""

import logging
from typing import Optional, Dict, Any, Callable

from dap_client.protocol import (
    InitializeRequest,
)
from .connection import DAPConnection, DAPConnectionError
from .session import DAPSession

logger = logging.getLogger(__name__)


class DAPClient:
    """Main DAP client for automated testing"""

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
        self.connection: Optional[DAPConnection] = None
        self.session: Optional[DAPSession] = None
        self.sequence = 1
        self.event_handlers: Dict[str, Callable] = {}
        self.connected = False

    def connect(self) -> bool:
        """Establish connection to DAP server"""
        try:
            self.connection = DAPConnection(self.host, self.port, self.timeout, self.read_timeout)
            if self.connection.connect():
                self.connected = True
                self._setup_event_handlers()
                return True
            return False
        except DAPConnectionError as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False

    def _setup_event_handlers(self) -> None:
        """Set up event handlers for DAP events"""
        self.connection.set_event_handler(self._handle_event)

    def _handle_event(self, event_data: Dict[str, Any]) -> None:
        """Handle incoming DAP events"""
        event_type = event_data.get("event")

        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type](event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
        else:
            logger.debug(f"Unhandled event: {event_type}")

    def initialize(
        self,
        adapter_id: str = "mlir-debugger",
        client_id: str = "automated-test-client",
    ) -> Dict[str, Any]:
        """Initialize debug session"""
        if not self.connection or not self.connection.connected:
            raise RuntimeError("Not connected to DAP server")

        request = InitializeRequest(adapter_id, client_id)
        result = self.connection.request(request)
        self.session = DAPSession(self.host, self.port)
        self.session.initialize(adapter_id, client_id)

        # Set up event handler for session
        self.session.connection.set_event_handler(self._handle_event)

        return result or {}

    def launch(self, program: str, no_debug: bool = True, **kwargs) -> Dict[str, Any]:
        """Launch the debugged program"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.launch(program, no_debug, **kwargs)

    def set_breakpoints(
        self,
        source: Dict[str, Any],
        breakpoints: list,
        line_breakpoints: Optional[list] = None,
        column_breakpoints: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Set breakpoints in source"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.set_breakpoints(
            source, breakpoints, line_breakpoints, column_breakpoints
        )

    def configuration_done(self) -> Dict[str, Any]:
        """Signal configuration is complete"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.configuration_done()

    def continue_execution(self, thread_id: int) -> Dict[str, Any]:
        """Continue execution - threadId is REQUIRED"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.continue_execution(thread_id)

    def disconnect(self, terminate_debuggee: bool = True) -> Dict[str, Any]:
        """Disconnect from debug server"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.disconnect(terminate_debuggee)

    def register_event_handler(
        self, event_type: str, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Register event handler for specific event type"""
        self.event_handlers[event_type] = handler

    def get_threads(self) -> Dict[str, Any]:
        """Get available threads"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.get_threads()

    def get_stacktrace(self, thread_id: int) -> Dict[str, Any]:
        """Get stack trace for a thread"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.get_stacktrace(thread_id)

    def get_scopes(self, frame_id: int) -> Dict[str, Any]:
        """Get scopes for a stack frame"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.get_scopes(frame_id)

    def get_variables(self, variable_reference: int) -> Dict[str, Any]:
        """Get variables"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.get_variables(variable_reference)

    def evaluate(self, expression: str, frame_id: Optional[int] = None) -> Dict[str, Any]:
        """Evaluate expression"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.evaluate(expression, frame_id)

    def symbolic_set_mode(self, enabled: bool = True) -> Dict[str, Any]:
        """Enable or disable symbolic debugging mode"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.symbolic_set_mode(enabled)

    def symbolic_evaluate(self, expression: str, frame_id: int = 0) -> Dict[str, Any]:
        """Evaluate symbolic expression"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.symbolic_evaluate(expression, frame_id)

    def symbolic_explore_paths(self, max_paths: int = 10) -> Dict[str, Any]:
        """Explore execution paths using symbolic execution"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.symbolic_explore_paths(max_paths)

    def symbolic_get_constraints(self) -> Dict[str, Any]:
        """Get current symbolic constraints"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        return self.session.symbolic_get_constraints()

    def close(self) -> None:
        """Close connection and cleanup"""
        if self.session:
            try:
                self.session.disconnect()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        self.connection = None
        self.session = None
        self.connected = False

    def __enter__(self):
        """Context manager entry"""
        if self.connect():
            return self
        raise RuntimeError("Failed to connect to DAP server")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False
