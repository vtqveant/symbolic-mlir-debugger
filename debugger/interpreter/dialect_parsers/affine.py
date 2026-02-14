#!/usr/bin/env python3
"""
Affine dialect parser.

Converts pymlir AST nodes for affine operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any, List
import dataclasses

import parser.astnodes as mast
from .base import BaseDialectParser
from ..operations import (
    Operation,
    LoopOperation,
    LoadOperation,
    StoreOperation,
    YieldOperation,
)


class AffineDialectParser(BaseDialectParser):
    """Parser for affine dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse an affine operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Map operation class names to parser methods
            if class_name == "AffineForOp":
                return self._parse_affine_for_operation(op_node)
            elif class_name == "AffineIfOp":
                return self._parse_affine_if_operation(op_node)
            elif class_name == "AffineLoadOp":
                return self._parse_affine_load_operation(op_node)
            elif class_name == "AffineStoreOp":
                return self._parse_affine_store_operation(op_node)
            elif class_name == "AffineYieldOp":
                return self._parse_affine_yield_operation(op_node)
            # Add other affine operations as needed

        # No handler found
        return None

    # Individual operation parsers
    def _parse_affine_for_operation(
        self, op_node: mast.Operation
    ) -> Optional[LoopOperation]:
        """Parse affine.for operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # affine.for may not have a destination (void)

        # Extract fields
        index = self._ssa_use_to_string(op_obj.index)
        lb = self._ssa_use_to_string(op_obj.begin)
        ub = self._ssa_use_to_string(op_obj.end)
        step = None
        if hasattr(op_obj, "step") and op_obj.step is not None:
            step = self._ssa_use_to_string(op_obj.step)

        # Handle iteration arguments if present
        iter_arg = None
        init = None
        result_type = None
        if hasattr(op_obj, "iter_args") and op_obj.iter_args:
            # For now, assume single iteration argument (follows scf.for pattern)
            if len(op_obj.iter_args) > 0:
                iter_arg_assignment = op_obj.iter_args[0]
                # iter_args is list of ArgumentAssignment objects with name/value fields
                iter_arg = self._ssa_use_to_string(iter_arg_assignment.name)
                init = self._ssa_use_to_string(iter_arg_assignment.value)

        # Determine result type
        if hasattr(op_obj, "iter_args_types") and op_obj.iter_args_types:
            # Use first iter_arg type as result type
            result_type = self._type_to_string(op_obj.iter_args_types[0])
        elif hasattr(op_obj, "out_type") and op_obj.out_type:
            result_type = self._type_to_string(op_obj.out_type)

        # Parse body region
        body_ops = []
        if hasattr(op_obj, "region") and op_obj.region is not None:
            body_ops = self._parse_region(op_obj.region)

        line = self._extract_line_number(op_node)

        return LoopOperation(
            dialect="affine",
            name="for",
            line=line,
            dest=dest or "",
            result_type=result_type,
            index=index,
            lb=lb,
            ub=ub,
            step=step,
            iter_arg=iter_arg,
            init=init,
            body=body_ops,
            attributes={},
        )

    def _parse_affine_if_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse affine.if operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract condition and operands
        cond = self._map_or_set_id_to_string(op_obj.cond)
        operands = [self._ssa_use_to_string(operand) for operand in op_obj.operands]

        # Parse body region
        body_ops = []
        if hasattr(op_obj, "body") and op_obj.body is not None:
            body_ops = self._parse_region(op_obj.body)

        # Parse else region if present
        else_ops = []
        if hasattr(op_obj, "elsebody") and op_obj.elsebody is not None:
            else_ops = self._parse_region(op_obj.elsebody)

        line = self._extract_line_number(op_node)

        # Create generic Operation with custom attributes
        attributes = {
            "cond": cond,
            "operands": operands,
        }
        if body_ops:
            attributes["body"] = body_ops
        if else_ops:
            attributes["elsebody"] = else_ops

        return Operation(
            dialect="affine",
            name="if",
            line=line,
            dest=dest or "",
            result_type=None,
            attributes=attributes,
        )

    def _parse_affine_load_operation(
        self, op_node: mast.Operation
    ) -> Optional[LoadOperation]:
        """Parse affine.load operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract memref and affine index
        memref = self._ssa_use_to_string(op_obj.arg)
        index = self._affine_expr_to_string(op_obj.index)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # Store affine index as attribute
        return LoadOperation(
            dialect="affine",
            name="load",
            line=line,
            dest=dest,
            result_type=result_type,
            memref=memref,
            indices=[],  # affine.load uses affine expression, not indices
            attributes={
                "affine_index": index,
            },
        )

    def _parse_affine_store_operation(
        self, op_node: mast.Operation
    ) -> Optional[StoreOperation]:
        """Parse affine.store operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # store may not have a destination

        # Extract fields
        addr = self._ssa_use_to_string(op_obj.addr)
        ref = self._ssa_use_to_string(op_obj.ref)
        index = self._affine_expr_to_string(op_obj.index)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return StoreOperation(
            dialect="affine",
            name="store",
            line=line,
            dest=dest or "",
            result_type=result_type,
            memref=addr,
            indices=[],  # affine.store uses affine expression
            value=ref,
            attributes={
                "affine_index": index,
            },
        )

    def _parse_affine_yield_operation(
        self, op_node: mast.Operation
    ) -> Optional[YieldOperation]:
        """Parse affine.yield operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract yield value if present
        value = None
        if hasattr(op_obj, "results") and op_obj.results:
            # Assume single result for now
            value = self._ssa_use_to_string(op_obj.results[0])

        line = self._extract_line_number(op_node)

        return YieldOperation(
            dialect="affine",
            name="yield",
            line=line,
            dest=dest or "",
            result_type=None,
            value=value,
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

    def _affine_expr_to_string(self, affine_expr) -> str:
        """Convert affine expression to string using parser context."""
        if self.parser_context and hasattr(
            self.parser_context, "_affine_expr_to_string"
        ):
            return self.parser_context._affine_expr_to_string(affine_expr)
        # Fallback
        try:
            return affine_expr.dump()
        except:
            return str(affine_expr)

    def _map_or_set_id_to_string(self, map_or_set_id) -> str:
        """Convert map_or_set_id to string using parser context."""
        if self.parser_context and hasattr(
            self.parser_context, "_map_or_set_id_to_string"
        ):
            return self.parser_context._map_or_set_id_to_string(map_or_set_id)
        # Fallback
        if hasattr(map_or_set_id, "value"):
            return map_or_set_id.value
        return str(map_or_set_id)
