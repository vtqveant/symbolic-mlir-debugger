"""Implementation of the Tensor dialect."""

import inspect
import sys
from ..dialect import Dialect, DialectOp, is_op
from .. import astnodes as mast
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass


Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Extract operation (from standard.extract_element)
@dataclass
class ExtractOperation(DialectOp):
    arg: SsaUse
    index: List[SsaUse]
    type: mast.Type
    _syntax_ = "tensor.extract {arg.ssa_use} [ {index.ssa_use_list} ] : {type.type}"
    _opname_ = "tensor.extract"


# Splat operation (from standard.splat)
@dataclass
class SplatOperation(DialectOp):
    arg: SsaUse
    type: Union[mast.VectorType, mast.TensorType]
    _syntax_ = "tensor.splat {arg.ssa_use} : {type.type}"  # (vector_type | tensor_type)
    _opname_ = "tensor.splat"


# Tensor load/store operations (legacy, may need updating)
@dataclass
class TensorLoadOperation(DialectOp):
    arg: SsaUse
    type: mast.Type
    _syntax_ = "tensor.load {arg.ssa_use} : {type.type}"
    _opname_ = "tensor.load"


@dataclass
class TensorStoreOperation(DialectOp):
    src: SsaUse
    dst: SsaUse
    type: mast.MemRefType
    _syntax_ = "tensor.store {src.ssa_use} , {dst.ssa_use} : {type.memref_type}"
    _opname_ = "tensor.store"


# Additional tensor operations from ops.md (stubs for now)
@dataclass
class CastOperation(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "tensor.cast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "tensor.cast"


@dataclass
class BitcastOperation(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "tensor.bitcast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "tensor.bitcast"


@dataclass
class CollapseShapeOperation(DialectOp):
    operand: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = (
        "tensor.collapse_shape {operand.ssa_use} : {src_type.type} to {dst_type.type}"
    )
    _opname_ = "tensor.collapse_shape"


@dataclass
class ExpandShapeOperation(DialectOp):
    operand: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = (
        "tensor.expand_shape {operand.ssa_use} : {src_type.type} to {dst_type.type}"
    )
    _opname_ = "tensor.expand_shape"


@dataclass
class ConcatOperation(DialectOp):
    operands: List[SsaUse]
    type: mast.Type
    _syntax_ = "tensor.concat {operands.ssa_use_list} : {type.type}"
    _opname_ = "tensor.concat"


@dataclass
class DimOperation(DialectOp):
    operand: mast.SsaId
    index: mast.SsaId
    type: mast.Type
    _syntax_ = "tensor.dim {operand.ssa_id} , {index.ssa_id} : {type.type}"
    _opname_ = "tensor.dim"


@dataclass
class EmptyOperation(DialectOp):
    type: mast.TensorType
    _syntax_ = "tensor.empty : {type.tensor_type}"
    _opname_ = "tensor.empty"


@dataclass
class ExtractSliceOperation(DialectOp):
    operand: SsaUse
    offsets: List[SsaUse]
    sizes: List[SsaUse]
    strides: List[SsaUse]
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "tensor.extract_slice {operand.ssa_use} [ {offsets.ssa_use_list} ] [ {sizes.ssa_use_list} ] [ {strides.ssa_use_list} ] : {src_type.type} to {dst_type.type}"
    _opname_ = "tensor.extract_slice"


@dataclass
class InsertSliceOperation(DialectOp):
    src: SsaUse
    dst: SsaUse
    offsets: List[SsaUse]
    sizes: List[SsaUse]
    strides: List[SsaUse]
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "tensor.insert_slice {src.ssa_use} into {dst.ssa_use} [ {offsets.ssa_use_list} ] [ {sizes.ssa_use_list} ] [ {strides.ssa_use_list} ] : {src_type.type} to {dst_type.type}"
    _opname_ = "tensor.insert_slice"


@dataclass
class FromElementsOperation(DialectOp):
    elements: List[SsaUse]
    type: mast.TensorType
    _syntax_ = "tensor.from_elements {elements.ssa_use_list} : {type.tensor_type}"
    _opname_ = "tensor.from_elements"


@dataclass
class GenerateOperation(DialectOp):
    type: mast.TensorType
    _syntax_ = "tensor.generate {type.tensor_type}"
    _opname_ = "tensor.generate"


@dataclass
class InsertOperation(DialectOp):
    src: SsaUse
    dst: SsaUse
    index: List[SsaUse]
    type: mast.Type
    _syntax_ = "tensor.insert {src.ssa_use} into {dst.ssa_use} [ {index.ssa_use_list} ] : {type.type}"
    _opname_ = "tensor.insert"


@dataclass
class PadOperation(DialectOp):
    operand: SsaUse
    low: List[SsaUse]
    high: List[SsaUse]
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "tensor.pad {operand.ssa_use} low [ {low.ssa_use_list} ] high [ {high.ssa_use_list} ] : {src_type.type} to {dst_type.type}"
    _opname_ = "tensor.pad"


@dataclass
class RankOperation(DialectOp):
    operand: SsaUse
    type: mast.Type
    _syntax_ = "tensor.rank {operand.ssa_use} : {type.type}"
    _opname_ = "tensor.rank"


@dataclass
class ReshapeOperation(DialectOp):
    operand: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "tensor.reshape {operand.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "tensor.reshape"


@dataclass
class ScatterOperation(DialectOp):
    indices: SsaUse
    updates: SsaUse
    target: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "tensor.scatter {indices.ssa_use} , {updates.ssa_use} into {target.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "tensor.scatter"


@dataclass
class GatherOperation(DialectOp):
    indices: SsaUse
    target: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "tensor.gather {indices.ssa_use} from {target.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "tensor.gather"


@dataclass
class YieldOperation(DialectOp):
    values: List[SsaUse]
    _syntax_ = "tensor.yield {values.ssa_use_list}"
    _opname_ = "tensor.yield"


# Inspect current module to get all classes defined above
tensor = Dialect(
    "tensor",
    ops=[
        m[1]
        for m in inspect.getmembers(
            sys.modules[__name__], lambda obj: is_op(obj, __name__)
        )
    ],
)
