"""Implementation of the Control Flow (cf) dialect."""

import inspect
import sys
from ..dialect import Dialect, DialectOp, is_op
from .. import astnodes as mast
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass


Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


@dataclass
class CfBrOp(DialectOp):
    block: mast.BlockId
    args: Optional[List[Tuple[mast.SsaId, mast.Type]]] = None
    _syntax_ = [
        "cf.br {block.block_id}",
        "cf.br {block.block_id} {args.block_arg_list}",
    ]
    _opname_ = "cf.br"


@dataclass
class CfCondBrOp(DialectOp):
    cond: SsaUse
    block_true: mast.BlockId
    block_false: mast.BlockId
    _syntax_ = [
        "cf.cond_br {cond.ssa_use} , {block_true.block_id} , {block_false.block_id}"
    ]
    _opname_ = "cf.cond_br"


# Inspect current module to get all classes defined above
cf = Dialect(
    "cf",
    ops=[
        m[1]
        for m in inspect.getmembers(
            sys.modules[__name__], lambda obj: is_op(obj, __name__)
        )
    ],
)
