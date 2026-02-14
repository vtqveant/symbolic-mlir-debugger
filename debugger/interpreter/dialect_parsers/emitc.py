#!/usr/bin/env python3
"""
EmitC dialect parser.

Converts pymlir AST nodes for emitc operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any, List
import dataclasses

import parser.astnodes as mast
from .base import BaseDialectParser
from ..operations import (
    Operation,
    BinaryOperation,
    UnaryOperation,
    ConstantOperation,
    CompareOperation,
)


class EmitcDialectParser(BaseDialectParser):
    """Parser for emitc dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse an emitc operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Special handling for operations with custom fields
            if class_name == "EmitCApplyOp":
                return self._parse_apply_operation(op_node)
            elif class_name == "EmitCCallOp":
                return self._parse_call_operation(op_node)
            elif class_name == "EmitCCallOpaqueOp":
                return self._parse_call_opaque_operation(op_node)
            elif class_name == "EmitCClassOp":
                return self._parse_class_operation(op_node)
            elif class_name == "EmitCCmpOp":
                return self._parse_cmp_operation(op_node)
            elif class_name == "EmitCConditionalOp":
                return self._parse_conditional_operation(op_node)
            elif class_name == "EmitCConstantOp":
                return self._parse_constant_operation(op_node)

            # Binary operations (Add, BitwiseAnd, BitwiseLeftShift, BitwiseOr, BitwiseRightShift, BitwiseXor, Assign)
            elif (
                class_name.endswith("Op")
                and hasattr(op_obj, "lhs")
                and hasattr(op_obj, "rhs")
            ):
                return self._parse_binary_operation(op_node)

            # Unary operations (AddressOf, BitwiseNot, Cast)
            elif class_name.endswith("Op") and hasattr(op_obj, "operand"):
                return self._parse_unary_operation(op_node)

            # Generic fallback
            else:
                return self._parse_generic_operation(op_node)

        return None

    def _parse_binary_operation(
        self, op_node: mast.Operation
    ) -> Optional[BinaryOperation]:
        """Parse binary emitc operation (add, bitwise_and, assign, etc.)."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operation name
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"emitc.{class_name[:-2].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "emitc"
            name = full_name

        lhs = self._ssa_use_to_string(op_obj.lhs)
        rhs = self._ssa_use_to_string(op_obj.rhs)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

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
        """Parse unary emitc operation (address_of, bitwise_not, cast)."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"emitc.{class_name[:-2].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "emitc"
            name = full_name

        operand = self._ssa_use_to_string(op_obj.operand)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)
        elif hasattr(op_obj, "dst_type"):  # For CastOperation
            result_type = self._type_to_string(op_obj.dst_type)

        line = self._extract_line_number(op_node)

        # For CastOperation, include src_type as attribute
        attributes = {}
        if hasattr(op_obj, "src_type"):
            attributes["src_type"] = self._type_to_string(op_obj.src_type)

        return UnaryOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            operand=operand,
            attributes=attributes,
        )

    def _parse_apply_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse emitc.apply operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        callee = None
        if hasattr(op_obj, "callee"):
            callee = self._ssa_use_to_string(op_obj.callee)

        args = []
        if hasattr(op_obj, "args"):
            args = [self._ssa_use_to_string(arg) for arg in op_obj.args]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        attributes = {
            "callee": callee,
            "args": args,
        }

        return Operation(
            dialect="emitc",
            name="apply",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes=attributes,
        )

    def _parse_call_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse emitc.call operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        callee = None
        if hasattr(op_obj, "callee"):
            callee = self._ssa_use_to_string(op_obj.callee)

        args = []
        if hasattr(op_obj, "args"):
            args = [self._ssa_use_to_string(arg) for arg in op_obj.args]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        attributes = {
            "callee": callee,
            "args": args,
        }

        return Operation(
            dialect="emitc",
            name="call",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes=attributes,
        )

    def _parse_call_opaque_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse emitc.call_opaque operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        callee = None
        if hasattr(op_obj, "callee"):
            callee = self._ssa_use_to_string(op_obj.callee)

        args = []
        if hasattr(op_obj, "args"):
            args = [self._ssa_use_to_string(arg) for arg in op_obj.args]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        attributes = {
            "callee": callee,
            "args": args,
        }

        return Operation(
            dialect="emitc",
            name="call_opaque",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes=attributes,
        )

    def _parse_class_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse emitc.class operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        name = None
        if hasattr(op_obj, "name"):
            name = self._ssa_use_to_string(op_obj.name)

        line = self._extract_line_number(op_node)

        attributes = {
            "name": name,
        }

        return Operation(
            dialect="emitc",
            name="class",
            line=line,
            dest=dest,
            result_type=None,
            attributes=attributes,
        )

    def _parse_cmp_operation(
        self, op_node: mast.Operation
    ) -> Optional[CompareOperation]:
        """Parse emitc.cmp operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        predicate = None
        if hasattr(op_obj, "predicate"):
            predicate = self._ssa_use_to_string(op_obj.predicate)

        lhs = self._ssa_use_to_string(op_obj.lhs)
        rhs = self._ssa_use_to_string(op_obj.rhs)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return CompareOperation(
            dialect="emitc",
            name="cmp",
            line=line,
            dest=dest,
            result_type=result_type,
            lhs=lhs,
            rhs=rhs,
            pred=predicate,
            attributes={},
        )

    def _parse_conditional_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse emitc.conditional operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        condition = self._ssa_use_to_string(op_obj.condition)
        true_value = self._ssa_use_to_string(op_obj.true_value)
        false_value = self._ssa_use_to_string(op_obj.false_value)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        attributes = {
            "condition": condition,
            "true_value": true_value,
            "false_value": false_value,
        }

        return Operation(
            dialect="emitc",
            name="conditional",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes=attributes,
        )

    def _parse_constant_operation(
        self, op_node: mast.Operation
    ) -> Optional[ConstantOperation]:
        """Parse emitc.constant operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        value = None
        if hasattr(op_obj, "value"):
            value = self._parse_constant_value(op_obj.value)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return ConstantOperation(
            dialect="emitc",
            name="constant",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )

    def _parse_generic_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse generic emitc operation with unknown structure."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Handle GenericOperation (quoted operation names in MLIR)
        if isinstance(op_obj, mast.GenericOperation):
            # Get full operation name (e.g., "emitc.constant")
            name_obj = op_obj.name
            if hasattr(name_obj, "value"):
                full_name = name_obj.value
            else:
                full_name = str(name_obj)

            # Strip dialect prefix
            if "." in full_name:
                dialect, name = full_name.split(".", 1)
            else:
                dialect = "emitc"
                name = full_name

            # Determine if binary or unary based on args length
            args = (
                op_obj.args
                if hasattr(op_obj, "args") and op_obj.args is not None
                else []
            )
            num_args = len(args)

            # Extract result type
            result_type = None
            if hasattr(op_obj, "type"):
                result_type = self._type_to_string(op_obj.type)

            # Parse attributes if present
            attributes = {}
            if hasattr(op_obj, "attributes") and op_obj.attributes is not None:
                attributes = self._parse_attribute(op_obj.attributes)

            line = self._extract_line_number(op_node)

            # Special handling for specific operation types
            if name == "constant":
                # Extract value from attributes
                value = attributes.get("value")
                return ConstantOperation(
                    dialect=dialect,
                    name=name,
                    line=line,
                    dest=dest,
                    result_type=result_type,
                    value=value,
                    attributes=attributes,
                )
            elif name == "cmp":
                # For cmp, we need pred, lhs, rhs
                # args length should be 2
                if num_args == 2:
                    lhs = self._ssa_use_to_string(args[0])
                    rhs = self._ssa_use_to_string(args[1])
                    pred = attributes.get("predicate")
                    return CompareOperation(
                        dialect=dialect,
                        name=name,
                        line=line,
                        dest=dest,
                        result_type=result_type,
                        pred=pred or "",
                        lhs=lhs,
                        rhs=rhs,
                        attributes=attributes,
                    )
                else:
                    # Fallback to generic operation
                    return Operation(
                        dialect=dialect,
                        name=name,
                        line=line,
                        dest=dest,
                        result_type=result_type,
                        attributes=attributes,
                    )

            # Handle binary operations (add, etc.)
            if num_args == 2:
                lhs = self._ssa_use_to_string(args[0])
                rhs = self._ssa_use_to_string(args[1])
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
            # Handle unary operations (cast, etc.)
            elif num_args == 1:
                operand = self._ssa_use_to_string(args[0])
                return UnaryOperation(
                    dialect=dialect,
                    name=name,
                    line=line,
                    dest=dest,
                    result_type=result_type,
                    operand=operand,
                    attributes=attributes,
                )
            else:
                # Generic operation with attributes (constant already handled)
                return Operation(
                    dialect=dialect,
                    name=name,
                    line=line,
                    dest=dest,
                    result_type=result_type,
                    attributes=attributes,
                )

        # Original logic for non-GenericOperation
        # Extract operation name
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"emitc.{class_name[:-2].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "emitc"
            name = full_name

        # Collect all fields as attributes
        attributes = {}
        # Exclude private fields (starting with _)
        for field_name in dir(op_obj):
            if field_name.startswith("_"):
                continue
            try:
                value = getattr(op_obj, field_name)
                # Skip callable values
                if callable(value):
                    continue
                # Convert SSA uses and types
                if isinstance(value, list):
                    attributes[field_name] = [self._ssa_use_to_string(v) for v in value]
                elif field_name.endswith("_type") or field_name == "type":
                    attributes[field_name] = self._type_to_string(value)
                elif isinstance(
                    value, (mast.SsaId, mast.StringLiteral, int, float, str)
                ):
                    attributes[field_name] = self._ssa_use_to_string(value)
                else:
                    attributes[field_name] = str(value)
            except:
                pass

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            attributes=attributes,
        )
