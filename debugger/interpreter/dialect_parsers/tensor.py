#!/usr/bin/env python3
"""
Tensor dialect parser.

Converts pymlir AST nodes for tensor operations directly to
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
    UnaryOperation,
    ConstantOperation,
)


class TensorDialectParser(BaseDialectParser):
    """Parser for tensor dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a tensor operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Map operation class names to parser methods
            if class_name == "ExtractOperation":
                return self._parse_extract_operation(op_node)
            elif class_name == "InsertOperation":
                return self._parse_insert_operation(op_node)
            elif class_name == "SplatOperation":
                return self._parse_splat_operation(op_node)
            elif class_name == "LoadOperation":
                return self._parse_load_operation(op_node)
            elif class_name == "StoreOperation":
                return self._parse_store_operation(op_node)
            elif class_name == "CastOperation":
                return self._parse_cast_operation(op_node)
            elif class_name == "BitcastOperation":
                return self._parse_bitcast_operation(op_node)
            elif class_name == "CollapseShapeOperation":
                return self._parse_collapse_shape_operation(op_node)
            elif class_name == "ExpandShapeOperation":
                return self._parse_expand_shape_operation(op_node)
            elif class_name == "DimOperation":
                return self._parse_dim_operation(op_node)
            elif class_name == "EmptyOperation":
                return self._parse_empty_operation(op_node)
            elif class_name == "ExtractSliceOperation":
                return self._parse_extract_slice_operation(op_node)
            elif class_name == "InsertSliceOperation":
                return self._parse_insert_slice_operation(op_node)
            elif class_name == "FromElementsOperation":
                return self._parse_from_elements_operation(op_node)
            elif class_name == "GenerateOperation":
                return self._parse_generate_operation(op_node)
            elif class_name == "PadOperation":
                return self._parse_pad_operation(op_node)
            elif class_name == "RankOperation":
                return self._parse_rank_operation(op_node)
            elif class_name == "ReshapeOperation":
                return self._parse_reshape_operation(op_node)
            elif class_name == "ScatterOperation":
                return self._parse_scatter_operation(op_node)
            elif class_name == "GatherOperation":
                return self._parse_gather_operation(op_node)
            elif class_name == "YieldOperation":
                return self._parse_yield_operation(op_node)
            elif class_name == "ConcatOperation":
                return self._parse_concat_operation(op_node)

        # No handler found
        return None

    # Individual operation parsers
    def _parse_extract_operation(
        self, op_node: mast.Operation
    ) -> Optional[LoadOperation]:
        """Parse tensor.extract operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract tensor and indices
        tensor = self._ssa_use_to_string(op_obj.arg)
        indices = [self._ssa_use_to_string(idx) for idx in op_obj.index]

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return LoadOperation(
            dialect="tensor",
            name="extract",
            line=line,
            dest=dest,
            result_type=result_type,
            memref=tensor,
            indices=indices,
            attributes={},
        )

    def _parse_insert_operation(
        self, op_node: mast.Operation
    ) -> Optional[StoreOperation]:
        """Parse tensor.insert operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract fields (note: pymlir's InsertOperation has src, dst, index)
        # Based on _parse_tensor_insert_op in parser.py
        src = self._ssa_use_to_string(op_obj.src)
        dst = self._ssa_use_to_string(op_obj.dst)
        indices = [self._ssa_use_to_string(idx) for idx in op_obj.index]

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return StoreOperation(
            dialect="tensor",
            name="insert",
            line=line,
            dest=dest,
            result_type=result_type,
            memref=dst,
            indices=indices,
            value=src,
            attributes={},
        )

    def _parse_splat_operation(
        self, op_node: mast.Operation
    ) -> Optional[UnaryOperation]:
        """Parse tensor.splat operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operand
        operand = self._ssa_use_to_string(op_obj.arg)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # Check for dynamic_sizes attribute
        attributes = {}
        if hasattr(op_obj, "dynamic_sizes") and op_obj.dynamic_sizes is not None:
            attributes["dynamic_sizes"] = [
                self._ssa_use_to_string(sz) for sz in op_obj.dynamic_sizes
            ]

        return UnaryOperation(
            dialect="tensor",
            name="splat",
            line=line,
            dest=dest,
            result_type=result_type,
            operand=operand,
            attributes=attributes,
        )

    def _parse_load_operation(self, op_node: mast.Operation) -> Optional[LoadOperation]:
        """Parse tensor.load operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract tensor (arg)
        tensor = self._ssa_use_to_string(op_obj.arg)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # tensor.load has no indices? Might have indices attribute.
        # Use empty indices list
        return LoadOperation(
            dialect="tensor",
            name="load",
            line=line,
            dest=dest,
            result_type=result_type,
            memref=tensor,
            indices=[],
            attributes={},
        )

    def _parse_store_operation(
        self, op_node: mast.Operation
    ) -> Optional[StoreOperation]:
        """Parse tensor.store operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # store may not have a destination

        # Extract args (args field)
        args = self._ssa_use_to_string(op_obj.args)

        # Extract type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # tensor.store is more complex; for now create generic Operation
        # with args attribute
        return Operation(
            dialect="tensor",
            name="store",
            line=line,
            dest=dest or "",
            result_type=result_type,
            attributes={
                "args": args,
            },
        )

    def _parse_cast_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.cast operation."""
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
            dialect="tensor",
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

    def _parse_bitcast_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.bitcast operation."""
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
            dialect="tensor",
            name="bitcast",
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
        """Parse tensor.collapse_shape operation."""
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
            dialect="tensor",
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
        """Parse tensor.expand_shape operation."""
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
            dialect="tensor",
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

    def _parse_dim_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.dim operation."""
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

        return Operation(
            dialect="tensor",
            name="dim",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={
                "operand": operand,
                "index": index,
            },
        )

    def _parse_empty_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.empty operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # No additional fields? Maybe dimensions.
        return Operation(
            dialect="tensor",
            name="empty",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={},
        )

    # Stub implementations for remaining operations (to be filled)
    def _parse_extract_slice_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse tensor.extract_slice operation."""
        return self._generic_operation(op_node, "extract_slice")

    def _parse_insert_slice_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse tensor.insert_slice operation."""
        return self._generic_operation(op_node, "insert_slice")

    def _parse_from_elements_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse tensor.from_elements operation."""
        return self._generic_operation(op_node, "from_elements")

    def _parse_generate_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.generate operation."""
        return self._generic_operation(op_node, "generate")

    def _parse_pad_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.pad operation."""
        return self._generic_operation(op_node, "pad")

    def _parse_rank_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.rank operation."""
        return self._generic_operation(op_node, "rank")

    def _parse_reshape_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.reshape operation."""
        return self._generic_operation(op_node, "reshape")

    def _parse_scatter_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.scatter operation."""
        return self._generic_operation(op_node, "scatter")

    def _parse_gather_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.gather operation."""
        return self._generic_operation(op_node, "gather")

    def _parse_yield_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.yield operation."""
        return self._generic_operation(op_node, "yield")

    def _parse_concat_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse tensor.concat operation."""
        return self._generic_operation(op_node, "concat")

    def _generic_operation(
        self, op_node: mast.Operation, name: str
    ) -> Optional[Operation]:
        """Generic fallback for tensor operations."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # dest may be empty for void ops

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # Collect all attributes from op_obj
        attributes = {}
        for attr_name in dir(op_obj):
            if not attr_name.startswith("_"):
                attr_value = getattr(op_obj, attr_name)
                # Skip callable attributes
                if not callable(attr_value):
                    # Convert SSA uses to strings
                    if isinstance(attr_value, mast.SsaId):
                        attributes[attr_name] = self._ssa_use_to_string(attr_value)
                    elif isinstance(attr_value, list):
                        # Try to convert each element
                        converted = []
                        for elem in attr_value:
                            if isinstance(elem, mast.SsaId):
                                converted.append(self._ssa_use_to_string(elem))
                            else:
                                converted.append(str(elem))
                        attributes[attr_name] = converted
                    else:
                        attributes[attr_name] = str(attr_value)

        return Operation(
            dialect="tensor",
            name=name,
            line=line,
            dest=dest or "",
            result_type=result_type,
            attributes=attributes,
        )
