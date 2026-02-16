"""Debug session management"""

import logging
from typing import Optional, Dict, Any

from dap_client.protocol import (
    InitializeRequest,
    LaunchRequest,
    SetBreakpointsRequest,
    ConfigurationDoneRequest,
    ContinueRequest,
    DisconnectRequest,
    SymbolicSetModeRequest,
    SymbolicEvaluateRequest,
    SymbolicExplorePathsRequest,
    SymbolicGetConstraintsRequest,
)
from .connection import DAPConnection

logger = logging.getLogger(__name__)


class DAPSession:
    """Manage DAP debug session"""

    def __init__(self, host: str = "localhost", port: int = 5678):
        self.host = host
        self.port = port
        self.connection: Optional[DAPConnection] = None
        self.thread_id: Optional[int] = None
        self.process_id: Optional[int] = None
        self.breakpoints: Dict[str, Any] = {}
        self.status = "idle"

    def initialize(
        self,
        adapter_id: str = "mlir-debugger",
        client_id: str = "automated-test-client",
    ) -> Dict[str, Any]:
        """Initialize debug session"""
        if self.status != "idle":
            raise RuntimeError("Session already initialized")

        request = InitializeRequest(adapter_id, client_id)
        self.connection = DAPConnection(self.host, self.port)
        self.connection.connect()

        try:
            result = self.connection.request(request)
            self.status = "initialized"
            logger.info("Debug session initialized")
            return result or {}
        except Exception as e:
            self.connection.disconnect()
            raise

    def launch(self, program: str, no_debug: bool = True, **kwargs) -> Dict[str, Any]:
        """Launch the debugged program"""
        if self.status != "initialized":
            raise RuntimeError("Session not initialized")

        request = LaunchRequest(program, no_debug, **kwargs)
        result = self.connection.request(request)
        self.status = "launched"
        logger.info(f"Program launched: {program}")
        return result or {}

    def set_breakpoints(
        self,
        source: Dict[str, Any],
        breakpoints: list,
        line_breakpoints: Optional[list] = None,
        column_breakpoints: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Set breakpoints in source"""
        if self.status != "launched":
            raise RuntimeError("Program not launched")

        request = SetBreakpointsRequest(
            source, breakpoints, line_breakpoints, column_breakpoints
        )
        result = self.connection.request(request)
        self.breakpoints[source["path"]] = result
        logger.info(f"Set {len(result.get('breakpoints', []))} breakpoints")
        return result or {}

    def configuration_done(self) -> Dict[str, Any]:
        """Signal configuration is complete"""
        if self.status != "launched":
            raise RuntimeError("Program not launched")

        request = ConfigurationDoneRequest()
        result = self.connection.request(request)
        self.status = "ready"
        logger.info("Configuration done, ready for execution")
        return result or {}

    def continue_execution(self, thread_id: int) -> Dict[str, Any]:
        """Continue execution"""
        if self.status != "ready":
            raise RuntimeError("Session not ready for execution")

        request = ContinueRequest(thread_id)
        result = self.connection.request(request)
        self.thread_id = thread_id
        self.status = "running"
        logger.info("Execution continued")
        return result or {}

    def disconnect(self, terminate_debuggee: bool = True) -> Dict[str, Any]:
        """Disconnect from debug server"""
        if not self.connection:
            return {}

        request = DisconnectRequest(terminate_debuggee)
        result = self.connection.request(request)
        self.connection.disconnect()
        self.status = "disconnected"
        logger.info("Disconnected from debug server")
        return result or {}

    def get_threads(self) -> Dict[str, Any]:
        """Get available threads"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        # This would be a real DAP request implementation
        # For now, return stub
        return {"threads": []}

    def get_stacktrace(self, thread_id: int) -> Dict[str, Any]:
        """Get stack trace for a thread"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        # This would be a real DAP request implementation
        # For now, return stub
        return {"stackTrace": []}

    def get_scopes(self, frame_id: int) -> Dict[str, Any]:
        """Get scopes for a stack frame"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        # This would be a real DAP request implementation
        # For now, return stub
        return {"scopes": []}

    def get_variables(self, variable_reference: int) -> Dict[str, Any]:
        """Get variables"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        # This would be a real DAP request implementation
        # For now, return stub
        return {"variables": []}

    def evaluate(
        self, expression: str, frame_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Evaluate expression"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        # This would be a real DAP request implementation
        # For now, return stub
        return {"result": None}

    def symbolic_set_mode(self, enabled: bool = True) -> Dict[str, Any]:
        """Enable or disable symbolic debugging mode"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        request = SymbolicSetModeRequest(enabled)
        result = self.connection.request(request)
        logger.info(f"Symbolic mode {'enabled' if enabled else 'disabled'}")
        return result or {}

    def symbolic_evaluate(self, expression: str, frame_id: int = 0) -> Dict[str, Any]:
        """Evaluate symbolic expression"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        request = SymbolicEvaluateRequest(expression, frame_id)
        result = self.connection.request(request)
        logger.info(f"Symbolic expression evaluated: {expression}")
        return result or {}

    def symbolic_explore_paths(self, max_paths: int = 10) -> Dict[str, Any]:
        """Explore execution paths using symbolic execution"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        request = SymbolicExplorePathsRequest(max_paths)
        result = self.connection.request(request)
        logger.info(f"Explored up to {max_paths} execution paths")
        return result or {}

    def symbolic_get_constraints(self) -> Dict[str, Any]:
        """Get current symbolic constraints"""
        if not self.connection:
            raise RuntimeError("Not connected to debug server")

        request = SymbolicGetConstraintsRequest()
        result = self.connection.request(request)
        logger.info("Retrieved symbolic constraints")
        return result or {}

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.status != "disconnected":
            self.disconnect()
        return False
