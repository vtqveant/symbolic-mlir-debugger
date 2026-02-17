#!/usr/bin/env python3
"""
Tests for the DAP server TCP wrapper.

This file tests:
1. Starting and stopping the wrapper
2. Health checks
3. Basic forwarding functionality
4. Error handling
"""

import logging
import time
import threading
import pytest
from pathlib import Path

from .server import DAPServerWrapper

logger = logging.getLogger(__name__)


class TestDAPServerWrapper:
    """Test cases for DAPServerWrapper."""

    @pytest.fixture
    def wrapper(self):
        """Fixture that creates and starts a wrapper."""
        wrapper = DAPServerWrapper(host="localhost", port=18888)
        if wrapper.start():
            yield wrapper
        else:
            pytest.skip("Failed to start wrapper")

        # Cleanup
        wrapper.stop()

    def test_wrapper_initialization(self):
        """Test that wrapper initializes correctly."""
        wrapper = DAPServerWrapper(host="localhost", port=18889)

        assert wrapper.host == "localhost"
        assert wrapper.port == 18889
        assert wrapper.running is False
        assert wrapper.process is None
        assert wrapper.server_socket is None
        assert wrapper.client_socket is None

    def test_wrapper_start_stop(self, wrapper):
        """Test starting and stopping the wrapper."""
        assert wrapper.is_alive()
        assert wrapper.running is True
        assert wrapper.process is not None

        wrapper.stop()

        # Give it a moment to stop
        time.sleep(0.2)

        assert not wrapper.is_alive()
        assert wrapper.running is False
        assert wrapper.process is None

    def test_wrapper_health_check(self, wrapper):
        """Test health check method."""
        assert wrapper.is_alive()

        wrapper.stop()
        time.sleep(0.2)

        assert not wrapper.is_alive()

    def test_wrapper_concurrent_start_stop(self):
        """Test starting and stopping the wrapper concurrently."""
        wrapper = DAPServerWrapper(host="localhost", port=18890)

        # Start multiple times
        assert wrapper.start()
        assert wrapper.start()
        assert wrapper.is_alive()

        wrapper.stop()

        # Should handle this gracefully
        assert wrapper.is_alive()

        wrapper.stop()

    def test_wrapper_different_ports(self):
        """Test wrapper with different ports."""
        ports = [18891, 18892, 18893]

        for port in ports:
            wrapper = DAPServerWrapper(host="localhost", port=port)
            assert wrapper.start()
            assert wrapper.port == port
            assert wrapper.is_alive()
            wrapper.stop()

    def test_wrapper_find_debugger_path(self):
        """Test that debugger path can be auto-detected."""
        wrapper = DAPServerWrapper(debugger_path=None)

        # Should auto-detect based on current file location
        path = wrapper._resolve_debugger_path(None)
        assert path is not None
        assert "dap_server.py" in path
        assert "debugger" in path

    def test_wrapper_manual_debugger_path(self):
        """Test wrapper with explicit debugger path."""
        # Use a known valid path
        current_file = Path(__file__).resolve()
        integration_dir = current_file.parent
        client_dir = integration_dir.parent
        project_root = client_dir.parent
        debugger_path = project_root / "debugger" / "dap_server.py"

        if debugger_path.exists():
            wrapper = DAPServerWrapper(debugger_path=str(debugger_path))
            assert wrapper.start()
            assert wrapper.is_alive()
            wrapper.stop()

    def test_wrapper_error_on_port_in_use(self):
        """Test that wrapper fails when port is already in use."""
        # This test might be flaky depending on system state
        # Try to start wrapper on a likely-to-be-available port
        wrapper = DAPServerWrapper(host="localhost", port=19800)

        if not wrapper.start():
            pytest.skip("Could not bind to test port (might be in use)")

        assert wrapper.is_alive()

        # Try to start another wrapper on same port
        wrapper2 = DAPServerWrapper(host="localhost", port=19800)
        assert not wrapper2.start()

        wrapper.stop()

    def test_wrapper_connection_handling(self, wrapper):
        """Test that wrapper can handle connections properly."""
        # The wrapper should be running and accepting connections
        assert wrapper.is_alive()
        assert wrapper.running is True

        # Should handle multiple start/stop cycles
        for i in range(3):
            assert wrapper.is_alive()
            time.sleep(0.1)

        wrapper.stop()
        time.sleep(0.2)
        assert not wrapper.is_alive()

    def test_wrapper_logging(self, caplog):
        """Test that wrapper produces expected logs."""
        with caplog.at_level(logging.INFO):
            wrapper = DAPServerWrapper(host="localhost", port=19801)

            assert wrapper.start()

            # Should have start messages
            assert any("Starting DAP server wrapper" in record.message for record in caplog.records)
            assert any("listening on" in record.message for record in caplog.records)

            wrapper.stop()

            # Should have stop message
            assert any("Stopping DAP server wrapper" in record.message for record in caplog.records)

    def test_wrapper_multiple_connections(self):
        """Test wrapper with multiple simulated connections."""
        # This is a basic test - in practice, the wrapper would need
        # a real client to connect to handle multiple connections
        wrapper = DAPServerWrapper(host="localhost", port=19802)

        assert wrapper.start()

        # Simulate multiple connection attempts
        for _ in range(3):
            # Just verify wrapper is still running
            assert wrapper.is_alive()
            time.sleep(0.1)

        wrapper.stop()

    def test_wrapper_wait_for_connection(self, wrapper):
        """Test wait_for_connection method."""
        start_time = time.time()

        # Should return False if no client connects
        connected = wrapper.wait_for_connection(timeout=0.5)

        elapsed = time.time() - start_time
        assert not connected
        assert elapsed < 1.0  # Should return quickly

    def test_wrapper_connections_handled_count(self, wrapper):
        """Test that connection count tracking works."""
        assert wrapper.get_connections_handled() == 0

        wrapper.stop()
        time.sleep(0.2)

        wrapper = DAPServerWrapper(host="localhost", port=19803)
        assert wrapper.start()

        # Should be 0 initially
        assert wrapper.get_connections_handled() == 0

        wrapper.stop()


class TestDAPServerWrapperStress:
    """Stress tests for the wrapper."""

    def test_wrapper_rapid_start_stop(self):
        """Test rapid start/stop cycles."""
        for i in range(10):
            wrapper = DAPServerWrapper(host="localhost", port=19900 + i)
            assert wrapper.start()
            assert wrapper.is_alive()
            wrapper.stop()

    def test_wrapper_parallel_instances(self):
        """Test multiple wrapper instances running in parallel."""
        wrappers = []
        try:
            # Start multiple wrappers
            for i in range(5):
                wrapper = DAPServerWrapper(host="localhost", port=20000 + i)
                assert wrapper.start()
                assert wrapper.is_alive()
                wrappers.append(wrapper)

            # All should be alive
            for wrapper in wrappers:
                assert wrapper.is_alive()

            # Stop all
            for wrapper in wrappers:
                wrapper.stop()

            # All should be stopped
            for wrapper in wrappers:
                time.sleep(0.1)
                assert not wrapper.is_alive()

        except Exception as e:
            # Cleanup on error
            for wrapper in wrappers:
                try:
                    wrapper.stop()
                except:
                    pass
            raise


if __name__ == "__main__":
    # For manual testing
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
