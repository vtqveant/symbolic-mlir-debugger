#!/usr/bin/env python3
"""
Debug utilities for formatting MLIR values in DAP server.

Provides type-specific formatting for shape, vector, tensor, and memory values.
"""

from typing import Any, Dict, List, Optional, Tuple
import z3


def format_shape_value(shape_tuple: Tuple[int, ...]) -> str:
    """Format shape tuple as (dim1, dim2, ...)."""
    if isinstance(shape_tuple, tuple):
        return f"({', '.join(str(d) for d in shape_tuple)})"
    return str(shape_tuple)


def format_vector_value(vector_data: List[Any]) -> str:
    """Format vector/list as [v1, v2, ...]."""
    if isinstance(vector_data, list):
        return f"[{', '.join(str(v) for v in vector_data)}]"
    return str(vector_data)


def format_memory_cell(memref_name: str, indices: Tuple[int, ...], value: Any) -> str:
    """Format memory cell as memref_name[i][j] = value."""
    index_str = "".join(f"[{i}]" for i in indices)
    return f"{memref_name}{index_str} = {value}"


def format_value(value: Any, value_type: Optional[str] = None) -> str:
    """Format a value based on its type and content.

    Attempts to detect shape tuples, vectors, and other structured values.
    """
    if value_type is None:
        # Try to infer type from value
        if isinstance(value, tuple):
            return format_shape_value(value)
        elif isinstance(value, list):
            return format_vector_value(value)
        elif isinstance(value, z3.ExprRef):
            return str(value)
        else:
            return str(value)

    # Use type string for more precise formatting
    if value_type.startswith("shape"):
        if isinstance(value, tuple):
            return format_shape_value(value)
    elif value_type.startswith("vector"):
        if isinstance(value, list):
            return format_vector_value(value)
    elif value_type.startswith("tensor") or value_type.startswith("memref"):
        # For tensor/memref values, check if it's a single cell or structured
        if isinstance(value, tuple):
            # Could be shape tuple for tensor dimensions
            return format_shape_value(value)

    # Default string representation
    return str(value)


def get_variable_summary(
    name: str,
    value: Any,
    value_type: Optional[str] = None,
    concrete_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Create a DAP-compatible variable summary.

    Returns dictionary with name, value, type, and presentation hints.
    """
    summary = {"name": name}

    # Determine display value
    display_value = None
    if concrete_value is not None:
        display_value = format_value(concrete_value, value_type)
    elif value is not None:
        display_value = format_value(value, value_type)

    if display_value is not None:
        summary["value"] = display_value

    if value_type is not None:
        summary["type"] = value_type

    # Add presentation hints for DAP
    if value_type and value_type.startswith("shape"):
        summary["presentationHint"] = "shape"
    elif value_type and value_type.startswith("vector"):
        summary["presentationHint"] = "array"
    elif value_type and (
        value_type.startswith("tensor") or value_type.startswith("memref")
    ):
        summary["presentationHint"] = "data"

    return summary


def format_memory_summary(
    memory_cells: Dict[str, Dict[Tuple[int, ...], Any]],
) -> List[Dict[str, Any]]:
    """Format memory cells for DAP variable inspection.

    Returns list of variable summaries for memory regions.
    """
    summaries = []

    for memref_name, cells in memory_cells.items():
        if not cells:
            continue

        # Create summary for memory region
        region_summary = {
            "name": f"{memref_name} (memory)",
            "value": f"{len(cells)} cells",
            "type": "memory_region",
            "presentationHint": "data",
            "variablesReference": 0,  # Will be set by DAP server for expansion
        }
        summaries.append(region_summary)

    return summaries
