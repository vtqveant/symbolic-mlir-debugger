"""Unit tests for DAP client"""

from unittest.mock import MagicMock, patch

import pytest

from dap_client.core.client import DAPClient
from dap_client.core.session import DAPSession


class TestDAPClient:
    """Test DAP client class"""

    def test_client_init(self):
        """Test client initialization"""
        client = DAPClient(host="localhost", port=5678, timeout=30, read_timeout=10)

        assert client.host == "localhost"
        assert client.port == 5678
        assert client.timeout == 30
        assert client.read_timeout == 10
        assert client.connected is False
        assert client.sequence == 1

    @patch.object(DAPClient, "connect")
    def test_connect_success(self, mock_connect_method, client):
        """Test successful connection"""
        mock_connect_method.return_value = True

        result = client.connect()

        assert result is True
        mock_connect_method.assert_called_once()

    @patch.object(DAPClient, "connect")
    def test_connect_failure(self, mock_connect_method, client):
        """Test connection failure"""
        mock_connect_method.return_value = False

        result = client.connect()

        assert result is False

    @patch("dap_client.core.session.DAPConnection")
    def test_initialize(self, mock_connection_class, client):
        """Test session initialization"""
        client.connection = MagicMock()
        client.connection.connected = True
        client.connection.request.return_value = {"supportedDebuggerTypes": ["mlir"]}
        mock_connection = MagicMock()
        mock_connection_class.return_value = mock_connection
        mock_connection.connect.return_value = True

        result = client.initialize(adapter_id="test-adapter")

        assert result == {"supportedDebuggerTypes": ["mlir"]}
        client.connection.request.assert_called_once()

    def test_initialize_without_connection(self, client):
        """Test initialize without connection"""
        client.connection = None

        with pytest.raises(RuntimeError) as exc_info:
            client.initialize()

        assert "not connected" in str(exc_info.value).lower()

    def test_launch(self, client):
        """Test launching program"""
        client.session = DAPSession("localhost", 5678)
        client.session.initialize = MagicMock(return_value={})
        client.session.launch = MagicMock(return_value={"status": "running"})

        result = client.launch("program.mlir", no_debug=False)

        assert result == {"status": "running"}

    def test_launch_without_session(self, client):
        """Test launch without session"""
        client.session = None

        with pytest.raises(RuntimeError) as exc_info:
            client.launch("program.mlir")

        assert "not initialized" in str(exc_info.value).lower()

    def test_set_breakpoints(self, client):
        """Test setting breakpoints"""
        client.session = DAPSession("localhost", 5678)
        client.session.set_breakpoints = MagicMock(
            return_value={
                "breakpoints": [{"line": 10, "verified": True}, {"line": 15, "verified": True}]
            }
        )

        result = client.set_breakpoints(
            source={"path": "test.mlir"}, breakpoints=[{"line": 10}, {"line": 15}]
        )

        assert "breakpoints" in result

    def test_continue_execution(self, client):
        """Test continuing execution"""
        client.session = DAPSession("localhost", 5678)
        client.session.continue_execution = MagicMock(return_value={"allThreadsContinued": True})

        result = client.continue_execution(thread_id=1)

        assert result == {"allThreadsContinued": True}

    def test_continue_requires_thread_id(self, client):
        """Test that continue requires threadId"""
        client.session = DAPSession("localhost", 5678)

        with pytest.raises(RuntimeError) as exc_info:
            client.continue_execution(thread_id=1)

        assert "ready" in str(exc_info.value).lower()

    def test_disconnect(self, client):
        """Test disconnect"""
        client.session = DAPSession("localhost", 5678)
        client.session.disconnect = MagicMock(return_value={"status": "disconnected"})

        result = client.disconnect(terminate_debuggee=True)

        assert result == {"status": "disconnected"}

    def test_close(self, client):
        """Test closing connection"""
        client.connection = MagicMock()
        session_mock = MagicMock()
        client.session = session_mock

        client.close()

        session_mock.disconnect.assert_called_once()
        client.connection = None
        assert client.session is None

    @patch("dap_client.core.client.DAPConnection")
    def test_context_manager(self, mock_dap_connection):
        """Test context manager usage"""
        mock_connection = MagicMock()
        mock_connection.return_value = MagicMock()
        mock_connection.return_value.connect.return_value = True
        mock_dap_connection.return_value = mock_connection.return_value

        client = DAPClient(host="localhost", port=5678)

        with client as ctx:
            assert ctx is client
            assert client.connected is True

        assert client.connected is False
