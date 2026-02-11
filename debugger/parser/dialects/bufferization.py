"""Implementation of the Bufferization dialect."""

import inspect
import sys
from ..dialect import Dialect, DialectOp, is_op
from .. import astnodes as mast
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass


Literal = Union[mast.StringLiteral, float, int, bool]
SsaUse = Union[mast.SsaId, Literal]


# Allocate a tensor with buffer semantics
@dataclass
class AllocTensorOperation(DialectOp):
    shape: List[SsaUse]
    type: mast.TensorType
    _syntax_ = "bufferization.alloc_tensor {shape.ssa_use_list} : {type.tensor_type}"
    _opname_ = "bufferization.alloc_tensor"


# Clone a buffer (deep copy)
@dataclass
class CloneOperation(DialectOp):
    src: SsaUse
    type: mast.Type
    _syntax_ = "bufferization.clone {src.ssa_use} : {type.type}"
    _opname_ = "bufferization.clone"


# Deallocate a buffer
@dataclass
class DeallocOperation(DialectOp):
    buffer: SsaUse
    type: mast.Type
    _syntax_ = "bufferization.dealloc {buffer.ssa_use} : {type.type}"
    _opname_ = "bufferization.dealloc"


# Deallocate a tensor
@dataclass
class DeallocTensorOperation(DialectOp):
    tensor: SsaUse
    type: mast.TensorType
    _syntax_ = "bufferization.dealloc_tensor {tensor.ssa_use} : {type.tensor_type}"
    _opname_ = "bufferization.dealloc_tensor"


# Materialize a tensor into a destination buffer
@dataclass
class MaterializeInDestinationOperation(DialectOp):
    src: SsaUse
    dst: SsaUse
    src_type: mast.Type
    dst_type: mast.Type
    _syntax_ = "bufferization.materialize_in_destination {src.ssa_use} , {dst.ssa_use} : {src_type.type} to {dst_type.type}"
    _opname_ = "bufferization.materialize_in_destination"


# Convert tensor to buffer
@dataclass
class ToBufferOperation(DialectOp):
    tensor: SsaUse
    tensor_type: mast.TensorType
    buffer_type: mast.MemRefType
    _syntax_ = "bufferization.to_buffer {tensor.ssa_use} : {tensor_type.tensor_type} to {buffer_type.memref_type}"
    _opname_ = "bufferization.to_buffer"


# Convert buffer to tensor
@dataclass
class ToTensorOperation(DialectOp):
    buffer: SsaUse
    buffer_type: mast.MemRefType
    tensor_type: mast.TensorType
    _syntax_ = "bufferization.to_tensor {buffer.ssa_use} : {buffer_type.memref_type} to {tensor_type.tensor_type}"
    _opname_ = "bufferization.to_tensor"


# Inspect current module to get all classes defined above
bufferization = Dialect(
    "bufferization",
    ops=[
        m[1]
        for m in inspect.getmembers(
            sys.modules[__name__], lambda obj: is_op(obj, __name__)
        )
    ],
)
