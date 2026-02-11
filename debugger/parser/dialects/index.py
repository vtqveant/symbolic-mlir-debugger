"""Implementation of the Index dialect."""

import inspect
import sys
from ..dialect import Dialect, DialectOp, UnaryOperation, BinaryOperation, is_op
from .. import astnodes as mast
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass


Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Binary Operations
class AddOperation(BinaryOperation):
    _opname_ = "index.add"


class SubOperation(BinaryOperation):
    _opname_ = "index.sub"


class MulOperation(BinaryOperation):
    _opname_ = "index.mul"


class DivSOperation(BinaryOperation):
    _opname_ = "index.divs"


class DivUOperation(BinaryOperation):
    _opname_ = "index.divu"


class RemSOperation(BinaryOperation):
    _opname_ = "index.rems"


class RemUOperation(BinaryOperation):
    _opname_ = "index.remu"


class AndOperation(BinaryOperation):
    _opname_ = "index.and"


class OrOperation(BinaryOperation):
    _opname_ = "index.or"


class XorOperation(BinaryOperation):
    _opname_ = "index.xor"


class ShiftLeftOperation(BinaryOperation):
    _opname_ = "index.shl"


class ShiftRightSignedOperation(BinaryOperation):
    _opname_ = "index.shrs"


class ShiftRightUnsignedOperation(BinaryOperation):
    _opname_ = "index.shru"


# Comparison Operation
@dataclass
class CmpOperation(DialectOp):
    predicate: str
    operand_a: mast.SsaId
    operand_b: mast.SsaId
    type: mast.Type
    _syntax_ = "index.cmp {predicate.bare_id} , {operand_a.ssa_id} , {operand_b.ssa_id} : {type.type}"
    _opname_ = "index.cmp"


# Constant Operations
@dataclass
class ConstantOperation(DialectOp):
    value: Literal
    type: mast.Type
    _syntax_ = "index.constant {value.constant_literal} : {type.type}"
    _opname_ = "index.constant"


@dataclass
class BoolConstantOperation(DialectOp):
    value: bool
    type: mast.Type
    _syntax_ = "index.bool.constant {value.constant_literal} : {type.type}"
    _opname_ = "index.bool.constant"


# Cast Operations
@dataclass
class CastSOperation(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "index.casts {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "index.casts"


@dataclass
class CastUOperation(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "index.castu {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "index.castu"


# Additional binary operations
class CeilDivSOperation(BinaryOperation):
    _opname_ = "index.ceildivs"


class CeilDivUOperation(BinaryOperation):
    _opname_ = "index.ceildivu"


class FloorDivSOperation(BinaryOperation):
    _opname_ = "index.floordivs"


class MaxSOperation(BinaryOperation):
    _opname_ = "index.maxs"


class MaxUOperation(BinaryOperation):
    _opname_ = "index.maxu"


class MinSOperation(BinaryOperation):
    _opname_ = "index.mins"


class MinUOperation(BinaryOperation):
    _opname_ = "index.minu"


# SizeOf operation (unary)
@dataclass
class SizeOfOperation(DialectOp):
    arg: SsaUse
    type: mast.Type
    _syntax_ = "index.sizeof {arg.ssa_use} : {type.type}"
    _opname_ = "index.sizeof"


# Inspect current module to get all classes defined above
index = Dialect(
    "index",
    ops=[
        m[1]
        for m in inspect.getmembers(
            sys.modules[__name__], lambda obj: is_op(obj, __name__)
        )
    ],
)
