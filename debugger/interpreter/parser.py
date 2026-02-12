#!/usr/bin/env python3
"""
MLIR parser using pymlir as backend.
"""

import sys
import os
from typing import Dict, Optional, Any

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import parser
import parser.astnodes as mast
from parser.parser import Parser
from lark import Tree

# Import dialect modules
try:
    from parser.dialects import (
        affine,
        func,
        linalg,
        scf,
        cf,
        arith,
        memref,
        tensor,
        index,
        math,
        bufferization,
        shape,
        vector,
        builtin,
        emitc,
    )

    HAVE_DIALECTS = True
except ImportError:
    HAVE_DIALECTS = False
    affine = func = linalg = scf = cf = arith = memref = tensor = index = math = (
        bufferization
    ) = shape = vector = builtin = emitc = None

# Import models from same directory
from .models import MLIRFunction
from .operations import operation_from_dict


class MLIRParser:
    """Parser for MLIR text format using pymlir library.

    Known limitations:
    - cf.cond_br with block references (^true, ^false) in generic operation attributes
      is not supported by pymlir's grammar. Use scf.if instead.
    """

    def __init__(self):
        """Initialize parser with operation dataclass mode."""
        self.parser = Parser()
        self._dialect_handlers = {}
        self._setup_dialect_handlers()

    def _setup_dialect_handlers(self):
        """Set up handlers for dialect-specific operations using automatic registration."""
        # Default handler for unknown operations
        self._dialect_handlers = {}

        if not HAVE_DIALECTS:
            return

        # Map of base classes to generic handlers
        base_class_handlers = {
            "BinaryOperation": self._parse_generic_binary_op,
            "UnaryOperation": self._parse_generic_unary_op,
            "CmpiOperation": self._parse_generic_cmpi_op,
            "CmpfOperation": self._parse_generic_cmpf_op,
            "ConstantOperation": self._parse_generic_constant_op,
        }

        # Special overrides for operations that need custom parsing
        # These map operation class names to custom parser methods
        special_handlers = {
            # CF dialect
            "BrOperation": self._parse_br_op,
            "CondBrOperation": self._parse_cond_br_op,
            # Memref dialect
            "LoadOperation": self._parse_memref_load_op,
            "StoreOperation": self._parse_memref_store_op,
            "SubviewOperation": self._parse_memref_subview_op,
            "ViewOperation": self._parse_memref_view_op,
            "CastOperation": self._parse_memref_cast_op,
            "CollapseShapeOperation": self._parse_memref_collapse_shape_op,
            "ExpandShapeOperation": self._parse_memref_expand_shape_op,
            "ReinterpretCastOperation": self._parse_memref_reinterpret_cast_op,
            "MemorySpaceCastOperation": self._parse_memref_memory_space_cast_op,
            "DimOperation": self._parse_memref_dim_op,
            "AllocOperation": self._parse_memref_alloc_op,
            "AllocaOperation": self._parse_memref_alloca_op,
            "DeallocOperation": self._parse_memref_dealloc_op,
            "DmaStartOperation": self._parse_memref_dma_start_op,
            "DmaWaitOperation": self._parse_memref_dma_wait_op,
            # Tensor dialect (prefixed keys)
            "tensor.ExtractOperation": self._parse_tensor_extract_op,
            "tensor.InsertOperation": self._parse_tensor_insert_op,
            # SCF dialect
            "SCFForOp": self._parse_scf_for_op,
            "SCFIfOp": self._parse_scf_if_op,
            "SCFYield": self._parse_scf_yield_op,
            "SCFConditionOp": self._parse_scf_condition_op,
            # Affine dialect
            "AffineForOp": self._parse_affine_for_op,
            "AffineIfOp": self._parse_affine_if_op,
            "AffineLoadOp": self._parse_affine_load_op,
            "AffineStoreOp": self._parse_affine_store_op,
        }

        # Collect all dialect modules
        dialect_modules = [
            affine,
            func,
            linalg,
            scf,
            cf,
            arith,
            memref,
            tensor,
            index,
            math,
            bufferization,
            shape,
            vector,
            builtin,
            emitc,
        ]

        for module in dialect_modules:
            if module is None:
                continue
            # Determine if module is a Dialect object (has ops) or a module containing a dialect object
            if hasattr(module, "ops"):
                dialect_obj = module
            else:
                # Module name like 'parser.dialects.arith' -> extract 'arith'
                dialect_name = module.__name__.split(".")[-1]
                dialect_obj = getattr(module, dialect_name, None)
                if dialect_obj is None or not hasattr(dialect_obj, "ops"):
                    continue
            for op_class in dialect_obj.ops:
                class_name = op_class.__name__
                # Check for special handler first
                if class_name in special_handlers:
                    self._dialect_handlers[class_name] = special_handlers[class_name]
                    continue
                # Determine base class hierarchy
                handler = None
                for base in op_class.__mro__:
                    base_name = base.__name__
                    if base_name in base_class_handlers:
                        handler = base_class_handlers[base_name]
                        break
                if handler:
                    self._dialect_handlers[class_name] = handler
                else:
                    # No matching base class, use generic field-based parser
                    self._dialect_handlers[class_name] = self._parse_generic_dialect_op

    def _extract_operation_positions(self, mlir_code: str) -> None:
        """Extract line and column positions for operations from raw parse tree.

        Populates self.operation_positions with (line, column) tuples in order
        of operations appearing in the source.
        Only collects operations inside functions (not module-level operations).
        """
        # Reset position tracking
        self.operation_positions = []
        self._op_pos_index = 0

        # Use pymlir's parser to get raw parse tree
        parser = Parser([])
        raw_tree = parser.parser.parse(mlir_code)

        # Walk tree and collect positions for operation nodes inside functions
        def walk_tree(node, in_function=False):
            if isinstance(node, Tree):
                # Check if we're entering or leaving a function
                if hasattr(node, "data"):
                    if node.data == "function":
                        in_function = True

                # Collect operation nodes if inside a function
                if in_function and hasattr(node, "data") and node.data == "operation":
                    # Get position metadata
                    if hasattr(node.meta, "line") and hasattr(node.meta, "column"):
                        line = node.meta.line
                        column = node.meta.column
                        self.operation_positions.append((line, column))
                    elif node.meta is not None:
                        # Some metadata present but not line/column
                        self.operation_positions.append((0, 0))
                    else:
                        self.operation_positions.append((0, 0))

                # Recursively walk children
                for child in node.children:
                    walk_tree(child, in_function)

        walk_tree(raw_tree)

    def _get_next_operation_line(self) -> int:
        """Get line number for next operation being parsed.

        Returns line number from operation_positions, or 0 if not available.
        Increments internal index.
        """
        if self._op_pos_index < len(self.operation_positions):
            line, _ = self.operation_positions[self._op_pos_index]
            self._op_pos_index += 1
            return line
        return 0

    def _extract_line_number(self, op: mast.Operation) -> int:
        """Extract line number from operation location.

        First tries to get line number from location attribute.
        If not available, falls back to extracted positions from raw parse tree.
        Returns line number if available, otherwise 0.
        """
        # Try to get line number from location attribute first
        if op.location is not None:
            # Check for FileLineColLoc type
            if hasattr(op.location, "line"):
                return op.location.line

            # Check for StrLocation type (e.g., "loc(unknown)")
            # Try to parse line number from string if possible
            if hasattr(op.location, "value"):
                import re

                match = re.search(r"loc\([^:]*:(\d+):", op.location.value)
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:
                        pass

        # Fallback to extracted positions from raw parse tree
        return self._get_next_operation_line()

    def _extract_location(self, op: mast.Operation) -> Dict[str, Any]:
        """Extract location information from operation.

        Returns a dictionary with location details, including type,
        file, line, column, and any other relevant fields.
        """
        if op.location is None:
            return {"type": "unknown", "line": 0}

        loc = op.location
        result = {}

        # Determine location type and extract fields
        if hasattr(loc, "__class__"):
            result["type"] = loc.__class__.__name__

        if isinstance(loc, mast.FileLineColLoc):
            result["file"] = loc.file
            result["line"] = loc.line
            if loc.col is not None:
                result["column"] = loc.col
            if loc.end_line is not None:
                result["end_line"] = loc.end_line
            if loc.end_col is not None:
                result["end_column"] = loc.end_col
        elif isinstance(loc, mast.CallSiteLoc):
            result["callee"] = self._extract_location_from_loc(loc.callee)
            result["caller"] = self._extract_location_from_loc(loc.caller)
        elif isinstance(loc, mast.FusedLoc):
            result["locations"] = [
                self._extract_location_from_loc(l) for l in loc.locations
            ]
            if loc.metadata is not None:
                result["metadata"] = self._parse_attribute(loc.metadata)
        elif isinstance(loc, mast.NameLoc):
            result["name"] = loc.name
            if loc.child is not None:
                result["child"] = self._extract_location_from_loc(loc.child)
        elif isinstance(loc, mast.UnknownLoc):
            result["type"] = "unknown"
        elif isinstance(loc, mast.StrLocation):
            result["type"] = "string"
            result["value"] = loc.value
        else:
            # Fallback: store string representation
            result["type"] = "unknown"
            result["raw"] = str(loc)

        return result

    def _extract_location_from_loc(self, loc) -> Dict[str, Any]:
        """Helper to extract location from a Location object."""
        # Simplified version that just extracts basic info
        if hasattr(loc, "__class__"):
            if isinstance(loc, mast.FileLineColLoc):
                return {
                    "type": "FileLineColLoc",
                    "file": loc.file,
                    "line": loc.line,
                    "column": loc.col if loc.col is not None else 0,
                }
            elif isinstance(loc, mast.StrLocation):
                return {"type": "StrLocation", "value": loc.value}
            # Add other types as needed
        return {"type": "unknown", "raw": str(loc)}

    def _preprocess_mlir(self, mlir_code: str) -> str:
        """Preprocess MLIR code to handle operations with comma syntax for attributes."""
        import re

        # Normalize block labels to synthetic labels (^block1, ^block2, ...)
        # because pymlir doesn't expose block labels
        # Find all block label definitions (^label:)
        block_label_pattern = r"^\s*\^([a-zA-Z0-9_]+):"
        labels_found = []
        for match in re.finditer(block_label_pattern, mlir_code, re.MULTILINE):
            label = match.group(1)
            if label not in labels_found:
                labels_found.append(label)

        # Create mapping from original label to synthetic label
        # Skip entry block (implicit) - we'll handle it separately
        label_map = {}
        for i, label in enumerate(labels_found):
            synthetic = f"^block{i + 1}"
            label_map[label] = synthetic

        # Replace label definitions and references
        for orig, synthetic in label_map.items():
            # Replace label definition: ^orig: -> ^blockN:
            # Keep indentation (spaces before caret)
            mlir_code = re.sub(
                rf"^\s*\^{orig}:", f"  {synthetic}:", mlir_code, flags=re.MULTILINE
            )
            # Replace label references: ^orig (not followed by colon or alnum)
            # Use word boundary? Simple global replace of ^orig with ^blockN
            mlir_code = re.sub(rf"\^{orig}(?![a-zA-Z0-9_:])", synthetic, mlir_code)

        # Mapping of predicate strings to integer values for arith.cmpi

        # Pattern for cf.cond_br or std.cond_br or bare cond_br
        # Matches: (cf|std)?.cond_br %cond, ^true, ^false
        # Use word boundary to avoid matching cond_br inside other words
        cond_br_pattern = (
            r"\b((cf|std)\.)?cond_br\b\s+([^,]+)\s*,\s*([^,]+)\s*,\s*([^:\n]+)"
        )
        # Pattern for cf.br or std.br or bare br
        # Matches: (cf|std)\.?br ^target
        # Use word boundary to avoid matching br inside other words (e.g., cond_br)
        br_pattern = r"\b((cf|std)\.)?br\b\s+([^\s:\n]+)"

        def replace_cond_br(match):
            dialect_prefix = match.group(2)  # cf or std or None
            cond = match.group(3).strip()
            true_block = match.group(4).strip()
            false_block = match.group(5).strip()
            # If already cf. prefix, leave as-is (dialect operation)
            if dialect_prefix == "cf":
                return match.group(0)  # no change
            # Convert std.cond_br or bare cond_br to cf.cond_br (dialect operation)
            return f"cf.cond_br {cond}, {true_block}, {false_block}"

        def replace_br(match):
            dialect_prefix = match.group(2)  # cf or std or None
            target_block = match.group(3).strip()
            # If already cf. prefix, leave as-is (dialect operation)
            if dialect_prefix == "cf":
                return match.group(0)  # no change
            # Convert std.br or bare br to cf.br (dialect operation)
            return f"cf.br {target_block}"

        mlir_code = re.sub(
            cond_br_pattern, replace_cond_br, mlir_code, flags=re.MULTILINE
        )
        mlir_code = re.sub(br_pattern, replace_br, mlir_code, flags=re.MULTILINE)
        # Replace non-standard arith.divi with arith.divsi (signed division)
        mlir_code = re.sub(r"arith\.divi", "arith.divsi", mlir_code)

        # Handle shape.const_shape [1, 2, 3] -> shape.const_shape 1, 2, 3 (remove brackets)
        # Also handle shape.const_shape (1, 2, 3) for compatibility
        # Pattern matches shape.const_shape followed by whitespace, [ or (, content, ] or )
        shape_const_shape_pattern = r"shape\.const_shape\s*[\[\(]([^\]\)]*)[\]\)]"

        def replace_shape_const_shape(match):
            inner = match.group(1).strip()
            return f"shape.const_shape {inner}"

        mlir_code = re.sub(
            shape_const_shape_pattern, replace_shape_const_shape, mlir_code
        )

        # Handle bufferization.alloc_tensor [%arg0, %arg1] -> bufferization.alloc_tensor %arg0, %arg1
        # Also handle parentheses for compatibility
        alloc_tensor_pattern = r"bufferization\.alloc_tensor\s*[\[\(]([^\]\)]*)[\]\)]"

        def replace_alloc_tensor(match):
            inner = match.group(1).strip()
            return f"bufferization.alloc_tensor {inner}"

        mlir_code = re.sub(alloc_tensor_pattern, replace_alloc_tensor, mlir_code)

        # Handle tensor<...xindex> -> tensor<...xi64> for pymlir compatibility
        # pymlir's grammar doesn't support index type in tensor elements
        tensor_index_pattern = r"tensor\<(\d*)xindex\>"

        def replace_tensor_index(match):
            dim = match.group(1)
            return f"tensor<{dim}xi64>"

        mlir_code = re.sub(tensor_index_pattern, replace_tensor_index, mlir_code)

        return mlir_code

    def parse_file(self, filepath: str) -> Dict[str, MLIRFunction]:
        """Parse an MLIR file and return functions."""
        with open(filepath, "r") as f:
            mlir_code = f.read()
        return self.parse_string(mlir_code)

    def parse_string(self, mlir_code: str) -> Dict[str, MLIRFunction]:
        """Parse MLIR code from string and return functions."""
        mlir_code = self._preprocess_mlir(mlir_code)
        # Extract operation positions from raw parse tree for line tracking
        self._extract_operation_positions(mlir_code)
        ast = parser.parse_string(mlir_code)
        return self._parse_ast(ast)

    def _parse_ast(self, ast: mast.MLIRFile) -> Dict[str, MLIRFunction]:
        """Parse pymlir AST into MLIRFunction objects."""
        self.functions = {}

        # Iterate through modules (usually one)
        for module in ast.modules:
            self._parse_module(module)

        return self.functions

    def _parse_module(self, module: mast.Module) -> None:
        """Parse a module and extract functions."""
        # Module has a region containing operations
        if not module.region or not module.region.body:
            return

        # The module region contains blocks (usually one)
        for block in module.region.body:
            for op in block.body:
                if isinstance(op.op, mast.Function):
                    self._parse_function(op)

    def _parse_function(self, func_op: mast.Operation) -> None:
        """Parse a function operation."""
        func = func_op.op  # mast.Function

        # Extract function name
        func_name = func.name.value if hasattr(func.name, "value") else str(func.name)

        # Extract arguments
        args = []
        if func.args:
            for arg in func.args:
                arg_name = (
                    arg.name.value if hasattr(arg.name, "value") else str(arg.name)
                )
                arg_type = self._type_to_string(arg.type)
                args.append((arg_name, arg_type))

        # Extract return type
        return_type = self._type_to_string(func.result_types)

        # Create MLIRFunction
        mlir_func = MLIRFunction(func_name, args, return_type)

        # Parse function body (region)
        if func.region and func.region.body:
            # Function region has blocks (usually one)
            for i, block in enumerate(func.region.body):
                self._parse_block(block, mlir_func, block_index=i)
            # Compute exit blocks after all edges added
            mlir_func.cfg.compute_exits()

        self.functions[func_name] = mlir_func

    def _parse_block(
        self, block: mast.Block, func: MLIRFunction, block_index: int = 0
    ) -> None:
        """Parse a basic block and add to function."""
        # Determine block label
        if block.label and block.label.name:
            label = block.label.name.value
            # Add ^ prefix if not present (for consistency with branch targets)
            if not label.startswith("^"):
                label = "^" + label
        else:
            # No label from pymlir - assign synthetic label
            if block_index == 0:
                label = "^entry"  # First block is entry
            else:
                label = f"^block{block_index}"

        # Set entry block in CFG
        if block_index == 0:
            func.cfg.entry = label

        # Ensure node exists in CFG
        func.cfg.add_node(label)

        # Create basic block
        bb = func.add_basic_block(label)

        # Parse block parameters if present
        if (
            block.label
            and hasattr(block.label, "arg_ids")
            and hasattr(block.label, "arg_types")
        ):
            if block.label.arg_ids and block.label.arg_types:
                for arg_id, arg_type in zip(block.label.arg_ids, block.label.arg_types):
                    # Convert SsaId to string (remove % prefix)
                    arg_name = self._ssa_use_to_string(arg_id)
                    arg_type_str = self._type_to_string(arg_type)
                    bb.parameters.append((arg_name, arg_type_str))

        # Set current block and function for edge detection
        self.current_block_label = label
        self.current_func = func

        # Parse operations in block
        for op in block.body:
            op_dict = self._parse_operation(op)
            if op_dict:
                # Line number is already set by _parse_operation via _extract_line_number
                bb.add_operation(op_dict)

        # Clear current block and function
        self.current_block_label = None
        self.current_func = None

    def _parse_operation(
        self, op: mast.Operation
    ) -> Optional[Any]:  # Returns Dict[str, Any] or Operation
        """Parse an operation into dictionary format."""
        op_obj = op.op
        class_name = op_obj.__class__.__name__
        result = None

        # Handle different operation types
        if isinstance(op_obj, mast.CustomOperation):
            result = self._parse_custom_operation(op, op_obj)
        elif isinstance(op_obj, mast.GenericOperation):
            result = self._parse_generic_operation(op, op_obj)
        elif class_name == "ReturnOperation":
            result = self._parse_return_operation(op_obj)
        elif class_name == "CallOperation":
            # Dispatch based on dialect (func vs emitc)
            if hasattr(op_obj, "func"):
                result = self._parse_call_op(op)
            elif hasattr(op_obj, "callee"):
                result = self._parse_emitc_call_op(op)
            # fallthrough to dialect handlers
        else:
            # Try dialect-prefixed handler first (e.g., "tensor.ExtractOperation")
            module = op_obj.__class__.__module__
            dialect = module.split(".")[-1] if "." in module else module
            prefixed_key = f"{dialect}.{class_name}"

            handler = None
            if prefixed_key in self._dialect_handlers:
                handler = self._dialect_handlers[prefixed_key]
            elif class_name in self._dialect_handlers:
                handler = self._dialect_handlers[class_name]

            if handler:
                # Pass the operation node so handler can access result_list
                result = handler(op)

        if result is None:
            print(f"Warning: Unsupported operation type: {class_name}")
            return None

        # Set line number from operation location
        result["line"] = self._extract_line_number(op)
        # Add full location information for debugging
        result["location"] = self._extract_location(op)

        # Convert to Operation dataclass
        return operation_from_dict(result)

    def _parse_custom_operation(
        self, op: mast.Operation, custom_op: mast.CustomOperation
    ) -> Dict[str, Any]:
        """Parse a CustomOperation (generic MLIR operation)."""
        # Normalize operation names (e.g., arith.constant0 -> arith.constant)
        op_name = custom_op.name
        if op_name.startswith("constant"):
            op_name = "constant"

        result = {
            "op": f"{custom_op.namespace}.{op_name}",
        }

        # Special handling for arith.constant
        if custom_op.namespace == "arith" and op_name == "constant":
            # Try to get constant value
            if custom_op.args is None:
                # constant0 pattern - assume value is 0
                result["value"] = self._parse_constant_value("0")
            elif custom_op.args:
                # constant with explicit value
                if len(custom_op.args) == 1:
                    arg = custom_op.args[0]
                    if hasattr(arg, "value"):
                        result["value"] = self._parse_constant_value(arg.value)
                    else:
                        result["value"] = self._parse_constant_value(str(arg))
                else:
                    # Multiple args? Shouldn't happen for constant
                    result["operands"] = [
                        self._parse_constant_value(str(arg)) for arg in custom_op.args
                    ]
            # Skip normal operand handling for constants
            # Add destination if result_list exists
            if op.result_list:
                result_item = op.result_list[0]
                if hasattr(result_item, "value") and hasattr(
                    result_item.value, "value"
                ):
                    result["dest"] = result_item.value.value
            # Add type
            if custom_op.type:
                type_str = self._type_to_string(custom_op.type[0])
                result["type"] = type_str
            return result

        # Add destination if result_list exists
        if op.result_list:
            # Assume single result for now
            result_item = op.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value

        # Add operands
        if custom_op.args:
            operands = []
            for arg in custom_op.args:
                if hasattr(arg, "value"):
                    operands.append(arg.value)
                else:
                    operands.append(str(arg))

            # For binary operations, assign lhs, rhs
            if len(operands) == 2:
                result["lhs"] = operands[0]
                result["rhs"] = operands[1]
            elif len(operands) == 1:
                result["value"] = operands[0]
            else:
                result["operands"] = operands

        # Add type
        if custom_op.type:
            # Assume single type for now
            type_str = self._type_to_string(custom_op.type[0])
            result["type"] = type_str

        return result

    def _parse_generic_operation(
        self, op: mast.Operation, generic_op: mast.GenericOperation
    ) -> Dict[str, Any]:
        """Parse a GenericOperation (generic MLIR operation with attributes)."""
        # Name is full operation name like "arith.cmpi"
        op_name = (
            generic_op.name.value
            if hasattr(generic_op.name, "value")
            else str(generic_op.name)
        )
        # Split namespace and operation name if possible
        if "." in op_name:
            namespace, op_short = op_name.split(".", 1)
        else:
            namespace, op_short = "", op_name

        result = {
            "op": op_name,
        }

        # Add destination if result_list exists
        if op.result_list:
            # Assume single result for now
            result_item = op.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value

        # Add operands
        if generic_op.args:
            operands = []
            for arg in generic_op.args:
                if hasattr(arg, "value"):
                    operands.append(arg.value)
                else:
                    operands.append(str(arg))

            # For binary operations, assign lhs, rhs
            if len(operands) == 2:
                result["lhs"] = operands[0]
                result["rhs"] = operands[1]
            elif len(operands) == 1:
                result["value"] = operands[0]
            else:
                result["operands"] = operands

        # Add attributes if present
        if generic_op.attributes:
            # Convert AttributeDict to dict
            attr_dict = self._parse_attribute_dict(generic_op.attributes)
            result["attributes"] = attr_dict
            # For known operations, promote specific attributes to top-level keys
            if op_name == "arith.cmpi" and "pred" in attr_dict:
                result["pred"] = attr_dict["pred"]

        # Add successors if present (for branch operations)
        if hasattr(generic_op, "successors") and generic_op.successors:
            successors = []
            for succ in generic_op.successors:
                if hasattr(succ, "value"):
                    successors.append(succ.value)
                else:
                    successors.append(str(succ))
            result["successors"] = successors

            # Special handling for branch operations: add cond key for cf.cond_br
            if op_name in ["cf.cond_br", "std.cond_br"] and "value" in result:
                result["cond"] = result["value"]
                # Also add true_block and false_block from successors
                if len(successors) >= 2:
                    result["true_block"] = "^" + successors[0]
                    result["false_block"] = "^" + successors[1]
            # For cf.br, add target_block from first successor
            elif op_name in ["cf.br", "std.br"] and len(successors) >= 1:
                result["target_block"] = "^" + successors[0]

        # Add type
        if generic_op.type:
            # Handle both single type and list of types
            if isinstance(generic_op.type, (list, tuple)):
                type_node = generic_op.type[0]
            else:
                type_node = generic_op.type
            type_str = self._type_to_string(type_node)
            result["type"] = type_str

        return result

    def _parse_return_operation(self, ret_op) -> Dict[str, Any]:
        """Parse a return operation."""
        result = {
            "op": "return",
        }

        if ret_op.values and len(ret_op.values) > 0:
            value = ret_op.values[0]
            if hasattr(value, "value"):
                result["value"] = value.value

        if ret_op.types and len(ret_op.types) > 0:
            type_str = self._type_to_string(ret_op.types[0])
            result["type"] = type_str

        return result

    def _type_to_string(self, type_node) -> str:
        """Convert a type AST node to string representation."""
        if isinstance(type_node, mast.SignlessIntegerType):
            return f"i{type_node.width}"
        elif isinstance(type_node, mast.IntegerType):
            # Signed/unsigned integer type
            prefix = (
                "i"
                if type_node.signedness == "signless"
                else "si"
                if type_node.signedness == "signed"
                else "ui"
            )
            return f"{prefix}{type_node.width}"
        elif isinstance(type_node, mast.IndexType):
            return "index"
        elif isinstance(type_node, mast.FloatType):
            return type_node.type.name
        elif isinstance(type_node, str):
            return type_node
        else:
            # Try to dump the type
            try:
                return type_node.dump()
            except:
                return str(type_node)

    def _parse_constant_value(self, value_str):
        """Parse a constant value string to appropriate Python type.

        Handles decimal integers, hexadecimal integers (0x...), floats,
        and boolean strings.
        """
        if isinstance(value_str, mast.Attribute):
            return self._parse_attribute(value_str)
        if isinstance(value_str, (int, float, bool)):
            return value_str
        s = str(value_str).strip()
        # Boolean literals
        if s.lower() == "true":
            return True
        if s.lower() == "false":
            return False
        # Hexadecimal integer
        if s.startswith("0x") or s.startswith("0X"):
            try:
                return int(s, 16)
            except ValueError:
                return s
        # Decimal integer
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            try:
                return int(s)
            except ValueError:
                return s
        # Float
        try:
            return float(s)
        except ValueError:
            pass
        # Return as string if nothing else matches
        return s

    def _parse_attribute(self, attr_node):
        """Convert an Attribute AST node to Python primitive value."""
        if isinstance(attr_node, mast.BoolAttr):
            return attr_node.value
        elif isinstance(attr_node, mast.IntegerAttr):
            # IntegerAttr has value and type fields
            # value could be a string (hex) or int
            val = attr_node.value
            if isinstance(val, str):
                # Handle hexadecimal literals
                if val.startswith("0x"):
                    return int(val, 16)
                # Try to parse as int
                try:
                    return int(val)
                except ValueError:
                    return val
            else:
                return val
        elif isinstance(attr_node, mast.FloatAttr):
            # FloatAttr has value and type fields
            val = attr_node.value
            if isinstance(val, str):
                # Could be hex float? Not handling now
                try:
                    return float(val)
                except ValueError:
                    return val
            else:
                return val
        elif isinstance(attr_node, mast.StringAttr):
            # StringAttr has value field (could be StringLiteral or string)
            val = attr_node.value
            if hasattr(val, "value"):
                return val.value  # StringLiteral
            else:
                return val
        elif isinstance(attr_node, mast.ArrayAttr):
            # ArrayAttr has value list of attributes
            return [self._parse_attribute(sub) for sub in attr_node.value]
        elif isinstance(attr_node, mast.DictionaryAttr):
            # DictionaryAttr has value list of AttributeEntry
            result = {}
            for entry in attr_node.value:
                key = entry.name
                value = entry.value
                if value is None:
                    result[key] = None
                else:
                    result[key] = self._parse_attribute(value)
            return result
        elif isinstance(attr_node, mast.UnitAttr):
            return None  # unit attribute represents no value
        elif isinstance(attr_node, mast.SymbolRefAttr):
            # SymbolRefAttr has path list of SymbolRefId
            return "::".join([str(p) for p in attr_node.path])
        elif isinstance(attr_node, mast.TypeAttr):
            # TypeAttr has value field (type node)
            return self._type_to_string(attr_node.value)
        elif isinstance(attr_node, mast.StringLiteral):
            # Bare string literal as attribute value
            return attr_node.value
        else:
            # For unsupported attribute types, return a string representation
            try:
                return attr_node.dump()
            except:
                return str(attr_node)

    def _parse_attribute_dict(self, attr_dict):
        """Convert an AttributeDict AST node to Python dict."""
        if attr_dict is None:
            return {}
        result = {}
        for entry in attr_dict.values:
            key = entry.name
            value = entry.value
            if value is None:
                result[key] = None
            else:
                result[key] = self._parse_attribute(value)
        return result

    # Affine dialect handlers
    def _parse_affine_for_op(self, op_node) -> Dict[str, Any]:
        """Parse affine.for operation."""
        # op_node is Operation node, op_node.op is AffineForOp instance
        op = op_node.op
        result = {
            "op": "affine.for",
            "index": op.index.value if hasattr(op.index, "value") else str(op.index),
            "lb": self._ssa_use_to_string(op.begin),
            "ub": self._ssa_use_to_string(op.end),
        }

        # Add destination if result_list exists
        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value

        if op.step:
            result["step"] = self._ssa_use_to_string(op.step)

        # Parse body region operations
        if op.region and op.region.body:
            # For now, just note that there's a body
            result["body"] = []
            # TODO: Parse operations in the region
            # For affine.for, the region contains a block with operations
            for block in op.region.body:
                for body_op in block.body:
                    op_dict = self._parse_operation(body_op)
                    if op_dict:
                        result["body"].append(op_dict)

        return result

    def _parse_affine_if_op(self, op_node) -> Dict[str, Any]:
        """Parse affine.if operation."""
        op = op_node.op
        result = {
            "op": "affine.if",
            "cond": self._map_or_set_id_to_string(op.cond),
            "operands": [self._ssa_use_to_string(operand) for operand in op.operands],
        }

        # Add destination if result_list exists
        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value

        # Parse body region
        if op.body and op.body.body:
            result["body"] = []
            for block in op.body.body:
                for body_op in block.body:
                    op_dict = self._parse_operation(body_op)
                    if op_dict:
                        result["body"].append(op_dict)

        # Parse else region if present
        if op.elsebody and op.elsebody.body:
            result["elsebody"] = []
            for block in op.elsebody.body:
                for body_op in block.body:
                    op_dict = self._parse_operation(body_op)
                    if op_dict:
                        result["elsebody"].append(op_dict)

        return result

    def _parse_affine_load_op(self, op_node) -> Dict[str, Any]:
        """Parse affine.load operation."""
        op = op_node.op
        result = {
            "op": "affine.load",
            "arg": self._ssa_use_to_string(op.arg),
            "index": self._affine_expr_to_string(op.index),
            "type": self._type_to_string(op.type),
        }
        # Add destination if result_list exists
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_affine_store_op(self, op_node) -> Dict[str, Any]:
        """Parse affine.store operation."""
        op = op_node.op
        result = {
            "op": "affine.store",
            "addr": self._ssa_use_to_string(op.addr),
            "ref": self._ssa_use_to_string(op.ref),
            "index": self._affine_expr_to_string(op.index),
            "type": self._type_to_string(op.type),
        }
        return result

    # Func dialect handlers
    def _parse_call_op(self, op_node) -> Dict[str, Any]:
        """Parse func.call operation."""
        op = op_node.op
        result = {
            "op": "func.call",
            "callee": op.func.value if hasattr(op.func, "value") else str(op.func),
            "args": [self._ssa_use_to_string(arg) for arg in op.args]
            if op.args
            else [],
        }

        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value"):
                result["dest"] = result_item.value

        if op.type:
            result["type"] = self._type_to_string(op.type)

        return result

    def _parse_call_indirect_op(self, op_node) -> Dict[str, Any]:
        """Parse func.call_indirect operation."""
        op = op_node.op
        # Similar to call but with function pointer
        result = {
            "op": "func.call_indirect",
            "args": [self._ssa_use_to_string(arg) for arg in op.args]
            if op.args
            else [],
        }

        if op.func:
            result["callee"] = self._ssa_use_to_string(op.func)

        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value"):
                result["dest"] = result_item.value

        if op.type:
            result["type"] = self._type_to_string(op.type)

        return result

    # Linalg dialect handlers (stubs for now)
    def _parse_linalg_batch_matmul(self, op) -> Dict[str, Any]:
        """Parse linalg.batch_matmul operation."""
        result = {
            "op": "linalg.batch_matmul",
        }
        # TODO: Implement proper parsing
        return result

    def _parse_linalg_conv_w(self, op) -> Dict[str, Any]:
        """Parse linalg.conv_1d operation."""
        result = {
            "op": "linalg.conv_1d",
        }
        # TODO: Implement proper parsing
        return result

    def _parse_linalg_conv_hw(self, op) -> Dict[str, Any]:
        """Parse linalg.conv_2d operation."""
        result = {
            "op": "linalg.conv_2d",
        }
        # TODO: Implement proper parsing
        return result

    def _parse_linalg_generic(self, op_node) -> Dict[str, Any]:
        """Parse linalg.generic operation."""
        op = op_node.op
        result = {
            "op": "linalg.generic",
        }

        # Extract input arguments
        if op.inargs:
            result["inputs"] = [
                arg.value if hasattr(arg, "value") else str(arg) for arg in op.inargs
            ]
            result["input_types"] = [self._type_to_string(t) for t in op.in_types]

        # Extract output arguments
        if op.outargs:
            result["outputs"] = [
                arg.value if hasattr(arg, "value") else str(arg) for arg in op.outargs
            ]
            result["output_types"] = [self._type_to_string(t) for t in op.out_types]
        elif op.init_args:
            result["outputs"] = [
                arg.value if hasattr(arg, "value") else str(arg) for arg in op.init_args
            ]
            result["output_types"] = [self._type_to_string(t) for t in op.init_types]

        # Extract attributes if present
        if op.attr:
            result["attributes"] = op.attr

        # Parse region body if present
        if op.region and op.region.body:
            # Generic op has a single block with block arguments
            result["body"] = []
            for block in op.region.body:
                # Block arguments are the iteration variables (stored in block label)
                if block.label and block.label.arg_ids and block.label.arg_types:
                    result["block_args"] = [
                        arg.value if hasattr(arg, "value") else str(arg)
                        for arg in block.label.arg_ids
                    ]
                    result["block_arg_types"] = [
                        self._type_to_string(arg_type)
                        for arg_type in block.label.arg_types
                    ]
                    result["block_arg_types"] = [
                        self._type_to_string(arg_type)
                        for arg_type in block.label.arg_types
                    ]

                # Parse operations in the block
                for body_op in block.body:
                    op_dict = self._parse_operation(body_op)
                    if op_dict:
                        result["body"].append(op_dict)

        # Add destination if result_list exists
        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value"):
                result["dest"] = result_item.value

        if op.out_type:
            result["result_type"] = self._type_to_string(op.out_type)

        return result

    def _parse_linalg_matmul(self, op_node) -> Dict[str, Any]:
        """Parse linalg.matmul operation."""
        op = op_node.op
        result = {
            "op": "linalg.matmul",
        }

        # Extract input and output arguments
        if hasattr(op, "a_id"):
            result["A"] = op.a_id.value if hasattr(op.a_id, "value") else str(op.a_id)
            result["B"] = op.b_id.value if hasattr(op.b_id, "value") else str(op.b_id)
            result["C"] = op.c_id.value if hasattr(op.c_id, "value") else str(op.c_id)

        # Extract types
        if hasattr(op, "a_type"):
            result["A_type"] = self._type_to_string(op.a_type)
            result["B_type"] = self._type_to_string(op.b_type)
            result["C_type"] = self._type_to_string(op.c_type)

        # Add destination if result_list exists
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value"):
                result["dest"] = result_item.value

        if op.out_type:
            result["result_type"] = self._type_to_string(op.out_type)

        return result

    def _parse_linalg_yield(self, op_node) -> Dict[str, Any]:
        """Parse linalg.yield operation."""
        op = op_node.op
        result = {
            "op": "linalg.yield",
        }
        # Extract yielded values
        if op.operand_ids:
            result["values"] = [
                operand.value if hasattr(operand, "value") else str(operand)
                for operand in op.operand_ids
            ]
            result["types"] = [self._type_to_string(t) for t in op.operand_types]
        return result

    # SCF dialect handlers
    def _parse_scf_for_op(self, op_node) -> Dict[str, Any]:
        """Parse scf.for operation."""
        op = op_node.op
        result = {
            "op": "scf.for",
            "iv": op.index.value if hasattr(op.index, "value") else str(op.index),
            "lb": self._ssa_use_to_string(op.begin),
            "ub": self._ssa_use_to_string(op.end),
            "step": self._ssa_use_to_string(op.step),
        }

        # Add destination if result_list exists
        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value

        # Handle iteration arguments if present
        if op.iter_args:
            # For now, assume single iteration argument
            if len(op.iter_args) > 0:
                iter_arg_assignment = op.iter_args[0]
                # ArgumentAssignment has 'name' and 'value' fields
                result["iter_arg"] = self._ssa_use_to_string(iter_arg_assignment.name)
                result["init"] = self._ssa_use_to_string(iter_arg_assignment.value)

        if op.out_type:
            result["result_type"] = self._type_to_string(op.out_type)

        # Parse body region
        if op.body and op.body.body:
            result["body"] = []
            for block in op.body.body:
                for body_op in block.body:
                    op_dict = self._parse_operation(body_op)
                    if op_dict:
                        result["body"].append(op_dict)

        return result

    def _parse_scf_if_op(self, op_node) -> Dict[str, Any]:
        """Parse scf.if operation."""
        op = op_node.op
        result = {
            "op": "scf.if",
            "cond": self._ssa_use_to_string(op.cond),
        }

        # Add destination if result_list exists
        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value

        # Parse body region
        if op.body and op.body.body:
            result["body"] = []
            for block in op.body.body:
                for body_op in block.body:
                    op_dict = self._parse_operation(body_op)
                    if op_dict:
                        result["body"].append(op_dict)

        # Parse else region if present
        if op.elsebody and op.elsebody.body:
            result["elsebody"] = []
            for block in op.elsebody.body:
                for body_op in block.body:
                    op_dict = self._parse_operation(body_op)
                    if op_dict:
                        result["elsebody"].append(op_dict)

        if op.out_types:
            result["result_types"] = [self._type_to_string(t) for t in op.out_types]

        return result

    def _parse_scf_yield_op(self, op_node) -> Dict[str, Any]:
        """Parse scf.yield operation."""
        op = op_node.op
        result = {
            "op": "scf.yield",
        }

        # Yield can have results (SCFYield has 'results' attribute)
        if hasattr(op, "results") and op.results:
            # Assume single result for now
            result["value"] = self._ssa_use_to_string(op.results[0])

        return result

    def _parse_scf_condition_op(self, op_node) -> Dict[str, Any]:
        """Parse scf.condition operation."""
        op = op_node.op
        result = {
            "op": "scf.condition",
        }

        if hasattr(op, "condition"):
            result["condition"] = self._ssa_use_to_string(op.condition)

        if hasattr(op, "args") and op.args:
            result["args"] = [self._ssa_use_to_string(arg) for arg in op.args]

        if hasattr(op, "out_types") and op.out_types:
            result["out_types"] = [self._type_to_string(t) for t in op.out_types]

        return result

    def _parse_br_op(self, op_node) -> Dict[str, Any]:
        """Parse br operation."""
        op = op_node.op
        target = op.block.value if hasattr(op.block, "value") else str(op.block)
        # Ensure target has ^ prefix for compatibility with block labels
        if not target.startswith("^"):
            target = "^" + target
        result = {
            "op": "cf.br",
            "target": target,
            "target_block": target,  # alias for interpreter compatibility
        }
        # Add destination if result_list exists
        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Parse arguments if present
        if hasattr(op, "args") and op.args:
            args_list = []
            for arg_tuple in op.args:
                # arg_tuple should be (SsaId, Type)
                ssa_id, typ = arg_tuple
                ssa_str = self._ssa_use_to_string(ssa_id)
                type_str = self._type_to_string(typ)
                args_list.append((ssa_str, type_str))
            result["args"] = args_list
        # Add edge to CFG
        if self.current_block_label is not None and self.current_func is not None:
            self.current_func.cfg.add_edge(self.current_block_label, target)
        return result

    def _parse_cond_br_op(self, op_node) -> Dict[str, Any]:
        """Parse cond_br operation."""
        op = op_node.op
        target_true = (
            op.block_true.value
            if hasattr(op.block_true, "value")
            else str(op.block_true)
        )
        target_false = (
            op.block_false.value
            if hasattr(op.block_false, "value")
            else str(op.block_false)
        )
        # Ensure targets have ^ prefix for compatibility with block labels
        if not target_true.startswith("^"):
            target_true = "^" + target_true
        if not target_false.startswith("^"):
            target_false = "^" + target_false
        result = {
            "op": "cf.cond_br",
            "cond": self._ssa_use_to_string(op.cond),
            "target_true": target_true,
            "target_false": target_false,
            "true_block": target_true,  # alias for interpreter compatibility
            "false_block": target_false,  # alias for interpreter compatibility
        }
        # Add destination if result_list exists
        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Add edges to CFG
        if self.current_block_label is not None and self.current_func is not None:
            self.current_func.cfg.add_edge(self.current_block_label, target_true)
            self.current_func.cfg.add_edge(self.current_block_label, target_false)
        return result

    def _parse_arith_binary_op(self, op_node):
        """Parse arith binary operation (addi, subi, muli, etc.)."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Extract operands
        result["lhs"] = self._ssa_use_to_string(op.operand_a)
        result["rhs"] = self._ssa_use_to_string(op.operand_b)
        # Extract type
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_arith_unary_op(self, op_node):
        """Parse arith unary operation (absf, ceilf, etc.)."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        result["value"] = self._ssa_use_to_string(op.operand)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_arith_cmpi_op(self, op_node):
        """Parse arith.cmpi operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        result["lhs"] = self._ssa_use_to_string(op.operand_a)
        result["rhs"] = self._ssa_use_to_string(op.operand_b)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        # Extract predicate (arith.cmpi uses integer predicate values)
        if hasattr(op, "predicate"):
            predicate = op.predicate
            # Map integer predicate to string if known
            if predicate == 0:
                result["pred"] = "eq"
            elif predicate == 1:
                result["pred"] = "ne"
            elif predicate == 2:
                result["pred"] = "slt"
            elif predicate == 3:
                result["pred"] = "sle"
            elif predicate == 4:
                result["pred"] = "sgt"
            elif predicate == 5:
                result["pred"] = "sge"
            else:
                # Keep as integer, interpreter will handle it
                result["pred"] = str(predicate)
        elif hasattr(op, "comptype"):
            # pymlir stores predicate as comptype (string like "slt")
            comptype = op.comptype
            result["pred"] = str(comptype)
        else:
            # Fallback - shouldn't happen with pymlir
            result["pred"] = "slt"
        return result

    def _parse_arith_cmpf_op(self, op_node):
        """Parse arith.cmpf operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        result["lhs"] = self._ssa_use_to_string(op.operand_a)
        result["rhs"] = self._ssa_use_to_string(op.operand_b)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        # Extract predicate (arith.cmpf uses integer predicate values)
        if hasattr(op, "predicate"):
            predicate = op.predicate
            # Map integer predicate to string if known
            # Using same mapping as cmpi for now
            if predicate == 0:
                result["pred"] = "eq"
            elif predicate == 1:
                result["pred"] = "ne"
            elif predicate == 2:
                result["pred"] = "slt"
            elif predicate == 3:
                result["pred"] = "sle"
            elif predicate == 4:
                result["pred"] = "sgt"
            elif predicate == 5:
                result["pred"] = "sge"
            else:
                # Keep as integer, interpreter will handle it
                result["pred"] = str(predicate)
        elif hasattr(op, "comptype"):
            # pymlir stores predicate as comptype (string like "slt")
            comptype = op.comptype
            result["pred"] = str(comptype)
        else:
            # Fallback - shouldn't happen with pymlir
            result["pred"] = "slt"
        return result

    def _parse_arith_constant_op(self, op_node):
        """Parse arith.constant operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        result["value"] = self._parse_constant_value(op.value)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_arith_select_op(self, op_node):
        """Parse arith.select operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        result["cond"] = self._ssa_use_to_string(op.cond)
        result["arg_true"] = self._ssa_use_to_string(op.arg_true)
        result["arg_false"] = self._ssa_use_to_string(op.arg_false)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_arith_cast_op(self, op_node):
        """Parse arith cast operation (index_cast, memref_cast, tensor_cast)."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        result["value"] = self._ssa_use_to_string(op.arg)
        if hasattr(op, "dst_type"):
            result["type"] = self._type_to_string(op.dst_type)
        elif hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    # Memref dialect handlers
    def _parse_memref_dim_op(self, op_node):
        """Parse memref.dim operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "index": self._ssa_use_to_string(op.index),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_alloc_op(self, op_node):
        """Parse memref.alloc operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "args": self._ssa_use_to_string(op.args),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_alloca_op(self, op_node):
        """Parse memref.alloca operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "args": self._ssa_use_to_string(op.args),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_dealloc_op(self, op_node):
        """Parse memref.dealloc operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "arg": self._ssa_use_to_string(op.arg),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_dma_start_op(self, op_node):
        """Parse memref.dma_start operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "src": self._ssa_use_to_string(op.src),
            "src_index": [self._ssa_use_to_string(idx) for idx in op.src_index],
            "dst": self._ssa_use_to_string(op.dst),
            "dst_index": [self._ssa_use_to_string(idx) for idx in op.dst_index],
            "size": self._ssa_use_to_string(op.size),
            "tag": self._ssa_use_to_string(op.tag),
            "tag_index": [self._ssa_use_to_string(idx) for idx in op.tag_index],
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
            "tag_type": self._type_to_string(op.tag_type),
        }
        if op.stride is not None:
            result["stride"] = self._ssa_use_to_string(op.stride)
        if op.transfer_per_stride is not None:
            result["transfer_per_stride"] = self._ssa_use_to_string(
                op.transfer_per_stride
            )
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_dma_wait_op(self, op_node):
        """Parse memref.dma_wait operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "tag": self._ssa_use_to_string(op.tag),
            "tag_index": [self._ssa_use_to_string(idx) for idx in op.tag_index],
            "size": self._ssa_use_to_string(op.size),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_load_op(self, op_node):
        """Parse memref.load operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "arg": self._ssa_use_to_string(op.arg),
            "index": [self._ssa_use_to_string(idx) for idx in op.index],
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_store_op(self, op_node):
        """Parse memref.store operation."""
        op = op_node.op
        # After fixing pymlir dialect definition:
        # op.value is the value to store (first operand)
        # op.memref is the memref to store into (second operand)
        result = {
            "op": op.__class__._opname_,
            "addr": self._ssa_use_to_string(op.memref),  # memref (second operand)
            "ref": self._ssa_use_to_string(op.value),  # value (first operand)
            "index": [self._ssa_use_to_string(idx) for idx in op.index],
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_subview_op(self, op_node):
        """Parse memref.subview operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "offsets": [self._ssa_use_to_string(off) for off in op.offsets],
            "sizes": [self._ssa_use_to_string(sz) for sz in op.sizes],
            "strides": [self._ssa_use_to_string(st) for st in op.strides],
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_view_op(self, op_node):
        """Parse memref.view operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "offset": self._ssa_use_to_string(op.offset),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op.sizes is not None:
            result["sizes"] = [self._ssa_use_to_string(sz) for sz in op.sizes]
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_cast_op(self, op_node):
        """Parse memref.cast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "arg": self._ssa_use_to_string(op.arg),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_collapse_shape_op(self, op_node):
        """Parse memref.collapse_shape operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_expand_shape_op(self, op_node):
        """Parse memref.expand_shape operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_reinterpret_cast_op(self, op_node):
        """Parse memref.reinterpret_cast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "offsets": [self._ssa_use_to_string(off) for off in op.offsets],
            "sizes": [self._ssa_use_to_string(sz) for sz in op.sizes],
            "strides": [self._ssa_use_to_string(st) for st in op.strides],
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_memref_memory_space_cast_op(self, op_node):
        """Parse memref.memory_space_cast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    # Tensor dialect handlers
    def _parse_tensor_extract_op(self, op_node):
        """Parse tensor.extract operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "arg": self._ssa_use_to_string(op.arg),
            "index": [self._ssa_use_to_string(idx) for idx in op.index],
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_splat_op(self, op_node):
        """Parse tensor.splat operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "arg": self._ssa_use_to_string(op.arg),
            "type": self._type_to_string(op.type),
            "attributes": {},
        }
        if hasattr(op, "dynamic_sizes") and op.dynamic_sizes is not None:
            result["attributes"]["dynamic_sizes"] = [
                self._ssa_use_to_string(sz) for sz in op.dynamic_sizes
            ]
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_load_op(self, op_node):
        """Parse tensor.load operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "arg": self._ssa_use_to_string(op.arg),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_store_op(self, op_node):
        """Parse tensor.store operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "args": self._ssa_use_to_string(op.args),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_cast_op(self, op_node):
        """Parse tensor.cast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "arg": self._ssa_use_to_string(op.arg),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_bitcast_op(self, op_node):
        """Parse tensor.bitcast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "arg": self._ssa_use_to_string(op.arg),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_collapse_shape_op(self, op_node):
        """Parse tensor.collapse_shape operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_expand_shape_op(self, op_node):
        """Parse tensor.expand_shape operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_concat_op(self, op_node):
        """Parse tensor.concat operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "args": self._ssa_use_to_string(op.args),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_dim_op(self, op_node):
        """Parse tensor.dim operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "index": self._ssa_use_to_string(op.index),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_empty_op(self, op_node):
        """Parse tensor.empty operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "type": self._type_to_string(op.type),
            "attributes": {},
        }
        if hasattr(op, "dynamic_sizes") and op.dynamic_sizes is not None:
            result["attributes"]["dynamic_sizes"] = [
                self._ssa_use_to_string(sz) for sz in op.dynamic_sizes
            ]
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_extract_slice_op(self, op_node):
        """Parse tensor.extract_slice operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "offsets": [self._ssa_use_to_string(off) for off in op.offsets],
            "sizes": [self._ssa_use_to_string(sz) for sz in op.sizes],
            "strides": [self._ssa_use_to_string(st) for st in op.strides],
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_insert_slice_op(self, op_node):
        """Parse tensor.insert_slice operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "src": self._ssa_use_to_string(op.src),
            "dst": self._ssa_use_to_string(op.dst),
            "offsets": [self._ssa_use_to_string(off) for off in op.offsets],
            "sizes": [self._ssa_use_to_string(sz) for sz in op.sizes],
            "strides": [self._ssa_use_to_string(st) for st in op.strides],
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_from_elements_op(self, op_node):
        """Parse tensor.from_elements operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "elements": [self._ssa_use_to_string(el) for el in op.elements],
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_generate_op(self, op_node):
        """Parse tensor.generate operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "type": self._type_to_string(op.type),
            "attributes": {},
        }
        if hasattr(op, "dynamic_extents") and op.dynamic_extents is not None:
            result["attributes"]["dynamic_extents"] = [
                self._ssa_use_to_string(ext) for ext in op.dynamic_extents
            ]
        if op.body and op.body.body:
            # Parse region body operations
            result["body"] = []
            for block in op.body.body:
                for body_op in block.body:
                    op_dict = self._parse_operation(body_op)
                    if op_dict:
                        result["body"].append(op_dict)
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_insert_op(self, op_node):
        """Parse tensor.insert operation."""
        print(f"DEBUG _parse_tensor_insert_op called: op_node={op_node}")
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "memref": self._ssa_use_to_string(op.dst),  # tensor being inserted into
            "value": self._ssa_use_to_string(op.src),  # value to insert
            "indices": [self._ssa_use_to_string(idx) for idx in op.index],
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_pad_op(self, op_node):
        """Parse tensor.pad operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "low": [self._ssa_use_to_string(l) for l in op.low],
            "high": [self._ssa_use_to_string(h) for h in op.high],
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_rank_op(self, op_node):
        """Parse tensor.rank operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_reshape_op(self, op_node):
        """Parse tensor.reshape operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "operand": self._ssa_use_to_string(op.operand),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_scatter_op(self, op_node):
        """Parse tensor.scatter operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "indices": self._ssa_use_to_string(op.indices),
            "updates": self._ssa_use_to_string(op.updates),
            "target": self._ssa_use_to_string(op.target),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_gather_op(self, op_node):
        """Parse tensor.gather operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "indices": self._ssa_use_to_string(op.indices),
            "target": self._ssa_use_to_string(op.target),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_tensor_yield_op(self, op_node):
        """Parse tensor.yield operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "values": [self._ssa_use_to_string(val) for val in op.values],
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    # Bufferization dialect handlers
    def _parse_bufferization_alloc_tensor_op(self, op_node):
        """Parse bufferization.alloc_tensor operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "shape": [self._ssa_use_to_string(s) for s in op.shape],
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_bufferization_clone_op(self, op_node):
        """Parse bufferization.clone operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "src": self._ssa_use_to_string(op.src),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_bufferization_dealloc_op(self, op_node):
        """Parse bufferization.dealloc operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "buffer": self._ssa_use_to_string(op.buffer),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_bufferization_dealloc_tensor_op(self, op_node):
        """Parse bufferization.dealloc_tensor operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "tensor": self._ssa_use_to_string(op.tensor),
            "type": self._type_to_string(op.type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_bufferization_materialize_in_destination_op(self, op_node):
        """Parse bufferization.materialize_in_destination operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "src": self._ssa_use_to_string(op.src),
            "dst": self._ssa_use_to_string(op.dst),
            "src_type": self._type_to_string(op.src_type),
            "dst_type": self._type_to_string(op.dst_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_bufferization_to_buffer_op(self, op_node):
        """Parse bufferization.to_buffer operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "tensor": self._ssa_use_to_string(op.tensor),
            "tensor_type": self._type_to_string(op.tensor_type),
            "buffer_type": self._type_to_string(op.buffer_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    def _parse_bufferization_to_tensor_op(self, op_node):
        """Parse bufferization.to_tensor operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
            "buffer": self._ssa_use_to_string(op.buffer),
            "buffer_type": self._type_to_string(op.buffer_type),
            "tensor_type": self._type_to_string(op.tensor_type),
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        return result

    # Shape dialect handlers
    def _parse_shape_binary_op(self, op_node):
        """Parse shape binary operation (add, div, etc.)."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Extract lhs and rhs if they exist
        if hasattr(op, "lhs"):
            result["lhs"] = self._ssa_use_to_string(op.lhs)
        if hasattr(op, "rhs"):
            result["rhs"] = self._ssa_use_to_string(op.rhs)
        # Extract type if exists
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_unary_op(self, op_node):
        """Parse shape unary operation (any, etc.)."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Extract shape if exists
        if hasattr(op, "shape"):
            result["shape"] = self._ssa_use_to_string(op.shape)
        # Extract type if exists
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_assuming_op(self, op_node):
        """Parse shape.assuming operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "condition"):
            result["condition"] = self._ssa_use_to_string(op.condition)
        return result

    def _parse_shape_assuming_all_op(self, op_node):
        """Parse shape.assuming_all operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "conditions"):
            result["conditions"] = [self._ssa_use_to_string(c) for c in op.conditions]
        return result

    def _parse_shape_yield_op(self, op_node):
        """Parse shape.assuming_yield operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "values"):
            result["values"] = [self._ssa_use_to_string(v) for v in op.values]
        return result

    def _parse_shape_broadcast_op(self, op_node):
        """Parse shape.broadcast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "shapes"):
            result["shapes"] = [self._ssa_use_to_string(s) for s in op.shapes]
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_concat_op(self, op_node):
        """Parse shape.concat operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "shapes"):
            result["shapes"] = [self._ssa_use_to_string(s) for s in op.shapes]
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_const_shape_op(self, op_node):
        """Parse shape.const_shape operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "shape"):
            result["shape"] = [self._ssa_use_to_string(s) for s in op.shape]
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_const_size_op(self, op_node):
        """Parse shape.const_size operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "value"):
            result["value"] = op.value
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_const_witness_op(self, op_node):
        """Parse shape.const_witness operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "value"):
            result["value"] = op.value
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_cstr_broadcastable_op(self, op_node):
        """Parse shape.cstr_broadcastable operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "shapes"):
            result["shapes"] = [self._ssa_use_to_string(s) for s in op.shapes]
        return result

    def _parse_shape_cstr_eq_op(self, op_node):
        """Parse shape.cstr_eq operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "lhs"):
            result["lhs"] = self._ssa_use_to_string(op.lhs)
        if hasattr(op, "rhs"):
            result["rhs"] = self._ssa_use_to_string(op.rhs)
        return result

    def _parse_shape_cstr_require_op(self, op_node):
        """Parse shape.cstr_require operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "condition"):
            result["condition"] = self._ssa_use_to_string(op.condition)
        return result

    def _parse_shape_debug_print_op(self, op_node):
        """Parse shape.debug_print operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "value"):
            result["value"] = self._ssa_use_to_string(op.value)
        return result

    def _parse_shape_dim_op(self, op_node):
        """Parse shape.dim operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "shape"):
            result["shape"] = self._ssa_use_to_string(op.shape)
        if hasattr(op, "index"):
            result["index"] = self._ssa_use_to_string(op.index)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_from_extent_tensor_op(self, op_node):
        """Parse shape.from_extent_tensor operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "tensor"):
            result["tensor"] = self._ssa_use_to_string(op.tensor)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_shape_from_extents_op(self, op_node):
        """Parse shape.from_extents operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "extents"):
            result["extents"] = [self._ssa_use_to_string(e) for e in op.extents]
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    # Vector dialect handlers
    def _parse_vector_bitcast_op(self, op_node):
        """Parse vector.bitcast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "source"):
            result["source"] = self._ssa_use_to_string(op.source)
        if hasattr(op, "source_type"):
            result["source_type"] = self._type_to_string(op.source_type)
        if hasattr(op, "result_type"):
            result["result_type"] = self._type_to_string(op.result_type)
        return result

    def _parse_vector_broadcast_op(self, op_node):
        """Parse vector.broadcast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "source"):
            result["source"] = self._ssa_use_to_string(op.source)
        if hasattr(op, "result_type"):
            result["result_type"] = self._type_to_string(op.result_type)
        return result

    def _parse_vector_compress_store_op(self, op_node):
        """Parse vector.compressstore operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Extract fields based on operation definition
        if hasattr(op, "base"):
            result["base"] = self._ssa_use_to_string(op.base)
        if hasattr(op, "indices"):
            result["indices"] = [self._ssa_use_to_string(i) for i in op.indices]
        if hasattr(op, "mask"):
            result["mask"] = self._ssa_use_to_string(op.mask)
        if hasattr(op, "value"):
            result["value"] = self._ssa_use_to_string(op.value)
        if hasattr(op, "base_type"):
            result["base_type"] = self._type_to_string(op.base_type)
        if hasattr(op, "mask_type"):
            result["mask_type"] = self._type_to_string(op.mask_type)
        if hasattr(op, "value_type"):
            result["value_type"] = self._type_to_string(op.value_type)
        return result

    def _parse_vector_constant_mask_op(self, op_node):
        """Parse vector.constant_mask operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "mask_dimensions"):
            result["mask_dimensions"] = op.mask_dimensions
        if hasattr(op, "result_type"):
            result["result_type"] = self._type_to_string(op.result_type)
        return result

    def _parse_vector_contract_op(self, op_node):
        """Parse vector.contract operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Extract fields
        fields = [
            "lhs",
            "rhs",
            "acc",
            "indexing_maps",
            "iterator_types",
            "lhs_type",
            "rhs_type",
            "acc_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op, field):
                value = getattr(op, field)
                if isinstance(value, list):
                    if field == "iterator_types" and isinstance(value[0], str):
                        result[field] = value
                    else:
                        result[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    result[field] = self._type_to_string(value)
                else:
                    result[field] = self._ssa_use_to_string(value)
        return result

    def _parse_vector_create_mask_op(self, op_node):
        """Parse vector.create_mask operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "operands"):
            result["operands"] = [self._ssa_use_to_string(o) for o in op.operands]
        if hasattr(op, "result_type"):
            result["result_type"] = self._type_to_string(op.result_type)
        return result

    def _parse_vector_deinterleave_op(self, op_node):
        """Parse vector.deinterleave operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "source"):
            result["source"] = self._ssa_use_to_string(op.source)
        if hasattr(op, "result_type"):
            result["result_type"] = self._type_to_string(op.result_type)
        return result

    def _parse_vector_expand_load_op(self, op_node):
        """Parse vector.expandload operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Extract fields
        fields = [
            "base",
            "indices",
            "mask",
            "pass_thru",
            "base_type",
            "mask_type",
            "pass_thru_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op, field):
                value = getattr(op, field)
                if isinstance(value, list):
                    result[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    result[field] = self._type_to_string(value)
                else:
                    result[field] = self._ssa_use_to_string(value)
        return result

    def _parse_vector_extract_op(self, op_node):
        """Parse vector.extract operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "vector"):
            result["vector"] = self._ssa_use_to_string(op.vector)
        if hasattr(op, "position"):
            result["position"] = [self._ssa_use_to_string(p) for p in op.position]
        if hasattr(op, "vector_type"):
            result["vector_type"] = self._type_to_string(op.vector_type)
        if hasattr(op, "result_type"):
            result["result_type"] = self._type_to_string(op.result_type)
        return result

    def _parse_vector_extract_strided_slice_op(self, op_node):
        """Parse vector.extract_strided_slice operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        fields = ["vector", "offsets", "sizes", "strides", "vector_type", "result_type"]
        for field in fields:
            if hasattr(op, field):
                value = getattr(op, field)
                if isinstance(value, list):
                    result[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    result[field] = self._type_to_string(value)
                else:
                    result[field] = self._ssa_use_to_string(value)
        return result

    def _parse_vector_fma_op(self, op_node):
        """Parse vector.fma operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        fields = [
            "lhs",
            "rhs",
            "acc",
            "lhs_type",
            "rhs_type",
            "acc_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op, field):
                value = getattr(op, field)
                if field.endswith("_type"):
                    result[field] = self._type_to_string(value)
                else:
                    result[field] = self._ssa_use_to_string(value)
        return result

    def _parse_vector_from_elements_op(self, op_node):
        """Parse vector.from_elements operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "elements"):
            result["elements"] = [self._ssa_use_to_string(e) for e in op.elements]
        if hasattr(op, "result_type"):
            result["result_type"] = self._type_to_string(op.result_type)
        return result

    def _parse_vector_gather_op(self, op_node):
        """Parse vector.gather operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        fields = [
            "base",
            "indices",
            "index_vec",
            "mask",
            "pass_thru",
            "base_type",
            "index_vec_type",
            "mask_type",
            "pass_thru_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op, field):
                value = getattr(op, field)
                if isinstance(value, list):
                    result[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    result[field] = self._type_to_string(value)
                else:
                    result[field] = self._ssa_use_to_string(value)
        return result

    def _parse_vector_insert_op(self, op_node):
        """Parse vector.insert operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        fields = [
            "source",
            "dest",
            "position",
            "source_type",
            "dest_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op, field):
                value = getattr(op, field)
                if isinstance(value, list):
                    result[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    result[field] = self._type_to_string(value)
                else:
                    result[field] = self._ssa_use_to_string(value)
        return result

    def _parse_vector_insert_strided_slice_op(self, op_node):
        """Parse vector.insert_strided_slice operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        fields = [
            "source",
            "dest",
            "offsets",
            "strides",
            "source_type",
            "dest_type",
            "result_type",
        ]
        for field in fields:
            if hasattr(op, field):
                value = getattr(op, field)
                if isinstance(value, list):
                    result[field] = [self._ssa_use_to_string(v) for v in value]
                elif field.endswith("_type"):
                    result[field] = self._type_to_string(value)
                else:
                    result[field] = self._ssa_use_to_string(value)
        return result

    def _parse_vector_interleave_op(self, op_node):
        """Parse vector.interleave operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "lhs"):
            result["lhs"] = self._ssa_use_to_string(op.lhs)
        if hasattr(op, "rhs"):
            result["rhs"] = self._ssa_use_to_string(op.rhs)
        if hasattr(op, "result_type"):
            result["result_type"] = self._type_to_string(op.result_type)
        return result

    # Builtin dialect handlers
    def _parse_builtin_module_op(self, op_node):
        """Parse builtin.module operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        # Module may have region, but for now we don't parse it
        return result

    def _parse_builtin_unrealized_conversion_cast_op(self, op_node):
        """Parse builtin.unrealized_conversion_cast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "inputs"):
            result["inputs"] = [self._ssa_use_to_string(i) for i in op.inputs]
        if hasattr(op, "outputs"):
            result["outputs"] = [self._type_to_string(o) for o in op.outputs]
        return result

    # EmitC dialect handlers
    def _parse_emitc_binary_op(self, op_node):
        """Parse emitc binary operation (add, assign, bitwise_and, etc.)."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "lhs"):
            result["lhs"] = self._ssa_use_to_string(op.lhs)
        if hasattr(op, "rhs"):
            result["rhs"] = self._ssa_use_to_string(op.rhs)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_emitc_unary_op(self, op_node):
        """Parse emitc unary operation (address_of, bitwise_not, etc.)."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "operand"):
            result["operand"] = self._ssa_use_to_string(op.operand)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_emitc_apply_op(self, op_node):
        """Parse emitc.apply operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "callee"):
            result["callee"] = op.callee
        if hasattr(op, "args"):
            result["args"] = [self._ssa_use_to_string(a) for a in op.args]
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_emitc_call_op(self, op_node):
        """Parse emitc.call operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "callee"):
            result["callee"] = op.callee
        if hasattr(op, "args"):
            result["args"] = [self._ssa_use_to_string(a) for a in op.args]
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_emitc_call_opaque_op(self, op_node):
        """Parse emitc.call_opaque operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "callee"):
            result["callee"] = op.callee
        if hasattr(op, "args"):
            result["args"] = [self._ssa_use_to_string(a) for a in op.args]
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_emitc_cast_op(self, op_node):
        """Parse emitc.cast operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "operand"):
            result["operand"] = self._ssa_use_to_string(op.operand)
        if hasattr(op, "src_type"):
            result["src_type"] = self._type_to_string(op.src_type)
        if hasattr(op, "dst_type"):
            result["dst_type"] = self._type_to_string(op.dst_type)
        return result

    def _parse_emitc_class_op(self, op_node):
        """Parse emitc.class operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "name"):
            result["name"] = op.name
        return result

    def _parse_emitc_cmp_op(self, op_node):
        """Parse emitc.cmp operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "predicate"):
            result["predicate"] = op.predicate
        if hasattr(op, "lhs"):
            result["lhs"] = self._ssa_use_to_string(op.lhs)
        if hasattr(op, "rhs"):
            result["rhs"] = self._ssa_use_to_string(op.rhs)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_emitc_conditional_op(self, op_node):
        """Parse emitc.conditional operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "condition"):
            result["condition"] = self._ssa_use_to_string(op.condition)
        if hasattr(op, "true_value"):
            result["true_value"] = self._ssa_use_to_string(op.true_value)
        if hasattr(op, "false_value"):
            result["false_value"] = self._ssa_use_to_string(op.false_value)
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    def _parse_emitc_constant_op(self, op_node):
        """Parse emitc.constant operation."""
        op = op_node.op
        result = {
            "op": op.__class__._opname_,
        }
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value
        if hasattr(op, "value"):
            result["value"] = op.value
        if hasattr(op, "type"):
            result["type"] = self._type_to_string(op.type)
        return result

    # Generic operation parsers (reuse existing arith parsers)
    def _parse_generic_binary_op(self, op_node):
        """Generic parser for binary operations (BinaryOperation subclasses)."""
        return self._parse_arith_binary_op(op_node)

    def _parse_generic_unary_op(self, op_node):
        """Generic parser for unary operations (UnaryOperation subclasses)."""
        return self._parse_arith_unary_op(op_node)

    def _parse_generic_cmpi_op(self, op_node):
        """Generic parser for integer comparison operations (CmpiOperation subclasses)."""
        return self._parse_arith_cmpi_op(op_node)

    def _parse_generic_cmpf_op(self, op_node):
        """Generic parser for float comparison operations (CmpfOperation subclasses)."""
        return self._parse_arith_cmpf_op(op_node)

    def _parse_generic_constant_op(self, op_node):
        """Generic parser for constant operations (ConstantOperation subclasses)."""
        return self._parse_arith_constant_op(op_node)

    # Generic dialect operation parser
    def _parse_generic_dialect_op(self, op_node):
        """Generic parser for dialect operations using dataclass fields."""
        import dataclasses

        op = op_node.op
        result = {
            "op": getattr(op.__class__, "_opname_", op.__class__.__name__),
        }

        # Extract destination from result_list if present
        if op_node.result_list:
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                result["dest"] = result_item.value.value

        # Convert fields based on their names and types
        if dataclasses.is_dataclass(op):
            for field in dataclasses.fields(op):
                field_name = field.name
                # Skip internal fields
                if field_name.startswith("_") or field_name in (
                    "match",
                    "_rule_",
                    "_syntax_",
                    "_syntax_fields_",
                    "_lark_",
                ):
                    continue
                value = getattr(op, field_name, None)
                if value is None:
                    continue

                # Convert based on field name patterns
                if field_name.endswith("_type") or field_name in (
                    "type",
                    "src_type",
                    "dst_type",
                    "element_type",
                    "result_type",
                ):
                    result[field_name] = self._type_to_string(value)
                elif field_name.endswith("_list") or isinstance(value, list):
                    # Convert list elements
                    if field_name == "index" and all(
                        isinstance(v, mast.SsaId) for v in value
                    ):
                        result[field_name] = [self._ssa_use_to_string(v) for v in value]
                    else:
                        # Generic list conversion
                        result[field_name] = [
                            self._ssa_use_to_string(v)
                            if hasattr(v, "value")
                            else str(v)
                            for v in value
                        ]
                else:
                    # Single value
                    result[field_name] = self._ssa_use_to_string(value)
        else:
            # Fallback: use existing attributes
            for attr in dir(op):
                if not attr.startswith("_") and not callable(getattr(op, attr)):
                    # Skip already handled attributes
                    if attr in result:
                        continue
                    value = getattr(op, attr)
                    if attr == "type":
                        result[attr] = self._type_to_string(value)
                    elif isinstance(value, (mast.SsaId, int, str, float, bool)):
                        result[attr] = self._ssa_use_to_string(value)

        return result

    # Helper methods
    def _ssa_use_to_string(self, ssa_use) -> str:
        """Convert SSA use (SsaId, int, etc.) to string."""
        if isinstance(ssa_use, mast.SsaId):
            return ssa_use.value
        elif isinstance(ssa_use, int):
            return str(ssa_use)
        else:
            return str(ssa_use)

    def _map_or_set_id_to_string(self, map_or_set_id) -> str:
        """Convert MapOrSetId to string."""
        if hasattr(map_or_set_id, "value"):
            return map_or_set_id.value
        return str(map_or_set_id)

    def _affine_expr_to_string(self, affine_expr) -> str:
        """Convert affine expression to string."""
        # For now, return dump
        try:
            return affine_expr.dump()
        except:
            return str(affine_expr)
