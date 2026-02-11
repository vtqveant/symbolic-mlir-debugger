#!/usr/bin/env python3
"""
Abstract memory model for symbolic execution.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union, Any
import z3


class MemoryModel(ABC):
    """Abstract base class for memory models."""

    @abstractmethod
    def allocate(self, name: str, shape: Tuple[int, ...], dtype: str) -> None:
        """Allocate a new memory region (memref).

        Args:
            name: Memref SSA name
            shape: Tuple of dimension sizes (dynamic dimensions as -1?)
            dtype: Element type string (e.g., 'i32', 'f32')
        """
        pass

    @abstractmethod
    def load(
        self,
        memref: str,
        indices: List[Union[int, z3.ExprRef]],
        dtype: str,
    ) -> z3.ExprRef:
        """Load value from memory at given indices.

        Args:
            memref: Memref SSA name
            indices: List of index expressions (concrete int or symbolic)
            dtype: Element type

        Returns:
            Symbolic expression for the loaded value
        """
        pass

    @abstractmethod
    def store(
        self,
        memref: str,
        indices: List[Union[int, z3.ExprRef]],
        value: z3.ExprRef,
        dtype: str,
    ) -> None:
        """Store value to memory at given indices.

        Args:
            memref: Memref SSA name
            indices: List of index expressions
            value: Symbolic expression to store
            dtype: Element type
        """
        pass

    def reinterpret_cast(
        self,
        src: str,
        dst: str,
        offsets: List[Union[int, z3.ExprRef]],
        sizes: List[Union[int, z3.ExprRef]],
        strides: List[Union[int, z3.ExprRef]],
    ) -> None:
        """Create a new view (memref) that aliases existing memory.

        This is a memref-specific operation. Default implementation raises
        NotImplementedError for memory models that don't support views.

        Args:
            src: Source memref name
            dst: Destination memref name (new view)
            offsets: Offset for each dimension
            sizes: Size for each dimension
            strides: Stride for each dimension
        """
        raise NotImplementedError("reinterpret_cast not supported by this memory model")

    @abstractmethod
    def get_concrete_value(
        self,
        memref: str,
        indices: List[int],
    ) -> Optional[Any]:
        """Get concrete value stored at concrete indices.

        Args:
            memref: Memref SSA name
            indices: Concrete integer indices

        Returns:
            Concrete Python value (int, float, etc.) or None if not available
        """
        pass

    @abstractmethod
    def set_concrete_value(
        self,
        memref: str,
        indices: List[int],
        value: Any,
    ) -> None:
        """Set concrete value at concrete indices.

        Args:
            memref: Memref SSA name
            indices: Concrete integer indices
            value: Concrete Python value
        """
        pass

    def fork(self) -> "MemoryModel":
        """Create a deep copy of the memory model for forking states.

        Returns:
            New memory model instance with copied state
        """
        # Default implementation raises NotImplementedError
        raise NotImplementedError("fork not implemented")

    def get_all_memory_entries(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all memory entries for debugging/DAP.

        Returns:
            Dictionary mapping memref name to list of entries, each with
            indices, symbolic expression, and concrete value if available.
        """
        # Default implementation returns empty dict
        return {}
