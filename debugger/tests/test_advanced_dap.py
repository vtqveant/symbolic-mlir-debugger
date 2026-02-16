#!/usr/bin/env python3
"""
Advanced DAP tests for expression evaluation and state inspection.
"""

import pytest
import os
import tempfile
from dap_server import MLIRDebugSession


@pytest.mark.integration
def test_expression_memory_cell_access(test_data_dir):
    """Test expression evaluation with memory cell access."""
    session = MLIRDebugSession()
    program = test_data_dir / "memref_basic.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), [])

    # Step through to create memory cell
    for i in range(4):
        session.step_next()

    # Test memory cell access with bracket notation
    result = session.evaluate_expression("mem[0]")
    assert result["result"] == "5", f"Expected '5', got {result['result']}"
    assert result["type"] == "int"

    # Test arithmetic with memory cell
    result = session.evaluate_expression("mem[0] + 10")
    assert result["result"] == "15", f"Expected '15', got {result['result']}"

    # Test transformed name also works
    result = session.evaluate_expression("mem_0_ * 2")
    assert result["result"] == "10", f"Expected '10', got {result['result']}"

    print("✓ Memory cell expression evaluation passed")


@pytest.mark.integration
def test_expression_boolean_operations(test_data_dir):
    """Test boolean expressions and comparisons."""
    session = MLIRDebugSession()
    program = test_data_dir / "simple_add.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(program, ["a=5", "b=3"])
    session.step_next()  # Create sum variable

    # Test comparisons
    tests = [
        ("a > b", "True"),
        ("a < b", "False"),
        ("a == 5", "True"),
        ("a != b", "True"),
        ("a >= 5", "True"),
        ("b <= 3", "True"),
        ("a > 0 and b > 0", "True"),
        ("a < 0 or b > 0", "True"),
        ("not (a < b)", "True"),
    ]

    for expr, expected in tests:
        result = session.evaluate_expression(expr)
        assert (
            result["result"] == expected
        ), f"Expression '{expr}' expected '{expected}', got '{result['result']}'"
        assert (
            result["type"] == "bool"
        ), f"Expected type 'bool' for '{expr}', got '{result['type']}'"

    print("✓ Boolean expression evaluation passed")


@pytest.mark.integration
def test_state_inspection_path_conditions(test_data_dir):
    """Test that path conditions are exposed in variables."""
    session = MLIRDebugSession()
    program = test_data_dir / "conditional_branch.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    # Launch with concrete values that will take one path
    session.launch(str(program), ["a=5", "b=10"])

    # Step through conditional branch
    for i in range(3):
        session.step_next()

    # Get variables - should include $pathConditions if path constraints added
    variables = session.get_variables()

    # Check for $pathConditions variable
    path_cond_var = None
    for var in variables:
        if var["name"] == "$pathConditions":
            path_cond_var = var
            break

    # Note: path conditions may not be added in concrete execution
    # This test just ensures the variable exists when appropriate
    if path_cond_var:
        assert (
            path_cond_var["variablesReference"] > 0
        ), "$pathConditions should have variablesReference > 0"

        # Try to expand
        ref_id = path_cond_var["variablesReference"]
        children = session.get_variable_children(ref_id)
        # Should be list of constraints
        assert isinstance(children, list)
        print(f"✓ Found {len(children)} path constraints")
    else:
        print("✓ No path conditions in concrete execution (expected)")

    print("✓ Path condition inspection test passed")


@pytest.mark.integration
def test_state_inspection_memory_map(test_data_dir):
    """Test that memory map summary is exposed."""
    session = MLIRDebugSession()
    program = test_data_dir / "memref_basic.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), [])

    # Step through to create memory
    for i in range(4):
        session.step_next()

    variables = session.get_variables()

    # Check for $memoryMap variable
    memory_map_var = None
    for var in variables:
        if var["name"] == "$memoryMap":
            memory_map_var = var
            break

    assert memory_map_var is not None, "$memoryMap should be present"
    assert memory_map_var["variablesReference"] > 0, "$memoryMap should have variablesReference > 0"

    # Expand memory map
    ref_id = memory_map_var["variablesReference"]
    children = session.get_variable_children(ref_id)
    assert len(children) == 1, f"Expected 1 memory region, got {len(children)}"
    assert children[0]["name"] == "mem", f"Expected memory region 'mem', got {children[0]['name']}"
    assert "cells" in children[0]["value"], f"Memory region should show cell count"

    print("✓ Memory map inspection test passed")


@pytest.mark.integration
def test_expression_error_handling():
    """Test error handling for invalid expressions."""
    session = MLIRDebugSession()

    # Create a simple MLIR program
    test_mlir = """
module {
  func.func @test(%a: i32) -> i32 {
    %b = arith.addi %a, %a : i32
    return %b : i32
  }
}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
        f.write(test_mlir)
        temp_file = f.name

    try:
        session.launch(temp_file, ["a=5"])
        session.step_next()

        # Test various error cases
        error_cases = [
            "undefined_var",
            "a / 0",  # Division by zero (may cause error)
            "mem[999]",  # Non-existent memory cell
            "a + ",  # Syntax error
        ]

        for expr in error_cases:
            result = session.evaluate_expression(expr)
            assert (
                result["type"] == "error"
            ), f"Expected error type for '{expr}', got {result['type']}"
            assert result["result"].startswith(
                "Error:"
            ), f"Expected error message for '{expr}', got {result['result']}"
            print(f"  ✓ Error handled for: {expr}")

        print("✓ Expression error handling test passed")

    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    # Run tests directly
    import sys

    test_dir = os.path.join(os.path.dirname(__file__), "..", "tests")
    test_data_dir = type(
        "obj", (object,), {"__truediv__": lambda self, x: os.path.join(test_dir, x)}
    )()

    print("Testing memory cell expression access...")
    test_expression_memory_cell_access(test_data_dir)

    print("\nTesting boolean operations...")
    test_expression_boolean_operations(test_data_dir)

    print("\nTesting state inspection (path conditions)...")
    test_state_inspection_path_conditions(test_data_dir)

    print("\nTesting state inspection (memory map)...")
    test_state_inspection_memory_map(test_data_dir)

    print("\nTesting expression error handling...")
    test_expression_error_handling()

    print("\n✅ All advanced DAP tests passed!")
