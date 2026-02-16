#!/usr/bin/env python3
"""
Arithmetic dialect execution handlers.

Handles operations: addi, subi, muli, divi, constant, cmpi, etc.
"""

import z3
from typing import Any

from .base import (
    BinaryOperationHandler,
    ConstantOperationHandler,
    CompareOperationHandler,
    UnaryOperationHandler,
)
from ..operations import (
    UnaryOperation,
)
from ..models import SymbolicState, MLIRFunction


# Binary arithmetic operations
class ArithAddIOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda left, right: left + right)


class ArithSubIOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda left, right: left - right)


class ArithMulIOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda left, right: left * right)


class ArithDivSIOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda left, right: left / right)  # Integer division in Z3


# Comparison operations predicate mapping
ARITH_CMPI_PREDICATE_MAP = {
    "eq": lambda left, right: left == right,
    "ne": lambda left, right: left != right,
    "slt": lambda left, right: left < right,
    "sle": lambda left, right: left <= right,
    "sgt": lambda left, right: left > right,
    "sge": lambda left, right: left >= right,
    "ult": lambda left, right: z3.ULT(left, right),  # Unsigned comparisons
    "ule": lambda left, right: z3.ULE(left, right),
    "ugt": lambda left, right: z3.UGT(left, right),
    "uge": lambda left, right: z3.UGE(left, right),
}


class ArithCmpiOpHandler(CompareOperationHandler):
    def __init__(self):
        super().__init__(predicate_map=ARITH_CMPI_PREDICATE_MAP)


# Constant operation handler (already provided by base)


class ArithIndexCastOpHandler(UnaryOperationHandler):
    """Handler for arith.index_cast operation."""

    def __init__(self):
        # Identity operator - index_cast is just type conversion
        super().__init__(operator=lambda x: x)

    def _try_concrete_evaluation(
        self, op: UnaryOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of index_cast."""
        operand_concrete = state.get_concrete_value(op.operand)
        print(f"DEBUG ArithIndexCastHandler: operand={op.operand}, concrete={operand_concrete}")
        if operand_concrete is not None:
            # Just pass through the concrete value
            return operand_concrete
        return None


# Function to register all arithmetic dialect handlers
def register_handlers(registry) -> None:
    """Register arithmetic dialect handlers with registry."""
    # print(f"DEBUG: Registering arithmetic dialect handlers")
    registry.register("arith.addi", ArithAddIOpHandler())
    registry.register("arith.subi", ArithSubIOpHandler())
    registry.register("arith.muli", ArithMulIOpHandler())
    registry.register("arith.divsi", ArithDivSIOpHandler())
    registry.register("arith.divui", ArithDivSIOpHandler())  # Same handler for unsigned
    registry.register("arith.divi", ArithDivSIOpHandler())  # Signed integer division
    registry.register("arith.constant", ConstantOperationHandler())
    registry.register("arith.index_cast", ArithIndexCastOpHandler())
    registry.register("arith.cmpi", ArithCmpiOpHandler())

    # Additional arithmetic operations
    registry.register("arith.addf", ArithAddIOpHandler())  # Float addition (simplified)
    registry.register("arith.subf", ArithSubIOpHandler())
    registry.register("arith.mulf", ArithMulIOpHandler())
    registry.register("arith.divf", ArithDivSIOpHandler())

    # Bitwise operations (simplified to integer operations)
    registry.register("arith.andi", ArithAddIOpHandler())  # Placeholder
    registry.register("arith.ori", ArithAddIOpHandler())
    registry.register("arith.xori", ArithAddIOpHandler())
