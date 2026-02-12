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
            if class_name == "CallOp" or class_name == "CallOperation":
                return self._parse_call_operation(op_node)
            elif class_name == "CallIndirectOp":
                return self._parse_call_indirect_operation(op_node)
            # Note: ReturnOp is a builtin operation, not part of func dialect
            # but handled by generic parser or builtin handler.

        # No handler found
        print(f"DEBUG FuncDialectParser: class {op_obj.__class__.__name__} not handled")
        return None

    # Individual operation parsers
    def _parse_call_operation(self, op_node: mast.Operation) -> Optional[CallOperation]:
        """Parse func.call operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # func.call may not have a destination (void)

        # Extract callee
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
            name="call",
            line=line,
            dest=dest or "",
            result_type=result_type,
            callee=callee or "",
            args=args,
        )

    def _parse_call_indirect_operation(
        self, op_node: mast.Operation
    ) -> Optional[CallOperation]:
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
