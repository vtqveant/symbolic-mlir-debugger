"""Unit tests for DAP protocol"""

import json

from dap_client.protocol import (
    DAPRequest,
    DAPResponse,
    DAPEvent,
    InitializeRequest,
    LaunchRequest,
    SetBreakpointsRequest,
    ConfigurationDoneRequest,
    ContinueRequest,
    DisconnectRequest,
)


class TestDAPRequest:
    """Test DAP request base class"""

    def test_create_request(self):
        """Test creating a basic request"""
        request = DAPRequest("testCommand", {"arg1": "value1"})
        assert request.command == "testCommand"
        assert request.arguments == {"arg1": "value1"}
        assert request.type.name.lower() == "request"

    def test_request_to_dict(self):
        """Test request serialization to dict"""
        request = DAPRequest("testCommand", {"arg1": "value1"})
        request.seq = 1

        result = request.to_dict()
        assert result["seq"] == 1
        assert result["command"] == "testCommand"
        assert result["arguments"] == {"arg1": "value1"}

    def test_request_to_json(self):
        """Test request serialization to JSON"""
        request = DAPRequest("testCommand", {"arg1": "value1"})
        request.seq = 1

        result = request.to_json()
        data = json.loads(result)
        assert data["seq"] == 1
        assert data["command"] == "testCommand"

    def test_request_from_dict(self):
        """Test creating request from dict"""
        data = {
            "seq": 1,
            "type": "request",
            "command": "testCommand",
            "arguments": {"arg1": "value1"},
        }

        request = DAPRequest.from_dict(data)
        assert request.command == "testCommand"
        assert request.arguments == {"arg1": "value1"}
        assert request.seq == 1


class TestDAPResponse:
    """Test DAP response base class"""

    def test_create_response(self):
        """Test creating a basic response"""
        response = DAPResponse(request_seq=1, success=True, message="Success")
        assert response.request_seq == 1
        assert response.success == True
        assert response.message == "Success"

    def test_response_to_dict(self):
        """Test response serialization to dict"""
        response = DAPResponse(request_seq=1, success=True, body={"result": "ok"})

        result = response.to_dict()
        assert result["request_seq"] == 1
        assert result["success"] == True
        assert result["body"] == {"result": "ok"}

    def test_response_to_json(self):
        """Test response serialization to JSON"""
        response = DAPResponse(request_seq=1, success=True, body={"result": "ok"})

        result = response.to_json()
        data = json.loads(result)
        assert data["request_seq"] == 1
        assert data["success"] == True

    def test_response_from_dict(self):
        """Test creating response from dict"""
        data = {
            "seq": 1,
            "type": "response",
            "request_seq": 1,
            "success": True,
            "body": {"result": "ok"},
        }

        response = DAPResponse.from_dict(data)
        assert response.request_seq == 1
        assert response.success == True


class TestDAPEvent:
    """Test DAP event base class"""

    def test_create_event(self):
        """Test creating a basic event"""
        event = DAPEvent("testEvent", {"key": "value"})
        assert event.event == "testEvent"
        assert event.body == {"key": "value"}
        assert event.type.name.lower() == "event"

    def test_event_to_dict(self):
        """Test event serialization to dict"""
        event = DAPEvent("testEvent", {"key": "value"})
        event.seq = 1

        result = event.to_dict()
        assert result["seq"] == 1
        assert result["event"] == "testEvent"
        assert result["body"] == {"key": "value"}

    def test_event_from_dict(self):
        """Test creating event from dict"""
        data = {"seq": 1, "type": "event", "event": "testEvent", "body": {"key": "value"}}

        event = DAPEvent.from_dict(data)
        assert event.event == "testEvent"
        assert event.body == {"key": "value"}


class TestInitializeRequest:
    """Test InitializeRequest"""

    def test_create_initialize_request(self):
        """Test creating initialize request"""
        request = InitializeRequest(adapter_id="test-adapter", client_id="test-client")

        assert request.command == "initialize"
        assert request.arguments["adapterID"] == "test-adapter"
        assert request.arguments["clientID"] == "test-client"
        assert request.arguments["columnsStartAt1"] == True
        assert request.arguments["linesStartAt1"] == True


class TestLaunchRequest:
    """Test LaunchRequest"""

    def test_create_launch_request(self):
        """Test creating launch request"""
        request = LaunchRequest("program.mlir", no_debug=False)

        assert request.command == "launch"
        assert request.arguments["program"] == "program.mlir"
        assert request.arguments["noDebug"] == False


class TestSetBreakpointsRequest:
    """Test SetBreakpointsRequest"""

    def test_create_setbreakpoints_request(self):
        """Test creating set breakpoints request"""
        source = {"path": "test.mlir"}
        breakpoints = [{"line": 10}, {"line": 20}]

        request = SetBreakpointsRequest(source, breakpoints)

        assert request.command == "setBreakpoints"
        assert request.arguments["source"]["path"] == "test.mlir"
        assert len(request.arguments["breakpoints"]) == 2


class TestConfigurationDoneRequest:
    """Test ConfigurationDoneRequest"""

    def test_create_configurationdone_request(self):
        """Test creating configuration done request"""
        request = ConfigurationDoneRequest()

        assert request.command == "configurationDone"
        assert request.arguments == {}


class TestContinueRequest:
    """Test ContinueRequest"""

    def test_create_continue_request(self):
        """Test creating continue request - threadId is REQUIRED"""
        request = ContinueRequest(thread_id=1)

        assert request.command == "continue"
        assert request.arguments["threadId"] == 1


class TestDisconnectRequest:
    """Test DisconnectRequest"""

    def test_create_disconnect_request(self):
        """Test creating disconnect request"""
        request = DisconnectRequest(terminate_debuggee=True)

        assert request.command == "disconnect"
        assert request.arguments["terminateDebuggee"] == True
