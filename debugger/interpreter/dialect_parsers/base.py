#!/usr/bin/env python3
"""
Base classes for dialect operation parsers.

Provides common patterns for parsing MLIR AST nodes into interpreter
Operation objects, skipping the intermediate dictionary representation.
"""

from typing import Any, Dict, Optional, Type
import dataclasses
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import parser.astnodes as mast
from ..operations import (
    Operation,
    BinaryOperation,
    UnaryOperation,
    CompareOperation,
    ConstantOperation,
)
from ..models import MLIRFunction


class BaseDialectParser:
    """Base class for dialect-specific parsers.

    Each dialect parser should inherit from this class and implement
    parsing methods for its operations. The parser should convert
    pymlir AST nodes directly to interpreter Operation objects.
    """

    def __init__(self, parser_context: Optional[Any] = None):
        """Initialize parser with optional context.

        Args:
            parser_context: Reference to the main MLIRParser instance
                           for accessing shared utilities and state.
        """
        self.parser_context = parser_context

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse an operation AST node.

        This is the main entry point for dialect parsers. Subclasses
        should override this method or register specific operation parsers.

        Args:
            op_node: The pymlir Operation AST node

        Returns:
            Operation object or None if operation not handled
        """
        # Default implementation: try to find a handler method
        op_obj = op_node.op

        # Determine operation class name
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__
            # Try to find method like parse_AddiOperation
            method_name = f"parse_{class_name}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                return method(op_node)

        return None

    # Common utility methods (adapted from MLIRParser)

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

    def _ssa_use_to_string(self, ssa_use) -> str:
        """Convert SSA use (SsaId, int, etc.) to string."""
        if isinstance(ssa_use, mast.SsaId):
            return ssa_use.value
        elif isinstance(ssa_use, int):
            return str(ssa_use)
        else:
            return str(ssa_use)

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
                return val.value
            return val
        elif isinstance(attr_node, mast.ArrayAttr):
            # ArrayAttr has value list
            return [self._parse_attribute(sub) for sub in attr_node.value]
        elif hasattr(mast, "AttributeDict") and isinstance(
            attr_node, mast.AttributeDict
        ):
            # AttributeDict has values list of AttributeEntry
            result = {}
            for entry in attr_node.values:
                # entry should have name and value attributes
                if hasattr(entry, "name") and hasattr(entry, "value"):
                    result[entry.name] = self._parse_attribute(entry.value)
            return result
        elif hasattr(mast, "DictionaryAttr") and isinstance(
            attr_node, mast.DictionaryAttr
        ):
            # DictionaryAttr has value list of AttributeEntry
            result = {}
            for entry in attr_node.value:
                # entry should have name and value attributes
                if hasattr(entry, "name") and hasattr(entry, "value"):
                    result[entry.name] = self._parse_attribute(entry.value)
            return result
        elif isinstance(attr_node, mast.TypeAttr):
            # TypeAttr has value type
            return self._type_to_string(attr_node.value)
        elif isinstance(attr_node, mast.UnitAttr):
            # UnitAttr has no value
            return None
        else:
            # Unhandled attribute type
            return str(attr_node)

    def _extract_destination(self, op_node: mast.Operation) -> Optional[str]:
        """Extract destination SSA value from operation result list."""
        if op_node.result_list:
            # Assume single result for now
            result_item = op_node.result_list[0]
            if hasattr(result_item, "value") and hasattr(result_item.value, "value"):
                return result_item.value.value
        return None

    def _extract_line_number(self, op_node: mast.Operation) -> int:
        """Extract line number from operation location.

        This should be implemented by the main parser context.
        For now, returns 0.
        """
        if self.parser_context and hasattr(self.parser_context, "_extract_line_number"):
            return self.parser_context._extract_line_number(op_node)
        return 0


class DialectParserRegistry:
    """Registry for dialect operation parsers.

    Maps dialect names to parser instances or operation class names
    to specific parser methods.
    """

    def __init__(self):
        self.parsers: Dict[str, BaseDialectParser] = {}
        self.operation_handlers: Dict[str, Any] = {}  # op_class_name -> handler

    def register_dialect(self, dialect_name: str, parser: BaseDialectParser) -> None:
        """Register a parser for a dialect."""
        self.parsers[dialect_name] = parser

    def register_operation(self, op_class_name: str, handler: Any) -> None:
        """Register a specific handler for an operation class."""
        self.operation_handlers[op_class_name] = handler

    def get_parser(self, dialect_name: str) -> Optional[BaseDialectParser]:
        """Get parser for dialect name."""
        return self.parsers.get(dialect_name)

    def get_operation_handler(self, op_class_name: str) -> Optional[Any]:
        """Get handler for operation class name."""
        return self.operation_handlers.get(op_class_name)

    def parse(self, op_node: mast.Operation) -> Optional[Operation]:
        """Attempt to parse an operation using registered parsers.

        Args:
            op_node: The pymlir Operation AST node

        Returns:
            Operation object or None if no parser can handle it
        """
        op_obj = op_node.op

        # First, try operation-specific handler
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__
            handler = self.get_operation_handler(class_name)
            if handler:
                return handler(op_node)

        # Then, try dialect parser based on operation name
        # Determine dialect from operation class or namespace
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__
            # Check if it's a DialectOp with _opname_
            if hasattr(op_obj.__class__, "_opname_"):
                opname = op_obj.__class__._opname_
                if "." in opname:
                    dialect_name = opname.split(".")[0]
                    parser = self.get_parser(dialect_name)
                    if parser:
                        return parser.parse_operation(op_node)

            # Handle GenericOperation (quoted operation names in MLIR)
            if class_name == "GenericOperation" and hasattr(op_obj, "name"):
                # name could be StringLiteral with value attribute, or plain string
                name_obj = op_obj.name
                if hasattr(name_obj, "value"):
                    opname = name_obj.value
                else:
                    opname = str(name_obj)
                if "." in opname:
                    dialect_name = opname.split(".")[0]
                    parser = self.get_parser(dialect_name)
                    if parser:
                        return parser.parse_operation(op_node)

            # Handle CustomOperation (namespace.name operations)
            if (
                class_name == "CustomOperation"
                and hasattr(op_obj, "namespace")
                and hasattr(op_obj, "name")
            ):
                opname = f"{op_obj.namespace}.{op_obj.name}"
                dialect_name = op_obj.namespace
                parser = self.get_parser(dialect_name)
                if parser:
                    return parser.parse_operation(op_node)

        return None
