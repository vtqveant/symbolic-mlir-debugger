"""Implementation of the Builtin dialect."""

import inspect
import sys
from dataclasses import dataclass
from typing import List, Union

from .. import astnodes as mast
from ..dialect import Dialect, DialectOp, is_op

Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Builtin operations
@dataclass
class BuiltinModuleOp(DialectOp):
    """Represents a builtin.module operation."""

    _syntax_ = "builtin.module"
    _opname_ = "builtin.module"


@dataclass
class BuiltinUnrealizedConversionCastOp(DialectOp):
    inputs: List[SsaUse]
    outputs: List[mast.Type]
    _syntax_ = "builtin.unrealized_conversion_cast {inputs.ssa_use_list} : {outputs.type_list}"
    _opname_ = "builtin.unrealized_conversion_cast"


# Inspect current module to get all classes defined above
builtin_preamble = """
type_list: type_list_no_parens
"""

builtin = Dialect(
    "builtin",
    ops=[m[1] for m in inspect.getmembers(sys.modules[__name__], lambda obj: is_op(obj, __name__))],
    preamble=builtin_preamble,
)
