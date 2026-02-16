#!/usr/bin/env python3
"""
Control flow (cf) dialect parser.

Converts pymlir AST nodes for control flow operations directly to
interpreter Operation objects, skipping the intermediate dictionary
representation.
"""

from typing import Optional, List, Tuple

import parser.astnodes as mast

from .base import BaseDialectParser
from ..operations import (
    Operation,
    ConditionalBranchOperation,
    UnconditionalBranchOperation,
)


class CfDialectParser(BaseDialectParser):
    """Parser for control flow dialect operations."""

    def parse_operation(self, op_node: mast.Operation) -> Optional[Operation]:
        """Parse a cf operation.

        Dispatches to appropriate parser based on operation class.
        """
        op_obj = op_node.op

        # Check operation class and dispatch
        if hasattr(op_obj, "__class__"):
            class_name = op_obj.__class__.__name__

            # Map operation class names to parser methods
            if class_name == "CfBrOp":
                return self._parse_br_operation(op_node)
            elif class_name == "CfCondBrOp":
                return self._parse_cond_br_operation(op_node)
            # Add other cf operations as needed

        # No handler found
        return None

    # Individual operation parsers
    def _parse_br_operation(
        self, op_node: mast.Operation
    ) -> Optional[UnconditionalBranchOperation]:
        """Parse cf.br operation."""
        op_obj = op_node.op

        # Extract destination (br may not have a destination)
        dest = self._extract_destination(op_node)

        # Extract target block
        target = None
        if hasattr(op_obj, "block"):
            target = self._extract_block_target(op_obj.block)

        # Extract arguments if present
        args: List[Tuple[str, str]] = []
        if hasattr(op_obj, "args") and op_obj.args:
            for arg_tuple in op_obj.args:
                # arg_tuple should be (SsaId, Type)
                ssa_id, typ = arg_tuple
                ssa_str = self._ssa_use_to_string(ssa_id)
                type_str = self._type_to_string(typ)
                args.append((ssa_str, type_str))

        # Get line number
        line = self._extract_line_number(op_node)

        # Add CFG edge if parser context available
        if self.parser_context and target:
            self._add_cfg_edge(target)

        return UnconditionalBranchOperation(
            dialect="cf",
            name="br",
            line=line,
            dest=dest or "",
            result_type=None,
            target_block=self._strip_caret(target) if target else "",
            args=args,
        )

    def _parse_cond_br_operation(
        self, op_node: mast.Operation
    ) -> Optional[ConditionalBranchOperation]:
        """Parse cf.cond_br operation."""
        op_obj = op_node.op

        # Extract destination (cond_br may not have a destination)
        dest = self._extract_destination(op_node)

        # Extract condition
        cond = None
        if hasattr(op_obj, "cond"):
            cond = self._ssa_use_to_string(op_obj.cond)

        # Extract target blocks
        target_true = None
        target_false = None
        if hasattr(op_obj, "block_true"):
            target_true = self._extract_block_target(op_obj.block_true)
        if hasattr(op_obj, "block_false"):
            target_false = self._extract_block_target(op_obj.block_false)

        # Get line number
        line = self._extract_line_number(op_node)

        # Add CFG edges if parser context available
        if self.parser_context and target_true and target_false:
            self._add_cfg_edge(target_true)
            self._add_cfg_edge(target_false)

        return ConditionalBranchOperation(
            dialect="cf",
            name="cond_br",
            line=line,
            dest=dest or "",
            result_type=None,
            cond=self._strip_caret(cond) if cond else "",
            true_block=self._strip_caret(target_true) if target_true else "",
            false_block=self._strip_caret(target_false) if target_false else "",
        )

    # Helper methods
    def _extract_block_target(self, block_node) -> str:
        """Extract block target string, ensuring ^ prefix for compatibility."""
        if hasattr(block_node, "value"):
            target = block_node.value
        else:
            target = str(block_node)

        # Ensure target has ^ prefix for compatibility with block labels
        if target and not target.startswith("^"):
            target = "^" + target

        return target

    def _strip_caret(self, block_label: str) -> str:
        """Remove leading ^ from block label for Operation dataclass."""
        if block_label and block_label.startswith("^"):
            return block_label[1:]
        return block_label or ""

    def _add_cfg_edge(self, target_block: str) -> None:
        """Add edge from current block to target block in CFG.

        Requires parser_context with current_block_label and current_func.
        """
        if not self.parser_context:
            return

        # Get current block label and function from parser context
        current_block = getattr(self.parser_context, "current_block_label", None)
        current_func = getattr(self.parser_context, "current_func", None)

        if current_block and current_func and hasattr(current_func, "cfg"):
            # Add edge to CFG (target_block already has ^ prefix)
            current_func.cfg.add_edge(current_block, target_block)
