#!/usr/bin/env python3
"""
Control Flow dialect execution handlers.

Handles operations: cond_br, br, br_args, etc.
"""

from typing import Any

from .base import OperationHandler
from ..operations import (
    ConditionalBranchOperation,
    UnconditionalBranchOperation,
    Operation,
)
from ..models import SymbolicState, MLIRFunction


class CondBrHandler(OperationHandler):
    """Handler for cf.cond_br operation."""

    def execute_symbolic(
        self,
        op: ConditionalBranchOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute conditional branch symbolically."""
        if not isinstance(op, ConditionalBranchOperation):
            raise TypeError(f"Expected ConditionalBranchOperation, got {type(op)}")
        if interpreter is None:
            raise ValueError("CondBrHandler requires interpreter parameter")
        interpreter.cf_executor.execute_conditional_branch(op, state, func, interpreter)

    def _try_concrete_evaluation(
        self, op: ConditionalBranchOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of condition."""
        cond_concrete = state.get_concrete_value(op.cond)
        if cond_concrete is not None:
            return cond_concrete
        return None

    def execute_concolic(
        self,
        op: ConditionalBranchOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute conditional branch concolically."""
        if not isinstance(op, ConditionalBranchOperation):
            raise TypeError(f"Expected ConditionalBranchOperation, got {type(op)}")
        if interpreter is None:
            raise ValueError("CondBrHandler requires interpreter parameter")
        interpreter.cf_executor.execute_conditional_branch_concolic(
            op, state, func, interpreter
        )


class BrHandler(OperationHandler):
    """Handler for cf.br operation."""

    def execute_symbolic(
        self,
        op: UnconditionalBranchOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute unconditional branch symbolically."""
        if not isinstance(op, UnconditionalBranchOperation):
            raise TypeError(f"Expected UnconditionalBranchOperation, got {type(op)}")
        if interpreter is None:
            raise ValueError("BrHandler requires interpreter parameter")
        interpreter.cf_executor.execute_unconditional_branch(
            op, state, func, interpreter
        )

    def _try_concrete_evaluation(
        self, op: UnconditionalBranchOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Unconditional branch doesn't produce values."""
        return None


class BrArgsHandler(OperationHandler):
    """Handler for cf.br_args operation (branch with arguments)."""

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute branch with arguments symbolically."""
        # For now, treat same as unconditional branch
        # TODO: Handle argument passing between blocks
        state.pc = None  # Will be set by interpreter based on operation dict

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        return None


# Function to register all cf dialect handlers
def register_handlers(registry) -> None:
    """Register cf dialect handlers with registry."""
    registry.register("cf.cond_br", CondBrHandler())
    registry.register("cf.br", BrHandler())
    registry.register("cf.br_args", BrArgsHandler())
