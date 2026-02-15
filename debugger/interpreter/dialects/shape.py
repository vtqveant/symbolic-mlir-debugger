#!/usr/bin/env python3
"""
Shape dialect execution handlers.

Handles operations: const_size, const_shape, add, div, dim, get_extent, etc.
"""

import z3
from typing import Any

from .base import (
    BinaryOperationHandler,
    ConstantOperationHandler,
    OperationHandler,
)
from ..operations import (
    Operation,
    ConstantOperation,
    ReturnOperation,
)
from ..models import SymbolicState, MLIRFunction


# Shape constant operations are similar to arithmetic constants
class ShapeConstSizeOpHandler(ConstantOperationHandler):
    """Handler for shape.const_size operation."""

    def execute_symbolic(
        self,
        op: ConstantOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute shape.const_size symbolically."""
        if not isinstance(op, ConstantOperation):
            raise TypeError(f"Expected ConstantOperation, got {type(op)}")

        # Try to get value from attributes if op.value is None
        value = op.value
        import sys

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
        import sys

        if isinstance(value, int):
            expr = z3.IntVal(value)
        elif isinstance(value, float):
            expr = z3.RealVal(value)
        else:
            # Fallback to symbolic variable
            expr = z3.FreshConst(z3.IntSort(), f"shape_const_{op.dest}")

        state.set_value(op.dest, expr, op.result_type or "!shape.size")

        # Also store concrete value if we have it
        if isinstance(value, (int, float)):
            state.set_concrete_value(op.dest, value)

    def _try_concrete_evaluation(
        self, op: ConstantOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of shape.const_size."""
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


class ShapeConstShapeOpHandler(OperationHandler):
    """Handler for shape.const_shape operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute shape.const_shape symbolically."""
        # shape.const_shape produces a shape value (list of dimensions)
        # For symbolic execution, create a fresh symbolic value for the shape
        if not op.dest:
            raise ValueError("shape.const_shape must have destination")

        expr = z3.FreshConst(z3.IntSort(), f"shape_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "shape")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """shape.const_shape doesn't have a simple concrete value."""
        return None


# Shape arithmetic operations (add, div) are binary operations
class ShapeAddOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l + r)


class ShapeDivOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l / r)


class ShapeDimOpHandler(OperationHandler):
    """Handler for shape.dim operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute shape.dim symbolically."""
        # shape.dim extracts a dimension from a shape
        # For symbolic execution, create a fresh symbolic value for the dimension
        if not op.dest:
            raise ValueError("shape.dim must have destination")

        # Get shape and index from operation dict
        # Note: operation_from_dict should parse shape.dim correctly
        # shape.dim has shape and index operands
        expr = z3.FreshConst(z3.IntSort(), f"dim_{op.dest}")
        state.set_value(op.dest, expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of shape.dim."""
        return None


# shape.get_extent is similar to shape.dim
class ShapeGetExtentOpHandler(ShapeDimOpHandler):
    """Handler for shape.get_extent operation."""

    pass


# Function to register all shape dialect handlers
def register_handlers(registry) -> None:
    """Register shape dialect handlers with registry."""
    registry.register("shape.const_size", ShapeConstSizeOpHandler())
    registry.register("shape.const_shape", ShapeConstShapeOpHandler())
    registry.register("shape.add", ShapeAddOpHandler())
    registry.register("shape.div", ShapeDivOpHandler())
    registry.register("shape.dim", ShapeDimOpHandler())
    registry.register("shape.get_extent", ShapeGetExtentOpHandler())
