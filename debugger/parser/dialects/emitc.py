"""Implementation of the EmitC dialect."""

import inspect
import sys
from dataclasses import dataclass
from typing import List, Union

from .. import astnodes as mast
from ..dialect import Dialect, DialectOp, is_op

Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# EmitC operations
@dataclass
class EmitCAddOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "emitc.add {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "emitc.add"


@dataclass
class EmitCAddressOfOp(DialectOp):
    operand: SsaUse
    type: mast.Type
    _syntax_ = "emitc.address_of {operand.ssa_use} : {type.type}"
    _opname_ = "emitc.address_of"


@dataclass
class EmitCApplyOp(DialectOp):
    callee: str
    args: List[SsaUse]
    type: mast.Type
    _syntax_ = "emitc.apply {callee.string} {args.ssa_use_list} : {type.type}"
    _opname_ = "emitc.apply"


@dataclass
class EmitCAssignOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "emitc.assign {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "emitc.assign"


@dataclass
class EmitCBitwiseAndOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "emitc.bitwise_and {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "emitc.bitwise_and"


@dataclass
class EmitCBitwiseLeftShiftOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "emitc.bitwise_left_shift {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "emitc.bitwise_left_shift"


@dataclass
class EmitCBitwiseNotOp(DialectOp):
    operand: SsaUse
    type: mast.Type
    _syntax_ = "emitc.bitwise_not {operand.ssa_use} : {type.type}"
    _opname_ = "emitc.bitwise_not"


@dataclass
class EmitCBitwiseOrOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "emitc.bitwise_or {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "emitc.bitwise_or"


@dataclass
class EmitCBitwiseRightShiftOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "emitc.bitwise_right_shift {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "emitc.bitwise_right_shift"


@dataclass
class EmitCBitwiseXorOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "emitc.bitwise_xor {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "emitc.bitwise_xor"


@dataclass
class EmitCCallOp(DialectOp):
    callee: str
    args: List[SsaUse]
    type: mast.Type
    _syntax_ = "emitc.call {callee.string} {args.ssa_use_list} : {type.type}"
    _opname_ = "emitc.call"


@dataclass
class EmitCCallOpaqueOp(DialectOp):
    callee: str
    args: List[SsaUse]
    type: mast.Type
    _syntax_ = "emitc.call_opaque {callee.string} {args.ssa_use_list} : {type.type}"
    _opname_ = "emitc.call_opaque"


@dataclass
class EmitCCastOp(DialectOp):
    operand: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "emitc.cast {operand.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "emitc.cast"


@dataclass
class EmitCClassOp(DialectOp):
    name: str
    _syntax_ = "emitc.class {name.string}"
    _opname_ = "emitc.class"


@dataclass
class EmitCCmpOp(DialectOp):
    predicate: str
    lhs: SsaUse
    rhs: SsaUse
    type: mast.Type
    _syntax_ = "emitc.cmp {predicate.string} , {lhs.ssa_use} , {rhs.ssa_use} : {type.type}"
    _opname_ = "emitc.cmp"


@dataclass
class EmitCConditionalOp(DialectOp):
    condition: SsaUse
    true_value: SsaUse
    false_value: SsaUse
    type: mast.Type
    _syntax_ = "emitc.conditional {condition.ssa_use} , {true_value.ssa_use} , {false_value.ssa_use} : {type.type}"
    _opname_ = "emitc.conditional"


@dataclass
class EmitCConstantOp(DialectOp):
    value: str
    type: mast.Type
    _syntax_ = "emitc.constant {value.string} : {type.type}"
    _opname_ = "emitc.constant"


# Inspect current module to get all classes defined above
emitc_preamble = """
string: string_literal
"""

emitc = Dialect(
    "emitc",
    ops=[m[1] for m in inspect.getmembers(sys.modules[__name__], lambda obj: is_op(obj, __name__))],
    preamble=emitc_preamble,
)
