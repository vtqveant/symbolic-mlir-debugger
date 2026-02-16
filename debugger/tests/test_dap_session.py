"""DAP server integration tests."""

import os

import pytest
from dap_server import MLIRDebugSession


@pytest.mark.integration
def test_dap_session_launch(test_data_dir):
    """Test launching a debug session."""
    session = MLIRDebugSession()

    # Launch with simple_add.mlir
    program = test_data_dir / "simple_add.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), ["a=5", "b=3"])

    # Check that stepper is created
    assert session.stepper is not None
    assert session.program_path == str(program)
    assert session.stepper.func_name == "add"


@pytest.mark.integration
def test_dap_session_breakpoints(test_data_dir):
    """Test setting breakpoints."""
    session = MLIRDebugSession()
    program = test_data_dir / "simple_add.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), ["a=5", "b=3"])

    # Set breakpoints via URI
    uri = f"file://{program}"
    lines = [6]  # line of arith.addi operation (actual source line)
    breakpoints = session.set_breakpoints(uri, lines)

    assert len(breakpoints) == 1
    assert breakpoints[0]["line"] == 6
    assert breakpoints[0]["verified"] == True

    # Check that stepper breakpoints are set
    assert 6 in session.stepper.breakpoints


@pytest.mark.integration
def test_dap_session_continue(test_data_dir):
    """Test continue execution with breakpoints."""
    session = MLIRDebugSession()
    program = test_data_dir / "simple_add.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), ["a=5", "b=3"])

    # Set breakpoint at line 6 (arith.addi)
    uri = f"file://{program}"
    session.set_breakpoints(uri, [6])

    # Continue execution - should stop at breakpoint
    stopped = session.continue_execution()
    assert stopped == True  # Should stop at breakpoint

    # Check location
    location = session.stepper.get_current_location()
    assert location["line"] == 6  # arith.addi is on line 6
    assert location["operation"] == "arith.addi"


@pytest.mark.integration
def test_dap_session_step(test_data_dir):
    """Test stepping."""
    session = MLIRDebugSession()
    program = test_data_dir / "simple_add.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), ["a=5", "b=3"])

    # Step once (should execute arith.addi)
    still_running = session.step_next()
    assert still_running == True

    location = session.stepper.get_current_location()
    assert location["line"] == 7  # return operation is on line 7
    assert location["operation"] == "func.return"

    # Step again (should terminate)
    still_running = session.step_next()
    assert still_running == False  # terminated


@pytest.mark.integration
def test_dap_session_stack_trace(test_data_dir):
    """Test stack trace generation."""
    session = MLIRDebugSession()
    program = test_data_dir / "simple_add.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), ["a=5", "b=3"])

    frames = session.get_stack_trace(1)
    assert len(frames) == 1
    frame = frames[0]
    # Frame name now includes block and operation context
    assert frame["name"].startswith("add")
    assert "[^entry]" in frame["name"]
    assert "(arith.addi)" in frame["name"]
    assert frame["line"] == 6  # current line (first operation arith.addi on line 6)


@pytest.mark.integration
def test_dap_session_variables(test_data_dir):
    """Test variable inspection."""
    session = MLIRDebugSession()
    program = test_data_dir / "simple_add.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), ["a=5", "b=3"])

    variables = session.get_variables()
    # Should have a and b
    var_names = [v["name"] for v in variables]
    assert "a" in var_names
    assert "b" in var_names

    # Check values
    for var in variables:
        if var["name"] == "a":
            assert var["value"] == "5"
        elif var["name"] == "b":
            assert var["value"] == "3"


@pytest.mark.integration
def test_dap_session_scopes(test_data_dir):
    """Test scopes and variable references."""
    session = MLIRDebugSession()
    program = test_data_dir / "simple_add.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), ["a=5", "b=3"])

    # Get scopes for frame 1 (only frame)
    scopes = session.get_scopes(1)
    assert len(scopes) == 1
    scope = scopes[0]
    assert scope["name"] == "Variables"
    assert scope["variablesReference"] == 1
    assert scope["expensive"] == False
    assert scope["presentationHint"] == "locals"

    # Get variables for reference 1
    variables = session.get_variables(1)
    var_names = [v["name"] for v in variables]
    assert "a" in var_names
    assert "b" in var_names

    # Check that variables have proper reference IDs
    for var in variables:
        # Regular variables should have variablesReference = 0 (leaf)
        if var["name"] in ["a", "b"]:
            assert var["variablesReference"] == 0
