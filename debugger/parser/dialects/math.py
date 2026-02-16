"""Implementation of the Math dialect."""

import inspect
import sys
from dataclasses import dataclass
from typing import Union

from .. import astnodes as mast
from ..dialect import Dialect, DialectOp, UnaryOperation, BinaryOperation, is_op

Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Unary Operations
class MathAbsFOp(UnaryOperation):
    _opname_ = "math.absf"


class MathAbsIOp(UnaryOperation):
    _opname_ = "math.absi"


class MathCosOp(UnaryOperation):
    _opname_ = "math.cos"


class MathSinOp(UnaryOperation):
    _opname_ = "math.sin"


class MathExpOp(UnaryOperation):
    _opname_ = "math.exp"


class MathLogOp(UnaryOperation):
    _opname_ = "math.log"


class MathSqrtOp(UnaryOperation):
    _opname_ = "math.sqrt"


class MathTanhOp(UnaryOperation):
    _opname_ = "math.tanh"


class MathFloorOp(UnaryOperation):
    _opname_ = "math.floor"


class MathCeilOp(UnaryOperation):
    _opname_ = "math.ceil"


class MathRoundOp(UnaryOperation):
    _opname_ = "math.round"


class MathCopySignOp(UnaryOperation):
    _opname_ = "math.copysign"


class MathErfOp(UnaryOperation):
    _opname_ = "math.erf"


class MathErfcOp(UnaryOperation):
    _opname_ = "math.erfc"


# Binary Operations
class MathAtan2Op(BinaryOperation):
    _opname_ = "math.atan2"


class MathFmaOp(BinaryOperation):
    _opname_ = "math.fma"


class MathPowFOp(BinaryOperation):
    _opname_ = "math.powf"


# Comparison Operation
@dataclass
class MathCmpFOp(DialectOp):
    predicate: str
    operand_a: mast.SsaId
    operand_b: mast.SsaId
    type: mast.Type
    _syntax_ = (
        "math.cmpf {predicate.bare_id} , {operand_a.ssa_id} , {operand_b.ssa_id} : {type.type}"
    )
    _opname_ = "math.cmpf"


# Constant Operation (if needed)
@dataclass
class MathConstantOp(DialectOp):
    value: Literal
    type: mast.Type
    _syntax_ = "math.constant {value.constant_literal} : {type.type}"
    _opname_ = "math.constant"


# Inspect current module to get all classes defined above
math = Dialect(
    "math",
    ops=[m[1] for m in inspect.getmembers(sys.modules[__name__], lambda obj: is_op(obj, __name__))],
)
