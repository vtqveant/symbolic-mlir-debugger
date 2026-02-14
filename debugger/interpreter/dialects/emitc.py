#!/usr/bin/env python3
"""
EmitC dialect execution handlers.

Handles operations: constant, add, bitwise operations, cmp, conditional, cast, etc.
"""

import logging
import z3
from typing import Any

logger = logging.getLogger(__name__)

from .base import (
    BinaryOperationHandler,
    ConstantOperationHandler,
    CompareOperationHandler,
    OperationHandler,
)
from ..operations import Operation, ConstantOperation, CompareOperation
from ..models import SymbolicState, MLIRFunction


# EmitC constant operation (similar to arith.constant)
class EmitCConstantHandler(ConstantOperationHandler):
    """Handler for emitc.constant operation."""

    def execute_symbolic(
        self,
        op: ConstantOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute emitc.constant symbolically."""
        if not isinstance(op, ConstantOperation):
            raise TypeError(f"Expected ConstantOperation, got {type(op)}")

        # Try to get value from attributes if op.value is None
        value = op.value
        if value is None and op.attributes and "value" in op.attributes:
            attr_val = op.attributes["value"]
            # Attribute might be string like "42"
            if isinstance(attr_val, str):
                try:
                    value = int(attr_val)
                except ValueError:
                    pass
            elif isinstance(attr_val, int):
                value = attr_val

        # Create Z3 constant from value
        if isinstance(value, int):
            expr = z3.IntVal(value)
            logger.debug("EmitCConstantHandler: value=%s, expr=%s", value, expr)
        elif isinstance(value, float):
            expr = z3.RealVal(value)
            logger.debug("EmitCConstantHandler: value=%s, expr=%s", value, expr)
        else:
            # Fallback to symbolic variable
            expr = z3.FreshConst(z3.IntSort(), f"emitc_const_{op.dest}")
            logger.debug("EmitCConstantHandler: value=%s, fallback expr=%s", value, expr)

        state.set_value(op.dest, expr, op.result_type or "i32")
        logger.debug("after set_value: state.get_value(%s) = %s", op.dest, state.get_value(op.dest))

        # Also store concrete value if we have it
        if isinstance(value, (int, float)):
            state.set_concrete_value(op.dest, value)
            logger.debug("after set_concrete_value: state.get_concrete_value(%s) = %s", op.dest, state.get_concrete_value(op.dest))

    def _try_concrete_evaluation(
        self, op: ConstantOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of emitc.constant."""
        # Try to get value from attributes if op.value is None
        value = op.value
        if value is None and op.attributes and "value" in op.attributes:
            attr_val = op.attributes["value"]
            if isinstance(attr_val, str):
                try:
                    return int(attr_val)
                except ValueError:
                    pass
            elif isinstance(attr_val, int):
                return attr_val
        return value  # may be None or int


# EmitC arithmetic operations
class EmitCAddHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l + r)


class EmitCSubHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l - r)


class EmitCMulHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l * r)


class EmitCDivHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l / r)


