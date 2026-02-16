#!/usr/bin/env python3
"""
Control flow execution utilities.

Provides ControlFlowExecutor for handling branch operations and state transitions.
"""

import z3
from .models import SymbolicState, MLIRFunction, MLIRValue
from .operations import ConditionalBranchOperation, UnconditionalBranchOperation


class ControlFlowExecutor:
    """Executes control flow operations using CFG edges."""

    def __init__(self):
        pass

    def _ensure_caret_prefix(self, block_label: str) -> str:
        """Ensure block label has ^ prefix for consistency with CFG."""
        if not block_label:
            return block_label
        if block_label.startswith("^"):
            return block_label
        return "^" + block_label

    def execute_conditional_branch(
        self,
        op: ConditionalBranchOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute conditional branch symbolically."""
        if not isinstance(op, ConditionalBranchOperation):
            raise TypeError(f"Expected ConditionalBranchOperation, got {type(op)}")

        # Get condition expression
        cond_expr = state.get_expr(op.cond)
        if cond_expr is None:
            raise ValueError(f"Cannot get expression for condition: {op.cond}")

        # Check if condition is concrete
        cond_concrete = state.get_concrete_value(op.cond)
        if cond_concrete is not None:
            # Concrete condition: take the appropriate branch and record path condition
            if cond_concrete:
                # True branch
                state.add_path_condition(cond_expr)
                state.pc = self._ensure_caret_prefix(op.true_block)
            else:
                # False branch
                state.add_path_condition(z3.Not(cond_expr))
                state.pc = self._ensure_caret_prefix(op.false_block)
            # Current state continues (no forking)
            return

        # Symbolic condition: fork both branches
        true_state = state.fork()
        false_state = state.fork()

        # Add path conditions
        true_state.add_path_condition(cond_expr)
        false_state.add_path_condition(z3.Not(cond_expr))

        # Set program counters
        true_state.pc = self._ensure_caret_prefix(op.true_block)
        false_state.pc = self._ensure_caret_prefix(op.false_block)

        # Add forked states to interpreter's worklist via state manager
        if interpreter is not None:
            interpreter.state_manager.add_state(true_state)
            interpreter.state_manager.add_state(false_state)

        # Terminate current state
        state.pc = None

    def execute_conditional_branch_concolic(
        self,
        op: ConditionalBranchOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute conditional branch concolically."""
        if not isinstance(op, ConditionalBranchOperation):
            raise TypeError(f"Expected ConditionalBranchOperation, got {type(op)}")

        # Get condition expression
        cond_expr = state.get_expr(op.cond)
        if cond_expr is None:
            raise ValueError(f"Cannot get expression for condition: {op.cond}")

        # Check if condition is concrete
        cond_concrete = state.get_concrete_value(op.cond)
        if cond_concrete is not None:
            # Concrete condition: take the appropriate branch and record path condition
            if cond_concrete:
                # True branch
                state.add_path_condition(cond_expr)
                state.pc = self._ensure_caret_prefix(op.true_block)
            else:
                # False branch
                state.add_path_condition(z3.Not(cond_expr))
                state.pc = self._ensure_caret_prefix(op.false_block)
            # Current state continues (no forking)
            return

        # Symbolic condition: fork both branches
        true_state = state.fork()
        false_state = state.fork()

        # Add path conditions
        true_state.add_path_condition(cond_expr)
        false_state.add_path_condition(z3.Not(cond_expr))

        # Set program counters
        true_state.pc = self._ensure_caret_prefix(op.true_block)
        false_state.pc = self._ensure_caret_prefix(op.false_block)

        # Add forked states to interpreter's worklist via state manager
        if interpreter is not None:
            interpreter.state_manager.add_state(true_state)
            interpreter.state_manager.add_state(false_state)

        # Terminate current state
        state.pc = None

    def execute_unconditional_branch(
        self,
        op: UnconditionalBranchOperation,
        state: SymbolicState,
        func: MLIRFunction,
        interpreter=None,
    ) -> None:
        """Execute unconditional branch symbolically."""
        if not isinstance(op, UnconditionalBranchOperation):
            raise TypeError(f"Expected UnconditionalBranchOperation, got {type(op)}")

        # Use target block as-is (should have ^ prefix)
        target_label = self._ensure_caret_prefix(op.target_block)

        # Get target block
        target_block = func.get_basic_block(target_label)
        if target_block is None:
            raise ValueError(f"Target block {target_label} not found in function")

        # Check if branch has arguments
        if hasattr(op, "args") and op.args:
            # Map branch arguments to block parameters
            if len(op.args) != len(target_block.parameters):
                raise ValueError(
                    f"Branch has {len(op.args)} arguments but target block "
                    f"{op.target_block} has {len(target_block.parameters)} parameters"
                )

            # For each argument, get value and map to parameter
            for (arg_name, arg_type), (param_name, param_type) in zip(
                op.args, target_block.parameters
            ):
                # Types must match in MLIR
                if arg_type != param_type:
                    raise ValueError(
                        f"Type mismatch: argument {arg_name} has type {arg_type}, "
                        f"but parameter {param_name} expects {param_type}"
                    )

                # Get value from current state
                mlir_value = state.values.get(arg_name)
                if mlir_value is None:
                    # Try to get concrete value
                    concrete_val = state.concrete_values.get(arg_name)
                    if concrete_val is not None:
                        # Create MLIRValue with concrete value
                        mlir_value = MLIRValue(name=arg_name, type=arg_type, concrete=concrete_val)
                    else:
                        raise ValueError(f"Cannot find value for argument {arg_name}")

                # Create new MLIRValue for parameter (with same value/expression)
                # Copy the value but with parameter name
                param_value = MLIRValue(name=param_name, expr=mlir_value.expr, type=param_type)
                state.values[param_name] = param_value

                # Also copy concrete value if present
                if arg_name in state.concrete_values:
                    state.concrete_values[param_name] = state.concrete_values[arg_name]

        # Update program counter (use normalized label)
        state.pc = target_label
