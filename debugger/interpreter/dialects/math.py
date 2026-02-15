#!/usr/bin/env python3
"""
Math dialect execution handlers.

Handles operations: absf, cos, sin, exp, log, sqrt, etc.
"""

import z3
from typing import Any

from .base import BinaryOperationHandler, UnaryOperationHandler
from ..operations import Operation
from ..models import SymbolicState, MLIRFunction


# Math operations can reuse arithmetic handlers for now
class MathAbsfOpHandler(UnaryOperationHandler):
    """Handler for math.absf operation."""

    def __init__(self):
        super().__init__(operator=None)

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute math.absf symbolically."""
        if not op.dest:
            raise ValueError("math.absf must have destination")
        # Create fresh symbolic value for absolute value
        expr = z3.FreshConst(z3.IntSort(), f"absf_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "f32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """math.absf doesn't have simple concrete value."""
        return None


class MathCosOpHandler(UnaryOperationHandler):
    """Handler for math.cos operation."""

    def __init__(self):
        super().__init__(operator=None)

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute math.cos symbolically."""
        if not op.dest:
            raise ValueError("math.cos must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"cos_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "f32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """math.cos doesn't have simple concrete value."""
        return None


class MathSinOpHandler(UnaryOperationHandler):
    """Handler for math.sin operation."""

    def __init__(self):
        super().__init__(operator=None)

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute math.sin symbolically."""
        if not op.dest:
            raise ValueError("math.sin must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"sin_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "f32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """math.sin doesn't have simple concrete value."""
        return None


class MathExpOpHandler(UnaryOperationHandler):
    """Handler for math.exp operation."""

    def __init__(self):
        super().__init__(operator=None)

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute math.exp symbolically."""
        if not op.dest:
            raise ValueError("math.exp must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"exp_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "f32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """math.exp doesn't have simple concrete value."""
        return None


class MathLogOpHandler(UnaryOperationHandler):
    """Handler for math.log operation."""

    def __init__(self):
        super().__init__(operator=None)

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute math.log symbolically."""
        if not op.dest:
            raise ValueError("math.log must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"log_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "f32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """math.log doesn't have simple concrete value."""
        return None


class MathSqrtOpHandler(UnaryOperationHandler):
    """Handler for math.sqrt operation."""

    def __init__(self):
        super().__init__(operator=None)

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute math.sqrt symbolically."""
        if not op.dest:
            raise ValueError("math.sqrt must have destination")
        expr = z3.FreshConst(z3.IntSort(), f"sqrt_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "f32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """math.sqrt doesn't have simple concrete value."""
        return None


class MathAtan2OpHandler(BinaryOperationHandler):
    """Handler for math.atan2 operation."""

    def __init__(self):
        super().__init__(operator=lambda l, r: z3.FreshConst(z3.IntSort(), "atan2"))


class MathFmaOpHandler(BinaryOperationHandler):
    """Handler for math.fma operation."""

    def __init__(self):
        super().__init__(operator=lambda l, r: z3.FreshConst(z3.IntSort(), "fma"))


class MathPowfOpHandler(BinaryOperationHandler):
    """Handler for math.powf operation."""

    def __init__(self):
        super().__init__(operator=lambda l, r: z3.FreshConst(z3.IntSort(), "powf"))


# Function to register all math dialect handlers
def register_handlers(registry) -> None:
    """Register math dialect handlers with registry."""
    registry.register("math.absf", MathAbsfOpHandler())
    registry.register("math.cos", MathCosOpHandler())
    registry.register("math.sin", MathSinOpHandler())
    registry.register("math.exp", MathExpOpHandler())
    registry.register("math.log", MathLogOpHandler())
    registry.register("math.sqrt", MathSqrtOpHandler())
    registry.register("math.atan2", MathAtan2OpHandler())
    registry.register("math.fma", MathFmaOpHandler())
    registry.register("math.powf", MathPowfOpHandler())
