"""Implementation of the Vector dialect."""

import inspect
import sys
from ..dialect import Dialect, DialectOp, is_op
from .. import astnodes as mast
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass


Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Vector operations
@dataclass
class VectorBitcastOp(DialectOp):
    source: SsaUse
    source_type: mast.Type
    result_type: mast.Type
    _syntax_ = (
        "vector.bitcast {source.ssa_use} : {source_type.type} to {result_type.type}"
    )
    _opname_ = "vector.bitcast"


@dataclass
class VectorBroadcastOp(DialectOp):
    source: SsaUse
    result_type: mast.Type
    _syntax_ = "vector.broadcast {source.ssa_use} : {result_type.type}"
    _opname_ = "vector.broadcast"


@dataclass
class VectorCompressStoreOp(DialectOp):
    base: SsaUse
    indices: List[SsaUse]
    mask: SsaUse
    value: SsaUse
    base_type: mast.Type
    mask_type: mast.Type
    value_type: mast.Type
    _syntax_ = "vector.compressstore {base.ssa_use} {indices.ssa_use_list} , {mask.ssa_use} , {value.ssa_use} : {base_type.type} , {mask_type.type} , {value_type.type}"
    _opname_ = "vector.compressstore"


@dataclass
class VectorConstantMaskOp(DialectOp):
    mask_dimensions: List[int]
    result_type: mast.Type
    _syntax_ = "vector.constant_mask {mask_dimensions.int_list} : {result_type.type}"
    _opname_ = "vector.constant_mask"


@dataclass
class VectorContractOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    acc: SsaUse
    indexing_maps: List[SsaUse]
    iterator_types: List[str]
    lhs_type: mast.Type
    rhs_type: mast.Type
    acc_type: mast.Type
    result_type: mast.Type
    _syntax_ = "vector.contract {lhs.ssa_use} , {rhs.ssa_use} , {acc.ssa_use} {indexing_maps.ssa_use_list} {iterator_types.string_list} : {lhs_type.type} , {rhs_type.type} , {acc_type.type} -> {result_type.type}"
    _opname_ = "vector.contract"


@dataclass
class VectorCreateMaskOp(DialectOp):
    operands: List[SsaUse]
    result_type: mast.Type
    _syntax_ = "vector.create_mask {operands.ssa_use_list} : {result_type.type}"
    _opname_ = "vector.create_mask"


@dataclass
class VectorDeinterleaveOp(DialectOp):
    source: SsaUse
    result_type: mast.Type
    _syntax_ = "vector.deinterleave {source.ssa_use} : {result_type.type}"
    _opname_ = "vector.deinterleave"


@dataclass
class VectorExpandLoadOp(DialectOp):
    base: SsaUse
    indices: List[SsaUse]
    mask: SsaUse
    pass_thru: SsaUse
    base_type: mast.Type
    mask_type: mast.Type
    pass_thru_type: mast.Type
    result_type: mast.Type
    _syntax_ = "vector.expandload {base.ssa_use} {indices.ssa_use_list} , {mask.ssa_use} , {pass_thru.ssa_use} : {base_type.type} , {mask_type.type} , {pass_thru_type.type} -> {result_type.type}"
    _opname_ = "vector.expandload"


@dataclass
class VectorExtractOp(DialectOp):
    vector: SsaUse
    position: List[SsaUse]
    vector_type: mast.Type
    result_type: mast.Type
    _syntax_ = "vector.extract {vector.ssa_use} {position.ssa_use_list} : {vector_type.type} to {result_type.type}"
    _opname_ = "vector.extract"


@dataclass
class VectorExtractStridedSliceOp(DialectOp):
    vector: SsaUse
    offsets: List[SsaUse]
    sizes: List[SsaUse]
    strides: List[SsaUse]
    vector_type: mast.Type
    result_type: mast.Type
    _syntax_ = "vector.extract_strided_slice {vector.ssa_use} {offsets.ssa_use_list} , {sizes.ssa_use_list} , {strides.ssa_use_list} : {vector_type.type} to {result_type.type}"
    _opname_ = "vector.extract_strided_slice"


@dataclass
class VectorFmaOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    acc: SsaUse
    lhs_type: mast.Type
    rhs_type: mast.Type
    acc_type: mast.Type
    result_type: mast.Type
    _syntax_ = "vector.fma {lhs.ssa_use} , {rhs.ssa_use} , {acc.ssa_use} : {lhs_type.type} , {rhs_type.type} , {acc_type.type} -> {result_type.type}"
    _opname_ = "vector.fma"


@dataclass
class VectorFromElementsOp(DialectOp):
    elements: List[SsaUse]
    result_type: mast.Type
    _syntax_ = "vector.from_elements {elements.ssa_use_list} : {result_type.type}"
    _opname_ = "vector.from_elements"


@dataclass
class VectorGatherOp(DialectOp):
    base: SsaUse
    indices: List[SsaUse]
    index_vec: SsaUse
    mask: SsaUse
    pass_thru: SsaUse
    base_type: mast.Type
    index_vec_type: mast.Type
    mask_type: mast.Type
    pass_thru_type: mast.Type
    result_type: mast.Type
    _syntax_ = "vector.gather {base.ssa_use} {indices.ssa_use_list} , {index_vec.ssa_use} , {mask.ssa_use} , {pass_thru.ssa_use} : {base_type.type} , {index_vec_type.type} , {mask_type.type} , {pass_thru_type.type} -> {result_type.type}"
    _opname_ = "vector.gather"


@dataclass
class VectorInsertOp(DialectOp):
    source: SsaUse
    dest: SsaUse
    position: List[SsaUse]
    source_type: mast.Type
    dest_type: mast.Type
    result_type: mast.Type
    _syntax_ = "vector.insert {source.ssa_use} , {dest.ssa_use} {position.ssa_use_list} : {source_type.type} , {dest_type.type} into {result_type.type}"
    _opname_ = "vector.insert"


@dataclass
class VectorInsertStridedSliceOp(DialectOp):
    source: SsaUse
    dest: SsaUse
    offsets: List[SsaUse]
    strides: List[SsaUse]
    source_type: mast.Type
    dest_type: mast.Type
    result_type: mast.Type
    _syntax_ = "vector.insert_strided_slice {source.ssa_use} , {dest.ssa_use} {offsets.ssa_use_list} , {strides.ssa_use_list} : {source_type.type} , {dest_type.type} into {result_type.type}"
    _opname_ = "vector.insert_strided_slice"


@dataclass
class VectorInterleaveOp(DialectOp):
    lhs: SsaUse
    rhs: SsaUse
    result_type: mast.Type
    _syntax_ = "vector.interleave {lhs.ssa_use} , {rhs.ssa_use} : {result_type.type}"
    _opname_ = "vector.interleave"


# Inspect current module to get all classes defined above
vector_preamble = """
int_list: "[" integer_literal ("," integer_literal)* "]"
string_list: "[" string_literal ("," string_literal)* "]"
"""

vector = Dialect(
    "vector",
    ops=[
        m[1]
        for m in inspect.getmembers(
            sys.modules[__name__], lambda obj: is_op(obj, __name__)
        )
    ],
    preamble=vector_preamble,
)
