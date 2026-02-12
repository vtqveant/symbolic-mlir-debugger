#!/usr/bin/env python3
"""
Tensor dialect execution handlers.

Handles operations: extract, insert, splat, etc.
"""

import z3
from typing import Any, Optional, Tuple, List, Union

from .base import OperationHandler
from ..operations import LoadOperation, StoreOperation, Operation
from ..models import SymbolicState, MLIRFunction


def parse_tensor_dimensions(tensor_type: str) -> List[str]:
    """Parse tensor type string and return list of dimension strings.

    Example: "tensor<?x?x10xi32>" -> ["?", "?", "10"]
    Handles nested types by skipping inside <> pairs.
    """
    # Find outermost '<' and '>'
    start = tensor_type.find("<")
    end = tensor_type.rfind(">")
    if start == -1 or end == -1:
        raise ValueError(f"Invalid tensor type: {tensor_type}")
    inner = tensor_type[start + 1 : end].strip()
    # Parse dimensions while skipping nested <>
    dimensions = []
    current = []
    depth = 0
    for ch in inner:
        if ch == "<":
            depth += 1
            current.append(ch)
        elif ch == ">":
            depth -= 1
            current.append(ch)
        elif ch == "x" and depth == 0:
            dimensions.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        dimensions.append("".join(current).strip())
    # The last token is element type, remove it
    if dimensions:
        dimensions.pop()
    return dimensions


def count_wildcards(dimensions: List[str]) -> int:
    """Count '?' wildcard dimensions."""
    return sum(1 for d in dimensions if d == "?")


def get_dimension_sizes(dimensions: List[str]) -> List[Union[int, None]]:
    """Convert dimension strings to int or None for wildcard."""
    result = []
    for d in dimensions:
        if d == "?":
            result.append(None)
        else:
            result.append(int(d))
    return result


