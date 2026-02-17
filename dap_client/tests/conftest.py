"""Pytest fixtures for DAP client tests"""

import pytest
from unittest.mock import patch, MagicMock

from ..core.client import DAPClient


@pytest.fixture
def client():
    """Create a DAP client fixture"""
    return DAPClient()


@pytest.fixture
def mock_connection():
    """Create a mock DAP connection"""
    with patch("dap_client.core.stdio_connection.StdioConnection") as mock:
        connection_instance = MagicMock()
        mock.return_value = connection_instance
        yield connection_instance
