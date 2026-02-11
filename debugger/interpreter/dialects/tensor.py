#!/usr/bin/env python3
"""
Tensor dialect execution handlers.

Handles operations: extract, insert, splat, etc.
"""

import z3
from typing import Any, Optional, Tuple

from .base import OperationHandler
from ..operations import LoadOperation, StoreOperation, Operation
from ..models import SymbolicState, MLIRFunction


class TensorExtractHandler(OperationHandler):
    """Handler for tensor.extract operation."""

    def execute_symbolic(
        self,
        op: LoadOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute tensor.extract symbolically."""
        if not isinstance(op, LoadOperation):
            raise TypeError(f"Expected LoadOperation, got {type(op)}")

        tensor = op.memref
        indices = op.indices

        # Try to get concrete indices
        concrete_indices = self._get_concrete_indices(indices, state)

        if concrete_indices is not None:
            # Multi-cell access with concrete indices
            tensor_value = state.get_memory_cell(tensor, concrete_indices)
            if tensor_value is None:
                # Uninitialized cell: create fresh symbolic value
                expr = z3.FreshConst(z3.IntSort(), f"tensor_{tensor}{concrete_indices}")
                state.set_memory_cell(
                    tensor, concrete_indices, expr, op.result_type or "i32"
                )
                tensor_value = state.get_memory_cell(tensor, concrete_indices)
            assert tensor_value is not None
            assert tensor_value.expr is not None
            state.set_value(op.dest, tensor_value.expr, op.result_type or "i32")
            # Try to get concrete value from tensor cell
            concrete_val = state.get_memory_cell_concrete(tensor, concrete_indices)
            if concrete_val is not None:
                state.set_concrete_value(op.dest, concrete_val)
        else:
            # Symbolic indices or no indices: fall back to single-cell model
            tensor_value = state.get_memory(tensor)
            if tensor_value is None:
                expr = z3.FreshConst(z3.IntSort(), f"tensor_{tensor}")
                state.set_memory(tensor, expr, op.result_type or "i32")
                tensor_value = state.get_memory(tensor)
            assert tensor_value is not None
            assert tensor_value.expr is not None
            state.set_value(op.dest, tensor_value.expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: LoadOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of tensor.extract."""
        tensor = op.memref
        indices = op.indices

        concrete_indices = self._get_concrete_indices(indices, state)
        if concrete_indices is not None:
            concrete_val = state.get_memory_cell_concrete(tensor, concrete_indices)
            if concrete_val is not None:
                return concrete_val

        # Check single-cell memory model
        tensor_concrete = state.get_concrete_value(tensor)
        if tensor_concrete is not None:
            return tensor_concrete

        return None

    def _get_concrete_indices(
        self, indices: list, state: SymbolicState
    ) -> Optional[Tuple[int, ...]]:
        """Convert index expressions to concrete tuple if all are concrete."""
        concrete_indices = []
        for idx in indices:
            idx_concrete = state.get_concrete_value(idx)
            if idx_concrete is None or not isinstance(idx_concrete, int):
                return None
            concrete_indices.append(idx_concrete)
        return tuple(concrete_indices)


class TensorInsertHandler(OperationHandler):
    """Handler for tensor.insert operation."""

    def execute_symbolic(
        self,
        op: StoreOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute tensor.insert symbolically."""
        if not isinstance(op, StoreOperation):
            raise TypeError(f"Expected StoreOperation, got {type(op)}")

        tensor = op.memref
        value = op.value
        indices = op.indices

        # Get value expression
        value_expr = state.get_expr(value)
        if value_expr is None:
            raise ValueError(f"Cannot get expression for value: {value}")

        # Try to get concrete indices
        concrete_indices = self._get_concrete_indices(indices, state)

        if concrete_indices is not None:
            # Multi-cell insert with concrete indices
            state.set_memory_cell(
                tensor, concrete_indices, value_expr, op.result_type or "i32"
            )
            # Store concrete value if available
            concrete_val = state.get_concrete_value(value)
            if concrete_val is not None:
                state.set_memory_cell_concrete(tensor, concrete_indices, concrete_val)
        else:
            # Symbolic indices or no indices: fall back to single-cell model
            state.set_memory(tensor, value_expr, op.result_type or "i32")
            # Store concrete value if available
            concrete_val = state.get_concrete_value(value)
            if concrete_val is not None:
                state.set_concrete_value(tensor, concrete_val)

    def _try_concrete_evaluation(
        self, op: StoreOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Insert operations don't produce values."""
        return None

    def _get_concrete_indices(
        self, indices: list, state: SymbolicState
    ) -> Optional[Tuple[int, ...]]:
        """Convert index expressions to concrete tuple if all are concrete."""
        concrete_indices = []
        for idx in indices:
            idx_concrete = state.get_concrete_value(idx)
            if idx_concrete is None or not isinstance(idx_concrete, int):
                return None
            concrete_indices.append(idx_concrete)
        return tuple(concrete_indices)


class TensorSplatHandler(OperationHandler):
    """Handler for tensor.splat operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute tensor.splat symbolically."""
        if not op.dest:
            raise ValueError("tensor.splat must have destination")

        # Create a fresh symbolic tensor
        expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
        state.set_memory(op.dest, expr, op.result_type or "tensor<?xi32>")
        state.set_value(op.dest, expr, op.result_type or "tensor<?xi32>")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Splat operations don't have simple concrete values."""
        return None


# Function to register all tensor dialect handlers
def register_handlers(registry) -> None:
    """Register tensor dialect handlers with registry."""
    registry.register("tensor.extract", TensorExtractHandler())
    registry.register("tensor.insert", TensorInsertHandler())
    registry.register("tensor.splat", TensorSplatHandler())
