#!/usr/bin/env python3
"""
Control Flow dialect execution handlers.

Handles operations: cond_br, br, etc. Note: cf.br supports arguments via cf.br ^block(%arg : type) syntax.
"""

from typing import Any

from .base import OperationHandler
from ..operations import (
    ConditionalBranchOperation,
    UnconditionalBranchOperation,
    Operation,
)
from ..models import SymbolicState, MLIRFunction


class CondBrOpHandler(OperationHandler):
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


class BrOpHandler(OperationHandler):
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


# Function to register all cf dialect handlers
def register_handlers(registry) -> None:
    """Register cf dialect handlers with registry."""
    registry.register("cf.cond_br", CondBrOpHandler())
    registry.register("cf.br", BrOpHandler())
