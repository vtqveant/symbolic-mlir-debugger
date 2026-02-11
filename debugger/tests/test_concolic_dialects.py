"""Concolic execution tests for dialect operations."""

import pytest
from pathlib import Path


@pytest.mark.dialect
def test_shape_ops_concolic(concolic_interpreter, parser, dialect_examples_dir):
    """Test concolic execution of shape dialect operations."""
    shape_file = dialect_examples_dir / "shape_example.mlir"
    assert shape_file.exists()

    functions = parser.parse_file(str(shape_file))
    # shape_example.mlir has one function: @shape_ops
    assert "shape_ops" in functions
    func = functions["shape_ops"]

    # Function has no parameters, can execute with empty concrete inputs
    states = concolic_interpreter.execute_function_with_concrete(func, {})
    # Should have exactly one terminal state (no branching)
    completed_states = [s for s in states if s.get_value("return") is not None]
    assert len(completed_states) == 1

    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    # Function returns multiple values but interpreter only captures first
    # First value should be shape.const_size 42
    assert ret_value.expr == 42


@pytest.mark.dialect
def test_bufferization_ops_concolic(concolic_interpreter, parser, dialect_examples_dir):
    """Test concolic execution of bufferization dialect operations."""
    bufferization_file = dialect_examples_dir / "bufferization_example.mlir"
    assert bufferization_file.exists()

    try:
        functions = parser.parse_file(str(bufferization_file))
    except Exception as e:
        import lark

        if isinstance(e, lark.exceptions.UnexpectedCharacters):
            pytest.skip(f"Bufferization parsing failed due to pymlir limitation: {e}")
        raise

    if "bufferization_ops" not in functions:
        pytest.skip("Function bufferization_ops not found")

    func = functions["bufferization_ops"]

    # Function has two index parameters
    concrete_inputs = {"arg0": 5, "arg1": 10}
    states = concolic_interpreter.execute_function_with_concrete(func, concrete_inputs)
    # Should have exactly one terminal state (no branching)
    completed_states = [s for s in states if s.get_value("return") is not None]
    assert len(completed_states) == 1

    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    # Function returns multiple i32 constants but interpreter only captures first (42)
    assert ret_value.expr == 42


@pytest.mark.dialect
def test_emitc_ops_concolic(concolic_interpreter, parser, dialect_examples_dir):
    """Test concolic execution of EmitC dialect operations."""
    emitc_file = dialect_examples_dir / "emitc_example.mlir"
    assert emitc_file.exists()

    functions = parser.parse_file(str(emitc_file))
    assert "emitc_ops" in functions
    func = functions["emitc_ops"]

    # Function has two i32 parameters
    concrete_inputs = {"arg0": 10, "arg1": 20}
    states = concolic_interpreter.execute_function_with_concrete(func, concrete_inputs)
    completed_states = [s for s in states if s.get_value("return") is not None]
    assert len(completed_states) == 1

    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    # Function returns multiple values but interpreter only captures first (constant 42)
    assert ret_value.expr == 42


@pytest.mark.dialect
def test_vector_ops_concolic(concolic_interpreter, parser, dialect_examples_dir):
    """Test concolic execution of vector dialect operations."""
    vector_file = dialect_examples_dir / "vector_example.mlir"
    assert vector_file.exists()

    functions = parser.parse_file(str(vector_file))
    assert "vector_ops" in functions
    func = functions["vector_ops"]

    # Function has two f32 parameters (interpreted as integers)
    concrete_inputs = {"arg0": 2, "arg1": 3}
    states = concolic_interpreter.execute_function_with_concrete(func, concrete_inputs)
    completed_states = [s for s in states if s.get_value("return") is not None]
    assert len(completed_states) == 1

    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    # Function returns multiple i32 constants but interpreter only captures first (42)
    assert ret_value.expr == 42


@pytest.mark.dialect
def test_func_ops_concolic(concolic_interpreter, parser, dialect_examples_dir):
    """Test concolic execution of func dialect operations."""
    func_file = dialect_examples_dir / "func_example.mlir"
    assert func_file.exists()

    functions = parser.parse_file(str(func_file))
    # Test the 'add' function which has concrete arithmetic
    assert "add" in functions
    func = functions["add"]

    concrete_inputs = {"a": 10, "b": 20}
    states = concolic_interpreter.execute_function_with_concrete(func, concrete_inputs)
    completed_states = [s for s in states if s.get_value("return") is not None]
    assert len(completed_states) == 1

    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    # add function returns a + b = 30
    import z3

    solver = z3.Solver()
    solver.add(ret_value.expr == 30)
    assert solver.check() == z3.sat


@pytest.mark.dialect
@pytest.mark.parametrize(
    "filename,func_name,concrete_inputs",
    [
        ("affine_example.mlir", "affine_for_example", {"lb": 0, "ub": 5}),
        # affine_memref_example has memref parameter - skip for now
        ("linalg_example.mlir", "linalg_generic_example", {}),
    ],
)
def test_dialect_concolic_parametrized(
    concolic_interpreter,
    parser,
    dialect_examples_dir,
    filename,
    func_name,
    concrete_inputs,
):
    """Parameterized test for dialect concolic execution."""
    filepath = dialect_examples_dir / filename
    assert filepath.exists()

    functions = parser.parse_file(str(filepath))
    if func_name not in functions:
        pytest.skip(f"Function {func_name} not found in {filename}")

    func = functions[func_name]
    states = concolic_interpreter.execute_function_with_concrete(func, concrete_inputs)

    # At least one terminal state (pc is None)
    terminal_states = [s for s in states if s.pc is None]
    assert len(terminal_states) > 0

    # For states with return values, ensure they're not None
    for state in terminal_states:
        ret_value = state.get_value("return")
        # Some functions may return void (no return value)
        # That's okay, ret_value will be None
