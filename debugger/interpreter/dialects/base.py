#!/usr/bin/env python3
"""
Base classes for dialect operation execution.

Provides common patterns for operation handling while preserving
dialect boundaries and operation semantics.
"""

from typing import Any, Dict, Optional, Callable
import z3

from ..models import SymbolicState, MLIRFunction
from ..operations import (
    Operation,
    BinaryOperation,
    CompareOperation,
    ConstantOperation,
    UnaryOperation,
)


class OperationHandler:
    """Base class for operation handlers.

    Each dialect should provide handler methods for its operations.
    Handlers can be registered in the dialect registry.
    """

    def execute_symbolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute operation symbolically.

        Should be overridden by dialect-specific handlers.
        interpreter: Optional interpreter instance for operations that need
                    to modify interpreter state (e.g., control flow).
        """
        raise NotImplementedError(
            f"Symbolic execution not implemented for {op.full_name}"
        )

    def execute_concolic(
        self, op: Operation, state: SymbolicState, func: MLIRFunction, interpreter=None
    ) -> None:
        """Execute operation concolically (concrete + symbolic).

        Default implementation tries concrete evaluation first,
        falls back to symbolic execution.
        """
        print(f"DEBUG OperationHandler.execute_concolic: op={op}, type={type(op)}")
        # Try to evaluate concretely if possible
        concrete_result = self._try_concrete_evaluation(op, state, func)
        if concrete_result is not None:
            # Store concrete result
            if op.dest:
                state.set_concrete_value(op.dest, concrete_result)
            # Also create symbolic expression for consistency
            self.execute_symbolic(op, state, func, interpreter)
        else:
            # Fall back to symbolic execution
            self.execute_symbolic(op, state, func, interpreter)

    def _try_concrete_evaluation(
        self, op: Operation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Attempt concrete evaluation of operation.

        Returns concrete value if all operands are concrete, None otherwise.
        """
        return None


