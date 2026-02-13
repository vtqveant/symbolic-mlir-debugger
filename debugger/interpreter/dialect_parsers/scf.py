#!/usr/bin/env python3
"""
Structured Control Flow (scf) dialect parser.

Converts pymlir AST nodes for scf operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any, List, Tuple
import dataclasses

import parser.astnodes as mast
from .base import BaseDialectParser
from ..operations import (
    Operation,
    LoopOperation,
    IfOperation,
    YieldOperation,
    TerminatorOperation,
)


class ScfDialectParser(BaseDialectParser):
    """Parser for structured control flow dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse an scf operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Map operation class names to parser methods
            if class_name == "SCFForOp":
                return self._parse_scf_for_operation(op_node)
            elif class_name == "SCFIfOp":
                return self._parse_scf_if_operation(op_node)
            elif class_name == "SCFYield":
                return self._parse_scf_yield_operation(op_node)
            elif class_name == "SCFConditionOp":
                return self._parse_scf_condition_operation(op_node)
            # Add other scf operations as needed

        # No handler found
        return None

    # Individual operation parsers
    def _parse_scf_for_operation(
        self, op_node: mast.Operation
    ) -> Optional[LoopOperation]:
        """Parse scf.for operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # scf.for may not have a destination (void)

        # Extract fields
        iv = self._ssa_use_to_string(op_obj.index)
        lb = self._ssa_use_to_string(op_obj.begin)
        ub = self._ssa_use_to_string(op_obj.end)
        step = self._ssa_use_to_string(op_obj.step)

        # Handle iteration arguments if present
        iter_arg = None
        init = None
        if hasattr(op_obj, "iter_args") and op_obj.iter_args:
            # For now, assume single iteration argument
            if len(op_obj.iter_args) > 0:
                iter_arg_assignment = op_obj.iter_args[0]
                # ArgumentAssignment has 'name' and 'value' fields
                iter_arg = self._ssa_use_to_string(iter_arg_assignment.name)
                init = self._ssa_use_to_string(iter_arg_assignment.value)

        # Parse body region
        body_ops = []
        if hasattr(op_obj, "body") and op_obj.body is not None:
            body_ops = self._parse_region(op_obj.body)

        line = self._extract_line_number(op_node)

        return LoopOperation(
            dialect="scf",
            name="for",
            line=line,
            dest=dest or "",
            result_type=None,
            index=iv,
            lb=lb,
            ub=ub,
            step=step,
            iter_arg=iter_arg,
            init=init,
            body=body_ops,
            attributes={},
        )

    def _parse_scf_if_operation(self, op_node: mast.Operation) -> Optional[IfOperation]:
        """Parse scf.if operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract condition
        cond = self._ssa_use_to_string(op_obj.cond)

        # Parse body region
        body_ops = []
        if hasattr(op_obj, "body") and op_obj.body is not None:
            body_ops = self._parse_region(op_obj.body)

        # Parse else region if present
        else_ops = []
        if hasattr(op_obj, "elsebody") and op_obj.elsebody is not None:
            else_ops = self._parse_region(op_obj.elsebody)

        # Extract result types if present
        result_types = []
        if hasattr(op_obj, "out_types") and op_obj.out_types:
            result_types = [self._type_to_string(t) for t in op_obj.out_types]

        line = self._extract_line_number(op_node)

        return IfOperation(
            dialect="scf",
            name="if",
            line=line,
            dest=dest or "",
            result_type=None,
            cond=cond,
            body=body_ops,
            elsebody=else_ops,
            result_types=result_types,
        )

    def _parse_scf_yield_operation(
        self, op_node: mast.Operation
    ) -> Optional[YieldOperation]:
        """Parse scf.yield operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract yield value if present
        value = None
        if hasattr(op_obj, "results") and op_obj.results:
            # Assume single result for now
            value = self._ssa_use_to_string(op_obj.results[0])

        line = self._extract_line_number(op_node)

        return YieldOperation(
            dialect="scf",
            name="yield",
            line=line,
            dest=dest or "",
            result_type=None,
            value=value,
        )

    def _parse_scf_condition_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse scf.condition operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract condition if present
        condition = None
        if hasattr(op_obj, "condition"):
            condition = self._ssa_use_to_string(op_obj.condition)

        # Extract arguments if present
        args = []
        if hasattr(op_obj, "args") and op_obj.args:
            args = [self._ssa_use_to_string(arg) for arg in op_obj.args]

        # Extract out types if present
        out_types = []
        if hasattr(op_obj, "out_types") and op_obj.out_types:
            out_types = [self._type_to_string(t) for t in op_obj.out_types]

        line = self._extract_line_number(op_node)

        # Create generic Operation with custom attributes
        attributes = {}
        if condition is not None:
            attributes["condition"] = condition
        if args:
            attributes["args"] = args
        if out_types:
            attributes["out_types"] = out_types

        return Operation(
            dialect="scf",
            name="condition",
            line=line,
            dest=dest or "",
            result_type=None,
            attributes=attributes,
        )

    # Helper methods
    def _parse_region(self, region) -> List[Any]:
        """Parse a region into a list of operation dictionaries or Operation objects."""
        if not hasattr(region, "body") or not region.body:
            return []

        ops = []
        for block in region.body:
            for op_node in block.body:
                # Use parser context to parse operation (supports both dict and Operation)
                if self.parser_context:
                    parsed = self.parser_context._parse_operation(op_node)
                    if parsed:
                        ops.append(parsed)
                else:
                    # Fallback: try to parse using base methods? For now skip
                    pass
        return ops
