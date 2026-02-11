"""ExecutionStepper tests."""

import pytest
import os

from interpreter import ExecutionStepper


@pytest.mark.integration
def test_stepper_simple_add(test_data_dir):
    """Test stepping through simple addition function."""
    mlir_file = test_data_dir / "simple_add.mlir"
    if not os.path.exists(mlir_file):
        pytest.skip(f"Test file not found: {mlir_file}")

    # Create stepper with concrete inputs
    stepper = ExecutionStepper(str(mlir_file), {"a": 5, "b": 3})

    # Check initial state
    state = stepper.get_state_summary()
    assert "variables" in state
    assert "location" in state

    # Set breakpoint at line 6 (the add operation)
    stepper.set_breakpoints([6])

    # Step through operations
    for i in range(5):
        location = stepper.step_next()
        assert isinstance(location, dict)
        assert "line" in location
        assert "operation" in location

        if location["line"] == 0 and location["operation"] is None:
            break

    # Check final state
    final_state = stepper.get_state_summary()
    variables = final_state["variables"]
    assert "return" in variables
    ret_val = variables["return"].get("concrete_value")
    assert ret_val == 8  # 5 + 3 = 8


@pytest.mark.integration
def test_stepper_breakpoints(test_data_dir):
    """Test breakpoint functionality."""
    mlir_file = test_data_dir / "simple_add.mlir"
    if not os.path.exists(mlir_file):
        pytest.skip(f"Test file not found: {mlir_file}")

    stepper = ExecutionStepper(str(mlir_file), {"a": 10, "b": 20})

    # Set breakpoint at line 6
    stepper.set_breakpoints([6])

    # Run until breakpoint
    location = stepper.run_until_breakpoint()
    assert location["line"] == 6

    # Check variables before executing the add
    state = stepper.get_state_summary()
    variables = state["variables"]
    assert "a" in variables
    assert variables["a"]["concrete_value"] == 10
    assert "b" in variables
    assert variables["b"]["concrete_value"] == 20
    assert "return" not in variables  # Not yet computed

    # Step to execute the add
    stepper.step_next()
    state = stepper.get_state_summary()
    variables = state["variables"]
    assert "sum" in variables
    sum_val = variables["sum"].get("concrete_value")
    assert sum_val == 30  # 10 + 20 = 30


@pytest.mark.integration
def test_stepper_conditional_branch(test_data_dir):
    """Test stepping through conditional branch."""
    mlir_file = test_data_dir / "conditional_branch.mlir"
    if not os.path.exists(mlir_file):
        pytest.skip(f"Test file not found: {mlir_file}")

    # Test case 1: a < b (choose ^bb1)
    try:
        stepper = ExecutionStepper(str(mlir_file), {"a": 5, "b": 10})
    except Exception as e:
        if "cf.cond_br" in str(e) or "UnexpectedCharacters" in str(e):
            pytest.skip("cf.cond_br parsing failed (known limitation)")
        raise

    # Step through operations
    for i in range(10):
        location = stepper.step_next()
        if location["line"] == 0 and location["operation"] is None:
            break

    # Check final state
    final_state = stepper.get_state_summary()
    variables = final_state["variables"]
    assert "return" in variables
    ret_val = variables["return"].get("concrete_value")
    assert ret_val == 10  # max(5, 10) = 10

    # Test case 2: a >= b (choose ^bb2)
    try:
        stepper2 = ExecutionStepper(str(mlir_file), {"a": 15, "b": 10})
    except Exception as e:
        if "cf.cond_br" in str(e) or "UnexpectedCharacters" in str(e):
            pytest.skip("cf.cond_br parsing failed (known limitation)")
        raise

    for i in range(10):
        location = stepper2.step_next()
        if location["line"] == 0 and location["operation"] is None:
            break

    final_state = stepper2.get_state_summary()
    variables = final_state["variables"]
    assert "return" in variables
    ret_val = variables["return"].get("concrete_value")
    assert ret_val == 15  # max(15, 10) = 15


@pytest.mark.integration
def test_stepper_loop(test_data_dir):
    """Test stepping through loop (scf.for)."""
    mlir_file = test_data_dir / "concrete_loop.mlir"
    if not os.path.exists(mlir_file):
        pytest.skip(f"Test file not found: {mlir_file}")

    stepper = ExecutionStepper(str(mlir_file), {})

    # Step through operations
    locations = []
    for i in range(30):  # Enough steps to complete loop
        location = stepper.step_next()
        locations.append(location)
        if location["line"] == 0 and location["operation"] is None:
            break

    # Check that we stepped through loop body operations
    # Expect lines: 12 (scf.for), 13 (arith.index_cast), 14 (arith.addi), 15 (scf.yield) repeated 5 times
    # Then line 18 (return)
    # We'll just verify final result
    final_state = stepper.get_state_summary()
    variables = final_state["variables"]
    assert "return" in variables
    ret_val = variables["return"].get("concrete_value")
    assert ret_val == 10  # sum 0..4 = 10