class BinaryOperationHandler(OperationHandler):
    """Handler for binary arithmetic operations."""

    def __init__(self, operator: Callable[[z3.ExprRef, z3.ExprRef], z3.ExprRef]):
        self.operator = operator

    def execute_symbolic(
        self,
        op: BinaryOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute binary operation symbolically."""
        if not isinstance(op, BinaryOperation):
            raise TypeError(f"Expected BinaryOperation, got {type(op)}")

        lhs_expr = state.get_expr(op.lhs)
        rhs_expr = state.get_expr(op.rhs)

        if lhs_expr is None or rhs_expr is None:
            raise ValueError(f"Cannot get expressions for operands: {op.lhs}, {op.rhs}")

        result_expr = self.operator(lhs_expr, rhs_expr)
        state.set_value(op.dest, result_expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: BinaryOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of binary operation."""
        lhs_concrete = state.get_concrete_value(op.lhs)
        rhs_concrete = state.get_concrete_value(op.rhs)
        print(
            f"DEBUG BinaryOperationHandler._try_concrete_evaluation: op={op.dest}, lhs={op.lhs}={lhs_concrete}, rhs={op.rhs}={rhs_concrete}"
        )

        if lhs_concrete is not None and rhs_concrete is not None:
            # Use the operator lambda with concrete values
            try:
                result = self.operator(lhs_concrete, rhs_concrete)
                print(f"DEBUG BinaryOperationHandler: concrete result={result}")
                return result
            except Exception:
                # Operator may not work with concrete values (should not happen)
                print("DEBUG BinaryOperationHandler: operator failed")
                return None
        return None


class ConstantOperationHandler(OperationHandler):
    """Handler for constant operations."""

    def execute_symbolic(
        self,
        op: ConstantOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute constant operation symbolically."""
        if not isinstance(op, ConstantOperation):
            raise TypeError(f"Expected ConstantOperation, got {type(op)}")

        # Create Z3 constant from value
        value = op.value
        if isinstance(value, int):
            expr = z3.IntVal(value)
        elif isinstance(value, float):
            expr = z3.RealVal(value)
        else:
            # Fallback to symbolic variable
            expr = z3.FreshConst(z3.IntSort(), f"const_{op.dest}")

        state.set_value(op.dest, expr, op.result_type or "i32")

        # Also store concrete value
        state.set_concrete_value(op.dest, value)

    def _try_concrete_evaluation(
        self, op: ConstantOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Constant operations always have concrete values."""
        return op.value


class CompareOperationHandler(OperationHandler):
    """Handler for comparison operations."""

    def __init__(
        self, predicate_map: Dict[str, Callable[[z3.ExprRef, z3.ExprRef], z3.ExprRef]]
    ):
        self.predicate_map = predicate_map

    def execute_symbolic(
        self,
        op: CompareOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute comparison operation symbolically."""
        if not isinstance(op, CompareOperation):
            raise TypeError(f"Expected CompareOperation, got {type(op)}")

        lhs_expr = state.get_expr(op.lhs)
        rhs_expr = state.get_expr(op.rhs)

        if lhs_expr is None or rhs_expr is None:
            raise ValueError(f"Cannot get expressions for operands: {op.lhs}, {op.rhs}")

        predicate_func = self.predicate_map.get(op.pred)
        if predicate_func is None:
            raise ValueError(f"Unknown predicate: {op.pred}")

        result_expr = predicate_func(lhs_expr, rhs_expr)
        state.set_value(op.dest, result_expr, op.result_type or "i1")

    def _try_concrete_evaluation(
        self, op: CompareOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of comparison."""
        lhs_concrete = state.get_concrete_value(op.lhs)
        rhs_concrete = state.get_concrete_value(op.rhs)

        if lhs_concrete is not None and rhs_concrete is not None:
            # Map predicate to Python comparison
            predicate_map = {
                "eq": lambda left, right: left == right,
                "ne": lambda left, right: left != right,
                "slt": lambda left, right: left < right,
                "sle": lambda left, right: left <= right,
                "sgt": lambda left, right: left > right,
                "sge": lambda left, right: left >= right,
                "ult": lambda left, right: left
                < right,  # unsigned - same for concrete ints
                "ule": lambda left, right: left <= right,
                "ugt": lambda left, right: left > right,
                "uge": lambda left, right: left >= right,
            }

            predicate_func = predicate_map.get(op.pred)
            if predicate_func:
                return predicate_func(lhs_concrete, rhs_concrete)

        return None


class UnaryOperationHandler(OperationHandler):
    """Handler for unary operations."""

    def __init__(self, operator: Optional[Callable[[z3.ExprRef], z3.ExprRef]] = None):
        self.operator = operator

    def execute_symbolic(
        self,
        op: UnaryOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute unary operation symbolically."""
        if not isinstance(op, UnaryOperation):
            raise TypeError(f"Expected UnaryOperation, got {type(op)}")

        if self.operator is None:
            raise NotImplementedError(
                f"UnaryOperationHandler.operator not set for {op.full_name}"
            )

        operand_expr = state.get_expr(op.operand)
        if operand_expr is None:
            raise ValueError(f"Cannot get expression for operand: {op.operand}")

        assert self.operator is not None  # checked above
        result_expr = self.operator(operand_expr)
        state.set_value(op.dest, result_expr, op.result_type or "i32")

    def _try_concrete_evaluation(
        self, op: UnaryOperation, state: SymbolicState, func: MLIRFunction
    ) -> Any:
        """Try concrete evaluation of unary operation."""
        operand_concrete = state.get_concrete_value(op.operand)
        if operand_concrete is not None:
            # We need to know the operator - subclasses should override
            return None
        return None


class DialectRegistry:
    """Registry for dialect operation handlers."""

    def __init__(self):
        self.handlers: Dict[str, OperationHandler] = {}

    def register(self, op_name: str, handler: OperationHandler) -> None:
        """Register handler for operation name (dialect.op)."""
        self.handlers[op_name] = handler

    def get_handler(self, op_name: str) -> Optional[OperationHandler]:
        """Get handler for operation name."""
        return self.handlers.get(op_name)

    def execute(
        self,
        op: Operation,
        state: SymbolicState,
        func: MLIRFunction,
        mode: str = "symbolic",
    ) -> None:
        """Execute operation using registered handler.

        Args:
            op: Operation to execute
            state: Current symbolic state
            func: Current MLIR function
            mode: "symbolic" or "concolic"
        """
        handler = self.get_handler(op.full_name)
        if handler is None:
            raise NotImplementedError(f"No handler registered for {op.full_name}")

        if mode == "symbolic":
            handler.execute_symbolic(op, state, func)
        elif mode == "concolic":
            handler.execute_concolic(op, state, func)
        else:
            raise ValueError(f"Unknown execution mode: {mode}")
