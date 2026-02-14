#!/usr/bin/env python3
"""
Bufferization dialect parser.

Converts pymlir AST nodes for bufferization operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any, List
import dataclasses

import parser.astnodes as mast
from .base import BaseDialectParser
from ..operations import Operation, UnaryOperation


class BufferizationDialectParser(BaseDialectParser):
    """Parser for bufferization dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a bufferization operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            if class_name == "BufferizationAllocTensorOp":
                return self._parse_alloc_tensor_operation(op_node)
            elif class_name == "BufferizationCloneOp":
                return self._parse_clone_operation(op_node)
            elif class_name == "BufferizationDeallocOp":
                return self._parse_dealloc_operation(op_node)
            elif class_name == "BufferizationDeallocTensorOp":
                return self._parse_dealloc_tensor_operation(op_node)
            elif class_name == "BufferizationMaterializeInDestinationOp":
                return self._parse_materialize_in_destination_operation(op_node)
            elif class_name == "BufferizationToBufferOp":
                return self._parse_to_buffer_operation(op_node)
            elif class_name == "BufferizationToTensorOp":
                return self._parse_to_tensor_operation(op_node)

        return None

    def _parse_alloc_tensor_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse bufferization.alloc_tensor operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract shape operands
        shape = []
        if hasattr(op_obj, "shape"):
            shape = [self._ssa_use_to_string(s) for s in op_obj.shape]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="bufferization",
            name="alloc_tensor",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "shape": shape,
            },
        )

    def _parse_clone_operation(
        self, op_node: mast.Operation
    ) -> Optional[UnaryOperation]:
        """Parse bufferization.clone operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = None
        if hasattr(op_obj, "src"):
            operand = self._ssa_use_to_string(op_obj.src)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return UnaryOperation(
            dialect="bufferization",
            name="clone",
            line=line,
            dest=dest,
            result_type=result_type,
            operand=operand,
            attributes={},
        )

    def _parse_dealloc_operation(
        self, op_node: mast.Operation
    ) -> Optional[UnaryOperation]:
        """Parse bufferization.dealloc operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # dealloc may not have a destination (void)
        # Still need to parse

        operand = None
        if hasattr(op_obj, "buffer"):
            operand = self._ssa_use_to_string(op_obj.buffer)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # dealloc is a unary operation that doesn't produce a result
        # Use UnaryOperation with dest=None
        return UnaryOperation(
            dialect="bufferization",
            name="dealloc",
            line=line,
            dest=dest,  # may be None
            result_type=result_type,
            operand=operand,
            attributes={},
        )

    def _parse_dealloc_tensor_operation(
        self, op_node: mast.Operation
    ) -> Optional[UnaryOperation]:
        """Parse bufferization.dealloc_tensor operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        operand = None
        if hasattr(op_obj, "tensor"):
            operand = self._ssa_use_to_string(op_obj.tensor)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return UnaryOperation(
            dialect="bufferization",
            name="dealloc_tensor",
            line=line,
            dest=dest,
            result_type=result_type,
            operand=operand,
            attributes={},
        )

    def _parse_materialize_in_destination_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse bufferization.materialize_in_destination operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        src = None
        dst = None
        if hasattr(op_obj, "src"):
            src = self._ssa_use_to_string(op_obj.src)
        if hasattr(op_obj, "dst"):
            dst = self._ssa_use_to_string(op_obj.dst)

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        result_type = dst_type

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="bufferization",
            name="materialize_in_destination",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "src": src,
                "dst": dst,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_to_buffer_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse bufferization.to_buffer operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = None
        if hasattr(op_obj, "tensor"):
            operand = self._ssa_use_to_string(op_obj.tensor)

        tensor_type = None
        buffer_type = None
        if hasattr(op_obj, "tensor_type"):
            tensor_type = self._type_to_string(op_obj.tensor_type)
        if hasattr(op_obj, "buffer_type"):
            buffer_type = self._type_to_string(op_obj.buffer_type)

        result_type = buffer_type

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="bufferization",
            name="to_buffer",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "operand": operand,
                "tensor_type": tensor_type,
                "buffer_type": buffer_type,
            },
        )

    def _parse_to_tensor_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse bufferization.to_tensor operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = None
        if hasattr(op_obj, "buffer"):
            operand = self._ssa_use_to_string(op_obj.buffer)

        buffer_type = None
        tensor_type = None
        if hasattr(op_obj, "buffer_type"):
            buffer_type = self._type_to_string(op_obj.buffer_type)
        if hasattr(op_obj, "tensor_type"):
            tensor_type = self._type_to_string(op_obj.tensor_type)

        result_type = tensor_type

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="bufferization",
            name="to_tensor",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "operand": operand,
                "buffer_type": buffer_type,
                "tensor_type": tensor_type,
            },
        )
