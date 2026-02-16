#!/usr/bin/env python3
"""
Linear Algebra (linalg) dialect parser.

Converts pymlir AST nodes for linalg operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any, List

import parser.astnodes as mast

from .base import BaseDialectParser
from ..operations import (
    Operation,
    LinalgGenericOperation,
    LinalgMatmulOperation,
    LinalgBatchMatmulOperation,
    LinalgYieldOperation,
)


class LinalgDialectParser(BaseDialectParser):
    """Parser for linear algebra dialect operations."""

    def __init__(self, parser_context: Optional[Any] = None):
        """Initialize parser with optional context.

        Args:
            parser_context: Reference to the main MLIRParser instance
                           for accessing shared utilities and state.
        """
        import sys

        print(
            f"[LinalgDialectParser] Initializing with context={parser_context}",
            file=sys.stderr,
        )
        super().__init__(parser_context)

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a linalg operation.

        Dispatches to appropriate parser based on operation class.
        """
        import sys

        print(
            f"[LinalgDialectParser] parse_operation called for {op_node}",
            file=sys.stderr,
        )
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__
            # Debug
            print(f"[LinalgDialectParser] Trying to parse {class_name}", file=sys.stderr)

            # Map operation class names to parser methods
            if class_name == "LinalgGeneric":
                return self._parse_linalg_generic_operation(op_node)
            elif class_name == "LinalgMatmul":
                return self._parse_linalg_matmul_operation(op_node)
            elif class_name == "LinalgBatchMatmul":
                return self._parse_linalg_batch_matmul_operation(op_node)
            elif class_name == "LinalgConv1D":
                return self._parse_linalg_conv_1d_operation(op_node)
            elif class_name == "LinalgConv2D":
                return self._parse_linalg_conv_2d_operation(op_node)
            elif class_name == "LinalgYield":
                return self._parse_linalg_yield_operation(op_node)
            # Add other linalg operations as needed

        # No handler found
        return None

    # Methods for base class's parse_operation fallback (pattern: parse_{Classname})
    def parse_LinalgGeneric(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse LinalgGeneric operation (called by base class pattern)."""
        import sys

        print(f"[LinalgDialectParser] parse_LinalgGeneric called", file=sys.stderr)
        return self._parse_linalg_generic_operation(op_node)

    def parse_LinalgMatmul(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse LinalgMatmul operation (called by base class pattern)."""
        import sys

        print(f"[LinalgDialectParser] parse_LinalgMatmul called", file=sys.stderr)
        return self._parse_linalg_matmul_operation(op_node)

    def parse_LinalgBatchMatmul(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse LinalgBatchMatmul operation (called by base class pattern)."""
        import sys

        print(f"[LinalgDialectParser] parse_LinalgBatchMatmul called", file=sys.stderr)
        return self._parse_linalg_batch_matmul_operation(op_node)

    def parse_LinalgYield(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse LinalgYield operation (called by base class pattern)."""
        import sys

        print(f"[LinalgDialectParser] parse_LinalgYield called", file=sys.stderr)
        return self._parse_linalg_yield_operation(op_node)

    # Individual operation parsers
    def _parse_linalg_generic_operation(
        self, op_node: mast.Operation
    ) -> Optional[LinalgGenericOperation]:
        """Parse linalg.generic operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract inputs and outputs based on old parser
        inputs = []
        input_types = []
        outputs = []
        output_types = []

        if hasattr(op_obj, "inargs") and op_obj.inargs:
            inputs = [arg.value if hasattr(arg, "value") else str(arg) for arg in op_obj.inargs]
            input_types = [self._type_to_string(t) for t in op_obj.in_types]

        # Extract output arguments (could be outargs or init_args)
        if hasattr(op_obj, "outargs") and op_obj.outargs:
            outputs = [arg.value if hasattr(arg, "value") else str(arg) for arg in op_obj.outargs]
            output_types = [self._type_to_string(t) for t in op_obj.out_types]
        elif hasattr(op_obj, "init_args") and op_obj.init_args:
            outputs = [arg.value if hasattr(arg, "value") else str(arg) for arg in op_obj.init_args]
            output_types = [self._type_to_string(t) for t in op_obj.init_types]

        # Extract attributes
        attributes = {}
        if hasattr(op_obj, "attr") and op_obj.attr:
            # Convert attributes to dict using base parser method
            attributes = self._parse_attribute(op_obj.attr)
            if not isinstance(attributes, dict):
                # If not a dict, wrap in dict or handle appropriately
                attributes = {"value": attributes}

        # Parse region body if present
        body_ops = []
        block_args = []
        block_arg_types = []
        if hasattr(op_obj, "region") and op_obj.region and op_obj.region.body:
            # Generic op has a single block with block arguments
            for block in op_obj.region.body:
                # Block arguments are the iteration variables (stored in block label)
                if (
                    hasattr(block, "label")
                    and block.label
                    and hasattr(block.label, "arg_ids")
                    and block.label.arg_ids
                    and hasattr(block.label, "arg_types")
                    and block.label.arg_types
                ):
                    block_args = [
                        arg.value if hasattr(arg, "value") else str(arg)
                        for arg in block.label.arg_ids
                    ]
                    block_arg_types = [
                        self._type_to_string(arg_type) for arg_type in block.label.arg_types
                    ]

                # Parse operations in the block
                if hasattr(block, "body"):
                    for body_op in block.body:
                        # Use parser context to parse operation
                        if self.parser_context:
                            parsed = self.parser_context._parse_operation(body_op)
                            if parsed:
                                body_ops.append(parsed)

        # Extract indexing maps and iterator types from attributes
        indexing_maps = []
        iterator_types = []
        if isinstance(attributes, dict) and "indexing_maps" in attributes:
            indexing_maps = attributes["indexing_maps"]
        if isinstance(attributes, dict) and "iterator_types" in attributes:
            iterator_types = attributes["iterator_types"]

        # Extract result type
        result_type = None
        if hasattr(op_obj, "out_type") and op_obj.out_type:
            result_type = self._type_to_string(op_obj.out_type)

        line = self._extract_line_number(op_node)

        return LinalgGenericOperation(
            dialect="linalg",
            name="generic",
            line=line,
            dest=dest or "",
            result_type=result_type,
            inputs=inputs,
            input_types=input_types,
            outputs=outputs,
            output_types=output_types,
            attributes=attributes,
            body=body_ops,
            block_args=block_args,
            block_arg_types=block_arg_types,
            indexing_maps=indexing_maps,
            iterator_types=iterator_types,
        )

    def _parse_linalg_matmul_operation(
        self, op_node: mast.Operation
    ) -> Optional[LinalgMatmulOperation]:
        """Parse linalg.matmul operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract A, B, C operands based on old parser
        A = ""
        B = ""
        C = ""
        A_type = ""
        B_type = ""
        C_type = ""

        if hasattr(op_obj, "a_id"):
            A = op_obj.a_id.value if hasattr(op_obj.a_id, "value") else str(op_obj.a_id)
            B = op_obj.b_id.value if hasattr(op_obj.b_id, "value") else str(op_obj.b_id)
            C = op_obj.c_id.value if hasattr(op_obj.c_id, "value") else str(op_obj.c_id)

        # Extract types
        if hasattr(op_obj, "a_type"):
            A_type = self._type_to_string(op_obj.a_type)
            B_type = self._type_to_string(op_obj.b_type)
            C_type = self._type_to_string(op_obj.c_type)

        # Extract result type
        result_type = None
        if hasattr(op_obj, "out_type") and op_obj.out_type:
            result_type = self._type_to_string(op_obj.out_type)

        line = self._extract_line_number(op_node)

        return LinalgMatmulOperation(
            dialect="linalg",
            name="matmul",
            line=line,
            dest=dest or "",
            result_type=result_type,
            A=A,
            B=B,
            C=C,
            A_type=A_type,
            B_type=B_type,
            C_type=C_type,
        )

    def _parse_linalg_batch_matmul_operation(
        self, op_node: mast.Operation
    ) -> Optional[LinalgBatchMatmulOperation]:
        """Parse linalg.batch_matmul operation."""
        # For now, treat as matmul operation since structure is similar
        # The old parser has a stub for batch_matmul
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract A, B, C operands - batch_matmul might have same structure as matmul
        A = ""
        B = ""
        C = ""
        A_type = ""
        B_type = ""
        C_type = ""

        # Try to use matmul fields first
        if hasattr(op_obj, "a_id"):
            A = op_obj.a_id.value if hasattr(op_obj.a_id, "value") else str(op_obj.a_id)
            B = op_obj.b_id.value if hasattr(op_obj.b_id, "value") else str(op_obj.b_id)
            C = op_obj.c_id.value if hasattr(op_obj.c_id, "value") else str(op_obj.c_id)

        # Extract types
        if hasattr(op_obj, "a_type"):
            A_type = self._type_to_string(op_obj.a_type)
            B_type = self._type_to_string(op_obj.b_type)
            C_type = self._type_to_string(op_obj.c_type)

        # Extract result type
        result_type = None
        if hasattr(op_obj, "out_type") and op_obj.out_type:
            result_type = self._type_to_string(op_obj.out_type)

        line = self._extract_line_number(op_node)

        return LinalgBatchMatmulOperation(
            dialect="linalg",
            name="batch_matmul",
            line=line,
            dest=dest or "",
            result_type=result_type,
            A=A,
            B=B,
            C=C,
            A_type=A_type,
            B_type=B_type,
            C_type=C_type,
        )

    def _parse_linalg_conv_1d_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse linalg.conv_1d operation."""
        # For now, treat as generic operation
        return self._parse_linalg_generic_operation(op_node)

    def _parse_linalg_conv_2d_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse linalg.conv_2d operation."""
        # For now, treat as generic operation
        return self._parse_linalg_generic_operation(op_node)

    def _parse_linalg_yield_operation(
        self, op_node: mast.Operation
    ) -> Optional[LinalgYieldOperation]:
        """Parse linalg.yield operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        # Extract yield values based on old parser
        values = []
        types = []

        if hasattr(op_obj, "operand_ids") and op_obj.operand_ids:
            values = [
                operand.value if hasattr(operand, "value") else str(operand)
                for operand in op_obj.operand_ids
            ]
            types = [self._type_to_string(t) for t in op_obj.operand_types]

        line = self._extract_line_number(op_node)

        return LinalgYieldOperation(
            dialect="linalg",
            name="yield",
            line=line,
            dest=dest or "",
            result_type=None,
            values=values,
            types=types,
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

    def _attribute_to_string(self, attr_value) -> str:
        """Convert attribute value to string representation."""
        if isinstance(attr_value, str):
            return attr_value
        elif hasattr(attr_value, "dump"):
            return attr_value.dump()
        else:
            return str(attr_value)
