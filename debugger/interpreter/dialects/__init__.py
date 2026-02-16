#!/usr/bin/env python3
"""
Dialect registry for operation execution.

Automatically discovers and registers dialect handlers.
"""

from typing import Optional
import importlib

from .base import DialectRegistry, OperationHandler

# Global dialect registry
_registry: Optional[DialectRegistry] = None


def get_registry() -> DialectRegistry:
    """Get or create the global dialect registry."""
    global _registry
    if _registry is None:
        _registry = DialectRegistry()
        _register_all_dialects(_registry)
    return _registry


def _register_all_dialects(registry: DialectRegistry) -> None:
    """Register handlers from all available dialect modules."""
    # List of available dialect modules (mirroring parser/dialects/)
    dialect_modules = [
        "arith",
        "memref",
        "cf",
        "func",
        "tensor",
        "shape",
        "scf",
        "affine",
        "linalg",
        "bufferization",
        "vector",
        "emitc",
        "math",
        "index",
        "builtin",
    ]

    for dialect_name in dialect_modules:
        try:
            module_name = f".{dialect_name}"
            module = importlib.import_module(module_name, package=__name__)

            if hasattr(module, "register_handlers"):
                module.register_handlers(registry)
                # print(f"Registered handlers for {dialect_name} dialect")  # Debug
        except ImportError:
            # Dialect module not implemented yet
            # print(f"Note: {dialect_name} dialect not implemented: {e}")  # Debug
            pass
        except Exception as e:
            # Don't fail registration if one dialect fails
            print(f"Warning: Failed to register {dialect_name} dialect: {e}")
            continue


# Convenience functions for using the registry
def execute_operation(op, state, func, mode="symbolic") -> None:
    """Execute operation using registered handler."""
    registry = get_registry()
    registry.execute(op, state, func, mode)


def get_handler(op_name: str) -> Optional[OperationHandler]:
    """Get handler for operation name."""
    registry = get_registry()
    return registry.get_handler(op_name)


def register_handler(op_name: str, handler: OperationHandler) -> None:
    """Register custom handler for operation name."""
    registry = get_registry()
    registry.register(op_name, handler)


# Export public API
__all__ = [
    "get_registry",
    "execute_operation",
    "get_handler",
    "register_handler",
    "DialectRegistry",
    "OperationHandler",
]
