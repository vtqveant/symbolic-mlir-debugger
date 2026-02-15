#!/usr/bin/env python3
"""
Builtin dialect execution handlers.

Handles operations: module, func, etc. (mostly structural operations).
"""

import z3
from typing import Any

from .base import OperationHandler
from ..operations import Operation, CallOperation, ReturnOperation
from ..models import SymbolicState, MLIRFunction


class BuiltinModuleOpHandler(OperationHandler):
    """Handler for builtin.module operation (structural)."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """builtin.module is structural, not executable."""
        pass

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """builtin.module doesn't produce a concrete value."""
        return None


class BuiltinFuncOpHandler(OperationHandler):
    """Handler for builtin.func operation (structural)."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """builtin.func is structural, not executable."""
        pass

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """builtin.func doesn't produce a concrete value."""
        return None


class BuiltinUnrealizedConversionCastOpHandler(OperationHandler):
    """Handler for builtin.unrealized_conversion_cast operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute builtin.unrealized_conversion_cast symbolically."""
        if not op.dest:
            raise ValueError("builtin.unrealized_conversion_cast must have destination")

        # Get operand expression if available
        operand_expr = None
        if hasattr(op, "operand"):
            operand_expr = state.get_expr(op.operand)
        elif hasattr(op, "value"):
            operand_expr = state.get_expr(op.value)

        # Treat as same value with different type
        if operand_expr is not None:
            state.set_value(op.dest, operand_expr, op.result_type or "i32")
        else:
            # Create fresh symbolic value
            expr = z3.FreshConst(z3.IntSort(), f"cast_{op.dest}")
            state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """unrealized_conversion_cast doesn't produce a concrete value."""
        return None


# Function to register all builtin dialect handlers
def register_handlers(registry) -> None:
    """Register builtin dialect handlers with registry."""
    registry.register("builtin.module", BuiltinModuleOpHandler())
    registry.register("builtin.func", BuiltinFuncOpHandler())
    registry.register(
        "builtin.unrealized_conversion_cast", BuiltinUnrealizedConversionCastOpHandler()
    )
