"""Unit tests for DAP connection"""

import socket
from unittest.mock import MagicMock, patch

import pytest

from dap_client.core.connection import DAPConnection, DAPConnectionError


class TestDAPConnection:
    """Test DAP connection management"""
    
    @pytest.fixture
    def connection(self):
        """Create a DAP connection fixture"""
        return DAPConnection(host="localhost", port=5678, timeout=5, read_timeout=2)
    
    def test_connection_init(self, connection):
        """Test connection initialization"""
        assert connection.host == "localhost"
        assert connection.port == 5678
        assert connection.timeout == 5
        assert connection.read_timeout == 2
        assert connection.connected is False
    
    @patch('socket.socket')
    def test_connect_success(self, mock_socket_class, connection):
        """Test successful connection"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        result = connection.connect()
        
        assert result is True
        assert connection.connected is True
        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
    
    @patch('socket.socket')
    def test_connect_timeout(self, mock_socket_class, connection):
        """Test connection timeout"""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.timeout()
        mock_socket_class.return_value = mock_socket
        
        with pytest.raises(DAPConnectionError) as exc_info:
            connection.connect()
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('socket.socket')
    def test_connect_refused(self, mock_socket_class, connection):
        """Test connection refused"""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = ConnectionRefusedError()
        mock_socket_class.return_value = mock_socket
        
        with pytest.raises(DAPConnectionError) as exc_info:
            connection.connect()
        
        assert "refused" in str(exc_info.value).lower()
    
    @patch('socket.socket')
    def test_disconnect(self, mock_socket_class, connection):
        """Test disconnection"""
        connection.connected = True
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        connection.disconnect()
        
        assert connection.connected is False
        if connection.socket:
            mock_socket.close.assert_called_once()
    
    def test_disconnect_when_not_connected(self, connection):
        """Test disconnect when not connected (should not raise)"""
        connection.disconnect()
    
    def test_send_request(self, connection):
        """Test sending a request"""
        from dap_client.protocol import InitializeRequest
        
        connection.connected = True
        connection.socket = MagicMock()
        
        request = InitializeRequest()
        connection.send(request)
        
        connection.socket.sendall.assert_called_once()


class TestDAPConnectionError:
    """Test DAPConnectionError exception"""
    
    def test_error_message(self):
        """Test error message creation"""
        error = DAPConnectionError("Test error message")
        assert str(error) == "Test error message"