class TensorExtractHandler(OperationHandler):
    """Handler for tensor.extract operation."""

    def execute_symbolic(
        self,
        op: LoadOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute tensor.extract symbolically."""
        if not isinstance(op, LoadOperation):
            raise TypeError(f"Expected LoadOperation, got {type(op)}")

        tensor = op.memref
        indices = op.indices

        # Try to get concrete indices
        concrete_indices = self._get_concrete_indices(indices, state)

        if concrete_indices is not None:
            # Multi-cell access with concrete indices
            tensor_value = state.get_memory_cell(tensor, concrete_indices)
            if tensor_value is None:
                # Uninitialized cell: create fresh symbolic value
                expr = z3.FreshConst(z3.IntSort(), f"tensor_{tensor}{concrete_indices}")
                state.set_memory_cell(
                    tensor, concrete_indices, expr, op.result_type or "i32"
                )
                tensor_value = state.get_memory_cell(tensor, concrete_indices)
            assert tensor_value is not None
            assert tensor_value.expr is not None
            state.set_value(op.dest, tensor_value.expr, op.result_type or "i32")
            # Try to get concrete value from tensor cell
            concrete_val = state.get_memory_cell_concrete(tensor, concrete_indices)
            if concrete_val is not None:
                state.set_concrete_value(op.dest, concrete_val)
        else:
            # Symbolic indices or no indices: fall back to single-cell model
            tensor_value = state.get_memory(tensor)
            if tensor_value is None:
                expr = z3.FreshConst(z3.IntSort(), f"tensor_{tensor}")
                state.set_memory(tensor, expr, op.result_type or "i32")
                tensor_value = state.get_memory(tensor)
            assert tensor_value is not None
            assert tensor_value.expr is not None
            state.set_value(op.dest, tensor_value.expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: LoadOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of tensor.extract."""
        tensor = op.memref
        indices = op.indices

        concrete_indices = self._get_concrete_indices(indices, state)
        if concrete_indices is not None:
            concrete_val = state.get_memory_cell_concrete(tensor, concrete_indices)
            if concrete_val is not None:
                return concrete_val

        # Check single-cell memory model
        tensor_concrete = state.get_concrete_value(tensor)
        if tensor_concrete is not None:
            return tensor_concrete

        return None

    def _get_concrete_indices(
        self, indices: list, state: SymbolicState
    ) -> Optional[Tuple[int, ...]]:
        """Convert index expressions to concrete tuple if all are concrete."""
        concrete_indices = []
        for idx in indices:
            idx_concrete = state.get_concrete_value(idx)
            if idx_concrete is None or not isinstance(idx_concrete, int):
                return None
            concrete_indices.append(idx_concrete)
        return tuple(concrete_indices)


class TensorInsertHandler(OperationHandler):
    """Handler for tensor.insert operation."""

    def execute_symbolic(
        self,
        op: StoreOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute tensor.insert symbolically."""
        if not isinstance(op, StoreOperation):
            raise TypeError(f"Expected StoreOperation, got {type(op)}")

        tensor = op.memref
        value = op.value
        indices = op.indices

        # Get value expression
        value_expr = state.get_expr(value)
        if value_expr is None:
            raise ValueError(f"Cannot get expression for value: {value}")

        # Try to get concrete indices
        concrete_indices = self._get_concrete_indices(indices, state)

        if concrete_indices is not None:
            # Multi-cell insert with concrete indices
            state.set_memory_cell(
                tensor, concrete_indices, value_expr, op.result_type or "i32"
            )
            # Store concrete value if available
            concrete_val = state.get_concrete_value(value)
            if concrete_val is not None:
                state.set_memory_cell_concrete(tensor, concrete_indices, concrete_val)
        else:
            # Symbolic indices or no indices: fall back to single-cell model
            state.set_memory(tensor, value_expr, op.result_type or "i32")
            # Store concrete value if available
            concrete_val = state.get_concrete_value(value)
            if concrete_val is not None:
                state.set_concrete_value(tensor, concrete_val)

    def _try_concrete_evaluation(
        self, op: StoreOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Insert operations don't produce values."""
        return None

    def _get_concrete_indices(
        self, indices: list, state: SymbolicState
    ) -> Optional[Tuple[int, ...]]:
        """Convert index expressions to concrete tuple if all are concrete."""
        concrete_indices = []
        for idx in indices:
            idx_concrete = state.get_concrete_value(idx)
            if idx_concrete is None or not isinstance(idx_concrete, int):
                return None
            concrete_indices.append(idx_concrete)
        return tuple(concrete_indices)


class TensorSplatHandler(OperationHandler):
    """Handler for tensor.splat operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute tensor.splat symbolically."""
        if not op.dest:
            raise ValueError("tensor.splat must have destination")

        # Extract dynamic sizes if present
        dynamic_sizes = op.attributes.get("dynamic_sizes", [])

        # Parse tensor type dimensions
        tensor_type = op.result_type or "tensor<?xi32>"
        dim_strings = parse_tensor_dimensions(tensor_type)
        wildcard_count = count_wildcards(dim_strings)
        if len(dynamic_sizes) != wildcard_count:
            raise ValueError(
                f"tensor.splat: expected {wildcard_count} dynamic sizes for type {tensor_type}, "
                f"got {len(dynamic_sizes)}"
            )

        # Build shape list
        shape = []
        dynamic_idx = 0
        for dim_str in dim_strings:
            if dim_str == "?":
                # Get dynamic size expression
                size_name = dynamic_sizes[dynamic_idx]
                # Strip leading '%' if present
                if size_name.startswith("%"):
                    size_name = size_name[1:]
                size_expr = state.get_expr(size_name)
                if size_expr is None:
                    # Create fresh symbolic expression for size
                    size_expr = z3.FreshConst(
                        z3.IntSort(), f"dim_{op.dest}_{dynamic_idx}"
                    )
                    state.set_value(size_name, size_expr, "index")
                shape.append(size_expr)
                dynamic_idx += 1
            else:
                shape.append(int(dim_str))

        # Store tensor shape in state
        state.set_tensor_shape(op.dest, shape)

        # Create a fresh symbolic tensor
        expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
        state.set_memory(op.dest, expr, tensor_type)
        state.set_value(op.dest, expr, tensor_type)

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Splat operations don't have simple concrete values."""
        return None


class TensorEmptyHandler(OperationHandler):
    """Handler for tensor.empty operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute tensor.empty symbolically."""
        if not op.dest:
            raise ValueError("tensor.empty must have destination")

        # Extract dynamic sizes if present
        dynamic_sizes = op.attributes.get("dynamic_sizes", [])

        # Parse tensor type dimensions
        tensor_type = op.result_type or "tensor<?xi32>"
        dim_strings = parse_tensor_dimensions(tensor_type)
        wildcard_count = count_wildcards(dim_strings)
        if len(dynamic_sizes) != wildcard_count:
            raise ValueError(
                f"tensor.empty: expected {wildcard_count} dynamic sizes for type {tensor_type}, "
                f"got {len(dynamic_sizes)}"
            )

        # Build shape list
        shape = []
        dynamic_idx = 0
        for dim_str in dim_strings:
            if dim_str == "?":
                size_name = dynamic_sizes[dynamic_idx]
                if size_name.startswith("%"):
                    size_name = size_name[1:]
                size_expr = state.get_expr(size_name)
                if size_expr is None:
                    size_expr = z3.FreshConst(
                        z3.IntSort(), f"dim_{op.dest}_{dynamic_idx}"
                    )
                    state.set_value(size_name, size_expr, "index")
                shape.append(size_expr)
                dynamic_idx += 1
            else:
                shape.append(int(dim_str))

        # Store tensor shape in state
        state.set_tensor_shape(op.dest, shape)

        # Create a fresh symbolic tensor (contents unspecified)
        expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
        state.set_memory(op.dest, expr, tensor_type)
        state.set_value(op.dest, expr, tensor_type)

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """empty operations don't have simple concrete values."""
        return None


class TensorGenerateHandler(OperationHandler):
    """Handler for tensor.generate operation."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute tensor.generate symbolically."""
        if not op.dest:
            raise ValueError("tensor.generate must have destination")

        # Extract dynamic extents if present
        dynamic_extents = op.attributes.get("dynamic_extents", [])

        # Parse tensor type dimensions
        tensor_type = op.result_type or "tensor<?xi32>"
        dim_strings = parse_tensor_dimensions(tensor_type)
        wildcard_count = count_wildcards(dim_strings)
        if len(dynamic_extents) != wildcard_count:
            raise ValueError(
                f"tensor.generate: expected {wildcard_count} dynamic extents for type {tensor_type}, "
                f"got {len(dynamic_extents)}"
            )

        # Build shape list
        shape = []
        dynamic_idx = 0
        for dim_str in dim_strings:
            if dim_str == "?":
                size_name = dynamic_extents[dynamic_idx]
                if size_name.startswith("%"):
                    size_name = size_name[1:]
                size_expr = state.get_expr(size_name)
                if size_expr is None:
                    size_expr = z3.FreshConst(
                        z3.IntSort(), f"dim_{op.dest}_{dynamic_idx}"
                    )
                    state.set_value(size_name, size_expr, "index")
                shape.append(size_expr)
                dynamic_idx += 1
            else:
                shape.append(int(dim_str))

        # Store tensor shape in state
        state.set_tensor_shape(op.dest, shape)

        # Create a fresh symbolic tensor (contents from region, ignored for now)
        expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
        state.set_memory(op.dest, expr, tensor_type)
        state.set_value(op.dest, expr, tensor_type)

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """generate operations don't have simple concrete values."""
        return None


# Function to register all tensor dialect handlers
def register_handlers(registry) -> None:
    """Register tensor dialect handlers with registry."""
    registry.register("tensor.extract", TensorExtractHandler())
    registry.register("tensor.insert", TensorInsertHandler())
    registry.register("tensor.splat", TensorSplatHandler())
    registry.register("tensor.empty", TensorEmptyHandler())
    registry.register("tensor.generate", TensorGenerateHandler())
