#!/usr/bin/env python3
"""
Affine dialect execution handlers.

Handles operations: for, if, load, store, etc.
"""

import z3
from typing import Any

from .base import OperationHandler
from ..operations import Operation, LoopOperation
from ..models import SymbolicState, MLIRFunction


class AffineForHandler(OperationHandler):
    """Handler for affine.for operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute affine.for symbolically."""
        if not isinstance(op, LoopOperation):
            raise TypeError(f"Expected LoopOperation, got {type(op)}")
        if interpreter is None:
            raise ValueError("AffineForHandler requires interpreter instance")

        dest = op.dest
        iv = op.index  # induction variable name (with %)
        lb_expr = interpreter._get_operand_expr(op.lb, state)
        ub_expr = interpreter._get_operand_expr(op.ub, state)
        step_expr = interpreter._get_operand_expr(op.step, state) if op.step else None

        # Default step is 1 if not provided
        if step_expr is None:
            step_expr = z3.IntVal(1)

        # Try to evaluate bounds concretely
        lb_concrete = interpreter._try_get_concrete_value(lb_expr, state)
        ub_concrete = interpreter._try_get_concrete_value(ub_expr, state)
        step_concrete = interpreter._try_get_concrete_value(step_expr, state)

        if (
            lb_concrete is not None
            and ub_concrete is not None
            and step_concrete is not None
        ):
            # Concrete bounds, unroll loop
            i = 0
            max_iterations = 100  # safety bound
            while True:
                iv_val = lb_concrete + i * step_concrete
                if step_concrete > 0 and iv_val >= ub_concrete:
                    break
                if step_concrete < 0 and iv_val <= ub_concrete:
                    break
                if i >= max_iterations:
                    print(
                        f"Warning: Loop unrolling limited to {max_iterations} iterations"
                    )
                    break

                # Create temporary state for this iteration (fork of current state)
                iter_state = state.fork()
                # Set induction variable value (concrete)
                if iv:
                    iv_name = iv[1:] if iv.startswith("%") else iv
                    iter_state.set_value(iv_name, z3.IntVal(iv_val), "index")
                    iter_state.set_concrete_value(iv_name, iv_val)

                # Execute body operations
                for body_op in op.body:
                    interpreter._execute_operation(body_op, iter_state, func)

                # Merge state changes? For affine.for without accumulator, just continue
                # For now, discard iter_state after execution
                i += 1

            # affine.for doesn't produce a value (unless with iter_args)
            # If dest exists, it's the result of the loop
            if dest:
                # TODO: Handle affine.for with iter_args and results
                # For now, create symbolic result
                expr = z3.Int(f"affine_for_{dest}")
                state.set_value(dest, expr, op.result_type or "index")
        else:
            # Symbolic bounds - assume loop runs 0 times
            print("Warning: Symbolic affine loop bounds, assuming zero iterations")
            if dest:
                # Create symbolic result
                expr = z3.Int(f"affine_for_{dest}")
                state.set_value(dest, expr, op.result_type or "index")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """affine.for doesn't produce a concrete value."""
        return None


class AffineIfHandler(OperationHandler):
    """Handler for affine.if operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute affine.if symbolically."""
        # Similar to cf.cond_br but with affine condition
        # For now, create symbolic result if dest exists
        if op.dest:
            expr = z3.Int(f"affine_if_{op.dest}")
            state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """affine.if doesn't produce a concrete value."""
        return None


class AffineLoadHandler(OperationHandler):
    """Handler for affine.load operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute affine.load symbolically."""
        # Load from memref with affine index
        # For now, treat as regular load (ignore affine index)
        if op.dest:
            expr = z3.Int(f"load_{op.dest}")
            state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """affine.load doesn't have simple concrete value."""
        return None


class AffineStoreHandler(OperationHandler):
    """Handler for affine.store operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute affine.store symbolically."""
        # Store to memref with affine index
        # For now, treat as regular store (ignore affine index)
        pass

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """affine.store doesn't produce a concrete value."""
        return None


# Function to register all affine dialect handlers
def register_handlers(registry) -> None:
    """Register affine dialect handlers with registry."""
    registry.register("affine.for", AffineForHandler())
    registry.register("affine.if", AffineIfHandler())
    registry.register("affine.load", AffineLoadHandler())
    registry.register("affine.store", AffineStoreHandler())
