#!/usr/bin/env python3
"""
Vector dialect parser.

Converts pymlir AST nodes for vector operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional

import parser.astnodes as mast

from .base import BaseDialectParser
from ..operations import Operation, BinaryOperation, UnaryOperation, ConstantOperation


class VectorDialectParser(BaseDialectParser):
    """Parser for vector dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a vector operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Special handling for constant mask operation (has mask_dimensions)
            if class_name == "VectorConstantMaskOp":
                return self._parse_constant_mask_operation(op_node)
            # Special handling for constant-like operations with value field
            elif class_name == "VectorConstantMaskOp":
                # Already handled above
                pass
            # Special handling for contract operation (complex attributes)
            elif class_name == "VectorContractOp":
                return self._parse_contract_operation(op_node)
            # Special handling for gather operation (complex)
            elif class_name == "VectorGatherOp":
                return self._parse_gather_operation(op_node)
            # Special handling for compress store (store-like)
            elif class_name == "VectorCompressStoreOp":
                return self._parse_compress_store_operation(op_node)
            # Special handling for expand load (load-like)
            elif class_name == "VectorExpandLoadOp":
                return self._parse_expand_load_operation(op_node)
            # Special handling for extract strided slice (complex)
            elif class_name == "VectorExtractStridedSliceOp":
                return self._parse_extract_strided_slice_operation(op_node)
            # Special handling for insert strided slice (complex)
            elif class_name == "VectorInsertStridedSliceOp":
                return self._parse_insert_strided_slice_operation(op_node)
            # Special handling for fma (ternary)
            elif class_name == "VectorFmaOp":
                return self._parse_fma_operation(op_node)

            # Binary operations (InterleaveOperation has lhs, rhs)
            elif class_name.endswith("Op") and hasattr(op_obj, "lhs") and hasattr(op_obj, "rhs"):
                return self._parse_binary_operation(op_node)

            # Unary operations (BroadcastOperation, DeinterleaveOperation have source)
            elif class_name.endswith("Op") and hasattr(op_obj, "source"):
                return self._parse_unary_operation(op_node)

            # Unary operations with operand field
            elif class_name.endswith("Op") and hasattr(op_obj, "operand"):
                return self._parse_unary_operation(op_node)

            # Operations with vector field (ExtractOperation)
            elif class_name.endswith("Op") and hasattr(op_obj, "vector"):
                return self._parse_generic_operation(op_node)

            # Operations with elements field (FromElementsOperation)
            elif class_name.endswith("Op") and hasattr(op_obj, "elements"):
                return self._parse_generic_operation(op_node)

            # Operations with base field (CompressStore, ExpandLoad already handled)
            # Generic fallback
            else:
                return self._parse_generic_operation(op_node)

        return None

    def _parse_binary_operation(self, op_node: mast.Operation) -> Optional[BinaryOperation]:
        """Parse binary vector operation (interleave, etc.)."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operation name
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"vector.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "vector"
            name = full_name

        lhs = self._ssa_use_to_string(op_obj.lhs)
        rhs = self._ssa_use_to_string(op_obj.rhs)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)
        elif hasattr(op_obj, "result_type"):
            result_type = self._type_to_string(op_obj.result_type)

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

    def _parse_unary_operation(self, op_node: mast.Operation) -> Optional[UnaryOperation]:
        """Parse unary vector operation (broadcast, deinterleave, etc.)."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"vector.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "vector"
            name = full_name

        # Determine operand field: source, operand, or vector
        operand = None
        if hasattr(op_obj, "source"):
            operand = self._ssa_use_to_string(op_obj.source)
        elif hasattr(op_obj, "operand"):
            operand = self._ssa_use_to_string(op_obj.operand)
        elif hasattr(op_obj, "vector"):
            operand = self._ssa_use_to_string(op_obj.vector)
        else:
            # Fallback: use first field that is SSA use? For now generic
            return self._parse_generic_operation(op_node)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)
        elif hasattr(op_obj, "result_type"):
            result_type = self._type_to_string(op_obj.result_type)

        line = self._extract_line_number(op_node)

        return UnaryOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            operand=operand,
            attributes={},
        )

    def _parse_constant_mask_operation(
        self, op_node: mast.Operation
    ) -> Optional[ConstantOperation]:
        """Parse vector.constant_mask operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract mask dimensions list
        value = None
        if hasattr(op_obj, "mask_dimensions"):
            value = op_obj.mask_dimensions  # list of ints

        result_type = None
        if hasattr(op_obj, "result_type"):
            result_type = self._type_to_string(op_obj.result_type)

        line = self._extract_line_number(op_node)

        return ConstantOperation(
            dialect="vector",
            name="constant_mask",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )

    def _parse_contract_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse vector.contract operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract fields
        attributes = {}
        fields = [
            "lhs",
            "rhs",
            "acc",
            "indexing_maps",
            "iterator_types",
            "lhs_type",
            "rhs_type",
            "acc_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op_obj, field):
                value = getattr(op_obj, field)
                if isinstance(value, list):
                    if field == "iterator_types" and isinstance(value[0], str):
                        attributes[field] = value
                    else:
                        attributes[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    attributes[field] = self._type_to_string(value)
                else:
                    attributes[field] = self._ssa_use_to_string(value)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="vector",
            name="contract",
            line=line,
            dest=dest,
            result_type=attributes.get("result_type"),
            attributes=attributes,
        )

    def _parse_gather_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse vector.gather operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        attributes = {}
        fields = [
            "base",
            "indices",
            "index_vec",
            "mask",
            "pass_thru",
            "base_type",
            "index_vec_type",
            "mask_type",
            "pass_thru_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op_obj, field):
                value = getattr(op_obj, field)
                if isinstance(value, list):
                    attributes[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    attributes[field] = self._type_to_string(value)
                else:
                    attributes[field] = self._ssa_use_to_string(value)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="vector",
            name="gather",
            line=line,
            dest=dest,
            result_type=attributes.get("result_type"),
            attributes=attributes,
        )

    def _parse_compress_store_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse vector.compressstore operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        attributes = {}
        fields = [
            "base",
            "indices",
            "mask",
            "value",
            "base_type",
            "mask_type",
            "value_type",
        ]
        for field in fields:
            if hasattr(op_obj, field):
                value = getattr(op_obj, field)
                if isinstance(value, list):
                    attributes[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    attributes[field] = self._type_to_string(value)
                else:
                    attributes[field] = self._ssa_use_to_string(value)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="vector",
            name="compressstore",
            line=line,
            dest=dest,
            result_type=None,  # store has no result
            attributes=attributes,
        )

    def _parse_expand_load_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse vector.expandload operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        attributes = {}
        fields = [
            "base",
            "indices",
            "mask",
            "pass_thru",
            "base_type",
            "mask_type",
            "pass_thru_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op_obj, field):
                value = getattr(op_obj, field)
                if isinstance(value, list):
                    attributes[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    attributes[field] = self._type_to_string(value)
                else:
                    attributes[field] = self._ssa_use_to_string(value)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="vector",
            name="expandload",
            line=line,
            dest=dest,
            result_type=attributes.get("result_type"),
            attributes=attributes,
        )

    def _parse_extract_strided_slice_operation(
        self, op_node: mast.Operation
    ) -> Optional[Operation]:
        """Parse vector.extract_strided_slice operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        attributes = {}
        fields = ["vector", "offsets", "sizes", "strides", "vector_type", "result_type"]
        for field in fields:
            if hasattr(op_obj, field):
                value = getattr(op_obj, field)
                if isinstance(value, list):
                    attributes[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    attributes[field] = self._type_to_string(value)
                else:
                    attributes[field] = self._ssa_use_to_string(value)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="vector",
            name="extract_strided_slice",
            line=line,
            dest=dest,
            result_type=attributes.get("result_type"),
            attributes=attributes,
        )

    def _parse_insert_strided_slice_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse vector.insert_strided_slice operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        attributes = {}
        fields = [
            "source",
            "dest",
            "offsets",
            "strides",
            "source_type",
            "dest_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op_obj, field):
                value = getattr(op_obj, field)
                if isinstance(value, list):
                    attributes[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    attributes[field] = self._type_to_string(value)
                else:
                    attributes[field] = self._ssa_use_to_string(value)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="vector",
            name="insert_strided_slice",
            line=line,
            dest=dest,
            result_type=attributes.get("result_type"),
            attributes=attributes,
        )

    def _parse_fma_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse vector.fma operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        attributes = {}
        fields = [
            "lhs",
            "rhs",
            "acc",
            "lhs_type",
            "rhs_type",
            "acc_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op_obj, field):
                value = getattr(op_obj, field)
                if field.endswith("_type"):
                    attributes[field] = self._type_to_string(value)
                else:
                    attributes[field] = self._ssa_use_to_string(value)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="vector",
            name="fma",
            line=line,
            dest=dest,
            result_type=attributes.get("result_type"),
            attributes=attributes,
        )

    def _parse_generic_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse generic vector operation with unknown structure."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operation name
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"vector.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "vector"
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
        elif hasattr(op_obj, "result_type"):
            result_type = self._type_to_string(op_obj.result_type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            attributes=attributes,
        )
