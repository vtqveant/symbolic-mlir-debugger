"""Test arithmetic operations parsing and execution."""

import pytest
import z3


@pytest.mark.parser
def test_arithmetic_parsing(parser, test_data_dir):
    """Test parsing of arithmetic operations."""
    mlir_file = test_data_dir / "arithmetic_ops.mlir"
    functions = parser.parse_file(str(mlir_file))

    assert len(functions) == 1
    func = functions["compute"]
    assert len(func.basic_blocks) == 1
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 6  # 5 arithmetic ops + return


@pytest.mark.interpreter
def test_arithmetic_symbolic_execution(parser, symbolic_interpreter, test_data_dir):
    """Test symbolic execution of arithmetic operations."""
    mlir_file = test_data_dir / "arithmetic_ops.mlir"
    functions = parser.parse_file(str(mlir_file))
    func = functions["compute"]

    states = symbolic_interpreter.execute_function(func)
    completed_states = [s for s in states if s.get_value("return") is not None]

    assert len(completed_states) == 1
    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    assert ret_value.expr is not None
    # Check that return expression is a Z3 expression
    assert isinstance(ret_value.expr, z3.ExprRef)


@pytest.mark.interpreter
def test_arithmetic_concolic_execution(parser, concolic_interpreter, test_data_dir):
    """Test concolic execution of arithmetic operations with concrete inputs."""
    mlir_file = test_data_dir / "arithmetic_ops.mlir"
    functions = parser.parse_file(str(mlir_file))
    func = functions["compute"]

    # Test with concrete inputs (avoid division by zero)
    concrete_inputs = {"a": 10, "b": 2}
    states = concolic_interpreter.execute_function_with_concrete(func, concrete_inputs)

    assert len(states) == 1
    state = states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    assert ret_value.expr is not None

    # Verify the result matches expected computation
    solver = z3.Solver()
    # Expected: (a - b) + (a * b) - (a / b) = (10 - 2) + (10 * 2) - (10 // 2)
    expected = (10 - 2) + (10 * 2) - (10 // 2)  # 8 + 20 - 5 = 23
    solver.add(ret_value.expr == expected)
    assert solver.check() == z3.sat
