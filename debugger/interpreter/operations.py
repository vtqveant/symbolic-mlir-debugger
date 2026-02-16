#!/usr/bin/env python3
"""
Operation dataclasses for MLIR operations.

Preserves MLIR dialect structure with typed operation representations.
Each operation belongs to a dialect and has dialect-specific fields.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


def clean_operand(operand) -> str:
    """Remove leading '%' from SSA value names, keep integer constants unchanged."""
    # Handle SsaId objects
    if hasattr(operand, "value"):
        operand = operand.value
    # Now operand should be a string
    if operand.startswith("%"):
        return operand[1:]
    return operand


@dataclass
class Operation:
    """Base operation dataclass.

    All operations have dialect, name, and line number.
    The full operation name is {dialect}.{name}.
    """

    dialect: str  # "arith", "memref", "cf", etc.
    name: str  # "addi", "load", "cond_br", etc.
    line: int = 0  # Source line number
    dest: Optional[str] = None  # Destination SSA value (without %)
    result_type: Optional[str] = None  # Result type string
    attributes: Dict[str, Any] = field(default_factory=dict)  # Operation attributes

    @property
    def full_name(self) -> str:
        """Full operation name: dialect.name"""
        return f"{self.dialect}.{self.name}"


@dataclass
class TerminatorOperation(Operation):
    """Operations that terminate basic blocks."""

    pass


@dataclass
class ConstantOperation(Operation):
    """Operations that produce constant values."""

    value: Any = None  # Constant value (int, float, etc.)


@dataclass
class BinaryOperation(Operation):
    """Binary operations with two operands."""

    lhs: str = ""  # Left operand SSA value (without %)
    rhs: str = ""  # Right operand SSA value (without %)


@dataclass
class UnaryOperation(Operation):
    """Unary operations with one operand."""

    operand: str = ""  # Operand SSA value (without %)


@dataclass
class CompareOperation(Operation):
    """Comparison operations."""

    pred: str = ""  # Predicate: "slt", "eq", "sgt", etc.
    lhs: str = ""
    rhs: str = ""


@dataclass
class MemoryOperation(Operation):
    """Operations accessing memory (memref/tensor)."""

    memref: str = ""  # Memref/tensor SSA value (without %)
    indices: List[str] = field(default_factory=list)  # Index expressions


@dataclass
class LoadOperation(MemoryOperation):
    """Load operations (memref.load, tensor.extract)."""

    pass


@dataclass
class StoreOperation(MemoryOperation):
    """Store operations (memref.store, tensor.insert)."""

    value: str = ""  # Value to store SSA value (without %)


@dataclass
class ReinterpretCastOperation(Operation):
    """Reinterpret cast operations (memref.reinterpret_cast)."""

    operand: str = ""  # Source memref SSA value (without %)
    offsets: List[str] = field(default_factory=list)
    sizes: List[str] = field(default_factory=list)
    strides: List[str] = field(default_factory=list)
    src_type: str = ""
    dst_type: str = ""


@dataclass
class ConditionalBranchOperation(TerminatorOperation):
    """Conditional branch operations."""

    cond: str = ""  # Condition SSA value (without %)
    true_block: str = ""  # True target block label (without ^)
    false_block: str = ""  # False target block label (without ^)


@dataclass
class UnconditionalBranchOperation(TerminatorOperation):
    """Unconditional branch operations."""

    target_block: str = ""  # Target block label (without ^)
    args: List[Tuple[str, str]] = field(default_factory=list)  # [(value_name, type)]


@dataclass
class CallOperation(Operation):
    """Function call operations."""

    callee: str = ""  # Function name
    args: List[str] = field(default_factory=list)  # Argument SSA values


@dataclass
class ReturnOperation(TerminatorOperation):
    """Return operations."""

    value: Optional[str] = None  # Return value SSA value (optional)


@dataclass
class LoopOperation(Operation):
    """Loop operations (affine.for, scf.for)."""

    index: str = ""  # Induction variable SSA value
    lb: str = ""  # Lower bound expression
    ub: str = ""  # Upper bound expression
    step: Optional[str] = None  # Step size (optional)
    iter_arg: Optional[str] = None  # Iteration argument SSA value (scf.for)
    init: Optional[str] = None  # Initial value for iteration argument (scf.for)
    body: List[Operation] = field(default_factory=list)  # Loop body operations


@dataclass
class IfOperation(Operation):
    """Conditional region operations (scf.if)."""

    cond: str = ""  # Condition SSA value
    body: List[Operation] = field(default_factory=list)  # Then body operations
    elsebody: List[Operation] = field(default_factory=list)  # Else body operations
    result_types: List[str] = field(default_factory=list)  # Result types


@dataclass
class YieldOperation(TerminatorOperation):
    """Yield operations (scf.yield)."""

    value: Optional[str] = None  # Yield value SSA value (optional)


@dataclass
class LinalgGenericOperation(Operation):
    """Linalg generic operation."""

    inputs: List[str] = field(default_factory=list)
    input_types: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    body: List[Operation] = field(default_factory=list)
    block_args: List[str] = field(default_factory=list)
    block_arg_types: List[str] = field(default_factory=list)
    indexing_maps: List[str] = field(default_factory=list)
    iterator_types: List[str] = field(default_factory=list)


@dataclass
class LinalgMatmulOperation(Operation):
    """Linalg matmul operation."""

    A: str = ""
    B: str = ""
    C: str = ""
    A_type: str = ""
    B_type: str = ""
    C_type: str = ""


@dataclass
class LinalgBatchMatmulOperation(Operation):
    """Linalg batch matmul operation."""

    # For simplicity, same as matmul but with batch dimension
    A: str = ""
    B: str = ""
    C: str = ""
    A_type: str = ""
    B_type: str = ""
    C_type: str = ""


@dataclass
class LinalgYieldOperation(TerminatorOperation):
    """Linalg yield operation (multiple values)."""

    values: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)
