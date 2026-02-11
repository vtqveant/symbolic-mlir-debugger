"""Implementation of the Math dialect."""

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
    _opname_ = "math.absf"


class AbsiOperation(UnaryOperation):
    _opname_ = "math.absi"


class CosOperation(UnaryOperation):
    _opname_ = "math.cos"


class SinOperation(UnaryOperation):
    _opname_ = "math.sin"


class ExpOperation(UnaryOperation):
    _opname_ = "math.exp"


class LogOperation(UnaryOperation):
    _opname_ = "math.log"


class SqrtOperation(UnaryOperation):
    _opname_ = "math.sqrt"


class TanhOperation(UnaryOperation):
    _opname_ = "math.tanh"


class FloorOperation(UnaryOperation):
    _opname_ = "math.floor"


class CeilOperation(UnaryOperation):
    _opname_ = "math.ceil"


class RoundOperation(UnaryOperation):
    _opname_ = "math.round"


class CopysignOperation(UnaryOperation):
    _opname_ = "math.copysign"


class ErfOperation(UnaryOperation):
    _opname_ = "math.erf"


class ErfcOperation(UnaryOperation):
    _opname_ = "math.erfc"


# Binary Operations
class Atan2Operation(BinaryOperation):
    _opname_ = "math.atan2"


class FmaOperation(BinaryOperation):
    _opname_ = "math.fma"


class PowfOperation(BinaryOperation):
    _opname_ = "math.powf"


# Comparison Operation
@dataclass
class CmpfOperation(DialectOp):
    predicate: str
    operand_a: mast.SsaId
    operand_b: mast.SsaId
    type: mast.Type
    _syntax_ = "math.cmpf {predicate.bare_id} , {operand_a.ssa_id} , {operand_b.ssa_id} : {type.type}"
    _opname_ = "math.cmpf"


# Constant Operation (if needed)
@dataclass
class ConstantOperation(DialectOp):
    value: Literal
    type: mast.Type
    _syntax_ = "math.constant {value.constant_literal} : {type.type}"
    _opname_ = "math.constant"


# Inspect current module to get all classes defined above
math = Dialect(
    "math",
    ops=[
        m[1]
        for m in inspect.getmembers(
            sys.modules[__name__], lambda obj: is_op(obj, __name__)
        )
    ],
)
