#!/usr/bin/env python3
"""
Dialect parser modules for converting pymlir AST to interpreter Operation objects.

Each dialect should provide a parser module that converts dialect-specific
AST nodes directly to interpreter Operation objects, skipping the intermediate
dictionary representation.
"""

from .base import BaseDialectParser, DialectParserRegistry
from .arith import ArithDialectParser
from .memref import MemrefDialectParser
from .tensor import TensorDialectParser
from .affine import AffineDialectParser
from .cf import CfDialectParser
from .scf import ScfDialectParser
from .func import FuncDialectParser
from .linalg import LinalgDialectParser
from .math import MathDialectParser
from .index import IndexDialectParser
from .bufferization import BufferizationDialectParser
from .shape import ShapeDialectParser
from .vector import VectorDialectParser
from .builtin import BuiltinDialectParser
from .emitc import EmitcDialectParser

__all__ = [
    "BaseDialectParser",
    "DialectParserRegistry",
    "ArithDialectParser",
    "MemrefDialectParser",
    "TensorDialectParser",
    "AffineDialectParser",
    "CfDialectParser",
    "ScfDialectParser",
    "FuncDialectParser",
    "LinalgDialectParser",
    "MathDialectParser",
    "IndexDialectParser",
    "BufferizationDialectParser",
    "ShapeDialectParser",
    "VectorDialectParser",
    "BuiltinDialectParser",
    "EmitcDialectParser",
]


def register_default_parsers(registry: DialectParserRegistry) -> None:
    """Register default dialect parsers with the registry."""
    registry.register_dialect("arith", ArithDialectParser())
    registry.register_dialect("memref", MemrefDialectParser())
    registry.register_dialect("tensor", TensorDialectParser())
    affine_parser = AffineDialectParser()
    registry.register_dialect("affine", affine_parser)
    cf_parser = CfDialectParser()
    registry.register_dialect("cf", cf_parser)
    scf_parser = ScfDialectParser()
    registry.register_dialect("scf", scf_parser)
    func_parser = FuncDialectParser()
    registry.register_dialect("func", func_parser)
    linalg_parser = LinalgDialectParser()
    registry.register_dialect("linalg", linalg_parser)
    registry.register_dialect("math", MathDialectParser())
    registry.register_dialect("index", IndexDialectParser())
    registry.register_dialect("bufferization", BufferizationDialectParser())
    registry.register_dialect("shape", ShapeDialectParser())
    registry.register_dialect("vector", VectorDialectParser())
    builtin_parser = BuiltinDialectParser()
    registry.register_dialect("builtin", builtin_parser)
    registry.register_dialect("emitc", EmitcDialectParser())
    # Register operation handlers for builtin operations
    registry.register_operation(
        "ReturnOperation", builtin_parser._parse_return_operation
    )
    # Register operation handlers for scf operations
    registry.register_operation("SCFForOp", scf_parser._parse_scf_for_operation)
    registry.register_operation("SCFIfOp", scf_parser._parse_scf_if_operation)
    registry.register_operation("SCFYield", scf_parser._parse_scf_yield_operation)
    registry.register_operation(
        "SCFConditionOp", scf_parser._parse_scf_condition_operation
    )
    # Register operation handlers for affine operations (since they lack _opname_)
    registry.register_operation(
        "AffineForOp", affine_parser._parse_affine_for_operation
    )
    registry.register_operation("AffineIfOp", affine_parser._parse_affine_if_operation)
    registry.register_operation(
        "AffineLoadOp", affine_parser._parse_affine_load_operation
    )
    registry.register_operation(
        "AffineStoreOp", affine_parser._parse_affine_store_operation
    )
    # Register operation handlers for func operations (since they lack _opname_)
    registry.register_operation("CallOperation", func_parser._parse_call_operation)
    registry.register_operation(
        "CallIndirectOperation", func_parser._parse_call_indirect_operation
    )
    # Register operation handlers for linalg operations (since they lack _opname_)
    registry.register_operation(
        "LinalgGeneric", linalg_parser._parse_linalg_generic_operation
    )
    registry.register_operation(
        "LinalgMatmul", linalg_parser._parse_linalg_matmul_operation
    )
    registry.register_operation(
        "LinalgBatchMatmul", linalg_parser._parse_linalg_batch_matmul_operation
    )
    registry.register_operation(
        "LinalgYield", linalg_parser._parse_linalg_yield_operation
    )
    # Register operation handlers for cf operations
    registry.register_operation("BrOperation", cf_parser._parse_br_operation)
    registry.register_operation("CondBrOperation", cf_parser._parse_cond_br_operation)
    # Add more default parsers here as they are implemented
