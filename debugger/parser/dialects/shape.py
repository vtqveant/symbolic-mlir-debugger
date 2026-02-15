"""Implementation of the Shape dialect."""

import inspect
import sys
from ..dialect import Dialect, DialectOp, is_op
from .. import astnodes as mast
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass


Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Shape operations
@dataclass
class ShapeAddOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "shape.add {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "shape.add"


@dataclass
class ShapeAnyOp(DialectOp):
    shape: SsaUse
    type: mast.Type
    _syntax_ = "shape.any {shape.ssa_use} : {type.type}"
    _opname_ = "shape.any"


@dataclass
class ShapeAssumingOp(DialectOp):
    condition: SsaUse
    _syntax_ = "shape.assuming {condition.ssa_use}"
    _opname_ = "shape.assuming"


@dataclass
class ShapeAssumingAllOp(DialectOp):
    conditions: List[SsaUse]
    _syntax_ = "shape.assuming_all {conditions.ssa_use_list}"
    _opname_ = "shape.assuming_all"


@dataclass
class ShapeAssumingYieldOp(DialectOp):
    values: List[SsaUse]
    _syntax_ = "shape.assuming_yield {values.ssa_use_list}"
    _opname_ = "shape.assuming_yield"


@dataclass
class ShapeBroadcastOp(DialectOp):
    shapes: List[SsaUse]
    type: mast.Type
    _syntax_ = "shape.broadcast {shapes.ssa_use_list} : {type.type}"
    _opname_ = "shape.broadcast"


@dataclass
class ShapeConcatOp(DialectOp):
    shapes: List[SsaUse]
    type: mast.Type
    _syntax_ = "shape.concat {shapes.ssa_use_list} : {type.type}"
    _opname_ = "shape.concat"


@dataclass
class ShapeConstShapeOp(DialectOp):
    shape: List[SsaUse]
    type: mast.Type
    _syntax_ = "shape.const_shape {shape.ssa_use_list} : {type.type}"
    _opname_ = "shape.const_shape"


@dataclass
class ShapeConstSizeOp(DialectOp):
    value: Literal
    type: mast.Type
    _syntax_ = "shape.const_size {value.constant_literal} : {type.type}"
    _opname_ = "shape.const_size"


@dataclass
class ShapeConstWitnessOp(DialectOp):
    value: Literal
    type: mast.Type
    _syntax_ = "shape.const_witness {value.constant_literal} : {type.type}"
    _opname_ = "shape.const_witness"


@dataclass
class ShapeCstrBroadcastableOp(DialectOp):
    shapes: List[SsaUse]
    _syntax_ = "shape.cstr_broadcastable {shapes.ssa_use_list}"
    _opname_ = "shape.cstr_broadcastable"


@dataclass
class ShapeCstrEqOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    _syntax_ = "shape.cstr_eq {lhs.ssa_use} , {rhs.ssa_use}"
    _opname_ = "shape.cstr_eq"


@dataclass
class ShapeCstrRequireOp(DialectOp):
    condition: SsaUse
    _syntax_ = "shape.cstr_require {condition.ssa_use}"
    _opname_ = "shape.cstr_require"


@dataclass
class ShapeDebugPrintOp(DialectOp):
    value: SsaUse
    _syntax_ = "shape.debug_print {value.ssa_use}"
    _opname_ = "shape.debug_print"


@dataclass
class ShapeDimOp(DialectOp):
    shape: SsaUse
    index: SsaUse
    type: mast.Type
    _syntax_ = "shape.dim {shape.ssa_use} , {index.ssa_use} : {type.type}"
    _opname_ = "shape.dim"


@dataclass
class ShapeDivOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "shape.div {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "shape.div"


@dataclass
class ShapeFromExtentTensorOp(DialectOp):
    tensor: SsaUse
    type: mast.Type
    _syntax_ = "shape.from_extent_tensor {tensor.ssa_use} : {type.type}"
    _opname_ = "shape.from_extent_tensor"


@dataclass
class ShapeFromExtentsOp(DialectOp):
    extents: List[SsaUse]
    type: mast.Type
    _syntax_ = "shape.from_extents {extents.ssa_use_list} : {type.type}"
    _opname_ = "shape.from_extents"


# Inspect current module to get all classes defined above
shape = Dialect(
    "shape",
    ops=[
        m[1]
        for m in inspect.getmembers(
            sys.modules[__name__], lambda obj: is_op(obj, __name__)
        )
    ],
)
