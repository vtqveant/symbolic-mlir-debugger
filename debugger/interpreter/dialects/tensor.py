#!/usr/bin/env python3
"""
Tensor dialect execution handlers.

Handles operations: extract, insert, splat, etc.
"""

import z3
from typing import Any, Optional, Tuple, List, Union

from .base import OperationHandler
from ..operations import LoadOperation, StoreOperation, Operation, UnaryOperation
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


def extract_element_type(tensor_type: str) -> str:
    """Extract element type from tensor type string."""
    # Find outermost '<' and '>'
    start = tensor_type.find("<")
    end = tensor_type.rfind(">")
    if start == -1 or end == -1:
        return "i32"  # fallback
    inner = tensor_type[start + 1 : end].strip()
    # Find last 'x' not inside nested <>
    depth = 0
    last_x_pos = -1
    for i, ch in enumerate(inner):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == "x" and depth == 0:
            last_x_pos = i
    if last_x_pos == -1:
        return inner.strip()
    return inner[last_x_pos + 1 :].strip()


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
        dtype = op.result_type or "i32"

        # Convert index names to values (int or z3 expression)
        index_values = []
        for idx_name in indices:
            # Try to get concrete value first
            concrete = state.get_concrete_value(idx_name)
            if concrete is not None and isinstance(concrete, int):
                index_values.append(concrete)
                continue
            # Try to parse as integer constant
            try:
                val = int(idx_name)
                index_values.append(val)
                continue
            except (ValueError, TypeError):
                pass
            # Get symbolic expression
            expr = state.get_expr(idx_name)
            if expr is None:
                # Create fresh symbolic index
                expr = z3.FreshConst(z3.IntSort(), f"index_{idx_name}")
                state.set_value(idx_name, expr, "index")
            index_values.append(expr)

        # Load from tensor memory model
        expr = state.tensor_memory_model.load(tensor, index_values, dtype)
        if op.dest:
            state.set_value(op.dest, expr, dtype)

        # Try to get concrete value
        concrete_val = self._try_concrete_evaluation(op, state, func)
        if concrete_val is not None and op.dest:
            state.set_concrete_value(op.dest, concrete_val)

    def _try_concrete_evaluation(
        self, op: LoadOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of tensor.extract."""
        tensor = op.memref
        indices = op.indices

        concrete_indices = self._get_concrete_indices(indices, state)
        if concrete_indices is not None:
            concrete_val = state.tensor_memory_model.get_concrete_value(
                tensor, list(concrete_indices)
            )
            if concrete_val is not None:
                return concrete_val

        # No concrete value found
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
        """Execute tensor.insert symbolically using copy-on-write semantics."""

        if not isinstance(op, StoreOperation):
            raise TypeError(f"Expected StoreOperation, got {type(op)}")

        src_tensor = op.memref
        value = op.value
        indices = op.indices

        # Destination tensor (result of insert)
        if not op.dest:
            raise ValueError("tensor.insert must have destination tensor")
        dst_tensor = op.dest

        # Get value expression
        value_expr = state.get_expr(value)
        if value_expr is None:
            raise ValueError(f"Cannot get expression for value: {value}")

        # Get concrete value if available
        concrete_val = state.get_concrete_value(value)

        # Parse indices (convert to int or z3 expression)
        index_values = []
        concrete_indices = []
        all_concrete = True
        for idx_name in indices:
            # Try to get concrete value first
            concrete = state.get_concrete_value(idx_name)
            if concrete is not None and isinstance(concrete, int):
                index_values.append(concrete)
                if concrete_indices is not None:
                    concrete_indices.append(concrete)
                continue
            # Try to parse as integer constant
            try:
                val = int(idx_name)
                index_values.append(val)
                if concrete_indices is not None:
                    concrete_indices.append(val)
                continue
            except (ValueError, TypeError):
                pass
            # Get symbolic expression
            expr = state.get_expr(idx_name)
            if expr is None:
                # Create fresh symbolic index
                expr = z3.FreshConst(z3.IntSort(), f"index_{idx_name}")
                state.set_value(idx_name, expr, "index")
            index_values.append(expr)
            all_concrete = False
            concrete_indices = None  # Can't use concrete indices if any symbolic

        # Extract element type from tensor type
        tensor_type = op.result_type or "tensor<?xi32>"
        element_type = self._extract_element_type(tensor_type)

        # Debug
        # Copy source tensor to destination (copy-on-write)
        state.tensor_memory_model.copy_tensor(src_tensor, dst_tensor)

        # Store value at indices in destination tensor
        state.tensor_memory_model.store(
            dst_tensor, index_values, value_expr, element_type
        )

        # Store concrete value if available and indices are concrete
        if concrete_val is not None and all_concrete and concrete_indices is not None:
            state.tensor_memory_model.set_concrete_value(
                dst_tensor, concrete_indices, concrete_val
            )

        # Also set the destination value in state's value map (tensor as whole)
        # For tensors, we can store a reference to the tensor memory
        tensor_expr = z3.FreshConst(z3.IntSort(), f"tensor_{dst_tensor}")
        state.set_value(dst_tensor, tensor_expr, tensor_type)

    def _extract_element_type(self, tensor_type: str) -> str:
        """Extract element type from tensor type string."""
        # Find outermost '<' and '>'
        start = tensor_type.find("<")
        end = tensor_type.rfind(">")
        if start == -1 or end == -1:
            return "i32"  # fallback
        inner = tensor_type[start + 1 : end].strip()
        # Find last 'x' not inside nested <>
        depth = 0
        last_x_pos = -1
        for i, ch in enumerate(inner):
            if ch == "<":
                depth += 1
            elif ch == ">":
                depth -= 1
            elif ch == "x" and depth == 0:
                last_x_pos = i
        if last_x_pos == -1:
            return inner.strip()
        return inner[last_x_pos + 1 :].strip()

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

        # Get value operand (splat value)
        value_operand = None
        if isinstance(op, UnaryOperation):
            value_operand = op.operand
        else:
            # Fallback to attributes
            value_operand = op.attributes.get("arg")
            if value_operand is None:
                # Try "value" attribute
                value_operand = op.attributes.get("value")

        if value_operand is None:
            raise ValueError("tensor.splat missing value operand")

        # Get value expression
        value_expr = state.get_expr(value_operand)
        if value_expr is None:
            # Create fresh symbolic value
            value_expr = z3.FreshConst(z3.IntSort(), f"val_{value_operand}")
            state.set_value(value_operand, value_expr, "i32")

        # Get concrete value if available
        concrete_val = state.get_concrete_value(value_operand)

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

        # Store tensor shape in tensor memory model
        state.set_tensor_shape(op.dest, shape)
        # Set dtype
        element_type = extract_element_type(tensor_type)
        state.tensor_memory_model.dtypes[op.dest] = element_type

        # Set splat value in tensor memory model
        state.tensor_memory_model.set_splat_value(
            tensor=op.dest,
            symbolic_expr=value_expr,
            concrete_value=concrete_val,
        )

        # Create a fresh symbolic tensor reference (for value map)
        expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
        state.set_value(op.dest, expr, tensor_type)
        # Do NOT store in legacy memory model

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

        # Store tensor shape in tensor memory model
        state.set_tensor_shape(op.dest, shape)

        # Create a fresh symbolic tensor reference (for value map)
        expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
        state.set_value(op.dest, expr, tensor_type)
        # Do NOT store in legacy memory model

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

        # Store tensor shape in tensor memory model
        state.set_tensor_shape(op.dest, shape)

        # Create a fresh symbolic tensor reference (for value map)
        expr = z3.FreshConst(z3.IntSort(), f"tensor_{op.dest}")
        state.set_value(op.dest, expr, tensor_type)
        # Do NOT store in legacy memory model

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
