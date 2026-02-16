#!/usr/bin/env python3
"""
Data models for symbolic MLIR interpreter.
"""

from typing import Dict, List, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, field
import z3

from .memory.base import MemoryModel
from .memory.memref import MemrefMemoryModel
from .memory.tensor import TensorMemoryModel
from .operations import Operation, LoopOperation


@dataclass
class MLIRValue:
    """Represents an MLIR SSA value with symbolic expression."""

    name: str
    expr: Optional[z3.ExprRef] = None
    type: Optional[str] = None
    concrete: Optional[Any] = None

    def __repr__(self) -> str:
        return f"MLIRValue({self.name}, expr={self.expr}, concrete={self.concrete})"


@dataclass
class BasicBlock:
    """Represents a basic block in MLIR."""

    label: str
    line: int = 0  # Source line number (0 for implicit blocks)
    operations: List[Operation] = field(default_factory=list)
    parameters: List[Tuple[str, str]] = field(default_factory=list)  # [(name, type)]

    def add_operation(self, op: Operation) -> None:
        self.operations.append(op)


@dataclass
class ControlFlowGraph:
    """Control Flow Graph representation for MLIR function."""

    # Mapping from block label to list of successor block labels
    edges: Dict[str, List[str]] = field(default_factory=dict)
    # Mapping from block label to list of predecessor block labels (optional, can be computed)
    predecessors: Dict[str, List[str]] = field(default_factory=dict)
    # Entry block label (default first block)
    entry: str = "^entry"
    # Exit block labels (blocks with no successors, i.e., return or unreachable)
    exits: List[str] = field(default_factory=list)
    # Dominator tree (mapping from block label to set of dominators)
    dominators: Dict[str, Set[str]] = field(default_factory=dict)
    # Post-dominator tree (optional)
    post_dominators: Dict[str, Set[str]] = field(default_factory=dict)

    def add_edge(self, src: str, dst: str) -> None:
        """Add directed edge from src to dst."""
        if src not in self.edges:
            self.edges[src] = []
        if dst not in self.edges[src]:
            self.edges[src].append(dst)
        # Update predecessors
        if dst not in self.predecessors:
            self.predecessors[dst] = []
        if src not in self.predecessors[dst]:
            self.predecessors[dst].append(src)

    def add_node(self, label: str) -> None:
        """Ensure node exists in CFG (with empty edge lists)."""
        if label not in self.edges:
            self.edges[label] = []
        if label not in self.predecessors:
            self.predecessors[label] = []

    def compute_exits(self) -> None:
        """Compute exit blocks (nodes with no outgoing edges)."""
        self.exits = [node for node in self.edges if not self.edges[node]]

    def compute_dominators(self) -> None:
        """Compute dominators for all nodes using iterative algorithm."""
        # Initialize: all nodes dominated by all nodes
        all_nodes = set(self.edges.keys()) | set(self.predecessors.keys())
        if not all_nodes:
            return
        # Entry node dominates only itself
        dom = {node: set(all_nodes) for node in all_nodes}
        dom[self.entry] = {self.entry}
        changed = True
        while changed:
            changed = False
            for node in all_nodes:
                if node == self.entry:
                    continue
                # Intersection of dominators of all predecessors
                preds = self.predecessors.get(node, [])
                if not preds:
                    new_dom = set()
                else:
                    new_dom = set.intersection(*(dom[p] for p in preds))
                new_dom.add(node)
                if new_dom != dom[node]:
                    dom[node] = new_dom
                    changed = True
        self.dominators = dom

    def get_dominator_tree(self) -> Dict[str, Optional[str]]:
        """Build dominator tree mapping node to immediate dominator."""
        self.compute_dominators()
        idom: Dict[str, Optional[str]] = {}
        for node in self.dominators:
            if node == self.entry:
                idom[node] = None
                continue
            # Find immediate dominator: dominators of node minus node itself
            candidates = self.dominators[node] - {node}
            # Choose candidate that dominates all other candidates
            for cand in candidates:
                if all(cand in self.dominators[other] for other in candidates):
                    idom[node] = cand
                    break
            else:
                idom[node] = None
        return idom


