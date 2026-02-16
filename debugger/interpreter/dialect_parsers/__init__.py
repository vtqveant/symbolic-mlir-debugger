#!/usr/bin/env python3
"""
Dialect parser modules for converting pymlir AST to interpreter Operation objects.

Each dialect should provide a parser module that converts dialect-specific
AST nodes directly to interpreter Operation objects, skipping the intermediate
dictionary representation.
"""

from .affine import AffineDialectParser
from .arith import ArithDialectParser
from .base import BaseDialectParser, DialectParserRegistry
from .bufferization import BufferizationDialectParser
from .builtin import BuiltinDialectParser
from .cf import CfDialectParser
from .emitc import EmitcDialectParser
from .func import FuncDialectParser
from .index import IndexDialectParser
from .linalg import LinalgDialectParser
from .math import MathDialectParser
from .memref import MemrefDialectParser
from .scf import ScfDialectParser
from .shape import ShapeDialectParser
from .tensor import TensorDialectParser
from .vector import VectorDialectParser

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
    # Add more default parsers here as they are implemented
