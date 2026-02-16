"""Implementation of the MemRef dialect."""

import inspect
import sys
from ..dialect import Dialect, DialectOp, is_op
from .. import astnodes as mast
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass

Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Dimension operation
@dataclass
class MemRefDimOp(DialectOp):
    operand: mast.SsaId
    index: mast.SsaId
    type: mast.Type
    _syntax_ = "memref.dim {operand.ssa_id} , {index.ssa_id} : {type.type}"
    _opname_ = "memref.dim"


# Memory allocation operations
@dataclass
class MemRefAllocOp(DialectOp):
    args: mast.DimAndSymbolList
    type: mast.MemRefType
    _syntax_ = "memref.alloc {args.dim_and_symbol_use_list} : {type.memref_type}"
    _opname_ = "memref.alloc"


@dataclass
class MemRefAllocaOp(DialectOp):
    args: mast.DimAndSymbolList
    type: mast.MemRefType
    _syntax_ = "memref.alloca {args.dim_and_symbol_use_list} : {type.memref_type}"
    _opname_ = "memref.alloca"


@dataclass
class MemRefDeallocOp(DialectOp):
    arg: SsaUse
    type: mast.MemRefType
    _syntax_ = "memref.dealloc {arg.ssa_use} : {type.memref_type}"
    _opname_ = "memref.dealloc"


# DMA operations
@dataclass
class MemRefDmaStartOp(DialectOp):
    src: SsaUse
    src_index: List[SsaUse]
    dst: SsaUse
    dst_index: List[SsaUse]
    size: SsaUse
    tag: SsaUse
    tag_index: List[SsaUse]
    src_type: mast.MemRefType
    dst_type: mast.MemRefType
    tag_type: mast.MemRefType
    stride: Optional[SsaUse] = None
    transfer_per_stride: Optional[SsaUse] = None
    _syntax_ = [
        "memref.dma_start {src.ssa_use} [ {src_index.ssa_use_list} ] , {dst.ssa_use} [ {dst_index.ssa_use_list} ] , {size.ssa_use} , {tag.ssa_use} [ {tag_index.ssa_use_list} ] : {src_type.memref_type} , {dst_type.memref_type} , {tag_type.memref_type}",
        "memref.dma_start {src.ssa_use} [ {src_index.ssa_use_list} ] , {dst.ssa_use} [ {dst_index.ssa_use_list} ] , {size.ssa_use} , {tag.ssa_use} [ {tag_index.ssa_use_list} ] , {stride.ssa_use} , {transfer_per_stride.ssa_use} : {src_type.memref_type} , {dst_type.memref_type} , {tag_type.memref_type}",
    ]
    _opname_ = "memref.dma_start"


@dataclass
class MemRefDmaWaitOp(DialectOp):
    tag: SsaUse
    tag_index: List[SsaUse]
    size: SsaUse
    type: mast.MemRefType
    _syntax_ = "memref.dma_wait {tag.ssa_use} [ {tag_index.ssa_use_list} ] , {size.ssa_use} : {type.memref_type}"
    _opname_ = "memref.dma_wait"


# Load/store operations
@dataclass
class MemRefLoadOp(DialectOp):
    arg: SsaUse
    index: List[SsaUse]
    type: mast.MemRefType
    _syntax_ = "memref.load {arg.ssa_use} [ {index.ssa_use_list} ] : {type.memref_type}"
    _opname_ = "memref.load"


@dataclass
class MemRefStoreOp(DialectOp):
    value: SsaUse
    memref: SsaUse
    index: List[SsaUse]
    type: mast.MemRefType
    _syntax_ = "memref.store {value.ssa_use} , {memref.ssa_use} [ {index.ssa_use_list} ] : {type.memref_type}"
    _opname_ = "memref.store"


# View operations
@dataclass
class MemRefSubviewOp(DialectOp):
    operand: SsaUse
    offsets: List[SsaUse]
    sizes: List[SsaUse]
    strides: List[SsaUse]
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "memref.subview {operand.ssa_use} [ {offsets.ssa_use_list} ] [ {sizes.ssa_use_list} ] [ {strides.ssa_use_list} ] : {src_type.type} to {dst_type.type}"
    _opname_ = "memref.subview"


@dataclass
class MemRefViewOp(DialectOp):
    operand: SsaUse
    offset: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    sizes: Optional[List[SsaUse]] = None
    _syntax_ = [
        "memref.view {operand.ssa_use} [ {offset.ssa_use} ] [ {sizes.ssa_use_list} ] : {src_type.type} to {dst_type.type}",
        "memref.view {operand.ssa_use} [ {offset.ssa_use} ] [  ] : {src_type.type} to {dst_type.type}",
    ]
    _opname_ = "memref.view"


# Additional memref operations from ops.md (stubs for now)
@dataclass
class MemRefCastOp(DialectOp):
    arg: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "memref.cast {arg.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "memref.cast"


@dataclass
class MemRefCollapseShapeOp(DialectOp):
    operand: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "memref.collapse_shape {operand.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "memref.collapse_shape"


@dataclass
class MemRefExpandShapeOp(DialectOp):
    operand: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "memref.expand_shape {operand.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "memref.expand_shape"


@dataclass
class MemRefReinterpretCastOp(DialectOp):
    operand: SsaUse
    offsets: List[SsaUse]
    sizes: List[SsaUse]
    strides: List[SsaUse]
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "memref.reinterpret_cast {operand.ssa_use} to offset: [ {offsets.ssa_use_list} ] , sizes: [ {sizes.ssa_use_list} ] , strides: [ {strides.ssa_use_list} ] : {src_type.type} to {dst_type.type}"
    _opname_ = "memref.reinterpret_cast"


@dataclass
class MemRefMemorySpaceCastOp(DialectOp):
    operand: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "memref.memory_space_cast {operand.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "memref.memory_space_cast"


# Inspect current module to get all classes defined above
memref = Dialect(
    "memref",
    ops=[m[1] for m in inspect.getmembers(sys.modules[__name__], lambda obj: is_op(obj, __name__))],
)
