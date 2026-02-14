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
from .operations import Operation, ReturnOperation

# Import dialect modules
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

# Import models from same directory
from .models import MLIRFunction

from .dialect_parsers import DialectParserRegistry, register_default_parsers


class MLIRParser:
    """Parser for MLIR text format using pymlir library.

    Known limitations:
    - cf.cond_br with block references (^true, ^false) in generic operation attributes
      is not supported by pymlir's grammar. Use scf.if instead.
    """

    def __init__(self):
        """Initialize parser with operation dataclass mode."""
        self.parser = Parser()
        # Dialect parser registry for direct Operation object parsing
        self.dialect_parser_registry = DialectParserRegistry()
        register_default_parsers(self.dialect_parser_registry)
        # Set parser context for all dialect parsers to enable region parsing
        for parser in self.dialect_parser_registry.parsers.values():
            parser.parser_context = self

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
            operation = self._parse_operation(op)
            if operation:
                # Line number is already set by _parse_operation via _extract_line_number
                bb.add_operation(operation)

        # Clear current block and function
        self.current_block_label = None
        self.current_func = None

    def _parse_operation(
        self, op: mast.Operation
    ) -> Optional[Any]:  # Returns Operation or None
        """Parse an operation into Operation object using dialect parser registry."""
        # Try dialect parser registry first (returns Operation objects directly)
        operation = self.dialect_parser_registry.parse(op)
        if operation is not None:
            # Set line number only if not already set by dialect parser
            if operation.line == 0:
                operation.line = self._extract_line_number(op)
            # Note: location information not stored in Operation currently
            return operation

        # No dialect parser registered for this operation
        # Create a generic Operation object as fallback
        op_obj = op.op
        class_name = op_obj.__class__.__name__

        # Extract destination if possible
        dest = None
        if hasattr(op_obj, "result_list") and op_obj.result_list:
            # Assume single result
            result_item = op_obj.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                dest = result_item.value.value

        # Determine dialect and name based on operation type
        dialect = "unknown"
        name = class_name
        if (
            class_name == "CustomOperation"
            and hasattr(op_obj, "namespace")
            and hasattr(op_obj, "name")
        ):
            dialect = op_obj.namespace
            name = op_obj.name
        elif class_name == "GenericOperation" and hasattr(op_obj, "name"):
            name_obj = op_obj.name
            if hasattr(name_obj, "value"):
                full_name = name_obj.value
            else:
                full_name = str(name_obj)
            if "." in full_name:
                dialect, name = full_name.split(".", 1)
            else:
                dialect = "unknown"
                name = full_name

        # Parse attributes if present
        attributes = {}
        if hasattr(op_obj, "attributes") and op_obj.attributes is not None:
            attributes = self._parse_attribute_dict(op_obj.attributes)

        # Extract result type
        result_type = None
        if hasattr(op_obj, "type"):
            result_type = self._type_to_string(op_obj.type)

        line = self._extract_line_number(op)

        return Operation(
            dialect=dialect,
            name=name,
            line=line,
            dest=dest or "",
            result_type=result_type,
            attributes=attributes,
        )

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
