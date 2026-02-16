#!/usr/bin/env python3
"""
Function (func) dialect parser.

Converts pymlir AST nodes for func operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any, List
import dataclasses

import parser.astnodes as mast
from .base import BaseDialectParser
from ..operations import (
    Operation,
    CallOperation,
    ReturnOperation,
)


class FuncDialectParser(BaseDialectParser):
    """Parser for function dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a func operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Map operation class names to parser methods
            if class_name == "FuncCallOp":
                return self._parse_call_operation(op_node)
            elif class_name == "FuncCallIndirectOp":
                return self._parse_call_indirect_operation(op_node)
            elif class_name == "FuncReturnOp":
                return self._parse_return_operation(op_node)

        # No handler found

        return None

    # Individual operation parsers
    def _parse_call_operation(self, op_node: mast.Operation) -> Optional[CallOperation]:
        """Parse func.call operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # func.call may not have a destination (void)

        # Extract callee (SymbolRefId)
        callee = None
        if hasattr(op_obj, "func"):
            func_obj = op_obj.func
            if hasattr(func_obj, "value"):
                callee = func_obj.value
            else:
                callee = str(func_obj)

        # Extract arguments
        args = []
        if hasattr(op_obj, "args") and op_obj.args:
            args = [self._ssa_use_to_string(arg) for arg in op_obj.args]

        # Extract result type from FunctionType
        result_type = None
        if hasattr(op_obj, "type"):
            type_obj = op_obj.type
            # Check if it's a FunctionType
            if isinstance(type_obj, mast.FunctionType):
                # Extract first result type
                if type_obj.result_types:
                    result_type = self._type_to_string(type_obj.result_types[0])
            else:
                result_type = self._type_to_string(type_obj)

        line = self._extract_line_number(op_node)

        return CallOperation(
            dialect="func",
            name="call",
            line=line,
            dest=dest or "",
            result_type=result_type,
            callee=callee or "",
            args=args,
        )

    def _parse_call_indirect_operation(self, op_node: mast.Operation) -> Optional[CallOperation]:
        """Parse func.call_indirect operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract callee (function pointer)
        callee = None
        if hasattr(op_obj, "func"):
            callee = self._ssa_use_to_string(op_obj.func)

        # Extract arguments
        args = []
        if hasattr(op_obj, "args") and op_obj.args:
            args = [self._ssa_use_to_string(arg) for arg in op_obj.args]

        # Extract result type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return CallOperation(
            dialect="func",
            name="call_indirect",
            line=line,
            dest=dest or "",
            result_type=result_type,
            callee=callee or "",
            args=args,
        )

    def _parse_return_operation(self, op_node: mast.Operation) -> Optional[ReturnOperation]:
        """Parse func.return operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract the return value (first value if multiple)
        value = None
        if hasattr(op_obj, "values") and op_obj.values:
            value = self._ssa_use_to_string(op_obj.values[0])

        line = self._extract_line_number(op_node)

        return ReturnOperation(
            dialect="func",
            name="return",
            line=line,
            dest=dest,
            value=value,
        )