@dataclass
class MLIRFunction:
    """Represents an MLIR function."""

    name: str
    args: List[Tuple[str, str]]  # (name, type)
    return_type: str
    basic_blocks: Dict[str, BasicBlock] = field(default_factory=dict)
    cfg: ControlFlowGraph = field(default_factory=ControlFlowGraph)
    current_block: Optional[BasicBlock] = None

    def add_basic_block(self, label: str, line: int = 0) -> BasicBlock:
        bb = BasicBlock(label, line)
        self.basic_blocks[label] = bb
        self.current_block = bb
        return bb

    def get_basic_block(self, label: str) -> Optional[BasicBlock]:
        return self.basic_blocks.get(label)


@dataclass
class LoopContext:
    """Represents the context of a loop being stepped through."""

    op: LoopOperation
    iv_name: str
    lb: Union[int, z3.ExprRef]
    ub: Union[int, z3.ExprRef]
    step: Union[int, z3.ExprRef]
    iter_arg_name: str
    init: Union[str, int]
    body_ops: List[Operation]
    current_iteration: int = 0
    iv_value: Union[int, z3.ExprRef] = None
    iter_arg_value: Union[int, z3.ExprRef] = None
    body_op_index: int = -1
    line: int = 0


@dataclass
class SymbolicState:
    """Represents a symbolic execution state."""

    pc: Optional[str]  # program counter (basic block label)
    path_condition: List[z3.ExprRef] = field(default_factory=list)
    values: Dict[str, MLIRValue] = field(default_factory=dict)
    concrete_values: Dict[str, Any] = field(
        default_factory=dict
    )  # Concrete values for concolic execution
    memory: Dict[str, MLIRValue] = field(
        default_factory=dict
    )  # Memory storage for memref/tensor values (single-cell, deprecated)
    memory_cells: Dict[str, Dict[Tuple[int, ...], MLIRValue]] = field(
        default_factory=dict
    )  # Multi-cell memory storage indexed by concrete indices (deprecated, use memory_model)
    memory_model: MemoryModel = field(
        default_factory=MemrefMemoryModel
    )  # Memory model for memref operations
    tensor_memory_model: TensorMemoryModel = field(
        default_factory=TensorMemoryModel
    )  # Memory model for tensor operations

    def set_tensor_shape(self, tensor: str, shape: List[Union[int, z3.ExprRef]]) -> None:
        """Store shape of a tensor."""
        self.tensor_memory_model.set_shape(tensor, shape)

    def get_tensor_shape(self, tensor: str) -> Optional[List[Union[int, z3.ExprRef]]]:
        """Retrieve shape of a tensor."""
        return self.tensor_memory_model.get_shape(tensor)

    def fork(self) -> "SymbolicState":
        """Create a copy of this state."""
        # Deep copy memory_cells (for backward compatibility)
        memory_cells_copy = {}
        for memref_name, cells in self.memory_cells.items():
            memory_cells_copy[memref_name] = {
                idx: MLIRValue(val.name, val.expr, val.type, val.concrete)
                for idx, val in cells.items()
            }

        # Fork memory models
        forked_memory_model = self.memory_model.fork()
        forked_tensor_memory_model = self.tensor_memory_model.fork()

        return SymbolicState(
            pc=self.pc,
            path_condition=list(self.path_condition),
            values={
                k: MLIRValue(v.name, v.expr, v.type, v.concrete) for k, v in self.values.items()
            },
            concrete_values=dict(self.concrete_values),
            memory={
                k: MLIRValue(v.name, v.expr, v.type, v.concrete) for k, v in self.memory.items()
            },
            memory_cells=memory_cells_copy,
            memory_model=forked_memory_model,
            tensor_memory_model=forked_tensor_memory_model,
        )

    def add_path_condition(self, condition: z3.ExprRef) -> None:
        self.path_condition.append(condition)

    def set_value(self, name: str, expr: z3.ExprRef, type: str = "i32") -> None:
        self.values[name] = MLIRValue(name, expr, type)

    def get_value(self, name: str) -> Optional[MLIRValue]:
        return self.values.get(name)

    def get_expr(self, name: str) -> Optional[z3.ExprRef]:
        """Get symbolic expression for SSA value."""
        value = self.get_value(name)
        if value is None:
            return None
        return value.expr

    def set_concrete_value(self, name: str, value: Any) -> None:
        self.concrete_values[name] = value

    def get_concrete_value(self, name: str) -> Optional[Any]:
        return self.concrete_values.get(name)

    def set_memory(self, name: str, expr: z3.ExprRef, type: str = "i32") -> None:
        """Set single-cell memory value (deprecated, for backward compatibility).

        For symbolic indices, uses memory model with dummy symbolic index.
        """
        # Update legacy storage
        self.memory[name] = MLIRValue(name, expr, type)

        # Update memory model with dummy symbolic index
        # This represents "whole memref" store with unknown indices
        try:
            # Create a dummy symbolic index to trigger symbolic store path
            dummy_index = z3.FreshConst(z3.IntSort(), f"dummy_idx_{name}")
            self.memory_model.store(name, [dummy_index], expr, type)
        except (NotImplementedError, AttributeError):
            pass

    def get_memory(self, name: str) -> Optional[MLIRValue]:
        """Get single-cell memory value (deprecated, for backward compatibility).

        For symbolic indices, uses memory model with dummy symbolic index.
        """
        # First check legacy storage
        if name in self.memory:
            return self.memory[name]

        # Try to load from memory model with dummy symbolic index
        # This represents "whole memref" access with unknown indices
        try:
            # Get dtype
            dtype = getattr(self.memory_model, "dtypes", {}).get(name, "i32")
            # Create a dummy symbolic index to trigger symbolic load path
            dummy_index = z3.FreshConst(z3.IntSort(), f"dummy_idx_{name}")
            expr = self.memory_model.load(name, [dummy_index], dtype)
            # Create MLIRValue for compatibility
            value = MLIRValue(name, expr, dtype)
            # Store in legacy storage
            self.memory[name] = value
            return value
        except (NotImplementedError, AttributeError, KeyError):
            return None

    def allocate_memory(self, name: str, shape: Tuple[int, ...], dtype: str) -> None:
        """Allocate a new memref in the memory model."""
        self.memory_model.allocate(name, shape, dtype)

    # Multi-cell memory methods
    def set_memory_cell(
        self, memref: str, indices: Tuple[int, ...], expr: z3.ExprRef, type: str = "i32"
    ) -> None:
        """Set memory cell at given concrete indices."""
        # Update legacy storage for backward compatibility
        if memref not in self.memory_cells:
            self.memory_cells[memref] = {}
        self.memory_cells[memref][indices] = MLIRValue(f"{memref}{indices}", expr, type)

        # Update memory model
        self.memory_model.store(memref, list(indices), expr, type)

    def get_memory_cell(self, memref: str, indices: Tuple[int, ...]) -> Optional[MLIRValue]:
        """Get memory cell at given concrete indices."""
        # First check legacy storage
        if memref in self.memory_cells and indices in self.memory_cells[memref]:
            return self.memory_cells[memref][indices]

        # Try to load from memory model
        try:
            # Get dtype from memory model or default
            dtype = getattr(self.memory_model, "dtypes", {}).get(memref, "i32")

            expr = self.memory_model.load(memref, list(indices), dtype)
            # Create MLIRValue for compatibility
            value = MLIRValue(f"{memref}{indices}", expr, dtype)

            # Store in legacy storage for future accesses
            if memref not in self.memory_cells:
                self.memory_cells[memref] = {}
            self.memory_cells[memref][indices] = value

            return value
        except (KeyError, NotImplementedError, AttributeError):
            # Memory model doesn't have this cell or doesn't support load
            return None

    def set_memory_cell_concrete(self, memref: str, indices: Tuple[int, ...], value: Any) -> None:
        """Set concrete value for memory cell."""
        # Update legacy storage
        key = f"mem_{memref}_{'_'.join(str(i) for i in indices)}"
        self.concrete_values[key] = value

        # Update memory model
        self.memory_model.set_concrete_value(memref, list(indices), value)

    def get_memory_cell_concrete(self, memref: str, indices: Tuple[int, ...]) -> Optional[Any]:
        """Get concrete value for memory cell."""
        # First check legacy storage
        key = f"mem_{memref}_{'_'.join(str(i) for i in indices)}"
        concrete = self.concrete_values.get(key)
        if concrete is not None:
            return concrete

        # Check memory model
        return self.memory_model.get_concrete_value(memref, list(indices))
