from .affine import affine as affine_dialect
from .scf import scf as scf_dialect
from .linalg import linalg
from .func import func as func_dialect
from .cf import cf as cf_dialect
from .arith import arith as arith_dialect
from .memref import memref as memref_dialect
from .tensor import tensor as tensor_dialect
from .index import index as index_dialect
from .math import math as math_dialect
from .bufferization import bufferization as bufferization_dialect
from .shape import shape as shape_dialect
from .vector import vector as vector_dialect
from .builtin import builtin as builtin_dialect
from .emitc import emitc as emitc_dialect

UPSTREAM_DIALECTS = [
    affine_dialect,
    scf_dialect,
    linalg,
    func_dialect,
    cf_dialect,
    arith_dialect,
    memref_dialect,
    tensor_dialect,
    index_dialect,
    math_dialect,
    bufferization_dialect,
    shape_dialect,
    vector_dialect,
    builtin_dialect,
    emitc_dialect,
]
