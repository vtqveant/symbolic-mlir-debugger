#!/usr/bin/env python3
"""
Func dialect execution handlers.

Handles operations: call, call_indirect, return, etc.
"""

from typing import Any

import z3

from .base import OperationHandler
from ..models import SymbolicState, MLIRFunction
from ..operations import Operation, CallOperation, ReturnOperation


class FuncCallOpHandler(OperationHandler):
    """Handler for func.call operation."""

    def execute_symbolic(
        self,
        op: CallOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute func.call symbolically."""
        if not isinstance(op, CallOperation):
            raise TypeError(f"Expected CallOperation, got {type(op)}")

        # Create symbolic result for function call
        expr = z3.Int(f"call_{op.callee}")
        if op.dest:
            state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: CallOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Function calls don't have simple concrete values."""
        return None


class FuncCallIndirectOpHandler(OperationHandler):
    """Handler for func.call_indirect operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute func.call_indirect symbolically."""
        # Create symbolic result
        expr = z3.Int("indirect_call")
        if op.dest:
            state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Indirect calls don't have simple concrete values."""
        return None


class FuncReturnOpHandler(OperationHandler):
    """Handler for func.return operation."""

    def execute_symbolic(
        self,
        op: ReturnOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute func.return symbolically."""
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
        self, op: ReturnOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try to evaluate return operation concretely by extracting return value."""
        return_op = op
        if not isinstance(return_op, ReturnOperation):
            return None

        # Extract the concrete value of the return operand if available
        if return_op.value is not None:
            concrete_val = state.get_concrete_value(return_op.value)
            if concrete_val is not None:
                return concrete_val

        return None


# Function to register all func dialect handlers
def register_handlers(registry) -> None:
    """Register func dialect handlers with registry."""

    registry.register("func.call", FuncCallOpHandler())
    registry.register("func.call_indirect", FuncCallIndirectOpHandler())
    registry.register("func.return", FuncReturnOpHandler())
    # Also register generic return without dialect prefix
    registry.register(".return", FuncReturnOpHandler())
    registry.register("shape.custom", FuncReturnOpHandler())
