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
class AbsfOperation(UnaryOperation):
    _opname_ = "arith.absf"


class CeilfOperation(UnaryOperation):
    _opname_ = "arith.ceilf"


class CosOperation(UnaryOperation):
    _opname_ = "arith.cos"


class ExpOperation(UnaryOperation):
    _opname_ = "arith.exp"


class NegfOperation(UnaryOperation):
    _opname_ = "arith.negf"


class TanhOperation(UnaryOperation):
    _opname_ = "arith.tanh"


class CopysignOperation(UnaryOperation):
    _opname_ = "arith.copysign"


class SIToFPOperation(UnaryOperation):
    _opname_ = "arith.sitofp"


# Arithmetic Operations
class AddiOperation(BinaryOperation):
    _opname_ = "arith.addi"


class AddfOperation(BinaryOperation):
    _opname_ = "arith.addf"


class AndOperation(BinaryOperation):
    _opname_ = "arith.and"


class DivisOperation(BinaryOperation):
    _opname_ = "arith.divis"


class DiviuOperation(BinaryOperation):
    _opname_ = "arith.diviu"


class RemisOperation(BinaryOperation):
    _opname_ = "arith.remis"


class RemiuOperation(BinaryOperation):
    _opname_ = "arith.remiu"


class DivfOperation(BinaryOperation):
    _opname_ = "arith.divf"


class MulfOperation(BinaryOperation):
    _opname_ = "arith.mulf"


class MulIOperation(BinaryOperation):
    _opname_ = "arith.muli"


class SubiOperation(BinaryOperation):
    _opname_ = "arith.subi"


class SubfOperation(BinaryOperation):
    _opname_ = "arith.subf"


class OrOperation(BinaryOperation):
    _opname_ = "arith.or"


class XorOperation(BinaryOperation):
    _opname_ = "arith.xor"


# Comparison Operations
@dataclass
class CmpiOperation(DialectOp):
    comptype: str
    operand_a: mast.SsaId
    operand_b: mast.SsaId
    type: mast.Type
    _syntax_ = "arith.cmpi {comptype.bare_id} , {operand_a.ssa_id} , {operand_b.ssa_id} : {type.type}"
    _opname_ = "arith.cmpi"


@dataclass
class CmpfOperation(DialectOp):
    comptype: str
    operand_a: mast.SsaId
    operand_b: mast.SsaId
    type: mast.Type
    _syntax_ = "arith.cmpf {comptype.bare_id} , {operand_a.ssa_id} , {operand_b.ssa_id} : {type.type}"
    _opname_ = "arith.cmpf"


# Constant Operation
@dataclass
class ConstantOperation(DialectOp):
    value: Literal
    type: mast.Type
    _syntax_ = "arith.constant {value.constant_literal} : {type.type}"
    _opname_ = "arith.constant"


# Cast Operations
@dataclass
class IndexCastOperation(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "arith.index_cast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "arith.index_cast"


@dataclass
class MemrefCastOperation(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "arith.memref_cast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "arith.memref_cast"


@dataclass
class TensorCastOperation(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "arith.tensor_cast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "arith.tensor_cast"


# Select Operation
@dataclass
class SelectOperation(DialectOp):
    cond: SsaUse
    arg_true: SsaUse
    arg_false: SsaUse
    type: mast.Type
    _syntax_ = "arith.select {cond.ssa_use} , {arg_true.ssa_use} , {arg_false.ssa_use} : {type.type}"
    _opname_ = "arith.select"


# Inspect current module to get all classes defined above
arith = Dialect(
    "arith",
    ops=[
        m[1]
        for m in inspect.getmembers(
            sys.modules[__name__], lambda obj: is_op(obj, __name__)
        )
    ],
)
