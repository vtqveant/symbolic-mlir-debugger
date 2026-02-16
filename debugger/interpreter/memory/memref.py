#!/usr/bin/env python3
"""
Memref memory model implementation.

Handles multi-dimensional memory storage with support for symbolic indices
and memref views (reinterpret_cast).
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Union, Any

import z3

from .base import MemoryModel


@dataclass
class MemrefView:
    """Represents a memref view (reinterpret_cast result).

    A view aliases underlying memory with different offset, sizes, strides.
    """

    # Reference to underlying memref (base allocation name)
    base: str
    # Transform: offset[i] + index[i] * stride[i]
    offsets: List[Union[int, z3.ExprRef]]
    sizes: List[Union[int, z3.ExprRef]]
    strides: List[Union[int, z3.ExprRef]]

    def map_indices(self, indices: List[Union[int, z3.ExprRef]]) -> List[Union[int, z3.ExprRef]]:
        """Map view indices to base indices."""
        if len(indices) != len(self.offsets):
            raise ValueError(f"Indices count {len(indices)} != view rank {len(self.offsets)}")

        # Apply offset + index * stride for each dimension
        mapped = []
        for i, idx in enumerate(indices):
            offset = self.offsets[i]
            stride = self.strides[i]

            # Compute offset + idx * stride
            if isinstance(idx, int) and isinstance(offset, int) and isinstance(stride, int):
                mapped.append(offset + idx * stride)
            elif isinstance(idx, int) and isinstance(offset, int):
                # offset is int, stride might be symbolic
                if stride == 1:
                    mapped.append(offset + idx)
                else:
                    # Need Z3 expression
                    mapped.append(offset + idx * stride)
            elif isinstance(idx, int) and isinstance(stride, int):
                # idx and stride are int, offset symbolic
                mapped.append(offset + idx * stride)
            elif isinstance(offset, int) and isinstance(stride, int):
                # offset and stride int, idx symbolic
                mapped.append(offset + idx * stride)
            else:
                # Mixed symbolic
                mapped.append(offset + idx * stride)

        return mapped


class MemrefMemoryModel(MemoryModel):
    """Memory model for memref operations with symbolic index support."""

    def __init__(self):
        # Maps memref name -> shape tuple
        self.shapes: Dict[str, Tuple[int, ...]] = {}
        # Maps memref name -> dtype string
        self.dtypes: Dict[str, str] = {}
        # Maps (memref_name, indices_tuple) -> symbolic expression
        self.storage: Dict[Tuple[str, Tuple[int, ...]], z3.ExprRef] = {}
        # Maps memref name -> concrete Python values (for concolic execution)
        self.concrete_storage: Dict[Tuple[str, Tuple[int, ...]], Any] = {}
        # Views created via reinterpret_cast: dest -> MemrefView
        self.views: Dict[str, MemrefView] = {}
        # Track which memrefs are base allocations (not views)
        self.base_allocations: Dict[str, bool] = {}

    def allocate(self, name: str, shape: Tuple[int, ...], dtype: str) -> None:
        """Allocate a new memref (base allocation)."""
        self.shapes[name] = shape
        self.dtypes[name] = dtype
        self.base_allocations[name] = True

        # Initialize storage for all indices? Not necessary - lazy allocation
        # We'll create entries on first store

    def _resolve_memref(self, memref: str) -> Tuple[str, Optional[MemrefView]]:
        """Resolve memref to its base allocation and view transformation.

        Returns:
            Tuple of (base_memref_name, view_or_none)
        """
        if memref in self.views:
            view = self.views[memref]
            return (view.base, view)
        return (memref, None)

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

    def load(
        self,
        memref: str,
        indices: List[Union[int, z3.ExprRef]],
        dtype: str,
    ) -> z3.ExprRef:
        """Load value from memory at given indices."""
        # Resolve view if any
        base_memref, view = self._resolve_memref(memref)

        # Map indices through view if needed
        if view is not None:
            mapped_indices = view.map_indices(indices)
        else:
            mapped_indices = indices

        # Check if all indices are concrete
        concrete_key = self._indices_to_key(mapped_indices)

        if concrete_key is not None:
            # Concrete indices - look up in storage
            storage_key = (base_memref, concrete_key)
            if storage_key in self.storage:
                return self.storage[storage_key]

            # Not found - create fresh symbolic value
            expr = z3.FreshConst(
                z3.IntSort(),
                f"memref_{base_memref}_{'_'.join(str(i) for i in concrete_key)}",
            )
            self.storage[storage_key] = expr
            return expr
        else:
            # Symbolic indices - create fresh symbolic value
            # For now, create a single symbolic variable for the entire access
            # In the future, we could track constraints between indices
            expr = z3.FreshConst(
                z3.IntSort(),
                f"memref_{base_memref}_symbolic_access",
            )
            return expr

    def store(
        self,
        memref: str,
        indices: List[Union[int, z3.ExprRef]],
        value: z3.ExprRef,
        dtype: str,
    ) -> None:
        """Store value to memory at given indices."""
        # Resolve view if any
        base_memref, view = self._resolve_memref(memref)

        # Map indices through view if needed
        if view is not None:
            mapped_indices = view.map_indices(indices)
        else:
            mapped_indices = indices

        # Check if all indices are concrete
        concrete_key = self._indices_to_key(mapped_indices)

        if concrete_key is not None:
            # Concrete indices - store in storage
            storage_key = (base_memref, concrete_key)
            self.storage[storage_key] = value
        else:
            # Symbolic indices - for now, we can't store at symbolic indices
            # without knowing which concrete cells are affected.
            # We could create a fresh symbolic value and add constraints,
            # but for simplicity, we'll store at a special key.
            # This is a limitation of the current implementation.
            storage_key = (base_memref, (-1,))  # Sentinel for symbolic store
            self.storage[storage_key] = value

    def reinterpret_cast(
        self,
        src: str,
        dst: str,
        offsets: List[Union[int, z3.ExprRef]],
        sizes: List[Union[int, z3.ExprRef]],
        strides: List[Union[int, z3.ExprRef]],
    ) -> None:
        """Create a new view (memref) that aliases existing memory."""
        # src must exist (as base allocation or another view)
        base_src, src_view = self._resolve_memref(src)

        if src_view is not None:
            # src is already a view, we need to compose transformations
            # For now, create view from the base allocation
            # This is a simplification - proper composition would require
            # applying src_view.transform then new transform
            pass

        # Create new view
        view = MemrefView(
            base=base_src,
            offsets=offsets,
            sizes=sizes,
            strides=strides,
        )
        self.views[dst] = view
        self.base_allocations[dst] = False

        # Copy shape and dtype from src (but with new sizes)
        # Actually sizes define the new shape
        self.shapes[dst] = tuple(sizes)  # Note: sizes could be symbolic
        self.dtypes[dst] = self.dtypes.get(base_src, "i32")

    def get_concrete_value(
        self,
        memref: str,
        indices: List[int],
    ) -> Optional[Any]:
        """Get concrete value stored at concrete indices."""
        # Resolve view if any
        base_memref, view = self._resolve_memref(memref)

        # Map indices through view if needed
        if view is not None:
            mapped_indices = view.map_indices(indices)
            # Ensure mapped indices are concrete
            if any(not isinstance(idx, int) for idx in mapped_indices):
                return None
            indices_tuple = tuple(mapped_indices)
        else:
            indices_tuple = tuple(indices)

        storage_key = (base_memref, indices_tuple)
        return self.concrete_storage.get(storage_key)

    def set_concrete_value(
        self,
        memref: str,
        indices: List[int],
        value: Any,
    ) -> None:
        """Set concrete value at concrete indices."""
        # Resolve view if any
        base_memref, view = self._resolve_memref(memref)

        # Map indices through view if needed
        if view is not None:
            mapped_indices = view.map_indices(indices)
            # Ensure mapped indices are concrete
            if any(not isinstance(idx, int) for idx in mapped_indices):
                # Can't set concrete value at symbolic mapped indices
                return
            indices_tuple = tuple(mapped_indices)
        else:
            indices_tuple = tuple(indices)

        storage_key = (base_memref, indices_tuple)
        self.concrete_storage[storage_key] = value

    def fork(self) -> "MemrefMemoryModel":
        """Create a deep copy of the memory model for forking states."""
        new_model = MemrefMemoryModel()

        # Copy primitive dicts
        new_model.shapes = dict(self.shapes)
        new_model.dtypes = dict(self.dtypes)
        new_model.base_allocations = dict(self.base_allocations)

        # Deep copy storage (z3 expressions are immutable, can share references)
        new_model.storage = dict(self.storage)

        # Deep copy concrete storage
        new_model.concrete_storage = dict(self.concrete_storage)

        # Deep copy views (need to copy MemrefView objects)
        new_model.views = {}
        for name, view in self.views.items():
            # Create new MemrefView with same data (lists are mutable, copy them)
            new_view = MemrefView(
                base=view.base,
                offsets=list(view.offsets),
                sizes=list(view.sizes),
                strides=list(view.strides),
            )
            new_model.views[name] = new_view

        return new_model

    def get_all_memory_entries(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all memory entries for debugging/DAP.

        Returns:
            Dictionary mapping memref name to list of entries, each with
            indices, symbolic expression, and concrete value if available.
        """
        entries = {}

        # Collect from storage (symbolic values)
        for (memref, indices), expr in self.storage.items():
            if memref not in entries:
                entries[memref] = []

            concrete = self.concrete_storage.get((memref, indices))
            entries[memref].append(
                {
                    "indices": indices,
                    "symbolic_expr": expr,
                    "concrete_value": concrete,
                }
            )

        # Also include memrefs that are allocated but have no entries yet
        for memref in self.shapes:
            if memref not in entries:
                entries[memref] = []

        return entries
