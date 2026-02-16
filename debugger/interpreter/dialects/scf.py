#!/usr/bin/env python3
"""
SCF dialect execution handlers.

Handles operations: for, if, yield, condition, etc.
"""

import logging
import z3
from typing import Any

logger = logging.getLogger(__name__)

from .base import OperationHandler
from ..operations import Operation, LoopOperation
from ..models import SymbolicState, MLIRFunction


class ScfForOpHandler(OperationHandler):
    """Handler for scf.for operation."""

    def execute_symbolic(
        self,
        op: Operation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute scf.for symbolically."""
        if not isinstance(op, LoopOperation):
            raise TypeError(f"Expected LoopOperation, got {type(op)}")
        if interpreter is None:
            raise ValueError("ScfForHandler requires interpreter instance")

        dest = op.dest
        if dest is None:
            # Loop without result (no iteration arguments)
            dest = ""  # placeholder, will not set value
        iv = op.index  # induction variable name (with %)
        lb_expr = interpreter._get_operand_expr(op.lb, state)
        ub_expr = interpreter._get_operand_expr(op.ub, state)
        step_expr = interpreter._get_operand_expr(op.step, state) if op.step else None
        iter_arg = op.iter_arg  # with %
        init_expr = interpreter._get_operand_expr(op.init, state) if op.init else None

        # Default step is 1 if not provided (should be provided for scf.for)
        if step_expr is None:
            step_expr = z3.IntVal(1)

        # Try to evaluate bounds concretely
        lb_concrete = interpreter._try_get_concrete_value(lb_expr, state)
        ub_concrete = interpreter._try_get_concrete_value(ub_expr, state)
        step_concrete = interpreter._try_get_concrete_value(step_expr, state)
        logger.debug(
            "ScfForHandler: lb_concrete=%s, ub_concrete=%s, step_concrete=%s",
            lb_concrete,
            ub_concrete,
            step_concrete,
        )

        if lb_concrete is not None and ub_concrete is not None and step_concrete is not None:
            logger.debug("ScfForHandler: Concrete bounds, unrolling loop")
            # Concrete bounds, unroll loop
            current_acc = init_expr
            i = 0
            max_iterations = 100  # safety bound
            while True:
                iv_val = lb_concrete + i * step_concrete
                logger.debug(
                    "ScfForHandler: iteration i=%s, iv_val=%s, current_acc=%s",
                    i,
                    iv_val,
                    current_acc,
                )
                if step_concrete > 0 and iv_val >= ub_concrete:
                    break
                if step_concrete < 0 and iv_val <= ub_concrete:
                    break
                if i >= max_iterations:
                    print(f"Warning: Loop unrolling limited to {max_iterations} iterations")
                    break

                # Create temporary state for this iteration (fork of current state)
                iter_state = state.fork()
                # Set induction variable value (concrete)
                iv_name = iv[1:] if iv.startswith("%") else iv
                iter_state.set_value(iv_name, z3.IntVal(iv_val), "i32")
                iter_state.set_concrete_value(iv_name, iv_val)
                logger.debug(
                    "ScfForHandler: expr for iv_name %s = %s",
                    iv_name,
                    iter_state.get_expr(iv_name),
                )
                # Set iteration argument value
                if iter_arg and init_expr is not None:
                    iter_arg_name = iter_arg[1:] if iter_arg.startswith("%") else iter_arg
                    if current_acc is not None:
                        iter_state.set_value(iter_arg_name, current_acc, op.result_type or "i32")
                    # Could also set concrete value if current_acc is concrete

                # Execute body operations
                yield_value = None
                for body_op in op.body:
                    if body_op.dialect == "scf" and body_op.name == "yield":
                        # This is the yield operation - get its value
                        yield_expr = interpreter._get_operand_expr(body_op.value, iter_state)
                        yield_value = yield_expr
                        logger.debug("ScfForHandler: yield_expr=%s", yield_expr)
                        # Don't execute further operations after yield
                        break
                    else:
                        # Execute the operation in the temporary state
                        interpreter._execute_operation(body_op, iter_state, func)

                if yield_value is None:
                    # No yield found - error
                    print("Error: Loop body missing scf.yield")
                    break

                current_acc = yield_value
                i += 1

            if dest and current_acc is not None:
                state.set_value(dest, current_acc, op.result_type or "i32")
        else:
            # Symbolic bounds - assume loop runs 0 times
            if dest and init_expr is not None:
                state.set_value(dest, init_expr, op.result_type or "i32")
            print("Warning: Symbolic loop bounds, assuming zero iterations")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """scf.for doesn't produce a concrete value."""
        return None


class ScfIfOpHandler(OperationHandler):
    """Handler for scf.if operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute scf.if symbolically."""
        # Similar to cf.cond_br
        print("Warning: scf.if not fully implemented")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """scf.if doesn't produce a concrete value."""
        return None


class ScfYieldOpHandler(OperationHandler):
    """Handler for scf.yield operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute scf.yield symbolically."""
        # Yield value from loop body - handled during loop unrolling
        pass

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """scf.yield doesn't produce a concrete value."""
        return None


class ScfConditionOpHandler(OperationHandler):
    """Handler for scf.condition operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute scf.condition symbolically."""
        print("Warning: scf.condition not implemented")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """scf.condition doesn't produce a concrete value."""
        return None


# Function to register all scf dialect handlers
def register_handlers(registry) -> None:
    """Register scf dialect handlers with registry."""
    registry.register("scf.for", ScfForOpHandler())
    registry.register("scf.if", ScfIfOpHandler())
    registry.register("scf.yield", ScfYieldOpHandler())
    registry.register("scf.condition", ScfConditionOpHandler())
