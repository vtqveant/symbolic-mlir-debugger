#!/usr/bin/env python3
"""
Shape dialect parser.

Converts pymlir AST nodes for shape operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, Any, List
import dataclasses

import parser.astnodes as mast
from .base import BaseDialectParser
from ..operations import Operation, BinaryOperation, UnaryOperation, ConstantOperation


class ShapeDialectParser(BaseDialectParser):
    """Parser for shape dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a shape operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Handle GenericOperation (quoted operation names in MLIR)
        if isinstance(op_obj, mast.GenericOperation):
            # Check if it's a shape operation by name
            if hasattr(op_obj, "name"):
                op_name_obj = op_obj.name
                # Extract string from StringLiteral or use as-is
                if hasattr(op_name_obj, "value"):
                    op_name = op_name_obj.value
                else:
                    op_name = str(op_name_obj)
                if op_name.startswith("shape."):
                    # Dispatch based on operation name
                    if op_name == "shape.const_size":
                        return self._parse_generic_const_size_operation(op_node)
                    elif op_name == "shape.const_shape":
                        return self._parse_generic_const_shape_operation(op_node)
                    elif op_name == "shape.add":
                        return self._parse_generic_binary_operation(op_node)
                    elif op_name == "shape.div":
                        return self._parse_generic_binary_operation(op_node)
                    elif op_name == "shape.get_extent":
                        return self._parse_generic_get_extent_operation(op_node)
                    # For other shape operations, use generic fallback
                    return self._parse_generic_operation(op_node)
            # Not a shape operation
            return None

        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Special handling for operations with custom fields
            if class_name == "ShapeConstShapeOp":
                return self._parse_const_shape_operation(op_node)
            elif class_name == "ShapeConstSizeOp":
                return self._parse_const_size_operation(op_node)
            elif class_name == "ShapeConstWitnessOp":
                return self._parse_const_witness_operation(op_node)
            elif class_name == "ShapeAssumingOp":
                return self._parse_assuming_operation(op_node)
            elif class_name == "ShapeAssumingAllOp":
                return self._parse_assuming_all_operation(op_node)
            elif class_name == "ShapeAssumingYieldOp":
                return self._parse_assuming_yield_operation(op_node)
            elif class_name == "ShapeBroadcastOp":
                return self._parse_broadcast_operation(op_node)
            elif class_name == "ShapeConcatOp":
                return self._parse_concat_operation(op_node)
            elif class_name == "ShapeCstrBroadcastableOp":
                return self._parse_cstr_broadcastable_operation(op_node)
            elif class_name == "ShapeCstrEqOp":
                return self._parse_cstr_eq_operation(op_node)
            elif class_name == "ShapeCstrRequireOp":
                return self._parse_cstr_require_operation(op_node)
            elif class_name == "ShapeDebugPrintOp":
                return self._parse_debug_print_operation(op_node)
            elif class_name == "ShapeDimOp":
                return self._parse_dim_operation(op_node)
            elif class_name == "ShapeFromExtentTensorOp":
                return self._parse_from_extent_tensor_operation(op_node)
            elif class_name == "ShapeFromExtentsOp":
                return self._parse_from_extents_operation(op_node)

            # Binary operations (AddOperation, DivOperation) have lhs, rhs
            elif class_name.endswith("Op") and hasattr(op_obj, "lhs") and hasattr(op_obj, "rhs"):
                return self._parse_binary_operation(op_node)

            # Unary operations (AnyOperation) have shape
            elif class_name.endswith("Op") and hasattr(op_obj, "shape"):
                return self._parse_unary_operation(op_node)

            # Generic fallback
            else:
                return self._parse_generic_operation(op_node)

        return None

    def _parse_binary_operation(self, op_node: mast.Operation) -> Optional[BinaryOperation]:
        """Parse binary shape operation (add, div)."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operation name
        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"shape.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "shape"
            name = full_name

        lhs = self._ssa_use_to_string(op_obj.lhs)
        rhs = self._ssa_use_to_string(op_obj.rhs)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

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
        """Parse unary shape operation (any)."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"shape.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "shape"
            name = full_name

        operand = self._ssa_use_to_string(op_obj.shape)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

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

    def _parse_const_shape_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.const_shape operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        shape = []
        if hasattr(op_obj, "shape"):
            shape = [self._ssa_use_to_string(s) for s in op_obj.shape]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="const_shape",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={"shape": shape},
        )

    def _parse_const_size_operation(self, op_node: mast.Operation) -> Optional[ConstantOperation]:
        """Parse shape.const_size operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        value = None
        if hasattr(op_obj, "value"):
            value = self._parse_constant_value(op_obj.value)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return ConstantOperation(
            dialect="shape",
            name="const_size",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )

    def _parse_const_witness_operation(
        self, op_node: mast.Operation
    ) -> Optional[ConstantOperation]:
        """Parse shape.const_witness operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        value = None
        if hasattr(op_obj, "value"):
            value = self._parse_constant_value(op_obj.value)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return ConstantOperation(
            dialect="shape",
            name="const_witness",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )

    def _parse_assuming_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.assuming operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        condition = None
        if hasattr(op_obj, "condition"):
            condition = self._ssa_use_to_string(op_obj.condition)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="assuming",
            line=line,
            dest=dest,
            result_type=None,
            attributes={"condition": condition},
        )

    def _parse_assuming_all_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.assuming_all operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        conditions = []
        if hasattr(op_obj, "conditions"):
            conditions = [self._ssa_use_to_string(c) for c in op_obj.conditions]

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="assuming_all",
            line=line,
            dest=dest,
            result_type=None,
            attributes={"conditions": conditions},
        )

    def _parse_assuming_yield_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.assuming_yield operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        values = []
        if hasattr(op_obj, "values"):
            values = [self._ssa_use_to_string(v) for v in op_obj.values]

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="assuming_yield",
            line=line,
            dest=dest,
            result_type=None,
            attributes={"values": values},
        )

    def _parse_broadcast_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.broadcast operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        shapes = []
        if hasattr(op_obj, "shapes"):
            shapes = [self._ssa_use_to_string(s) for s in op_obj.shapes]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="broadcast",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={"shapes": shapes},
        )

    def _parse_concat_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.concat operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        shapes = []
        if hasattr(op_obj, "shapes"):
            shapes = [self._ssa_use_to_string(s) for s in op_obj.shapes]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="concat",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={"shapes": shapes},
        )

    def _parse_cstr_broadcastable_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.cstr_broadcastable operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        shapes = []
        if hasattr(op_obj, "shapes"):
            shapes = [self._ssa_use_to_string(s) for s in op_obj.shapes]

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="cstr_broadcastable",
            line=line,
            dest=dest,
            result_type=None,
            attributes={"shapes": shapes},
        )

    def _parse_cstr_eq_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.cstr_eq operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        lhs = None
        rhs = None
        if hasattr(op_obj, "lhs"):
            lhs = self._ssa_use_to_string(op_obj.lhs)
        if hasattr(op_obj, "rhs"):
            rhs = self._ssa_use_to_string(op_obj.rhs)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="cstr_eq",
            line=line,
            dest=dest,
            result_type=None,
            attributes={"lhs": lhs, "rhs": rhs},
        )

    def _parse_cstr_require_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.cstr_require operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        condition = None
        if hasattr(op_obj, "condition"):
            condition = self._ssa_use_to_string(op_obj.condition)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="cstr_require",
            line=line,
            dest=dest,
            result_type=None,
            attributes={"condition": condition},
        )

    def _parse_debug_print_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.debug_print operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        value = None
        if hasattr(op_obj, "value"):
            value = self._ssa_use_to_string(op_obj.value)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="debug_print",
            line=line,
            dest=dest,
            result_type=None,
            attributes={"value": value},
        )

    def _parse_dim_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.dim operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        shape = None
        index = None
        if hasattr(op_obj, "shape"):
            shape = self._ssa_use_to_string(op_obj.shape)
        if hasattr(op_obj, "index"):
            index = self._ssa_use_to_string(op_obj.index)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="dim",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={"shape": shape, "index": index},
        )

    def _parse_from_extent_tensor_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.from_extent_tensor operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        tensor = None
        if hasattr(op_obj, "tensor"):
            tensor = self._ssa_use_to_string(op_obj.tensor)

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="from_extent_tensor",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={"tensor": tensor},
        )

    def _parse_from_extents_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.from_extents operation."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        extents = []
        if hasattr(op_obj, "extents"):
            extents = [self._ssa_use_to_string(e) for e in op_obj.extents]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="from_extents",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={"extents": extents},
        )

    def _parse_generic_const_size_operation(
        self, op_node: mast.Operation
    ) -> Optional[ConstantOperation]:
        """Parse shape.const_size generic operation."""
        op_obj = op_node.op
        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract value from attributes
        value = None
        import sys

        if hasattr(op_obj, "attributes"):
            # attributes is a dictionary attribute
            attr_dict = self._parse_attribute(op_obj.attributes)
            if isinstance(attr_dict, dict) and "value" in attr_dict:
                value = self._parse_constant_value(attr_dict["value"])

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return ConstantOperation(
            dialect="shape",
            name="const_size",
            line=line,
            dest=dest,
            result_type=result_type,
            value=value,
            attributes={},
        )

    def _parse_generic_const_shape_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.const_shape generic operation."""
        op_obj = op_node.op
        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract shape from attributes
        shape_attr = None
        if hasattr(op_obj, "attributes"):
            attr_dict = self._parse_attribute(op_obj.attributes)
            if "shape" in attr_dict:
                shape_attr = attr_dict["shape"]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return Operation(
            dialect="shape",
            name="const_shape",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes={"shape": shape_attr},
        )

    def _parse_generic_binary_operation(self, op_node: mast.Operation) -> Optional[BinaryOperation]:
        """Parse shape.add/div generic operation."""
        op_obj = op_node.op
        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operation name from generic op
        op_name_obj = op_obj.name if hasattr(op_obj, "name") else "shape.add"
        if hasattr(op_name_obj, "value"):
            op_name = op_name_obj.value
        else:
            op_name = str(op_name_obj)
        name = op_name.split(".", 1)[1] if "." in op_name else op_name

        # Extract operands from args
        lhs = rhs = None
        if hasattr(op_obj, "args") and len(op_obj.args) >= 2:
            lhs = self._ssa_use_to_string(op_obj.args[0])
            rhs = self._ssa_use_to_string(op_obj.args[1])

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        return BinaryOperation(
            dialect="shape",
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            lhs=lhs,
            rhs=rhs,
            attributes={},
        )

    def _parse_generic_get_extent_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse shape.get_extent generic operation."""
        op_obj = op_node.op
        dest = self._extract_destination(op_node)
        if dest is None:
            return None

        # Extract operands from args
        operands = []
        if hasattr(op_obj, "args"):
            operands = [self._ssa_use_to_string(arg) for arg in op_obj.args]

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        attributes = {
            "operands": operands,
        }

        return Operation(
            dialect="shape",
            name="get_extent",
            line=line,
            dest=dest,
            result_type=result_type,
            attributes=attributes,
        )

    def _parse_generic_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Fallback generic parser for shape operations."""
        op_obj = op_node.op

        dest = self._extract_destination(op_node)
        # dest may be None for operations without result

        if hasattr(op_obj.__class__, "_opname_"):
            full_name = op_obj.__class__._opname_
        else:
            class_name = op_obj.__class__.__name__
            full_name = f"shape.{class_name[:-9].lower()}"

        if "." in full_name:
            dialect, name = full_name.split(".", 1)
        else:
            dialect = "shape"
            name = full_name

        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op_node)

        # Collect any other fields as attributes
        attributes = {}
        # Could iterate over op_obj fields, but for now leave empty
        # We'll rely on special handlers for most operations

        return Operation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=result_type,
            attributes=attributes,
        )
