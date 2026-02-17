#!/usr/bin/env python3
"""
Manual test for DAP server TCP wrapper.
This test can be run without pytest installed.
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


def test_basic_wrapper():
    """Test basic wrapper functionality."""
    print("=" * 70)
    print("Test 1: Basic wrapper start/stop")
    print("=" * 70)

    wrapper = DAPServerWrapper(host="localhost", port=21111)

    try:
        # Test initialization
        print("1. Testing initialization...")
        assert wrapper.host == "localhost"
        assert wrapper.port == 21111
        print("   ✓ Initialization works")

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
        print("   ✓ Wrapper is alive")

        # Test stop
        print("4. Stopping wrapper...")
        wrapper.stop()
        time.sleep(0.2)

        if wrapper.is_alive():
            print("   ✗ Wrapper is still alive")
            return False
        print("   ✓ Wrapper stopped")

        print("\n✓ Test 1 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 1 FAILED: {e}\n")
        return False
    finally:
        if wrapper.is_alive():
            wrapper.stop()


def test_multiple_instances():
    """Test multiple wrapper instances."""
    print("=" * 70)
    print("Test 2: Multiple wrapper instances")
    print("=" * 70)

    wrappers = []
    try:
        # Start multiple wrappers
        print("1. Starting 5 wrapper instances...")
        for i in range(5):
            wrapper = DAPServerWrapper(host="localhost", port=21112 + i)
            if not wrapper.start():
                print(f"   ✗ Failed to start wrapper {i}")
                return False
            wrappers.append(wrapper)
            print(f"   ✓ Wrapper {i} started (port: {21112 + i})")

        # Check all are alive
        print("2. Checking all wrappers are alive...")
        for i, wrapper in enumerate(wrappers):
            if not wrapper.is_alive():
                print(f"   ✗ Wrapper {i} is not alive")
                return False
        print("   ✓ All wrappers are alive")

        # Stop all
        print("3. Stopping all wrappers...")
        for wrapper in wrappers:
            wrapper.stop()
        time.sleep(0.2)

        # Check all are stopped
        print("4. Checking all wrappers are stopped...")
        for wrapper in wrappers:
            if wrapper.is_alive():
                print("   ✗ Wrapper is still alive")
                return False
        print("   ✓ All wrappers are stopped")

        print("\n✓ Test 2 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 2 FAILED: {e}\n")
        return False
    finally:
        # Cleanup any remaining wrappers
        for wrapper in wrappers:
            try:
                if wrapper.is_alive():
                    wrapper.stop()
            except:
                pass


def test_rapid_start_stop():
    """Test rapid start/stop cycles."""
    print("=" * 70)
    print("Test 3: Rapid start/stop cycles")
    print("=" * 70)

    try:
        # Run many start/stop cycles
        print("1. Running 20 start/stop cycles...")
        for i in range(20):
            wrapper = DAPServerWrapper(host="localhost", port=21113 + (i % 5))

            if not wrapper.start():
                print(f"   ✗ Failed to start wrapper in cycle {i}")
                return False

            if not wrapper.is_alive():
                print(f"   ✗ Wrapper not alive in cycle {i}")
                return False

            wrapper.stop()
            time.sleep(0.05)

        print("   ✓ All cycles completed successfully")

        print("\n✓ Test 3 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 3 FAILED: {e}\n")
        return False


def test_health_check_methods():
    """Test health check methods."""
    print("=" * 70)
    print("Test 4: Health check methods")
    print("=" * 70)

    wrapper = DAPServerWrapper(host="localhost", port=21114)

    try:
        # Test wait_for_connection
        print("1. Testing wait_for_connection (should return False)...")
        start = time.time()
        connected = wrapper.wait_for_connection(timeout=0.5)
        elapsed = time.time() - start
        assert not connected
        assert elapsed < 1.0
        print("   ✓ wait_for_connection returns False correctly")

        # Test get_connections_handled
        print("2. Testing get_connections_handled...")
        count = wrapper.get_connections_handled()
        assert count == 0
        print("   ✓ get_connections_handled returns 0")

        # Start and check again
        print("3. Starting wrapper and checking again...")
        if not wrapper.start():
            print("   ✗ Failed to start wrapper")
            return False

        assert wrapper.get_connections_handled() == 0
        print("   ✓ Still returns 0")

        wrapper.stop()
        time.sleep(0.2)

        # Test is_alive
        print("4. Testing is_alive after stop...")
        if wrapper.is_alive():
            print("   ✗ Wrapper is still alive")
            return False
        print("   ✓ is_alive returns False correctly")

        print("\n✓ Test 4 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 4 FAILED: {e}\n")
        return False
    finally:
        if wrapper.is_alive():
            wrapper.stop()


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("DAP Server TCP Wrapper - Manual Test Suite")
    print("=" * 70 + "\n")

    tests = [
        ("Basic wrapper start/stop", test_basic_wrapper),
        ("Multiple wrapper instances", test_multiple_instances),
        ("Rapid start/stop cycles", test_rapid_start_stop),
        ("Health check methods", test_health_check_methods),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}\n")
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
