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
class MathAbsfHandler(UnaryOperationHandler):
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


class MathCosHandler(UnaryOperationHandler):
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


class MathSinHandler(UnaryOperationHandler):
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


class MathExpHandler(UnaryOperationHandler):
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


class MathLogHandler(UnaryOperationHandler):
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


class MathSqrtHandler(UnaryOperationHandler):
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


class MathAtan2Handler(BinaryOperationHandler):
    """Handler for math.atan2 operation."""

    def __init__(self):
        super().__init__(operator=lambda l, r: z3.FreshConst(z3.IntSort(), "atan2"))


class MathFmaHandler(BinaryOperationHandler):
    """Handler for math.fma operation."""

    def __init__(self):
        super().__init__(operator=lambda l, r: z3.FreshConst(z3.IntSort(), "fma"))


class MathPowfHandler(BinaryOperationHandler):
    """Handler for math.powf operation."""

    def __init__(self):
        super().__init__(operator=lambda l, r: z3.FreshConst(z3.IntSort(), "powf"))


# Function to register all math dialect handlers
def register_handlers(registry) -> None:
    """Register math dialect handlers with registry."""
    registry.register("math.absf", MathAbsfHandler())
    registry.register("math.cos", MathCosHandler())
    registry.register("math.sin", MathSinHandler())
    registry.register("math.exp", MathExpHandler())
    registry.register("math.log", MathLogHandler())
    registry.register("math.sqrt", MathSqrtHandler())
    registry.register("math.atan2", MathAtan2Handler())
    registry.register("math.fma", MathFmaHandler())
    registry.register("math.powf", MathPowfHandler())
