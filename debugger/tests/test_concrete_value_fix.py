#!/usr/bin/env python3
"""
Test to verify that concrete values are properly set in MLIRValue objects.

This test verifies the fix for the issue where concrete value expressions were not
set in MLIRValue when creating values from concrete arguments in control flow.
"""

import os
import sys

# Add the debugger directory to the path
debugger_dir = os.path.join(os.path.dirname(__file__), "..", "debugger")
sys.path.insert(0, debugger_dir)

from interpreter.models import SymbolicState, MLIRValue


def test_mlirvalue_concrete_value():
    """Test that MLIRValue properly stores concrete values."""
    # Create a value with both symbolic expression and concrete value
    state = SymbolicState(pc=None)
    state.set_concrete_value("test_arg", 42)
    state.values["test_arg"] = MLIRValue("test_arg", expr=None, type="i32", concrete=42)

    # Verify concrete value is stored
    value = state.values["test_arg"]
    assert value.concrete == 42, f"Expected concrete value 42, got {value.concrete}"
    print("✓ MLIRValue stores concrete value correctly")

    # Test forking preserves concrete values
    forked_state = state.fork()
    forked_value = forked_state.values["test_arg"]
    assert (
        forked_value.concrete == 42
    ), f"Expected forked concrete value 42, got {forked_value.concrete}"
    print("✓ Forking preserves concrete values")


def test_mlirvalue_concrete_only():
    """Test that MLIRValue can be created with only concrete value."""
    # Create a value with only concrete value (no symbolic expression)
    value = MLIRValue("test", type="i32", concrete=42)

    # Verify concrete value is stored
    assert value.concrete == 42, f"Expected concrete value 42, got {value.concrete}"
    print("✓ MLIRValue can be created with only concrete value")


def test_mlirvalue_without_concrete():
    """Test that MLIRValue can be created without concrete value."""
    # Create a value without concrete value
    value = MLIRValue("test", type="i32", concrete=None)

    # Verify concrete value is None
    assert value.concrete is None, f"Expected concrete value None, got {value.concrete}"
    print("✓ MLIRValue can be created without concrete value")


if __name__ == "__main__":
    print("Testing concrete value handling in MLIRValue...")
    print()

    try:
        test_mlirvalue_concrete_value()
        test_mlirvalue_concrete_only()
        test_mlirvalue_without_concrete()
        print()
        print("All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
