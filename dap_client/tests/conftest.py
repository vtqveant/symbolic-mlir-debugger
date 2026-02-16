"""Pytest fixtures for DAP client tests"""

import pytest
from dap_client.core.client import DAPClient


@pytest.fixture
def client():
    """Create a DAP client fixture"""
    return DAPClient(host="localhost", port=5678)


@pytest.fixture
def mock_connection():
    """Create a mock DAP connection"""
    with patch('dap_client.core.connection.DAPConnection') as mock:
        connection_instance = MagicMock()
        mock.return_value = connection_instance
        yield connection_instance