# EmitC bitwise operations (create fresh symbolic values since Z3 Int doesn't have bitwise ops)
class EmitCBitwiseAndHandler(OperationHandler):
    """Handler for emitc.bitwise_and operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute emitc.bitwise_and symbolically."""
        if not op.dest:
            raise ValueError("emitc.bitwise_and must have destination")

        # Create fresh symbolic value (Z3 Int doesn't have bitwise AND)
        expr = z3.FreshConst(z3.IntSort(), f"bitwise_and_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of bitwise_and."""
        # Could implement concrete bitwise AND if operands are concrete
        return None


class EmitCBitwiseOrHandler(EmitCBitwiseAndHandler):
    """Handler for emitc.bitwise_or operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        if not op.dest:
            raise ValueError("emitc.bitwise_or must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"bitwise_or_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "i32")


class EmitCBitwiseXorHandler(EmitCBitwiseAndHandler):
    """Handler for emitc.bitwise_xor operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        if not op.dest:
            raise ValueError("emitc.bitwise_xor must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"bitwise_xor_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "i32")


class EmitCBitwiseLeftShiftHandler(EmitCBitwiseAndHandler):
    """Handler for emitc.bitwise_left_shift operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        if not op.dest:
            raise ValueError("emitc.bitwise_left_shift must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"shl_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "i32")


class EmitCBitwiseRightShiftHandler(EmitCBitwiseAndHandler):
    """Handler for emitc.bitwise_right_shift operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        if not op.dest:
            raise ValueError("emitc.bitwise_right_shift must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"shr_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "i32")


class EmitCAssignHandler(OperationHandler):
    """Handler for emitc.assign operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute emitc.assign symbolically."""
        if not op.dest:
            raise ValueError("emitc.assign must have destination")

        # Get RHS expression
        rhs_expr = None
        if hasattr(op, "rhs"):
            rhs_expr = state.get_expr(op.rhs)

        if rhs_expr is not None:
            state.set_value(op.dest, rhs_expr, op.result_type or "i32")
        else:
            # Create fresh symbolic value
            expr = z3.FreshConst(z3.IntSort(), f"assign_{op.dest}")
            state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """assign doesn't produce a concrete value."""
        return None


class EmitCBitwiseNotHandler(OperationHandler):
    """Handler for emitc.bitwise_not operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute emitc.bitwise_not symbolically."""
        if not op.dest:
            raise ValueError("emitc.bitwise_not must have destination")

        expr = z3.FreshConst(z3.IntSort(), f"bitwise_not_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """bitwise_not doesn't have simple concrete value."""
        return None


# EmitC comparison operation
EMITC_CMP_PREDICATE_MAP = {
    "eq": lambda l, r: l == r,
    "ne": lambda l, r: l != r,
    "slt": lambda l, r: l < r,
    "sle": lambda l, r: l <= r,
    "sgt": lambda l, r: l > r,
    "sge": lambda l, r: l >= r,
    "ult": lambda l, r: l < r,  # unsigned - same for concrete ints
    "ule": lambda l, r: l <= r,
    "ugt": lambda l, r: l > r,
    "uge": lambda l, r: l >= r,
    # Integer codes: 0=eq, 1=ne, 2=lt, 3=le, 4=gt, 5=ge, 6=three_way
    "0": lambda l, r: l == r,
    "1": lambda l, r: l != r,
    "2": lambda l, r: l < r,
    "3": lambda l, r: l <= r,
    "4": lambda l, r: l > r,
    "5": lambda l, r: l >= r,
}


class EmitCCmpHandler(CompareOperationHandler):
    def __init__(self):
        super().__init__(predicate_map=EMITC_CMP_PREDICATE_MAP)

    def execute_symbolic(
        self,
        op: CompareOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute emitc.cmp symbolically with integer predicate support."""
        # Convert integer predicate to string if needed
        if not op.pred and op.attributes and "predicate" in op.attributes:
            predicate_val = op.attributes["predicate"]
            if isinstance(predicate_val, int):
                op.pred = str(predicate_val)
            elif isinstance(predicate_val, str):
                op.pred = predicate_val

        # Call parent implementation
        super().execute_symbolic(op, state, func, interpreter)


class EmitCConditionalHandler(OperationHandler):
    """Handler for emitc.conditional operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute emitc.conditional symbolically."""
        if not op.dest:
            raise ValueError("emitc.conditional must have destination")

        # Create a conditional expression
        expr = z3.FreshConst(z3.IntSort(), f"conditional_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """conditional doesn't have simple concrete value."""
        return None


class EmitCCastHandler(OperationHandler):
    """Handler for emitc.cast operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute emitc.cast symbolically."""
        if not op.dest:
            raise ValueError("emitc.cast must have destination")

        # Get operand expression
        operand_expr = None
        if hasattr(op, "operand"):
            operand_expr = state.get_expr(op.operand)
        elif hasattr(op, "value"):
            operand_expr = state.get_expr(op.value)

        # Cast between types - treat as same value with different type
        if operand_expr is not None:
            state.set_value(op.dest, operand_expr, op.result_type or "i32")
        else:
            # Create fresh symbolic value
            expr = z3.FreshConst(z3.IntSort(), f"cast_{op.dest}")
            state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """cast doesn't produce a concrete value."""
        return None


# Function to register all emitc dialect handlers
def register_handlers(registry) -> None:
    """Register emitc dialect handlers with registry."""
    registry.register("emitc.constant", EmitCConstantHandler())
    registry.register("emitc.add", EmitCAddHandler())
    registry.register("emitc.sub", EmitCSubHandler())
    registry.register("emitc.mul", EmitCMulHandler())
    registry.register("emitc.div", EmitCDivHandler())
    registry.register("emitc.bitwise_and", EmitCBitwiseAndHandler())
    registry.register("emitc.bitwise_or", EmitCBitwiseOrHandler())
    registry.register("emitc.bitwise_xor", EmitCBitwiseXorHandler())
    registry.register("emitc.bitwise_left_shift", EmitCBitwiseLeftShiftHandler())
    registry.register("emitc.bitwise_right_shift", EmitCBitwiseRightShiftHandler())
    registry.register("emitc.assign", EmitCAssignHandler())
    registry.register("emitc.bitwise_not", EmitCBitwiseNotHandler())
    registry.register("emitc.cmp", EmitCCmpHandler())
    registry.register("emitc.conditional", EmitCConditionalHandler())
    registry.register("emitc.cast", EmitCCastHandler())
