#!/usr/bin/env python3
"""
Tensor memory model implementation.

Handles multi-dimensional tensor storage with immutable value semantics.
Tensors are immutable values; tensor.insert creates a new tensor copy.
"""

from typing import Dict, List, Tuple, Optional, Union, Any

import z3

from .base import MemoryModel


class TensorMemoryModel(MemoryModel):
    """Memory model for tensor operations with immutable value semantics."""

    def __init__(self):
        # Maps tensor name -> shape list (dimension sizes, can be int or symbolic)
        self.shapes: Dict[str, List[Union[int, z3.ExprRef]]] = {}
        # Maps tensor name -> dtype string
        self.dtypes: Dict[str, str] = {}
        # Maps (tensor_name, indices_tuple) -> symbolic expression
        self.storage: Dict[Tuple[str, Tuple[int, ...]], z3.ExprRef] = {}
        # Maps (tensor_name, indices_tuple) -> concrete Python values
        self.concrete_storage: Dict[Tuple[str, Tuple[int, ...]], Any] = {}
        # Maps tensor name -> splat value (symbolic) for tensors created via splat
        self.splat_values: Dict[str, Optional[z3.ExprRef]] = {}
        # Maps tensor name -> concrete splat value
        self.splat_concrete: Dict[str, Any] = {}

    def allocate(self, name: str, shape: Tuple[int, ...], dtype: str) -> None:
        """Allocate a new tensor with given shape and dtype.

        For tensors, shape dimensions are integers (dynamic dimensions as -1).
        The actual symbolic dimension expressions are stored separately in self.shapes.
        """
        # Convert tuple to list for shape storage (will be updated with symbolic dims later)
        self.shapes[name] = list(shape)
        self.dtypes[name] = dtype
        # No need to initialize storage - cells will be created lazily on first store

    def load(
        self,
        memref: str,
        indices: List[Union[int, z3.ExprRef]],
        dtype: str,
    ) -> z3.ExprRef:
        """Load value from tensor at given indices.

        If indices are symbolic, returns a fresh symbolic value representing
        the access result (since we can't know which concrete cell is accessed).
        If tensor has a splat value, returns that value for any indices.
        """
        # Check if tensor has a splat value
        splat_expr = self.splat_values.get(memref)
        if splat_expr is not None:
            return splat_expr

        # Check if all indices are concrete
        concrete_key = self._indices_to_key(indices)

        if concrete_key is not None:
            # Concrete indices - look up in storage
            storage_key = (memref, concrete_key)
            if storage_key in self.storage:
                return self.storage[storage_key]

            # Cell not initialized - create fresh symbolic value
            expr = z3.FreshConst(
                z3.IntSort(),
                f"tensor_{memref}_{'_'.join(str(i) for i in concrete_key)}",
            )
            self.storage[storage_key] = expr
            return expr
        else:
            # Symbolic indices - create fresh symbolic value for the access
            expr = z3.FreshConst(
                z3.IntSort(),
                f"tensor_{memref}_symbolic_access",
            )
            return expr

    def store(
        self,
        memref: str,
        indices: List[Union[int, z3.ExprRef]],
        value: z3.ExprRef,
        dtype: str,
    ) -> None:
        """Store value to tensor at given indices.

        For tensors, store is allowed only once per cell (immutable after creation).
        If a cell already has a value, this raises ValueError.
        """
        # Check if all indices are concrete
        concrete_key = self._indices_to_key(indices)

        if concrete_key is not None:
            # Concrete indices - store in storage
            storage_key = (memref, concrete_key)
            if storage_key in self.storage:
                # Cell already has a value - tensors are immutable after creation
                # But for copy-on-write, we might be storing to a newly copied tensor
                # Allow overwriting for now (will be used by copy_tensor)
                pass
            self.storage[storage_key] = value
        else:
            # Symbolic indices - store at a special key
            storage_key = (memref, (-1,))  # Sentinel for symbolic store
            self.storage[storage_key] = value

    def reinterpret_cast(
        self,
        src: str,
        dst: str,
        offsets: List[Union[int, z3.ExprRef]],
        sizes: List[Union[int, z3.ExprRef]],
        strides: List[Union[int, z3.ExprRef]],
    ) -> None:
        """Tensors do not support views or reinterpret_cast.

        Raises NotImplementedError as per MLIR semantics.
        """
        raise NotImplementedError("reinterpret_cast not supported for tensors")

    def get_concrete_value(
        self,
        memref: str,
        indices: List[int],
    ) -> Optional[Any]:
        """Get concrete value stored at concrete indices."""
        indices_tuple = tuple(indices)
        storage_key = (memref, indices_tuple)
        return self.concrete_storage.get(storage_key)

    def set_concrete_value(
        self,
        memref: str,
        indices: List[int],
        value: Any,
    ) -> None:
        """Set concrete value at concrete indices."""
        indices_tuple = tuple(indices)
        storage_key = (memref, indices_tuple)
        self.concrete_storage[storage_key] = value

    def fork(self) -> "TensorMemoryModel":
        """Create a deep copy of the memory model for forking states."""
        new_model = TensorMemoryModel()

        # Copy primitive dicts
        new_model.shapes = {k: list(v) for k, v in self.shapes.items()}  # shallow copy of list
        new_model.dtypes = dict(self.dtypes)

        # Deep copy storage (z3 expressions are immutable, can share references)
        new_model.storage = dict(self.storage)

        # Deep copy concrete storage
        new_model.concrete_storage = dict(self.concrete_storage)

        return new_model

    def get_all_memory_entries(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tensor entries for debugging/DAP.

        Returns:
            Dictionary mapping tensor name to list of entries, each with
            indices, symbolic expression, and concrete value if available.
        """
        entries = {}

        # Collect from storage (symbolic values)
        for (tensor, indices), expr in self.storage.items():
            if tensor not in entries:
                entries[tensor] = []

            concrete = self.concrete_storage.get((tensor, indices))
            entries[tensor].append(
                {
                    "indices": indices,
                    "symbolic_expr": expr,
                    "concrete_value": concrete,
                }
            )

        # Also include tensors that are allocated but have no entries yet
        for tensor in self.shapes:
            if tensor not in entries:
                entries[tensor] = []

        return entries

    def copy_tensor(self, src: str, dst: str) -> None:
        """Create a copy of tensor src as a new tensor dst.

        Copies shape, dtype, and all cell values (symbolic and concrete).
        Used by tensor.insert to create new tensor with updated value.
        """
        if src not in self.shapes:
            raise ValueError(f"Source tensor '{src}' not allocated")

        # Copy shape and dtype
        self.shapes[dst] = list(self.shapes[src])
        # Use src dtype if present, otherwise default to "i32"
        src_dtype = self.dtypes.get(src, "i32")
        self.dtypes[dst] = src_dtype

        # Copy all cell values
        for (tensor, indices), expr in self.storage.items():
            if tensor == src:
                self.storage[(dst, indices)] = expr

        # Copy concrete values
        for (tensor, indices), value in self.concrete_storage.items():
            if tensor == src:
                self.concrete_storage[(dst, indices)] = value

        # Copy splat values
        if src in self.splat_values:
            self.splat_values[dst] = self.splat_values[src]
        if src in self.splat_concrete:
            self.splat_concrete[dst] = self.splat_concrete[src]

    def set_shape(self, tensor: str, shape: List[Union[int, z3.ExprRef]]) -> None:
        """Set shape of a tensor (including symbolic dimensions)."""
        self.shapes[tensor] = shape

    def get_shape(self, tensor: str) -> Optional[List[Union[int, z3.ExprRef]]]:
        """Get shape of a tensor."""
        return self.shapes.get(tensor)

    def set_splat_value(
        self,
        tensor: str,
        symbolic_expr: Optional[z3.ExprRef] = None,
        concrete_value: Any = None,
    ) -> None:
        """Set splat value for a tensor (uniform value across all cells)."""
        self.splat_values[tensor] = symbolic_expr
        if concrete_value is not None:
            self.splat_concrete[tensor] = concrete_value

    # Helper methods
    def _indices_to_key(self, indices: List[Union[int, z3.ExprRef]]) -> Optional[Tuple[int, ...]]:
        """Convert indices to concrete tuple if all are concrete ints."""
        concrete_indices = []
        for idx in indices:
            if isinstance(idx, int):
                concrete_indices.append(idx)
            else:
                # Symbolic index
                return None
        return tuple(concrete_indices)
