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


class BuiltinModuleHandler(OperationHandler):
    """Handler for builtin.module operation (structural)."""

    def execute_symbolic(
        self, op: Any, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """builtin.module is structural, not executable."""
        pass

    def _try_concrete_evaluation(
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """builtin.module doesn't produce a concrete value."""
        return None


class BuiltinFuncHandler(OperationHandler):
    """Handler for builtin.func operation (structural)."""

    def execute_symbolic(
        self, op: Any, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """builtin.func is structural, not executable."""
        pass

    def _try_concrete_evaluation(
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """builtin.func doesn't produce a concrete value."""
        return None


class BuiltinUnrealizedConversionCastHandler(OperationHandler):
    """Handler for builtin.unrealized_conversion_cast operation."""

    def execute_symbolic(
        self, op: Any, state: SymbolicState, func: MLIRFunction, interpreter=None
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
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """unrealized_conversion_cast doesn't produce a concrete value."""
        return None


class BuiltinReturnHandler(OperationHandler):
    """Handler for builtin.return operation."""

    def execute_symbolic(
        self, op: Any, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute builtin.return symbolically."""
        return_op = op
        if not isinstance(return_op, ReturnOperation):
            raise TypeError(f"Expected ReturnOperation, got {type(op)}")
        # Store return value if present
        if return_op.value is not None:
            ret_expr = state.get_expr(return_op.value)
            if ret_expr is not None:
                result_type = "unknown"
                if return_op.result_type:
                    result_type = return_op.result_type
                state.set_value("return", ret_expr, result_type)
                # Also propagate concrete value if available
                concrete_val = state.get_concrete_value(return_op.value)
                if concrete_val is not None:
                    state.set_concrete_value("return", concrete_val)
            else:
                # Create a fresh symbolic variable for the missing value
                fresh_expr = z3.FreshConst(z3.IntSort(), f"ret_{return_op.value}")
                result_type = "unknown"
                if return_op.result_type:
                    result_type = return_op.result_type
                state.set_value("return", fresh_expr, result_type)
        else:
            # No return value (void return)
            pass
        state.pc = None  # Terminate state

    def _try_concrete_evaluation(
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Return operations don't produce values."""
        return None


# Function to register all builtin dialect handlers
def register_handlers(registry) -> None:
    """Register builtin dialect handlers with registry."""
    registry.register("builtin.module", BuiltinModuleHandler())
    registry.register("builtin.func", BuiltinFuncHandler())
    registry.register(
        "builtin.unrealized_conversion_cast", BuiltinUnrealizedConversionCastHandler()
    )
    registry.register("builtin.return", BuiltinReturnHandler())
