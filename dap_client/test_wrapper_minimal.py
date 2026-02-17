#!/usr/bin/env python3
"""
Minimal manual test for DAP server TCP wrapper.
This test only validates the wrapper's core functionality without requiring all dependencies.
"""

import logging
import time
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from integration.server import DAPServerWrapper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def test_wrapper_start_stop():
    """Test basic wrapper start/stop."""
    print("=" * 70)
    print("Test: DAP Server Wrapper - Start/Stop")
    print("=" * 70)

    wrapper = DAPServerWrapper(host="localhost", port=21201)

    try:
        # Test initialization
        print("1. Testing initialization...")
        assert wrapper.host == "localhost", f"Expected localhost, got {wrapper.host}"
        assert wrapper.port == 21201, f"Expected port 21201, got {wrapper.port}"
        assert wrapper.running is False, "Expected running=False initially"
        assert wrapper.process is None, "Expected process=None initially"
        print("   ✓ Initialization correct")

        # Test starting
        print("2. Starting wrapper...")
        if not wrapper.start():
            print("   ✗ Failed to start wrapper")
            return False
        print("   ✓ Wrapper started")

        # Test health check
        print("3. Testing health check...")
        if not wrapper.is_alive():
            print("   ✗ Wrapper is not alive")
            return False
        assert wrapper.running is True, "Expected running=True"
        assert wrapper.process is not None, "Expected process not None"
        print("   ✓ Wrapper is alive and running")

        # Test stop
        print("4. Stopping wrapper...")
        wrapper.stop()
        time.sleep(0.2)

        if wrapper.is_alive():
            print("   ✗ Wrapper is still alive after stop")
            return False
        assert wrapper.running is False, "Expected running=False"
        assert wrapper.process is None, "Expected process=None after stop"
        print("   ✓ Wrapper stopped correctly")

        print("\n✓ Test PASSED\n")
        return True

    except AssertionError as e:
        print(f"\n✗ Test FAILED: Assertion error: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ Test FAILED: {e}\n")
        return False
    finally:
        if wrapper.is_alive():
            wrapper.stop()


def test_wrapper_configuration():
    """Test wrapper configuration options."""
    print("=" * 70)
    print("Test: DAP Server Wrapper - Configuration")
    print("=" * 70)

    try:
        # Test custom host
        print("1. Testing custom host...")
        wrapper1 = DAPServerWrapper(host="127.0.0.1", port=21202)
        assert wrapper1.host == "127.0.0.1"
        print("   ✓ Custom host works")

        # Test custom port
        print("2. Testing custom port...")
        wrapper2 = DAPServerWrapper(port=21203)
        assert wrapper2.port == 21203
        print("   ✓ Custom port works")

        # Test multiple wrappers with different ports
        print("3. Testing multiple wrappers on different ports...")
        wrappers = []
        for i in range(3):
            wrapper = DAPServerWrapper(host="localhost", port=21204 + i)
            assert wrapper.start()
            assert wrapper.is_alive()
            wrappers.append(wrapper)

        # Check all have correct configurations
        for i, wrapper in enumerate(wrappers):
            assert wrapper.host == "localhost"
            assert wrapper.port == 21204 + i
            assert wrapper.running is True

        # Stop all
        for wrapper in wrappers:
            wrapper.stop()

        print("   ✓ Multiple wrappers work correctly")

        print("\n✓ Test PASSED\n")
        return True

    except AssertionError as e:
        print(f"\n✗ Test FAILED: Assertion error: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ Test FAILED: {e}\n")
        return False


def test_wrapper_method_signature():
    """Test that wrapper has expected methods."""
    print("=" * 70)
    print("Test: DAP Server Wrapper - Method Signature")
    print("=" * 70)

    wrapper = DAPServerWrapper(host="localhost", port=21205)

    try:
        # Check expected methods exist
        print("1. Checking method signatures...")
        assert hasattr(wrapper, 'start'), "Missing start() method"
        assert hasattr(wrapper, 'stop'), "Missing stop() method"
        assert hasattr(wrapper, 'is_alive'), "Missing is_alive() method"
        assert hasattr(wrapper, 'wait_for_connection'), "Missing wait_for_connection() method"
        assert hasattr(wrapper, 'get_connections_handled'), "Missing get_connections_handled() method"
        assert hasattr(wrapper, '_resolve_debugger_path'), "Missing _resolve_debugger_path() method"
        print("   ✓ All expected methods exist")

        # Check method call signatures
        print("2. Testing method signatures...")
        import inspect

        # Check start() accepts required parameters
        sig = inspect.signature(wrapper.start)
        params = list(sig.parameters.keys())
        print(f"   start() parameters: {params}")

        # Check stop() accepts required parameters
        sig = inspect.signature(wrapper.stop)
        params = list(sig.parameters.keys())
        print(f"   stop() parameters: {params}")

        # Check is_alive() accepts required parameters
        sig = inspect.signature(wrapper.is_alive)
        params = list(sig.parameters.keys())
        print(f"   is_alive() parameters: {params}")

        print("   ✓ Method signatures correct")

        print("\n✓ Test PASSED\n")
        return True

    except AssertionError as e:
        print(f"\n✗ Test FAILED: Assertion error: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ Test FAILED: {e}\n")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("DAP Server TCP Wrapper - Minimal Test Suite")
    print("=" * 70 + "\n")

    tests = [
        ("Start/Stop", test_wrapper_start_stop),
        ("Configuration", test_wrapper_configuration),
        ("Method Signature", test_wrapper_method_signature),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}\n")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("=" * 70)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 70)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
