#!/usr/bin/env python3
"""
Vector dialect execution handlers.

Handles operations: broadcast, bitcast, fma, etc.
"""

import z3
from typing import Any

from .base import OperationHandler
from ..operations import Operation
from ..models import SymbolicState, MLIRFunction


class VectorBroadcastHandler(OperationHandler):
    """Handler for vector.broadcast operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute vector.broadcast symbolically."""
        if not op.dest:
            raise ValueError("vector.broadcast must have destination")

        # operand may be in "value" (generic parser) or "source" (specialized)
        # Get source expression if available
        source_expr = None
        if hasattr(op, "value"):
            source_expr = state.get_expr(op.value)
        elif hasattr(op, "source"):
            source_expr = state.get_expr(op.source)

        # Create a fresh symbolic value for the broadcast result
        expr = z3.FreshConst(z3.IntSort(), f"vec_broadcast_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "vector<?xi32>")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Broadcast operations don't have simple concrete values."""
        return None


class VectorBitcastHandler(OperationHandler):
    """Handler for vector.bitcast operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute vector.bitcast symbolically."""
        if not op.dest:
            raise ValueError("vector.bitcast must have destination")

        # operand may be in "value" (generic parser) or "source" (specialized)
        # Get source expression if available
        source_expr = None
        if hasattr(op, "value"):
            source_expr = state.get_expr(op.value)
        elif hasattr(op, "source"):
            source_expr = state.get_expr(op.source)

        # Create a fresh symbolic value for the bitcast result
        expr = z3.FreshConst(z3.IntSort(), f"vec_bitcast_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "vector<?xi32>")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Bitcast operations don't have simple concrete values."""
        return None


class VectorFmaHandler(OperationHandler):
    """Handler for vector.fma operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute vector.fma symbolically."""
        if not op.dest:
            raise ValueError("vector.fma must have destination")

        # Get operand expressions if available
        lhs_expr = rhs_expr = acc_expr = None
        if hasattr(op, "lhs") and hasattr(op, "rhs") and hasattr(op, "acc"):
            lhs_expr = state.get_expr(op.lhs)
            rhs_expr = state.get_expr(op.rhs)
            acc_expr = state.get_expr(op.acc)
        elif hasattr(op, "operands") and len(op.operands) >= 3:
            lhs_expr = state.get_expr(op.operands[0])
            rhs_expr = state.get_expr(op.operands[1])
            acc_expr = state.get_expr(op.operands[2])

        # Create a fresh symbolic value for FMA result
        expr = z3.FreshConst(z3.IntSort(), f"vec_fma_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "vector<?xi32>")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """FMA operations don't have simple concrete values."""
        return None


# Function to register all vector dialect handlers
def register_handlers(registry) -> None:
    """Register vector dialect handlers with registry."""
    registry.register("vector.broadcast", VectorBroadcastHandler())
    registry.register("vector.bitcast", VectorBitcastHandler())
    registry.register("vector.fma", VectorFmaHandler())
