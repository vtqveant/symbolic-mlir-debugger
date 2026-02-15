#!/usr/bin/env python3
"""
Index dialect parser.

Converts pymlir AST nodes for index operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any
import dataclasses

import parser.astnodes as mast
from .base import BaseDialectParser
from ..operations import (
    Operation,
    BinaryOperation,
    UnaryOperation,
    CompareOperation,
    ConstantOperation,
)


class IndexDialectParser(BaseDialectParser):
    """Parser for index dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse an index operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Special handling for known operation classes
            if class_name == "IndexCmpOp":
                return self._parse_cmp_operation(op_node)
            elif class_name == "IndexConstantOp":
                return self._parse_constant_operation(op_node)
            elif class_name == "IndexBoolConstantOp":
                return self._parse_bool_constant_operation(op_node)
            elif class_name == "IndexCastSOp":
                return self._parse_cast_s_operation(op_node)
            elif class_name == "IndexCastUOp":
                return self._parse_cast_u_operation(op_node)
            elif class_name == "IndexSizeOfOp":
                return self._parse_size_of_operation(op_node)

            # Binary operations (AddOperation, SubOperation, etc.)
            elif (
                class_name.endswith("Op")
                and hasattr(op_obj, "operand_a")
                and hasattr(op_obj, "operand_b")
                and class_name not in ("IndexCmpOp", "IndexCastSOp", "IndexCastUOp")
            ):
                return self._parse_binary_operation(op_node)

            # Unary operations (none currently, but handle if any)
            elif class_name.endswith("Op") and hasattr(op_obj, "operand"):
                return self._parse_unary_operation(op_node)

        # No handler found
        return None

    def _parse_binary_operation(
        self, op_node: mast.Operation
    ) -> Optional[BinaryOperation]:
        """Parse binary index operation (add, sub, mul, etc.)."""
        op_obj = op_node.op

        # Extract destination
        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operation name from class
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"index.{class_name[:-2].lower()}"  # Remove 'Op' suffix

        # Parse dialect and name
        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "index"
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

        return BinaryOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            lhs=lhs,
            rhs=rhs,
            attributes={},
        )

    def _parse_unary_operation(
        self, op_node: mast.Operation
    ) -> Optional[UnaryOperation]:
        """Parse unary index operation (currently none, but generic)."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"index.{class_name[:-2].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "index"
            name = full_name

        operand = self._ssa_use_to_string(op_obj.operand)

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

    def _parse_cmp_operation(
        self, op_node: mast.Operation
    ) -> Optional[CompareOperation]:
        """Parse index.cmp operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract predicate (string)
        pred = None
        if hasattr(op_obj, "predicate"):
            predicate = op_obj.predicate
            pred = str(predicate)
        else:
            pred = "eq"  # Default fallback

        # Extract operands
        lhs = self._ssa_use_to_string(op_obj.operand_a)
        rhs = self._ssa_use_to_string(op_obj.operand_b)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return CompareOperation(
            dialect="index",
            name="cmp",
            line=line,
            dest=dest,
            result_type=result_type,
            lhs=lhs,
            rhs=rhs,
            pred=pred,
            attributes={},
        )

    def _parse_constant_operation(
        self, op_node: mast.Operation
    ) -> Optional[ConstantOperation]:
        """Parse index.constant operation."""
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
            dialect="index",
            name="constant",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )

    def _parse_bool_constant_operation(
        self, op_node: mast.Operation
    ) -> Optional[ConstantOperation]:
        """Parse index.bool.constant operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract boolean value
        value = None
        if hasattr(op_obj, "value"):
            value = bool(op_obj.value)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return ConstantOperation(
            dialect="index",
            name="bool.constant",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )

    def _parse_cast_s_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse index.casts operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operand (arg)
        operand = None
        if hasattr(op_obj, "arg"):
            operand = self._ssa_use_to_string(op_obj.arg)
        else:
            return None

        # Extract src and dst types
        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        result_type = dst_type  # result type is dst_type

        line = self._extract_line_number(op_node)

        # Create generic Operation with custom attributes
        return Operation(
            dialect="index",
            name="casts",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "operand": operand,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_cast_u_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse index.castu operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = None
        if hasattr(op_obj, "arg"):
            operand = self._ssa_use_to_string(op_obj.arg)
        else:
            return None

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        result_type = dst_type

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="index",
            name="castu",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "operand": operand,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_size_of_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse index.sizeof operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = None
        if hasattr(op_obj, "arg"):
            operand = self._ssa_use_to_string(op_obj.arg)
        else:
            return None

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # Could be UnaryOperation but we need to preserve type info
        return UnaryOperation(
            dialect="index",
            name="sizeof",
            line=line,
            dest=dest,
            result_type=result_type,
            operand=operand,
            attributes={},
        )
