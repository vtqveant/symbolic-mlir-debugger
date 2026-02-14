#!/usr/bin/env python3
"""
Memref dialect parser.

Converts pymlir AST nodes for memref operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any
import dataclasses

import parser.astnodes as mast
from .base import BaseDialectParser
from ..operations import (
    Operation,
    LoadOperation,
    StoreOperation,
    ReinterpretCastOperation,
    MemoryOperation,
)


class MemrefDialectParser(BaseDialectParser):
    """Parser for memref dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a memref operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Map operation class names to parser methods
            if class_name == "MemRefLoadOp":
                return self._parse_load_operation(op_node)
            elif class_name == "MemRefStoreOp":
                return self._parse_store_operation(op_node)
            elif class_name == "MemRefDimOp":
                return self._parse_dim_operation(op_node)
            elif class_name == "MemRefAllocOp":
                return self._parse_alloc_operation(op_node)
            elif class_name == "MemRefAllocaOp":
                return self._parse_alloca_operation(op_node)
            elif class_name == "MemRefDeallocOp":
                return self._parse_dealloc_operation(op_node)
            elif class_name == "MemRefSubviewOp":
                return self._parse_subview_operation(op_node)
            elif class_name == "MemRefViewOp":
                return self._parse_view_operation(op_node)
            elif class_name == "MemRefCastOp":
                return self._parse_cast_operation(op_node)
            elif class_name == "MemRefCollapseShapeOp":
                return self._parse_collapse_shape_operation(op_node)
            elif class_name == "MemRefExpandShapeOp":
                return self._parse_expand_shape_operation(op_node)
            elif class_name == "MemRefReinterpretCastOp":
                return self._parse_reinterpret_cast_operation(op_node)
            elif class_name == "MemRefMemorySpaceCastOp":
                return self._parse_memory_space_cast_operation(op_node)
            elif class_name == "MemRefDmaStartOp":
                return self._parse_dma_start_operation(op_node)
            elif class_name == "MemRefDmaWaitOp":
                return self._parse_dma_wait_operation(op_node)

        # No handler found
        return None

    # Individual operation parsers
    def _parse_load_operation(self, op_node: mast.Operation) -> Optional[LoadOperation]:
        """Parse memref.load operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract memref and indices
        memref = self._ssa_use_to_string(op_obj.arg)
        indices = [self._ssa_use_to_string(idx) for idx in op_obj.index]

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return LoadOperation(
            dialect="memref",
            name="load",
            line=line,
            dest=dest,
            result_type=result_type,
            memref=memref,
            indices=indices,
            attributes={},
        )

    def _parse_store_operation(
        self, op_node: mast.Operation
    ) -> Optional[StoreOperation]:
        """Parse memref.store operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # Note: store may not have a destination (void result)
        # Use empty string for dest if not present

        # Extract fields (note: pymlir's StoreOperation has memref, value, index)
        memref = self._ssa_use_to_string(op_obj.memref)
        value = self._ssa_use_to_string(op_obj.value)
        indices = [self._ssa_use_to_string(idx) for idx in op_obj.index]

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return StoreOperation(
            dialect="memref",
            name="store",
            line=line,
            dest=dest or "",  # store is void, dest may be empty
            result_type=result_type,
            memref=memref,
            indices=indices,
            value=value,
            attributes={},
        )

    def _parse_dim_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse memref.dim operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = self._ssa_use_to_string(op_obj.operand)
        index = self._ssa_use_to_string(op_obj.index)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # Create generic Operation with custom attributes
        return Operation(
            dialect="memref",
            name="dim",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "operand": operand,
                "index": index,
            },
        )

    def _parse_alloc_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse memref.alloc operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract args (dimensions)
        args = self._ssa_use_to_string(op_obj.args)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="alloc",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "args": args,
            },
        )

    def _parse_alloca_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse memref.alloca operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        args = self._ssa_use_to_string(op_obj.args)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="alloca",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "args": args,
            },
        )

    def _parse_dealloc_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse memref.dealloc operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # dealloc may not have a destination (void)

        arg = self._ssa_use_to_string(op_obj.arg)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="dealloc",
            line=line,
            dest=dest or "",
            result_type=result_type,
            attributes={
                "arg": arg,
            },
        )

    def _parse_subview_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse memref.subview operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = self._ssa_use_to_string(op_obj.operand)
        offsets = [self._ssa_use_to_string(off) for off in op_obj.offsets]
        sizes = [self._ssa_use_to_string(sz) for sz in op_obj.sizes]
        strides = [self._ssa_use_to_string(st) for st in op_obj.strides]

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="subview",
            line=line,
            dest=dest,
            result_type=dst_type,
            attributes={
                "operand": operand,
                "offsets": offsets,
                "sizes": sizes,
                "strides": strides,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_view_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse memref.view operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = self._ssa_use_to_string(op_obj.operand)
        offset = self._ssa_use_to_string(op_obj.offset)

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        sizes = []
        if hasattr(op_obj, "sizes") and op_obj.sizes is not None:
            sizes = [self._ssa_use_to_string(sz) for sz in op_obj.sizes]

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="view",
            line=line,
            dest=dest,
            result_type=dst_type,
            attributes={
                "operand": operand,
                "offset": offset,
                "sizes": sizes,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_cast_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse memref.cast operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        arg = self._ssa_use_to_string(op_obj.arg)

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="cast",
            line=line,
            dest=dest,
            result_type=dst_type,
            attributes={
                "arg": arg,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_collapse_shape_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse memref.collapse_shape operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = self._ssa_use_to_string(op_obj.operand)

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="collapse_shape",
            line=line,
            dest=dest,
            result_type=dst_type,
            attributes={
                "operand": operand,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_expand_shape_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse memref.expand_shape operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = self._ssa_use_to_string(op_obj.operand)

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="expand_shape",
            line=line,
            dest=dest,
            result_type=dst_type,
            attributes={
                "operand": operand,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_reinterpret_cast_operation(
        self, op_node: mast.Operation
    ) -> Optional[ReinterpretCastOperation]:
        """Parse memref.reinterpret_cast operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = self._ssa_use_to_string(op_obj.operand)
        offsets = [self._ssa_use_to_string(off) for off in op_obj.offsets]
        sizes = [self._ssa_use_to_string(sz) for sz in op_obj.sizes]
        strides = [self._ssa_use_to_string(st) for st in op_obj.strides]

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        line = self._extract_line_number(op_node)

        return ReinterpretCastOperation(
            dialect="memref",
            name="reinterpret_cast",
            line=line,
            dest=dest,
            result_type=dst_type,
            operand=operand,
            offsets=offsets,
            sizes=sizes,
            strides=strides,
            src_type=src_type,
            dst_type=dst_type,
            attributes={},
        )

    def _parse_memory_space_cast_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse memref.memory_space_cast operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        operand = self._ssa_use_to_string(op_obj.operand)

        src_type = None
        dst_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="memory_space_cast",
            line=line,
            dest=dest,
            result_type=dst_type,
            attributes={
                "operand": operand,
                "src_type": src_type,
                "dst_type": dst_type,
            },
        )

    def _parse_dma_start_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse memref.dma_start operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # dma_start may not have a destination

        src = self._ssa_use_to_string(op_obj.src)
        src_index = [self._ssa_use_to_string(idx) for idx in op_obj.src_index]
        dst = self._ssa_use_to_string(op_obj.dst)
        dst_index = [self._ssa_use_to_string(idx) for idx in op_obj.dst_index]
        size = self._ssa_use_to_string(op_obj.size)
        tag = self._ssa_use_to_string(op_obj.tag)
        tag_index = [self._ssa_use_to_string(idx) for idx in op_obj.tag_index]

        src_type = None
        dst_type = None
        tag_type = None
        if hasattr(op_obj, "src_type"):
            src_type = self._type_to_string(op_obj.src_type)
        if hasattr(op_obj, "dst_type"):
            dst_type = self._type_to_string(op_obj.dst_type)
        if hasattr(op_obj, "tag_type"):
            tag_type = self._type_to_string(op_obj.tag_type)

        attributes = {
            "src": src,
            "src_index": src_index,
            "dst": dst,
            "dst_index": dst_index,
            "size": size,
            "tag": tag,
            "tag_index": tag_index,
            "src_type": src_type,
            "dst_type": dst_type,
            "tag_type": tag_type,
        }

        # Optional fields
        if hasattr(op_obj, "stride") and op_obj.stride is not None:
            attributes["stride"] = self._ssa_use_to_string(op_obj.stride)
        if (
            hasattr(op_obj, "transfer_per_stride")
            and op_obj.transfer_per_stride is not None
        ):
            attributes["transfer_per_stride"] = self._ssa_use_to_string(
                op_obj.transfer_per_stride
            )

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="dma_start",
            line=line,
            dest=dest or "",
            result_type=None,
            attributes=attributes,
        )

    def _parse_dma_wait_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse memref.dma_wait operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)

        tag = self._ssa_use_to_string(op_obj.tag)
        tag_index = [self._ssa_use_to_string(idx) for idx in op_obj.tag_index]
        size = self._ssa_use_to_string(op_obj.size)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="memref",
            name="dma_wait",
            line=line,
            dest=dest or "",
            result_type=result_type,
            attributes={
                "tag": tag,
                "tag_index": tag_index,
                "size": size,
            },
        )
