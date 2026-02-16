#!/usr/bin/env python3
"""
Memref dialect execution handlers.

Handles operations: alloc, alloca, load, store, etc.
"""

import re
from typing import Any, Tuple, Optional, List, Union

import z3

from .base import OperationHandler
from ..models import SymbolicState, MLIRFunction, MLIRValue
from ..operations import (
    LoadOperation,
    StoreOperation,
    Operation,
    ReinterpretCastOperation,
)


def parse_memref_type(memref_type: str) -> Tuple[List[int], str]:
    """Parse memref type string into shape tuple and dtype.

    Examples:
        "memref<8x8xf32>" -> ([8, 8], "f32")
        "memref<?xi32>" -> ([-1], "i32")
        "memref<*xf64>" -> ([-1], "f64")  # unranked
    """
    # Extract content inside <>
    match = re.match(r"memref<(.+)>", memref_type.strip())
    if not match:
        # Fallback: assume 1D dynamic with given dtype
        return ([-1], memref_type)

    inner = match.group(1)
    # Handle unranked memref<*xf32>
    if inner.startswith("*x"):
        dtype = inner[2:]  # remove "*x"
        return ([-1], dtype)

    # Split by 'x' to separate dimensions and dtype
    parts = inner.split("x")
    if len(parts) < 2:
        # Probably single dimension
        if parts[0].endswith("i") or parts[0].endswith("f"):
            # Actually a dtype with no dimension? unlikely
            return ([-1], parts[0])
        else:
            # Single dimension, dtype missing? assume i32
            try:
                dim = int(parts[0])
                return ([dim], "i32")
            except ValueError:
                return ([-1], "i32")

    # Last part is dtype
    dtype = parts[-1]
    dim_parts = parts[:-1]

    shape = []
    for dim in dim_parts:
        if dim == "?":
            shape.append(-1)
        else:
            try:
                shape.append(int(dim))
            except ValueError:
                shape.append(-1)  # unknown dimension

    return (shape, dtype)


class MemrefAllocOpHandler(OperationHandler):
    """Handler for memref.alloc operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute memref.alloc symbolically."""
        # Create fresh symbolic variable for the memref
        if not op.dest:
            raise ValueError("memref.alloc must have destination")
        assert op.dest is not None
        dest = op.dest
        result_type = op.result_type or "memref<?xi32>"
        # For now, create a single symbolic value for the entire memref
        expr = z3.FreshConst(z3.IntSort(), f"memref_{dest}")
        state.set_value(dest, expr, result_type)

        # Parse shape and dtype from memref type
        shape_list, dtype = parse_memref_type(result_type)
        shape = tuple(shape_list)

        # Allocate in memory model
        state.allocate_memory(dest, shape, dtype)

        # Also allocate in memory_cells dictionary (legacy)
        state.memory_cells[dest] = {}
        # Set single-cell memory for compatibility with existing tests
        state.set_memory(dest, expr, result_type)

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Allocation doesn't produce a concrete value."""
        return None


