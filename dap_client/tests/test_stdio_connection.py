"""Unit tests for Stdio DAP connection"""

from unittest.mock import MagicMock, patch


import pytest

from ..core.stdio_connection import StdioConnection, DAPConnectionError


class TestStdioConnection:
    """Test StdioConnection class"""

    @pytest.fixture
    def connection(self):
        """Create a StdioConnection fixture"""
        return StdioConnection(debugger_path="/fake/path/dap_server.py", timeout=5, read_timeout=2)

    def test_connection_init(self, connection):
        """Test connection initialization"""
        assert connection.debugger_path == "/fake/path/dap_server.py"
        assert connection.timeout == 5
        assert connection.read_timeout == 2
        assert connection.connected is False
        assert connection.process is None

    def test_resolve_debugger_path_custom(self):
        """Test debugger path resolution with custom path"""
        connection = StdioConnection(debugger_path="/custom/path/server.py")
        assert connection.debugger_path == "/custom/path/server.py"

    @patch("pathlib.Path.exists")
    def test_resolve_debugger_path_auto(self, mock_exists):
        """Test debugger path auto-detection"""
        mock_exists.return_value = True
        connection = StdioConnection(debugger_path=None)
        # Should resolve to a path
        assert "dap_server.py" in connection.debugger_path

    @patch("subprocess.Popen")
    def test_connect_success(self, mock_popen_class, connection):
        """Test successful connection"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        mock_popen_class.return_value = mock_process

        result = connection.connect()

        assert result is True
        assert connection.connected is True
        assert connection.process is mock_process
        mock_popen_class.assert_called_once()
        # Should start reader thread
        assert connection._reader_thread is not None
        assert connection._reader_thread.is_alive()

    @patch("subprocess.Popen")
    def test_connect_process_terminates(self, mock_popen_class, connection):
        """Test connection when process terminates immediately"""
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process terminated
        mock_process.communicate.return_value = (b"", b"Error message")
        mock_popen_class.return_value = mock_process

        with pytest.raises(DAPConnectionError) as exc_info:
            connection.connect()

        assert "failed to start" in str(exc_info.value).lower()
        assert connection.connected is False

    @patch("subprocess.Popen")
    def test_connect_file_not_found(self, mock_popen_class, connection):
        """Test connection when debugger path not found"""
        mock_popen_class.side_effect = FileNotFoundError("No such file")

        with pytest.raises(DAPConnectionError) as exc_info:
            connection.connect()

        assert "not found" in str(exc_info.value).lower()

    @patch("subprocess.Popen")
    def test_disconnect(self, mock_popen_class, connection):
        """Test disconnection"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        mock_popen_class.return_value = mock_process

        connection.connect()
        assert connection.connected is True

        # Mock reader thread
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        connection._reader_thread = mock_thread

        connection.disconnect()

        assert connection.connected is False
        mock_process.terminate.assert_called_once()
        mock_thread.join.assert_called_once()

    def test_disconnect_when_not_connected(self, connection):
        """Test disconnect when not connected (should not raise)"""
        connection.disconnect()
        assert connection.connected is False

    @patch("subprocess.Popen")
    def test_send_request(self, mock_popen_class, connection):
        """Test sending a request"""
        from dap_client.protocol import InitializeRequest

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_stdin = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        mock_popen_class.return_value = mock_process

        connection.connect()
        connection.connected = True

        request = InitializeRequest()

        # Mock the process.stdin.write method
        with patch.object(mock_stdin, "write") as mock_write:
            with patch.object(mock_stdin, "flush") as mock_flush:
                connection.send(request)
                mock_write.assert_called_once()
                mock_flush.assert_called_once()

    @patch("subprocess.Popen")
    def test_set_event_handler(self, mock_popen_class, connection):
        """Test setting event handler"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        mock_popen_class.return_value = mock_process

        connection.connect()

        def dummy_handler(event):
            pass

        connection.set_event_handler(dummy_handler)
        assert connection.event_handler == dummy_handler

    @patch("subprocess.Popen")
    def test_context_manager(self, mock_popen_class):
        """Test context manager usage"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        mock_popen_class.return_value = mock_process

        connection = StdioConnection(debugger_path="/fake/path")

        with patch.object(connection, "connect") as mock_connect:

            def connect_side_effect():
                connection.connected = True
                return True

            mock_connect.side_effect = connect_side_effect
            with connection as ctx:
                assert ctx is connection
                assert connection.connected is True

        # Disconnect should be called on exit
        with patch.object(connection, "disconnect") as mock_disconnect:
            with connection:
                pass
            mock_disconnect.assert_called_once()


class TestDAPConnectionError:
    """Test DAPConnectionError exception"""

    def test_error_message(self):
        """Test error message creation"""
        error = DAPConnectionError("Test error message")
        assert str(error) == "Test error message"
