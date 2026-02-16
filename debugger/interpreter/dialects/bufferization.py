#!/usr/bin/env python3
"""
Bufferization dialect execution handlers.

Handles operations: alloc_tensor, to_buffer, to_tensor, clone, etc.
"""

from typing import Any

import z3

from .base import OperationHandler
from ..models import SymbolicState, MLIRFunction
from ..operations import Operation


class BufferizationAllocTensorOpHandler(OperationHandler):
    """Handler for bufferization.alloc_tensor operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute bufferization.alloc_tensor symbolically."""
        if not op.dest:
            raise ValueError("bufferization.alloc_tensor must have destination")

        # shape is a list of SSA values
        # Create a fresh symbolic value for the tensor
        expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "tensor<?xi32>")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """alloc_tensor doesn't produce a concrete value."""
        return None


class BufferizationToBufferOpHandler(OperationHandler):
    """Handler for bufferization.to_buffer operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute bufferization.to_buffer symbolically."""
        if not op.dest:
            raise ValueError("bufferization.to_buffer must have destination")

        # Get tensor expression
        tensor_expr = None
        if hasattr(op, "tensor"):
            tensor_expr = state.get_expr(op.tensor)

        # Convert tensor to buffer - treat as same value with different type
        if tensor_expr is not None:
            state.set_value(op.dest, tensor_expr, op.result_type or "memref<?xi32>")
        else:
            # Create fresh symbolic value
            expr = z3.FreshConst(z3.IntSort(), f"buffer_{op.dest}")
            state.set_value(op.dest, expr, op.result_type or "memref<?xi32>")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """to_buffer doesn't produce a concrete value."""
        return None


class BufferizationToTensorOpHandler(OperationHandler):
    """Handler for bufferization.to_tensor operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute bufferization.to_tensor symbolically."""
        if not op.dest:
            raise ValueError("bufferization.to_tensor must have destination")

        # Get buffer expression
        buffer_expr = None
        if hasattr(op, "buffer"):
            buffer_expr = state.get_expr(op.buffer)

        # Convert buffer to tensor - treat as same value with different type
        if buffer_expr is not None:
            state.set_value(op.dest, buffer_expr, op.result_type or "tensor<?xi32>")
        else:
            # Create fresh symbolic value
            expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
            state.set_value(op.dest, expr, op.result_type or "tensor<?xi32>")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """to_tensor doesn't produce a concrete value."""
        return None


class BufferizationCloneOpHandler(OperationHandler):
    """Handler for bufferization.clone operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute bufferization.clone symbolically."""
        if not op.dest:
            raise ValueError("bufferization.clone must have destination")

        # Get source expression
        src_expr = None
        if hasattr(op, "src"):
            src_expr = state.get_expr(op.src)

        # Clone creates a copy - treat as same value
        if src_expr is not None:
            state.set_value(op.dest, src_expr, op.result_type or op.result_type or "memref<?xi32>")
        else:
            # Create fresh symbolic value
            expr = z3.FreshConst(z3.IntSort(), f"clone_{op.dest}")
            state.set_value(op.dest, expr, op.result_type or "memref<?xi32>")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """clone doesn't produce a concrete value."""
        return None


# Function to register all bufferization dialect handlers
def register_handlers(registry) -> None:
    """Register bufferization dialect handlers with registry."""
    registry.register("bufferization.alloc_tensor", BufferizationAllocTensorOpHandler())
    registry.register("bufferization.to_buffer", BufferizationToBufferOpHandler())
    registry.register("bufferization.to_tensor", BufferizationToTensorOpHandler())
    registry.register("bufferization.clone", BufferizationCloneOpHandler())