class MemrefLoadOpHandler(OperationHandler):
    """Handler for memref.load operation."""

    def execute_symbolic(  # type: ignore[override]
        self,
        op: LoadOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute memref.load symbolically."""
        if not isinstance(op, LoadOperation):
            raise TypeError(f"Expected LoadOperation, got {type(op)}")
        if not op.dest:
            raise ValueError("memref.load must have destination")
        dest = op.dest  # type: ignore[assignment]
        result_type = op.result_type or "i32"

        memref = op.memref
        indices = op.indices

        # Try to get concrete indices
        concrete_indices = self._get_concrete_indices(indices, state)

        if concrete_indices is not None:
            # Multi-cell memory access
            cell = state.get_memory_cell(memref, concrete_indices)
            if cell is not None:
                # Cell exists, use its value
                assert cell.expr is not None
                state.set_value(dest, cell.expr, result_type)
                return

            # Cell doesn't exist, create fresh symbolic value
            expr = z3.FreshConst(
                z3.IntSort(),
                f"memref_{memref}_{'_'.join(str(i) for i in concrete_indices)}",
            )
            state.set_memory_cell(memref, concrete_indices, expr, result_type)
            state.set_value(dest, expr, result_type)
        else:
            # Symbolic indices, use single-cell memory model (deprecated)
            mem_value = state.get_memory(memref)
            if mem_value is None:
                expr = z3.FreshConst(z3.IntSort(), f"memref_{memref}")
                state.set_memory(memref, expr, result_type)
                mem_value = MLIRValue(memref, expr, result_type)

            assert mem_value.expr is not None
            state.set_value(dest, mem_value.expr, result_type)

    def _try_concrete_evaluation(  # type: ignore[override]
        self, op: LoadOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of load."""
        memref = op.memref
        indices = op.indices

        concrete_indices = self._get_concrete_indices(indices, state)
        if concrete_indices is not None:
            concrete_val = state.get_memory_cell_concrete(memref, concrete_indices)
            if concrete_val is not None:
                return concrete_val

        # Check single-cell memory model
        mem_concrete = state.get_concrete_value(memref)
        if mem_concrete is not None:
            return mem_concrete

        return None

    def _get_concrete_indices(
        self, indices: list, state: SymbolicState
    ) -> Optional[Tuple[int, ...]]:
        """Convert index expressions to concrete tuple if all are concrete."""
        concrete_indices = []
        for idx in indices:
            idx_concrete = state.get_concrete_value(idx)
            if idx_concrete is None or not isinstance(idx_concrete, int):
                # Try to parse idx as integer constant string
                try:
                    idx_concrete = int(idx)
                except (ValueError, TypeError):
                    return None
            concrete_indices.append(idx_concrete)
        return tuple(concrete_indices)


class MemrefStoreOpHandler(OperationHandler):
    """Handler for memref.store operation."""

    def execute_symbolic(  # type: ignore[override]
        self,
        op: StoreOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute memref.store symbolically."""
        if not isinstance(op, StoreOperation):
            raise TypeError(f"Expected StoreOperation, got {type(op)}")

        memref = op.memref
        value = op.value
        indices = op.indices

        # Get value expression
        value_expr = state.get_expr(value)
        if value_expr is None:
            raise ValueError(f"Cannot get expression for value: {value}")

        # Try to get concrete indices
        concrete_indices = self._get_concrete_indices(indices, state)

        if concrete_indices is not None:
            # Multi-cell memory storage
            state.set_memory_cell(memref, concrete_indices, value_expr, op.result_type or "i32")
            # Also store concrete value if available
            concrete_val = state.get_concrete_value(value)
            if concrete_val is not None:
                state.set_memory_cell_concrete(memref, concrete_indices, concrete_val)
        else:
            # Symbolic indices, use single-cell memory model (deprecated)
            state.set_memory(memref, value_expr, op.result_type or "i32")

            # Store concrete value if available
            concrete_val = state.get_concrete_value(value)
            if concrete_val is not None:
                state.set_concrete_value(memref, concrete_val)

    def _try_concrete_evaluation(  # type: ignore[override]
        self, op: StoreOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Store operations don't produce values."""
        return None

    def _get_concrete_indices(
        self, indices: list, state: SymbolicState
    ) -> Optional[Tuple[int, ...]]:
        """Convert index expressions to concrete tuple if all are concrete."""
        concrete_indices = []
        for idx in indices:
            idx_concrete = state.get_concrete_value(idx)
            if idx_concrete is None or not isinstance(idx_concrete, int):
                # Try to parse idx as integer constant string
                try:
                    idx_concrete = int(idx)
                except (ValueError, TypeError):
                    return None
            concrete_indices.append(idx_concrete)
        return tuple(concrete_indices)


class MemrefAllocaOpHandler(MemrefAllocOpHandler):
    """Handler for memref.alloca operation (same as alloc for now)."""

    pass


class MemrefReinterpretCastOpHandler(OperationHandler):
    """Handler for memref.reinterpret_cast operation."""

    def execute_symbolic(  # type: ignore[override]
        self,
        op: ReinterpretCastOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute memref.reinterpret_cast symbolically."""
        if not isinstance(op, ReinterpretCastOperation):
            raise TypeError(f"Expected ReinterpretCastOperation, got {type(op)}")

        src = op.operand
        dst = op.dest
        if dst is None:
            raise ValueError("memref.reinterpret_cast must have destination")

        # Convert offsets, sizes, strides to concrete ints or symbolic expressions
        offsets = self._convert_parameter_list(op.offsets, state)
        sizes = self._convert_parameter_list(op.sizes, state)
        strides = self._convert_parameter_list(op.strides, state)

        # Call memory model
        state.memory_model.reinterpret_cast(src, dst, offsets, sizes, strides)

        # Also set a symbolic value for the new memref (for compatibility)
        # Create fresh symbolic variable for the new memref view
        expr = z3.FreshConst(z3.IntSort(), f"memref_{dst}")
        state.set_value(dst, expr, op.dst_type or "memref<?xi32>")

    def _try_concrete_evaluation(  # type: ignore[override]
        self, op: ReinterpretCastOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Reinterpret cast doesn't produce concrete values."""
        return None

    def _convert_parameter_list(
        self, params: List[str], state: SymbolicState
    ) -> List[Union[int, z3.ExprRef]]:
        """Convert list of SSA values to concrete ints or symbolic expressions."""
        result = []
        for param in params:
            # Try to get concrete value
            concrete = state.get_concrete_value(param)
            if concrete is not None and isinstance(concrete, int):
                result.append(concrete)
                continue

            # Try to parse as integer constant
            try:
                val = int(param)
                result.append(val)
                continue
            except (ValueError, TypeError):
                pass

            # Get symbolic expression
            expr = state.get_expr(param)
            if expr is None:
                # Create fresh symbolic variable
                expr = z3.FreshConst(z3.IntSort(), f"param_{param}")
                state.set_value(param, expr, "i32")
            result.append(expr)
        return result


# Function to register all memref dialect handlers
def register_handlers(registry) -> None:
    """Register memref dialect handlers with registry."""
    registry.register("memref.alloc", MemrefAllocOpHandler())
    registry.register("memref.alloca", MemrefAllocaOpHandler())
    registry.register("memref.load", MemrefLoadOpHandler())
    registry.register("memref.store", MemrefStoreOpHandler())
    registry.register("memref.reinterpret_cast", MemrefReinterpretCastOpHandler())
