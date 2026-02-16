#!/usr/bin/env python3
"""
Math dialect parser.

Converts pymlir AST nodes for math operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional

import parser.astnodes as mast

from .base import BaseDialectParser
from ..operations import (
    Operation,
    BinaryOperation,
    UnaryOperation,
    CompareOperation,
    ConstantOperation,
)


class MathDialectParser(BaseDialectParser):
    """Parser for math dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a math operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Special handling for known operation classes (must come before generic checks)
            if class_name == "MathCmpFOp":
                return self._parse_cmpf_operation(op_node)
            elif class_name == "MathConstantOp":
                return self._parse_constant_operation(op_node)

            # Binary operations (Atan2Operation, FmaOperation, PowfOperation)
            elif (
                class_name.endswith("Op")
                and hasattr(op_obj, "operand_a")
                and hasattr(op_obj, "operand_b")
                and class_name != "MathCmpFOp"
            ):
                return self._parse_binary_operation(op_node)

            # Unary operations (AbsfOperation, CosOperation, etc.)
            elif class_name.endswith("Op") and hasattr(op_obj, "operand"):
                return self._parse_unary_operation(op_node)

        # No handler found
        return None

    def _parse_binary_operation(self, op_node: mast.Operation) -> Optional[BinaryOperation]:
        """Parse binary math operation (atan2, fma, powf, etc.)."""
        op_obj = op_node.op

        # Extract destination
        dest = self._extract_destination(op_node)
        if dest is None:
            # Operation might not have a destination (should not happen for math)
            return None

        # Extract operation name from class
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            # Fallback to class name without 'Operation'
            class_name = op_obj.__class__.__name__
            full_name = f"math.{class_name[:-9].lower()}"  # Remove 'Operation' suffix

        # Parse dialect and name
        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "math"
            name = full_name

        # Extract operands
        lhs = self._ssa_use_to_string(op_obj.operand_a)
        rhs = self._ssa_use_to_string(op_obj.operand_b)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        # Get line number
        line = self._extract_line_number(op_node)

        # Check for special attributes (e.g., fma may have extra attributes?)
        attributes = {}
        # No special attributes for math binary ops currently

        return BinaryOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            lhs=lhs,
            rhs=rhs,
            attributes=attributes,
        )

    def _parse_unary_operation(self, op_node: mast.Operation) -> Optional[UnaryOperation]:
        """Parse unary math operation (absf, cos, sin, etc.)."""
        op_obj = op_node.op

        # Extract destination
        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operation name
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"math.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "math"
            name = full_name

        # Extract operand
        operand = self._ssa_use_to_string(op_obj.operand)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return UnaryOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            operand=operand,
            attributes={},
        )

    def _parse_cmpf_operation(self, op_node: mast.Operation) -> Optional[CompareOperation]:
        """Parse math.cmpf operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract predicate (string)
        pred = None
        if hasattr(op_obj, "predicate"):
            predicate = op_obj.predicate
            # predicate is already a string (e.g., "ult", "ule", "ueq", etc.)
            pred = str(predicate)
        else:
            pred = "ueq"  # Default fallback

        # Extract operands
        lhs = self._ssa_use_to_string(op_obj.operand_a)
        rhs = self._ssa_use_to_string(op_obj.operand_b)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return CompareOperation(
            dialect="math",
            name="cmpf",
            line=line,
            dest=dest,
            result_type=result_type,
            lhs=lhs,
            rhs=rhs,
            pred=pred,
            attributes={},
        )

    def _parse_constant_operation(self, op_node: mast.Operation) -> Optional[ConstantOperation]:
        """Parse math.constant operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract constant value
        value = None
        if hasattr(op_obj, "value"):
            value = self._parse_constant_value(op_obj.value)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return ConstantOperation(
            dialect="math",
            name="constant",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )
