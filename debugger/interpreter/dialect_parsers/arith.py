#!/usr/bin/env python3
"""
Arithmetic (arith) dialect parser.

Converts pymlir AST nodes for arithmetic operations directly to
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


class ArithDialectParser(BaseDialectParser):
    """Parser for arithmetic dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse an arithmetic operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Special handling for known operation classes (must come before generic checks)
            if class_name == "CmpiOperation":
                return self._parse_cmpi_operation(op_node)
            elif class_name == "CmpfOperation":
                return self._parse_cmpf_operation(op_node)
            elif class_name == "ConstantOperation":
                return self._parse_constant_operation(op_node)
            elif class_name == "SelectOperation":
                return self._parse_select_operation(op_node)
            elif class_name == "IndexCastOperation":
                return self._parse_index_cast_operation(op_node)

            # Binary operations (AddiOperation, SubiOperation, etc.)
            # Exclude Cmpi/Cmpf which have operand_a/operand_b but are not binary arithmetic ops
            elif (
                class_name.endswith("Operation")
                and hasattr(op_obj, "operand_a")
                and hasattr(op_obj, "operand_b")
                and class_name not in ("CmpiOperation", "CmpfOperation")
            ):
                # Check if it's a BinaryOperation subclass from pymlir
                # We'll handle all binary ops with generic parser
                return self._parse_binary_operation(op_node)

            # Unary operations (AbsfOperation, CeilfOperation, etc.)
            elif class_name.endswith("Operation") and hasattr(op_obj, "operand"):
                return self._parse_unary_operation(op_node)

        # No handler found
        return None

    def _parse_binary_operation(
        self, op_node: mast.Operation
    ) -> Optional[BinaryOperation]:
        """Parse binary arithmetic operation (addi, subi, muli, etc.)."""
        op_obj = op_node.op

        # Extract destination
        dest = self._extract_destination(op_node)
        if dest is None:
            # Operation might not have a destination (should not happen for arith)
            return None

        # Extract operation name from class
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            # Fallback to class name without 'Operation'
            class_name = op_obj.__class__.__name__
            full_name = f"arith.{class_name[:-9].lower()}"  # Remove 'Operation' suffix

        # Parse dialect and name
        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "arith"
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
            attributes={},  # Binary arith ops typically have no attributes
        )

    def _parse_unary_operation(
        self, op_node: mast.Operation
    ) -> Optional[UnaryOperation]:
        """Parse unary arithmetic operation (absf, ceilf, etc.)."""
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
            full_name = f"arith.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "arith"
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

    def _parse_cmpi_operation(
        self, op_node: mast.Operation
    ) -> Optional[CompareOperation]:
        """Parse arith.cmpi operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract predicate
        pred = None
        if hasattr(op_obj, "predicate"):
            predicate = op_obj.predicate
            # Map integer predicate to string
            predicate_map = {0: "eq", 1: "ne", 2: "slt", 3: "sle", 4: "sgt", 5: "sge"}
            pred = predicate_map.get(predicate, str(predicate))
        elif hasattr(op_obj, "comptype"):
            # pymlir stores predicate as comptype (string like "slt")
            pred = str(op_obj.comptype)
        else:
            pred = "slt"  # Default fallback

        # Extract operands
        lhs = self._ssa_use_to_string(op_obj.operand_a)
        rhs = self._ssa_use_to_string(op_obj.operand_b)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return CompareOperation(
            dialect="arith",
            name="cmpi",
            line=line,
            dest=dest,
            result_type=result_type,
            lhs=lhs,
            rhs=rhs,
            pred=pred,
            attributes={},
        )

    def _parse_cmpf_operation(
        self, op_node: mast.Operation
    ) -> Optional[CompareOperation]:
        """Parse arith.cmpf operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract predicate (same mapping as cmpi for now)
        pred = None
        if hasattr(op_obj, "predicate"):
            predicate = op_obj.predicate
            predicate_map = {0: "eq", 1: "ne", 2: "slt", 3: "sle", 4: "sgt", 5: "sge"}
            pred = predicate_map.get(predicate, str(predicate))
        elif hasattr(op_obj, "comptype"):
            pred = str(op_obj.comptype)
        else:
            pred = "slt"

        lhs = self._ssa_use_to_string(op_obj.operand_a)
        rhs = self._ssa_use_to_string(op_obj.operand_b)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return CompareOperation(
            dialect="arith",
            name="cmpf",
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
        """Parse arith.constant operation."""
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
            dialect="arith",
            name="constant",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )

    def _parse_select_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse arith.select operation.

        Note: arith.select is not a Binary/Unary/Compare operation.
        For now, return a generic Operation with custom fields.
        """
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract fields
        cond = self._ssa_use_to_string(op_obj.cond)
        arg_true = self._ssa_use_to_string(op_obj.arg_true)
        arg_false = self._ssa_use_to_string(op_obj.arg_false)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # Create generic Operation with custom attributes
        return Operation(
            dialect="arith",
            name="select",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "cond": cond,
                "arg_true": arg_true,
                "arg_false": arg_false,
            },
        )

    def _parse_index_cast_operation(
        self, op_node: mast.Operation
    ) -> Optional[UnaryOperation]:
        """Parse arith.index_cast operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operand (arg field)
        operand = None
        if hasattr(op_obj, "arg"):
            operand = self._ssa_use_to_string(op_obj.arg)
        elif hasattr(op_obj, "operand"):
            operand = self._ssa_use_to_string(op_obj.operand)
        else:
            return None

        result_type = None
        if hasattr(op_obj, "dst_type"):
            result_type = self._type_to_string(op_obj.dst_type)
        elif hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return UnaryOperation(
            dialect="arith",
            name="index_cast",
            line=line,
            dest=dest,
            result_type=result_type,
            operand=operand,
            attributes={},
        )
