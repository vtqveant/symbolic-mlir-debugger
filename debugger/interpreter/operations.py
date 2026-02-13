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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to legacy dictionary format for backward compatibility."""
        result = {
            "op": self.full_name,
            "line": self.line,
        }
        if self.dest:
            result["dest"] = self.dest
        if self.result_type:
            result["type"] = self.result_type
        if self.attributes:
            result["attributes"] = self.attributes
        return result


@dataclass
class TerminatorOperation(Operation):
    """Operations that terminate basic blocks."""

    pass


@dataclass
class ConstantOperation(Operation):
    """Operations that produce constant values."""

    value: Any = None  # Constant value (int, float, etc.)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.value is not None:
            result["value"] = self.value
        return result


@dataclass
class BinaryOperation(Operation):
    """Binary operations with two operands."""

    lhs: str = ""  # Left operand SSA value (without %)
    rhs: str = ""  # Right operand SSA value (without %)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["lhs"] = self.lhs
        result["rhs"] = self.rhs
        return result


@dataclass
class UnaryOperation(Operation):
    """Unary operations with one operand."""

    operand: str = ""  # Operand SSA value (without %)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["operand"] = self.operand
        return result


@dataclass
class CompareOperation(Operation):
    """Comparison operations."""

    pred: str = ""  # Predicate: "slt", "eq", "sgt", etc.
    lhs: str = ""
    rhs: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["pred"] = self.pred
        result["lhs"] = self.lhs
        result["rhs"] = self.rhs
        return result


@dataclass
class MemoryOperation(Operation):
    """Operations accessing memory (memref/tensor)."""

    memref: str = ""  # Memref/tensor SSA value (without %)
    indices: List[str] = field(default_factory=list)  # Index expressions

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["memref"] = self.memref
        if self.indices:
            result["indices"] = self.indices
        return result


@dataclass
class LoadOperation(MemoryOperation):
    """Load operations (memref.load, tensor.extract)."""

    pass


@dataclass
class StoreOperation(MemoryOperation):
    """Store operations (memref.store, tensor.insert)."""

    value: str = ""  # Value to store SSA value (without %)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["value"] = self.value
        return result


@dataclass
class ReinterpretCastOperation(Operation):
    """Reinterpret cast operations (memref.reinterpret_cast)."""

    operand: str = ""  # Source memref SSA value (without %)
    offsets: List[str] = field(default_factory=list)
    sizes: List[str] = field(default_factory=list)
    strides: List[str] = field(default_factory=list)
    src_type: str = ""
    dst_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["operand"] = self.operand
        if self.offsets:
            result["offsets"] = self.offsets
        if self.sizes:
            result["sizes"] = self.sizes
        if self.strides:
            result["strides"] = self.strides
        result["src_type"] = self.src_type
        result["dst_type"] = self.dst_type
        return result


@dataclass
class ConditionalBranchOperation(TerminatorOperation):
    """Conditional branch operations."""

    cond: str = ""  # Condition SSA value (without %)
    true_block: str = ""  # True target block label (without ^)
    false_block: str = ""  # False target block label (without ^)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["cond"] = self.cond
        result["true_block"] = self.true_block
        result["false_block"] = self.false_block
        result["successors"] = [self.true_block, self.false_block]
        return result


@dataclass
class UnconditionalBranchOperation(TerminatorOperation):
    """Unconditional branch operations."""

    target_block: str = ""  # Target block label (without ^)
    args: List[Tuple[str, str]] = field(default_factory=list)  # [(value_name, type)]

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["target_block"] = self.target_block
        result["successors"] = [self.target_block]
        if self.args:
            result["args"] = self.args
        return result


@dataclass
class CallOperation(Operation):
    """Function call operations."""

    callee: str = ""  # Function name
    args: List[str] = field(default_factory=list)  # Argument SSA values

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["callee"] = self.callee
        result["args"] = self.args
        return result


@dataclass
class ReturnOperation(TerminatorOperation):
    """Return operations."""

    value: Optional[str] = None  # Return value SSA value (optional)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.value is not None:
            result["value"] = self.value
        return result


@dataclass
class LoopOperation(Operation):
    """Loop operations (affine.for, scf.for)."""

    index: str = ""  # Induction variable SSA value
    lb: str = ""  # Lower bound expression
    ub: str = ""  # Upper bound expression
    step: Optional[str] = None  # Step size (optional)
    iter_arg: Optional[str] = None  # Iteration argument SSA value (scf.for)
    init: Optional[str] = None  # Initial value for iteration argument (scf.for)
    body: List[Dict[str, Any]] = field(default_factory=list)  # Loop body operations

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["index"] = self.index
        result["lb"] = self.lb
        result["ub"] = self.ub
        if self.step:
            result["step"] = self.step
        if self.iter_arg:
            result["iter_arg"] = self.iter_arg
        if self.init:
            result["init"] = self.init
        if self.body:
            result["body"] = self.body
        return result


@dataclass
class IfOperation(Operation):
    """Conditional region operations (scf.if)."""

    cond: str = ""  # Condition SSA value
    body: List[Dict[str, Any]] = field(default_factory=list)  # Then body operations
    elsebody: List[Dict[str, Any]] = field(default_factory=list)  # Else body operations
    result_types: List[str] = field(default_factory=list)  # Result types

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["cond"] = self.cond
        if self.body:
            result["body"] = self.body
        if self.elsebody:
            result["elsebody"] = self.elsebody
        if self.result_types:
            result["result_types"] = self.result_types
        return result


@dataclass
class YieldOperation(TerminatorOperation):
    """Yield operations (scf.yield)."""

    value: Optional[str] = None  # Yield value SSA value (optional)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.value is not None:
            result["value"] = self.value
        return result


@dataclass
class LinalgGenericOperation(Operation):
    """Linalg generic operation."""

    inputs: List[str] = field(default_factory=list)
    input_types: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    body: List[Dict[str, Any]] = field(default_factory=list)
    block_args: List[str] = field(default_factory=list)
    block_arg_types: List[str] = field(default_factory=list)
    indexing_maps: List[str] = field(default_factory=list)
    iterator_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.inputs:
            result["inputs"] = self.inputs
        if self.input_types:
            result["input_types"] = self.input_types
        if self.outputs:
            result["outputs"] = self.outputs
        if self.output_types:
            result["output_types"] = self.output_types
        if self.attributes:
            result["attributes"] = self.attributes
        if self.body:
            result["body"] = self.body
        if self.block_args:
            result["block_args"] = self.block_args
        if self.block_arg_types:
            result["block_arg_types"] = self.block_arg_types
        if self.indexing_maps:
            result["indexing_maps"] = self.indexing_maps
        if self.iterator_types:
            result["iterator_types"] = self.iterator_types
        return result


@dataclass
class LinalgMatmulOperation(Operation):
    """Linalg matmul operation."""

    A: str = ""
    B: str = ""
    C: str = ""
    A_type: str = ""
    B_type: str = ""
    C_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.A:
            result["A"] = self.A
        if self.B:
            result["B"] = self.B
        if self.C:
            result["C"] = self.C
        if self.A_type:
            result["A_type"] = self.A_type
        if self.B_type:
            result["B_type"] = self.B_type
        if self.C_type:
            result["C_type"] = self.C_type
        return result


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

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.A:
            result["A"] = self.A
        if self.B:
            result["B"] = self.B
        if self.C:
            result["C"] = self.C
        if self.A_type:
            result["A_type"] = self.A_type
        if self.B_type:
            result["B_type"] = self.B_type
        if self.C_type:
            result["C_type"] = self.C_type
        return result


@dataclass
class LinalgYieldOperation(TerminatorOperation):
    """Linalg yield operation (multiple values)."""

    values: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.values:
            result["values"] = self.values
        if self.types:
            result["types"] = self.types
        return result


# Utility functions for operation conversion


def operation_from_dict(op_dict: Dict[str, Any]) -> Operation:
    """Create Operation instance from legacy dictionary format.

    Attempts to infer the appropriate operation type based on
    the operation name and dictionary keys.

    If op_dict is already an Operation instance, return it unchanged.
    """
    if isinstance(op_dict, Operation):
        return op_dict
    op_name = op_dict.get("op", "")
    line = op_dict.get("line", 0)

    # Parse dialect and name
    if "." in op_name:
        dialect, name = op_name.split(".", 1)
    else:
        dialect = ""  # No dialect prefix (e.g., "return")
        name = op_name

    # Map operation names to operation types
    if name == "constant" or "const_" in name:
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        return ConstantOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            value=op_dict.get("value"),
            attributes=op_dict.get("attributes", {}),
        )

    # Binary arithmetic operations
    binary_ops = {
        "addi",
        "subi",
        "muli",
        "divi",
        "divsi",
        "divui",
        "remis",
        "remiu",
        "andi",
        "ori",
        "xori",
        "add",
        "sub",
        "mul",
        "div",
        "addf",
        "subf",
        "mulf",
        "divf",
    }
    if name in binary_ops:
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        lhs = clean_operand(op_dict.get("lhs", ""))
        rhs = clean_operand(op_dict.get("rhs", ""))
        return BinaryOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            lhs=lhs,
            rhs=rhs,
            attributes=op_dict.get("attributes", {}),
        )

    # Unary operations
    unary_ops = {
        "index_cast",
        "absf",
        "absi",
        "negf",
        "sitofp",
        "uitofp",
        "truncf",
        "extf",
        "splat",
    }
    if name in unary_ops:
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        # Try "arg" (used by cast ops), then "value", then "operand"
        operand = op_dict.get("arg", op_dict.get("value", op_dict.get("operand", "")))
        operand = clean_operand(operand)
        return UnaryOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            operand=operand,
            attributes=op_dict.get("attributes", {}),
        )

    # Comparison operations
    if name == "cmpi" or name == "cmpf" or name == "cmp":
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        lhs = clean_operand(op_dict.get("lhs", ""))
        rhs = clean_operand(op_dict.get("rhs", ""))
        return CompareOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            pred=op_dict.get("pred", ""),
            lhs=lhs,
            rhs=rhs,
            attributes=op_dict.get("attributes", {}),
        )

    # Memory operations
    if "load" in name or "extract" in name:
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        memref = clean_operand(
            op_dict.get("memref", op_dict.get("arg", op_dict.get("addr", "")))
        )
        indices = [
            clean_operand(idx)
            for idx in op_dict.get("indices", op_dict.get("index", []))
        ]
        return LoadOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            memref=memref,
            indices=indices,
            attributes=op_dict.get("attributes", {}),
        )

    if "store" in name or "insert" in name:
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        # Handle both old (src/dst/index) and new (memref/value/indices) formats
        # Also handle memref.store fields (addr, ref)
        memref = op_dict.get("memref")
        if memref is None:
            # Try dst (old tensor.insert format)
            memref = op_dict.get("dst")
        if memref is None:
            # Try addr (memref.store format)
            memref = op_dict.get("addr")
        value = op_dict.get("value")
        if value is None:
            # Try src (old tensor.insert format)
            value = op_dict.get("src")
        if value is None:
            # Try ref (memref.store format)
            value = op_dict.get("ref")
        indices = op_dict.get("indices")
        if indices is None:
            indices = op_dict.get("index", [])

        memref = clean_operand(memref if memref is not None else "")
        value = clean_operand(value if value is not None else "")
        indices = [clean_operand(idx) for idx in indices]

        # Debug
        print(
            f"DEBUG operation_from_dict insert: op_dict keys={list(op_dict.keys())}, memref={memref}, value={value}, indices={indices}"
        )
        return StoreOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            memref=memref,
            indices=indices,
            value=value,
            attributes=op_dict.get("attributes", {}),
        )

    # Reinterpret cast operations
    if name == "reinterpret_cast":
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        operand = clean_operand(op_dict.get("operand", ""))
        offsets = [clean_operand(idx) for idx in op_dict.get("offsets", [])]
        sizes = [clean_operand(idx) for idx in op_dict.get("sizes", [])]
        strides = [clean_operand(idx) for idx in op_dict.get("strides", [])]
        src_type = op_dict.get("src_type", "")
        dst_type = op_dict.get("dst_type", "")
        return ReinterpretCastOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            operand=operand,
            offsets=offsets,
            sizes=sizes,
            strides=strides,
            src_type=src_type,
            dst_type=dst_type,
            attributes=op_dict.get("attributes", {}),
        )

    # Branch operations
    if name == "cond_br":
        cond = clean_operand(op_dict.get("cond", ""))
        return ConditionalBranchOperation(
            dialect=dialect,
            name=name,
            line=line,
            cond=cond,
            true_block=op_dict.get("true_block", ""),
            false_block=op_dict.get("false_block", ""),
        )

    if name == "br":
        # Extract args if present
        args_list = []
        if "args" in op_dict:
            for value_name, type_str in op_dict["args"]:
                cleaned_name = clean_operand(value_name)
                args_list.append((cleaned_name, type_str))
        return UnconditionalBranchOperation(
            dialect=dialect,
            name=name,
            line=line,
            target_block=op_dict.get("target_block", ""),
            args=args_list,
        )

    # Call operations
    if name == "call" or name == "call_indirect":
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        args = [clean_operand(arg) for arg in op_dict.get("args", [])]
        return CallOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            callee=op_dict.get("callee", ""),
            args=args,
        )

    # Return operations (including misparsed shape.return as .sizereturn)
    if name == "return" or name == "sizereturn":
        # For sizereturn, map first operand to value if not already present
        if (
            name == "sizereturn"
            and "value" not in op_dict
            and "operands" in op_dict
            and len(op_dict["operands"]) > 0
        ):
            op_dict["value"] = op_dict["operands"][0]
        value = op_dict.get("value")
        if value is not None:
            value = clean_operand(value)
        return ReturnOperation(
            dialect=dialect,
            name=name,
            line=line,
            value=value,
        )

    # Loop operations
    if name == "for":
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        # scf.for uses "iv", affine.for uses "index"
        index = clean_operand(op_dict.get("iv", op_dict.get("index", "")))
        lb = clean_operand(op_dict.get("lb", ""))
        ub = clean_operand(op_dict.get("ub", ""))
        step = op_dict.get("step")
        if step is not None:
            step = clean_operand(step)
        iter_arg = op_dict.get("iter_arg")
        if iter_arg is not None:
            iter_arg = clean_operand(iter_arg)
        init = op_dict.get("init")
        if init is not None:
            init = clean_operand(init)
        return LoopOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            index=index,
            lb=lb,
            ub=ub,
            step=step,
            iter_arg=iter_arg,
            init=init,
            body=op_dict.get("body", []),
        )

    # If operations (scf.if, affine.if)
    if name == "if":
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        cond = clean_operand(op_dict.get("cond", ""))
        body = op_dict.get("body", [])
        elsebody = op_dict.get("elsebody", [])
        result_types = op_dict.get("result_types", [])
        return IfOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            cond=cond,
            body=body,
            elsebody=elsebody,
            result_types=result_types,
        )

    # Yield operations (scf.yield)
    if name == "yield" and dialect != "linalg":
        dest = op_dict.get("dest")
        if dest is not None:
            dest = clean_operand(dest)
        value = op_dict.get("value")
        if value is not None:
            value = clean_operand(value)
        return YieldOperation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest,
            result_type=op_dict.get("type"),
            value=value,
        )
    # Linalg operations
    if dialect == "linalg":
        if name == "generic":
            inputs = [clean_operand(i) for i in op_dict.get("inputs", [])]
            input_types = op_dict.get("input_types", [])
            outputs = [clean_operand(o) for o in op_dict.get("outputs", [])]
            output_types = op_dict.get("output_types", [])
            attributes = op_dict.get("attributes", {})
            body = op_dict.get("body", [])
            block_args = [clean_operand(a) for a in op_dict.get("block_args", [])]
            block_arg_types = op_dict.get("block_arg_types", [])
            indexing_maps = op_dict.get("indexing_maps", [])
            iterator_types = op_dict.get("iterator_types", [])
            return LinalgGenericOperation(
                dialect=dialect,
                name=name,
                line=line,
                dest=clean_operand(op_dict.get("dest")) if op_dict.get("dest") else "",
                result_type=op_dict.get("type"),
                inputs=inputs,
                input_types=input_types,
                outputs=outputs,
                output_types=output_types,
                attributes=attributes,
                body=body,
                block_args=block_args,
                block_arg_types=block_arg_types,
                indexing_maps=indexing_maps,
                iterator_types=iterator_types,
            )
        elif name == "matmul":
            A = clean_operand(op_dict.get("A", ""))
            B = clean_operand(op_dict.get("B", ""))
            C = clean_operand(op_dict.get("C", ""))
            A_type = op_dict.get("A_type", "")
            B_type = op_dict.get("B_type", "")
            C_type = op_dict.get("C_type", "")
            return LinalgMatmulOperation(
                dialect=dialect,
                name=name,
                line=line,
                dest=clean_operand(op_dict.get("dest")) if op_dict.get("dest") else "",
                result_type=op_dict.get("type"),
                A=A,
                B=B,
                C=C,
                A_type=A_type,
                B_type=B_type,
                C_type=C_type,
            )
        elif name == "batch_matmul":
            A = clean_operand(op_dict.get("A", ""))
            B = clean_operand(op_dict.get("B", ""))
            C = clean_operand(op_dict.get("C", ""))
            A_type = op_dict.get("A_type", "")
            B_type = op_dict.get("B_type", "")
            C_type = op_dict.get("C_type", "")
            return LinalgBatchMatmulOperation(
                dialect=dialect,
                name=name,
                line=line,
                dest=clean_operand(op_dict.get("dest")) if op_dict.get("dest") else "",
                result_type=op_dict.get("type"),
                A=A,
                B=B,
                C=C,
                A_type=A_type,
                B_type=B_type,
                C_type=C_type,
            )
        elif name == "conv_1d" or name == "conv_2d":
            # For now treat as generic operation with attributes
            pass
        elif name == "yield":
            values = [clean_operand(v) for v in op_dict.get("values", [])]
            types = op_dict.get("types", [])
            return LinalgYieldOperation(
                dialect=dialect,
                name=name,
                line=line,
                dest=clean_operand(op_dict.get("dest")) if op_dict.get("dest") else "",
                result_type=op_dict.get("type"),
                values=values,
                types=types,
            )

    # Default generic operation
    dest = op_dict.get("dest")
    if dest is not None:
        dest = clean_operand(dest)
    return Operation(
        dialect=dialect,
        name=name,
        line=line,
        dest=dest,
        result_type=op_dict.get("type"),
        attributes=op_dict.get("attributes", {}),
    )


def dict_to_operation(op_dict: Dict[str, Any]) -> Operation:
    """Alias for operation_from_dict for backward compatibility."""
    return operation_from_dict(op_dict)


def operation_to_dict(operation: Operation) -> Dict[str, Any]:
    """Convert Operation instance to legacy dictionary format."""
    return operation.to_dict()
