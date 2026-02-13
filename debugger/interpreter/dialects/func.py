#!/usr/bin/env python3
"""
Func dialect execution handlers.

Handles operations: call, call_indirect, return, etc.
"""

import z3
from typing import Any

from .base import OperationHandler
from ..operations import Operation, CallOperation, ReturnOperation
from ..models import SymbolicState, MLIRFunction


class FuncCallHandler(OperationHandler):
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


class FuncCallIndirectHandler(OperationHandler):
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


class FuncReturnHandler(OperationHandler):
    """Handler for return operation."""

    def execute_symbolic(
        self,
        op: ReturnOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute return symbolically."""
        if not isinstance(op, ReturnOperation):
            raise TypeError(f"Expected ReturnOperation, got {type(op)}")
        print(
            f"DEBUG FuncReturnHandler: op.value={op.value}, op.result_type={op.result_type}"
        )
        # Store return value if present
        if op.value is not None:
            ret_expr = state.get_expr(op.value)
            print(f"DEBUG FuncReturnHandler: ret_expr={ret_expr}")
            if ret_expr is not None:
                state.set_value("return", ret_expr, op.result_type or "i32")
                print("DEBUG FuncReturnHandler: set return value")
                # Also propagate concrete value if available
                concrete_val = state.get_concrete_value(op.value)
                if concrete_val is not None:
                    state.set_concrete_value("return", concrete_val)
                    print(
                        f"DEBUG FuncReturnHandler: set concrete return value {concrete_val}"
                    )
            else:
                # Create a fresh symbolic variable for the missing value
                import z3

                fresh_expr = z3.FreshConst(z3.IntSort(), f"ret_{op.value}")
                state.set_value("return", fresh_expr, op.result_type or "i32")
                print("DEBUG FuncReturnHandler: created fresh return expr")
        else:
            # No return value (void return)
            pass
        state.pc = None  # Terminate state
        print("DEBUG FuncReturnHandler: set pc=None")

    def _try_concrete_evaluation(
        self, op: ReturnOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Return operations don't produce values."""
        return None


# Function to register all func dialect handlers
def register_handlers(registry) -> None:
    """Register func dialect handlers with registry."""
    import sys

    print(f"DEBUG func.register_handlers: registering func handlers", file=sys.stderr)
    registry.register("func.call", FuncCallHandler())
    registry.register("func.call_indirect", FuncCallIndirectHandler())
    registry.register("func.return", FuncReturnHandler())
    # Also register generic return without dialect prefix
    registry.register(".return", FuncReturnHandler())
    # Handle misparsed return operations (pymlir bug workaround)
    # TODO: Fix pymlir lexer/parser to correctly parse "return" after "!shape.size"
    registry.register("ape.sizereturn", FuncReturnHandler())
    registry.register("e.sizereturn", FuncReturnHandler())
    registry.register("pe.sizereturn", FuncReturnHandler())
    registry.register("hape.sizereturn", FuncReturnHandler())
    registry.register("shape.sizereturn", FuncReturnHandler())
    registry.register("sizereturn", FuncReturnHandler())
    registry.register(".sizereturn", FuncReturnHandler())
    print(f"DEBUG func.register_handlers: done", file=sys.stderr)
