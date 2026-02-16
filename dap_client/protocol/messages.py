"""DAP Protocol Message Classes"""

from typing import Any, Dict, Optional
from enum import IntEnum
from .constants import (
    COMMAND_INITIALIZE, COMMAND_LAUNCH, COMMAND_DISCONNECT,
    COMMAND_SET_BREAKPOINTS, COMMAND_CONFIGURATION_DONE, COMMAND_CONTINUE
)


class SequenceType(IntEnum):
    """Sequence type enumeration"""
    REQUEST = 0
    RESPONSE = 1
    EVENT = 2


class DAPRequest:
    """Base class for DAP requests"""
    
    def __init__(self, command: str, arguments: Optional[Dict[str, Any]] = None):
        self.type = SequenceType.REQUEST
        self.seq: int = 0
        self.command = command
        self.arguments = arguments or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary"""
        return {
            "seq": self.seq,
            "type": self.type.name.lower(),
            "command": self.command,
            "arguments": self.arguments
        }
    
    def to_json(self) -> str:
        """Convert request to JSON string"""
        import json
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DAPRequest':
        """Create request from dictionary"""
        request = cls(data["command"], data.get("arguments"))
        request.seq = data["seq"]
        request.type = SequenceType[data["type"].upper()]
        return request


class DAPResponse:
    """Base class for DAP responses"""
    
    def __init__(self, request_seq: int, success: bool = True, 
                 message: Optional[str] = None, body: Optional[Dict[str, Any]] = None):
        self.type = SequenceType.RESPONSE
        self.request_seq = request_seq
        self.success = success
        self.message = message
        self.body = body or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        result = {
            "type": self.type.name.lower(),
            "request_seq": self.request_seq,
            "success": self.success
        }
        if self.message:
            result["message"] = self.message
        if self.body:
            result["body"] = self.body
        return result
    
    def to_json(self) -> str:
        """Convert response to JSON string"""
        import json
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DAPResponse':
        """Create response from dictionary"""
        body = data.get("body")
        return cls(
            request_seq=data["request_seq"],
            success=data["success"],
            message=data.get("message"),
            body=body
        )


class DAPEvent:
    """Base class for DAP events"""
    
    def __init__(self, event: str, body: Optional[Dict[str, Any]] = None):
        self.type = SequenceType.EVENT
        self.seq: int = 0
        self.event = event
        self.body = body or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        result = {
            "seq": self.seq,
            "type": self.type.name.lower(),
            "event": self.event
        }
        if self.body:
            result["body"] = self.body
        return result
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        import json
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DAPEvent':
        """Create event from dictionary"""
        return cls(
            event=data["event"],
            body=data.get("body")
        )


# Specific command implementations

class InitializeRequest(DAPRequest):
    """Initialize request"""
    
    def __init__(self, adapter_id: str = "mlir-debugger", 
                 client_id: str = "automated-test-client"):
        arguments = {
            "adapterID": adapter_id,
            "clientID": client_id,
            "columnsStartAt1": True,
            "linesStartAt1": True,
            "pathFormat": "path",
            "supportsVariableType": True,
            "supportsVariablePaging": True,
            "supportsRunInTerminalRequest": True
        }
        super().__init__(COMMAND_INITIALIZE, arguments)


class LaunchRequest(DAPRequest):
    """Launch request"""
    
    def __init__(self, program: str, no_debug: bool = True, **kwargs):
        arguments = {
            "program": program,
            "noDebug": no_debug,
            **kwargs
        }
        super().__init__(COMMAND_LAUNCH, arguments)


class SetBreakpointsRequest(DAPRequest):
    """Set breakpoints request"""
    
    def __init__(self, source: Dict[str, Any], breakpoints: list, 
                 line_breakpoints: Optional[list] = None,
                 column_breakpoints: Optional[list] = None):
        arguments = {
            "source": source,
            "breakpoints": breakpoints or []
        }
        if line_breakpoints:
            arguments["lineBreakpoints"] = line_breakpoints
        if column_breakpoints:
            arguments["columnBreakpoints"] = column_breakpoints
        super().__init__(COMMAND_SET_BREAKPOINTS, arguments)


class ConfigurationDoneRequest(DAPRequest):
    """Configuration done request"""
    
    def __init__(self):
        super().__init__(COMMAND_CONFIGURATION_DONE, {})


class ContinueRequest(DAPRequest):
    """Continue request"""
    
    def __init__(self, thread_id: int):
        """Continue request - threadId is REQUIRED"""
        arguments = {
            "threadId": thread_id
        }
        super().__init__(COMMAND_CONTINUE, arguments)


class DisconnectRequest(DAPRequest):
    """Disconnect request"""
    
    def __init__(self, terminate_debuggee: Optional[bool] = None, force: bool = False):
        arguments = {}
        if terminate_debuggee is not None:
            arguments["terminateDebuggee"] = terminate_debuggee
        super().__init__(COMMAND_DISCONNECT, arguments)
