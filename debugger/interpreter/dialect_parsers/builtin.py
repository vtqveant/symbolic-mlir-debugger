#!/usr/bin/env python3
"""
Builtin dialect parser.

Converts pymlir AST nodes for builtin operations directly to
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
    ReturnOperation,
)


class BuiltinDialectParser(BaseDialectParser):
    """Parser for builtin dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a builtin operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Special handling for unrealized_conversion_cast (has inputs, outputs)
            if class_name == "BuiltinUnrealizedConversionCastOp":
                return self._parse_unrealized_conversion_cast_operation(op_node)
            # Module operation (builtin.module) - typically handled at module level
            elif class_name == "BuiltinModuleOp":
                return self._parse_module_operation(op_node)
            elif class_name == "FuncReturnOp":
                return self._parse_return_operation(op_node)
            # Generic fallback
            else:
                return self._parse_generic_operation(op_node)

        return None

    def _parse_unrealized_conversion_cast_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse builtin.unrealized_conversion_cast operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract inputs
        inputs = []
        if hasattr(op_obj, "inputs"):
            inputs = [self._ssa_use_to_string(inp) for inp in op_obj.inputs]

        # Extract outputs (types)
        outputs = []
        if hasattr(op_obj, "outputs"):
            outputs = [self._type_to_string(out) for out in op_obj.outputs]

        line = self._extract_line_number(op_node)

        attributes = {
            "inputs": inputs,
            "outputs": outputs,
        }

        return Operation(
            dialect="builtin",
            name="unrealized_conversion_cast",
            line=line,
            dest=dest,
            result_type=None,  # This operation may have multiple results?
            attributes=attributes,
        )

    def _parse_module_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse builtin.module operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # Module may not have a destination? It's a container

        line = self._extract_line_number(op_node)

        # Module operation typically has regions, but we just return a basic operation
        return Operation(
            dialect="builtin",
            name="module",
            line=line,
            dest=dest,
            result_type=None,
            attributes={},
        )

    def _parse_return_operation(self, op_node: mast.Operation) -> Optional[ReturnOperation]:
        """Parse return operation."""
        op_obj = op_node.op

        # Return operations don't have destinations, but extract anyway
        dest = self._extract_destination(op_node) or ""

        # Extract return value if present
        value = None
        if hasattr(op_obj, "values") and op_obj.values and len(op_obj.values) > 0:
            val_node = op_obj.values[0]
            if hasattr(val_node, "value"):
                value = self._ssa_use_to_string(val_node.value)
            else:
                value = self._ssa_use_to_string(val_node)

        # Extract return type if present
        result_type = None
        if hasattr(op_obj, "types") and op_obj.types and len(op_obj.types) > 0:
            result_type = self._type_to_string(op_obj.types[0])

        line = self._extract_line_number(op_node)

        return ReturnOperation(
            dialect="builtin",
            name="return",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
        )

    def _parse_generic_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse generic builtin operation with unknown structure."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operation name
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"builtin.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "builtin"
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
                elif isinstance(value, (mast.SsaId, mast.StringLiteral, int, float, str)):
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
