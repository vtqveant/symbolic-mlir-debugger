"""Implementation of the Index dialect."""

import inspect
import sys
from dataclasses import dataclass
from typing import Union

from .. import astnodes as mast
from ..dialect import Dialect, DialectOp, BinaryOperation, is_op

Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Binary Operations
class IndexAddOp(BinaryOperation):
    _opname_ = "index.add"


class IndexSubOp(BinaryOperation):
    _opname_ = "index.sub"


class IndexMulOp(BinaryOperation):
    _opname_ = "index.mul"


class IndexDivSOp(BinaryOperation):
    _opname_ = "index.divs"


class IndexDivUOp(BinaryOperation):
    _opname_ = "index.divu"


class IndexRemSOp(BinaryOperation):
    _opname_ = "index.rems"


class IndexRemUOp(BinaryOperation):
    _opname_ = "index.remu"


class IndexAndOp(BinaryOperation):
    _opname_ = "index.and"


class IndexOrOp(BinaryOperation):
    _opname_ = "index.or"


class IndexXorOp(BinaryOperation):
    _opname_ = "index.xor"


class IndexShiftLeftOp(BinaryOperation):
    _opname_ = "index.shl"


class IndexShiftRightSignedOp(BinaryOperation):
    _opname_ = "index.shrs"


class IndexShiftRightUnsignedOp(BinaryOperation):
    _opname_ = "index.shru"


# Comparison Operation
@dataclass
class IndexCmpOp(DialectOp):
    predicate: str
    operand_a: mast.SsaId
    operand_b: mast.SsaId
    type: mast.Type
    _syntax_ = (
        "index.cmp {predicate.bare_id} , {operand_a.ssa_id} , {operand_b.ssa_id} : {type.type}"
    )
    _opname_ = "index.cmp"


# Constant Operations
@dataclass
class IndexConstantOp(DialectOp):
    value: Literal
    type: mast.Type
    _syntax_ = "index.constant {value.constant_literal} : {type.type}"
    _opname_ = "index.constant"


@dataclass
class IndexBoolConstantOp(DialectOp):
    value: bool
    type: mast.Type
    _syntax_ = "index.bool.constant {value.constant_literal} : {type.type}"
    _opname_ = "index.bool.constant"


# Cast Operations
@dataclass
class IndexCastSOp(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "index.casts {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "index.casts"


@dataclass
class IndexCastUOp(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "index.castu {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "index.castu"


# Additional binary operations
class IndexCeilDivSOp(BinaryOperation):
    _opname_ = "index.ceildivs"


class IndexCeilDivUOp(BinaryOperation):
    _opname_ = "index.ceildivu"


class IndexFloorDivSOp(BinaryOperation):
    _opname_ = "index.floordivs"


class IndexMaxSOp(BinaryOperation):
    _opname_ = "index.maxs"


class IndexMaxUOp(BinaryOperation):
    _opname_ = "index.maxu"


class IndexMinSOp(BinaryOperation):
    _opname_ = "index.mins"


class IndexMinUOp(BinaryOperation):
    _opname_ = "index.minu"


# SizeOf operation (unary)
@dataclass
class IndexSizeOfOp(DialectOp):
    arg: SsaUse
    type: mast.Type
    _syntax_ = "index.sizeof {arg.ssa_use} : {type.type}"
    _opname_ = "index.sizeof"


# Inspect current module to get all classes defined above
index = Dialect(
    "index",
    ops=[m[1] for m in inspect.getmembers(sys.modules[__name__], lambda obj: is_op(obj, __name__))],
)
