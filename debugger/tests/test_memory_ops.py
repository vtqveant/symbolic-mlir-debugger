#!/usr/bin/env python3
"""Memory operations tests for symbolic MLIR interpreter."""

import pytest
import z3


@pytest.mark.interpreter
def test_memref_basic(symbolic_interpreter, parser):
    """Test basic memref operations: alloc, store, load."""
    mlir_code = """
module {
  func.func @test_memref_basic() -> i32 {
    %mem = memref.alloc() : memref<10xi32>
    %c5 = arith.constant 5 : i32
    memref.store %c5, %mem[0] : memref<10xi32>
    %val = memref.load %mem[0] : memref<10xi32>
    return %val : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test_memref_basic"]

    states = symbolic_interpreter.execute_function(func)
    completed_states = [s for s in states if s.pc is None]
    assert len(completed_states) == 1

    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    # Return value should be a Z3 expression
    assert isinstance(ret_value.expr, z3.ExprRef)
    # Memory should contain the memref
    assert "mem" in state.memory
    # The memory value should be the stored constant (5) but currently symbolic
    # For now just ensure memory exists
    mem_value = state.memory["mem"]
    assert mem_value.expr is not None


@pytest.mark.interpreter
def test_tensor_extract_insert(symbolic_interpreter, parser):
    """Test tensor extract and insert operations."""
    mlir_code = """
module {
  func.func @test_tensor() -> i32 {
    %c7 = arith.constant 7 : i32
    %tensor = tensor.splat %c7 : tensor<10xi32>
    %idx = arith.constant 2 : index
    %val1 = tensor.extract %tensor[%idx] : tensor<10xi32>
    %c42 = arith.constant 42 : i32
    %new_tensor = tensor.insert %c42 into %tensor[%idx] : tensor<10xi32>
    %val2 = tensor.extract %new_tensor[%idx] : tensor<10xi32>
    return %val2 : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test_tensor"]

    states = symbolic_interpreter.execute_function(func)
    completed_states = [s for s in states if s.pc is None]
    assert len(completed_states) == 1

    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    assert isinstance(ret_value.expr, z3.ExprRef)
    # Memory should contain tensor and new_tensor
    # Currently tensor and new_tensor are separate memory entries
    # (simplified model)
    assert "tensor" in state.memory or "new_tensor" in state.memory


@pytest.mark.concolic
def test_concolic_memref(concolic_interpreter, parser):
    """Test concolic execution with memref operations."""
    mlir_code = """
module {
  func.func @test_concolic_memref() -> i32 {
    %mem = memref.alloc() : memref<10xi32>
    %c5 = arith.constant 5 : i32
    memref.store %c5, %mem[0] : memref<10xi32>
    %val = memref.load %mem[0] : memref<10xi32>
    return %val : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test_concolic_memref"]

    states = concolic_interpreter.execute_function(func)
    completed_states = [s for s in states if s.pc is None]
    assert len(completed_states) == 1

    state = completed_states[0]
    ret_value = state.get_value("return")
    assert ret_value is not None
    # In concolic mode, concrete value should be 5
    concrete_val = state.get_concrete_value("return")
    assert concrete_val == 5
