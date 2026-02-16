"""Implementation of the Arithmetic (arith) dialect."""

import inspect
import sys
from ..dialect import Dialect, DialectOp, UnaryOperation, BinaryOperation, is_op
from .. import astnodes as mast
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass

Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Unary Operations
class ArithAbsFOp(UnaryOperation):
    _opname_ = "arith.absf"


class ArithCeilFOp(UnaryOperation):
    _opname_ = "arith.ceilf"


class ArithCosOp(UnaryOperation):
    _opname_ = "arith.cos"


class ArithExpOp(UnaryOperation):
    _opname_ = "arith.exp"


class ArithNegFOp(UnaryOperation):
    _opname_ = "arith.negf"


class ArithTanhOp(UnaryOperation):
    _opname_ = "arith.tanh"


class ArithCopySignOp(UnaryOperation):
    _opname_ = "arith.copysign"


class ArithSIToFPOp(UnaryOperation):
    _opname_ = "arith.sitofp"


# Arithmetic Operations
class ArithAddIOp(BinaryOperation):
    _opname_ = "arith.addi"


class ArithAddFOp(BinaryOperation):
    _opname_ = "arith.addf"


class ArithAndOp(BinaryOperation):
    _opname_ = "arith.and"


class ArithDivSIOp(BinaryOperation):
    _opname_ = "arith.divis"


class ArithDivUIOp(BinaryOperation):
    _opname_ = "arith.diviu"


class ArithRemSIOp(BinaryOperation):
    _opname_ = "arith.remis"


class ArithRemUIOp(BinaryOperation):
    _opname_ = "arith.remiu"


class ArithDivFOp(BinaryOperation):
    _opname_ = "arith.divf"


class ArithMulFOp(BinaryOperation):
    _opname_ = "arith.mulf"


class ArithMulIOp(BinaryOperation):
    _opname_ = "arith.muli"


class ArithSubIOp(BinaryOperation):
    _opname_ = "arith.subi"


class ArithSubFOp(BinaryOperation):
    _opname_ = "arith.subf"


class ArithOrOp(BinaryOperation):
    _opname_ = "arith.or"


class ArithXorOp(BinaryOperation):
    _opname_ = "arith.xor"


# Comparison Operations
@dataclass
class ArithCmpIOp(DialectOp):
    comptype: str
    operand_a: mast.SsaId
    operand_b: mast.SsaId
    type: mast.Type
    _syntax_ = (
        "arith.cmpi {comptype.bare_id} , {operand_a.ssa_id} , {operand_b.ssa_id} : {type.type}"
    )
    _opname_ = "arith.cmpi"


@dataclass
class ArithCmpFOp(DialectOp):
    comptype: str
    operand_a: mast.SsaId
    operand_b: mast.SsaId
    type: mast.Type
    _syntax_ = (
        "arith.cmpf {comptype.bare_id} , {operand_a.ssa_id} , {operand_b.ssa_id} : {type.type}"
    )
    _opname_ = "arith.cmpf"


# Constant Operation
@dataclass
class ArithConstantOp(DialectOp):
    value: Literal
    type: mast.Type
    _syntax_ = "arith.constant {value.constant_literal} : {type.type}"
    _opname_ = "arith.constant"


# Cast Operations
@dataclass
class ArithIndexCastOp(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "arith.index_cast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "arith.index_cast"


@dataclass
class ArithMemrefCastOp(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "arith.memref_cast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "arith.memref_cast"


@dataclass
class ArithTensorCastOp(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "arith.tensor_cast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "arith.tensor_cast"


# Select Operation
@dataclass
class ArithSelectOp(DialectOp):
    cond: SsaUse
    arg_true: SsaUse
    arg_false: SsaUse
    type: mast.Type
    _syntax_ = (
        "arith.select {cond.ssa_use} , {arg_true.ssa_use} , {arg_false.ssa_use} : {type.type}"
    )
    _opname_ = "arith.select"


# Inspect current module to get all classes defined above
arith = Dialect(
    "arith",
    ops=[m[1] for m in inspect.getmembers(sys.modules[__name__], lambda obj: is_op(obj, __name__))],
)
