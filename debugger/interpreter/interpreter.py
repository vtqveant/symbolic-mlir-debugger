#!/usr/bin/env python3
"""
Symbolic and concolic interpreters for MLIR programs.
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple, cast
import z3

logger = logging.getLogger(__name__)

from .models import MLIRFunction, SymbolicState
from .dialects import get_handler
from .control_flow import ControlFlowExecutor
from .state_manager import StateManager
from .operations import (
    Operation,
    ConditionalBranchOperation,
    UnconditionalBranchOperation,
)


class SymbolicInterpreter:
    """Symbolic interpreter for MLIR functions."""

    def __init__(self):
        self.solver = z3.Solver()
        self.cf_executor = ControlFlowExecutor()
        self.state_manager = StateManager()

    def _convert_to_operation(self, op: Any) -> Operation:
        """Convert op (dict or Operation) to Operation object.

        For backward compatibility with dict-based operations.
        """
        if isinstance(op, Operation):
            return op
        elif isinstance(op, dict):
            # Convert legacy dict representation to Operation
            op_type = op.get("op", "")
            if "." in op_type:
                dialect, name = op_type.split(".", 1)
            else:
                dialect = "unknown"
                name = op_type
            line = op.get("line", 0)
            dest = op.get("dest")
            result_type = op.get("result_type")
            attributes = op.get("attributes", {})
            # Handle special operation types
            if op_type == "cf.cond_br":
                return ConditionalBranchOperation(
                    dialect=dialect,
                    name=name,
                    line=line,
                    dest=dest,
                    result_type=result_type,
                    attributes=attributes,
                    cond=op.get("cond", ""),
                    true_block=op.get("true_block", ""),
                    false_block=op.get("false_block", ""),
                )
            elif op_type == "cf.br":
                return UnconditionalBranchOperation(
                    dialect=dialect,
                    name=name,
                    line=line,
                    dest=dest,
                    result_type=result_type,
                    attributes=attributes,
                    target_block=op.get("target_block", ""),
                    args=op.get("args", []),
                )
            else:
                return Operation(
                    dialect=dialect,
                    name=name,
                    line=line,
                    dest=dest,
                    result_type=result_type,
                    attributes=attributes,
                )
        else:
            raise TypeError(f"Unsupported operation type: {type(op)}")

    def _try_execute_with_registry(
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> bool:
        """Try to execute operation using dialect registry.

        Returns True if operation was handled by registry, False otherwise.
        """
        # Operations that should be handled by legacy elif branches
        # (e.g., control flow that needs state forking)
        legacy_ops = {"cf.cond_br", "cf.br"}

        # Convert to Operation object (handles both dict and Operation)
        op_obj = self._convert_to_operation(op)
        op_type = f"{op_obj.dialect}.{op_obj.name}"

        if op_type in legacy_ops:
            return False

        try:
            # Try to get handler
            handler = get_handler(op_obj.full_name)
            if handler:
                logger.debug(
                    "Registry handler found for %s, handler=%s",
                    op_obj.full_name,
                    handler.__class__.__name__,
                )
                handler.execute_symbolic(op_obj, state, func, self)
                logger.debug("Handler executed successfully for %s", op_obj.full_name)
                return True
            else:
                logger.debug("No handler found for %s", op_obj.full_name)
                pass
        except Exception:
            # Registry execution failed, fall back to legacy handler
            # print(f"Registry execution failed for {op_type}: {e}")  # Debug
            pass
        # Operation not handled by registry
        return False

    def _get_operand_expr(self, operand: str, state: SymbolicState) -> Any:
        """Get Z3 expression for an operand (SSA value or constant)."""
        # Strip leading '%' if present
        if operand.startswith("%"):
            operand = operand[1:]

        # Check if it's an integer constant
        try:
            return z3.IntVal(int(operand))
        except ValueError:
            pass

        # Look up as SSA value
        mlir_value = state.get_value(operand)
        if mlir_value and mlir_value.expr is not None:
            return mlir_value.expr

        # Not found, create fresh symbolic variable
        expr = z3.FreshConst(z3.IntSort(), f"unknown_{operand}")
        state.set_value(operand, expr, "unknown")
        return expr

    def _try_get_concrete_value(self, expr: Any, state: SymbolicState) -> Optional[Any]:
        """Try to extract concrete value from Z3 expression."""
        if isinstance(expr, z3.IntNumRef):
            return expr.as_long()
        elif isinstance(expr, z3.BoolRef):
            # Check if it's a constant True/False
            try:
                if expr.decl().kind() == z3.Z3_OP_TRUE:
                    return True
                elif expr.decl().kind() == z3.Z3_OP_FALSE:
                    return False
            except:
                pass

        # Try to get variable name from expression (if it's a Z3 variable)
        try:
            if isinstance(expr, z3.ExprRef) and expr.decl().arity() == 0:
                var_name = expr.decl().name()
                # Look up concrete value in state
                concrete = state.get_concrete_value(var_name)
                if concrete is not None:
                    return concrete
        except:
            pass

        # Could also check solver for satisfiability, but for now return None
        return None

    def _get_concrete_operand(
        self, operand: str, state: SymbolicState
    ) -> Optional[Any]:
        """Get concrete value for an operand if available."""
        # First try to get as integer constant
        try:
            return int(operand)
        except ValueError:
            pass

        # Get the Z3 expression
        expr = self._get_operand_expr(operand, state)
        # Try to get concrete value from expression
        return self._try_get_concrete_value(expr, state)

    def _evaluate_indices(
        self, indices: List[str], state: SymbolicState
    ) -> Optional[Tuple[int, ...]]:
        """Evaluate list of index operands to concrete integer tuple.
        Returns None if any index is symbolic (not concrete)."""
        concrete_indices = []
        for idx in indices:
            concrete_idx = self._get_concrete_operand(idx, state)
            if concrete_idx is None:
                return None
            concrete_indices.append(concrete_idx)
        return tuple(concrete_indices)

    def _execute_operation(
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> None:
        """Execute a single operation using dialect registry or fallback."""
        # Try to execute using dialect registry first
        if self._try_execute_with_registry(op, state, func):
            return

        # Convert to Operation object (handles both dict and Operation)
        op_obj = self._convert_to_operation(op)
        op_type = f"{op_obj.dialect}.{op_obj.name}"

        if op_type == "cf.cond_br":
            from .operations import ConditionalBranchOperation

            branch_op = cast(ConditionalBranchOperation, op_obj)
            self.cf_executor.execute_conditional_branch(branch_op, state, func, self)

        elif op_type == "cf.br":
            from .operations import UnconditionalBranchOperation

            branch_op = cast(UnconditionalBranchOperation, op_obj)
            self.cf_executor.execute_unconditional_branch(branch_op, state, func, self)

        elif op_type == "func.return":
            # Function return
            from .operations import ReturnOperation

            return_op = cast(ReturnOperation, op_obj)
            if return_op.value is not None:
                ret_expr = self._get_operand_expr(return_op.value, state)
                result_type = "unknown"
                if return_op.result_type:
                    result_type = return_op.result_type
                state.set_value("return", ret_expr, result_type)
            state.pc = None

        else:
            # Unknown operation - treat as no-op
            print(f"Warning: Unknown operation type {op_type}, skipping")
            # Still need to produce a result if there's a dest
            if hasattr(op_obj, "dest") and op_obj.dest is not None:
                # Create fresh symbolic value
                expr = z3.FreshConst(z3.IntSort(), f"unknown_{op_type}")
                state.set_value(
                    op_obj.dest, expr, getattr(op_obj, "result_type", "unknown")
                )

    def execute_function(self, func: MLIRFunction) -> List[SymbolicState]:
        """Symbolically execute an MLIR function."""
        # Initialize state with symbolic arguments
        initial_state = SymbolicState(pc=list(func.basic_blocks.keys())[0])

        # Create symbolic variables for function arguments
        for arg_name, arg_type in func.args:
            # Strip '%' prefix from argument name
            clean_arg_name = arg_name[1:] if arg_name.startswith("%") else arg_name
            sym_var = z3.Int(clean_arg_name)
            initial_state.set_value(clean_arg_name, sym_var, arg_type)

        # Reset state manager and add initial state
        self.state_manager.clear()
        self.state_manager.add_state(initial_state)

        loop_counter = 0
        state_block_visits = {}  # (id(state), pc) -> count

        while self.state_manager.has_states():
            loop_counter += 1
            if loop_counter > 10000:
                print(
                    f"Warning: Infinite loop detected, breaking after {loop_counter} iterations"
                )
                print(f"Remaining states: {self.state_manager.get_worklist_size()}")
                if self.state_manager.has_states():
                    # Get a state from worklist without removing it
                    states = self.state_manager.worklist
                    if states:
                        state = states[-1]
                        print(f"Current state pc: {state.pc}")
                        print(f"Basic block keys: {list(func.basic_blocks.keys())}")
                break

            state = self.state_manager.get_next_state()
            if state is None:
                break

            # Infinite loop detection: if state revisits same block too many times
            key = (id(state), state.pc)
            state_block_visits[key] = state_block_visits.get(key, 0) + 1
            if state_block_visits[key] > 5:
                print(f"Warning: Infinite loop in block {state.pc}, terminating state")
                state.pc = None
                self.state_manager.complete_state(state)
                continue

            # Check if state has terminated (pc is None)
            if state.pc is None:
                self.state_manager.complete_state(state)
                continue

            bb = func.get_basic_block(state.pc)
            if not bb:
                self.state_manager.complete_state(state)
                continue

            terminated = False
            for op in bb.operations:
                self._execute_operation(op, state, func)
                if state.pc is None:
                    self.state_manager.complete_state(state)
                    terminated = True
                    break

            if not terminated and state.pc is not None:
                # State needs to continue execution in another block
                # Push it back onto the worklist
                self.state_manager.add_state(state)

        return self.state_manager.get_all_completed()


class ConcolicInterpreter(SymbolicInterpreter):
    """Concolic interpreter that mixes concrete and symbolic execution."""

    def __init__(self):
        super().__init__()
        self.explored_paths = []
        self.input_models = []

    def _try_execute_with_registry(
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> bool:
        """Try to execute operation using dialect registry with concolic support."""
        # Operations that should be handled by legacy elif branches
        # (e.g., control flow that needs state forking)
        legacy_ops = {"cf.cond_br", "cf.br"}

        # Convert to Operation object (handles both dict and Operation)
        op_obj = self._convert_to_operation(op)
        op_type = f"{op_obj.dialect}.{op_obj.name}"

        if op_type in legacy_ops:
            logger.debug("concolic: Skipping registry for legacy op %s", op_type)
            return False

        try:
            # Try to get handler
            handler = get_handler(op_obj.full_name)
            if handler:
                logger.debug(
                    "concolic: Registry handler found for %s, handler=%s",
                    op_obj.full_name,
                    handler.__class__.__name__,
                )
                handler.execute_concolic(op_obj, state, func, self)
                logger.debug(
                    "concolic: Handler executed successfully for %s", op_obj.full_name
                )
                return True
            else:
                logger.debug("concolic: No handler found for %s", op_obj.full_name)
        except Exception as e:
            # Registry execution failed, fall back to legacy handler
            print(f"Registry execution failed for {op_type}: {e}")
            import traceback

            traceback.print_exc()
            pass

        return False

    def _execute_operation(
        self, op: Dict[str, Any], state: SymbolicState, func: MLIRFunction
    ) -> None:
        """Execute operation with concolic support."""
        self._execute_operation_concolic(op, state, func)

    def explore_paths(
        self, func: MLIRFunction, max_paths: int = 10
    ) -> List[Dict[str, Any]]:
        """Explore multiple execution paths using concolic execution."""
        # Start with random concrete inputs

        # Generate initial random inputs for function arguments
        initial_inputs = {}
        for arg_name, arg_type in func.args:
            clean_name = arg_name[1:] if arg_name.startswith("%") else arg_name
            # For i32, generate random value in range [-10, 10]
            initial_inputs[clean_name] = random.randint(-10, 10)

        paths = []
        queue = [initial_inputs]
        explored_conditions = set()
        loop_counter = 0

        while queue and len(paths) < max_paths:
            loop_counter += 1
            if loop_counter > 100:
                print(
                    f"Warning: explore_paths loop exceeded safety limit after {loop_counter} iterations"
                )
                break
            concrete_inputs = queue.pop(0)

            # Run symbolic execution with concrete inputs
            states = self.execute_function_with_concrete(func, concrete_inputs)

            # Get the completed state (there should be exactly one for deterministic execution)
            completed_states = [s for s in states if s.get_value("return") is not None]
            logger.debug(
                "explore_paths: states count=%s, completed_states count=%s",
                len(states),
                len(completed_states),
            )
            if not completed_states:
                logger.debug("explore_paths: no completed states, skipping")
                continue

            state = completed_states[0]
            path_condition = state.path_condition

            # Record this path
            paths.append(
                {
                    "inputs": concrete_inputs,
                    "path_condition": path_condition,
                    "return_value": (
                        ret_val.expr
                        if (ret_val := state.get_value("return")) is not None
                        and ret_val.expr is not None
                        else None
                    ),
                }
            )

            # Try to negate each branch condition to find new paths
            for i, condition in enumerate(path_condition):
                # Create new path condition with this condition negated
                new_condition = []
                for j, cond in enumerate(path_condition):
                    if j < i:
                        new_condition.append(cond)  # Keep previous conditions
                    elif j == i:
                        new_condition.append(z3.Not(cond))  # Negate this condition
                    else:
                        break  # Don't add later conditions (different path)

                # Check if we've already explored this condition combination
                cond_key = tuple(str(c) for c in new_condition)
                if cond_key in explored_conditions:
                    continue

                explored_conditions.add(cond_key)

                # Use Z3 to find inputs satisfying new condition
                solver = z3.Solver()
                for cond in new_condition:
                    solver.add(cond)

                if solver.check() == z3.sat:
                    model = solver.model()
                    new_inputs = {}
                    for arg_name, _ in func.args:
                        clean_name = (
                            arg_name[1:] if arg_name.startswith("%") else arg_name
                        )
                        # Get value from model, fallback to random
                        z3_var = z3.Int(clean_name)
                        if model[z3_var] is not None and isinstance(
                            model[z3_var], z3.IntNumRef
                        ):
                            new_inputs[clean_name] = model[z3_var].as_long()  # type: ignore
                        else:
                            new_inputs[clean_name] = random.randint(-10, 10)
                    queue.append(new_inputs)

        return paths

    def execute_function_with_concrete(
        self, func: MLIRFunction, concrete_inputs: Dict[str, int]
    ) -> List[SymbolicState]:
        """Execute function with concrete input values."""
        # Initialize state with symbolic arguments but also set concrete values
        initial_state = SymbolicState(pc=list(func.basic_blocks.keys())[0])

        # Create symbolic variables and set concrete values
        for arg_name, arg_type in func.args:
            clean_name = arg_name[1:] if arg_name.startswith("%") else arg_name
            sym_var = z3.Int(clean_name)
            initial_state.set_value(clean_name, sym_var, arg_type)

            if clean_name in concrete_inputs:
                initial_state.set_concrete_value(
                    clean_name, concrete_inputs[clean_name]
                )

        # Reset state manager and add initial state
        self.state_manager.clear()
        self.state_manager.add_state(initial_state)
        loop_counter = 0
        # Track visits per state per block to detect infinite loops
        state_block_visits = {}  # (id(state), pc) -> count

        while self.state_manager.has_states():
            loop_counter += 1
            if loop_counter > 10000:
                print(
                    f"Warning: Infinite loop detected in concolic execution, breaking after {loop_counter} iterations"
                )
                break

            state = self.state_manager.get_next_state()
            if state is None:
                break

            if state.pc is None:
                self.state_manager.complete_state(state)
                continue

            # Infinite loop detection: if state revisits same block too many times
            key = (id(state), state.pc)
            state_block_visits[key] = state_block_visits.get(key, 0) + 1
            if state_block_visits[key] > 5:
                print(f"Warning: Infinite loop in block {state.pc}, terminating state")
                state.pc = None
                self.state_manager.complete_state(state)
                continue

            bb = func.get_basic_block(state.pc)
            if not bb:
                self.state_manager.complete_state(state)
                continue

            terminated = False
            for op in bb.operations:
                self._execute_operation_concolic(op, state, func)
                if state.pc is None:
                    self.state_manager.complete_state(state)
                    terminated = True
                    break

            if not terminated and state.pc is not None:
                # State needs to continue execution in another block
                # Push it back onto the worklist
                self.state_manager.add_state(state)

        return self.state_manager.get_all_completed()

    def _execute_operation_concolic(
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> None:
        """Execute operation with concolic support (use concrete values when available)."""
        # Try to execute using dialect registry first
        if self._try_execute_with_registry(op, state, func):
            return

        # Convert to Operation object (handles both dict and Operation)
        op_obj = self._convert_to_operation(op)
        super()._execute_operation(op_obj, state, func)

    def _get_concrete_operand(
        self, operand: str, state: SymbolicState
    ) -> Optional[Any]:
        """Get concrete value for an operand if available."""
        # Debug: print what we're looking for
        # print(f"DEBUG _get_concrete_operand: operand='{operand}'")

        # Check if it's an SSA value
        if operand.startswith("%"):
            value_name = operand[1:]
            concrete = state.get_concrete_value(value_name)
            if concrete is not None:
                # print(f"DEBUG: Found concrete value for {value_name}: {concrete} (type: {type(concrete)})")
                return concrete

            # Check if we have a symbolic value that's actually a constant
            mlir_value = state.get_value(value_name)
            if mlir_value and mlir_value.expr is not None:
                # Check if it's a constant integer
                if isinstance(mlir_value.expr, z3.IntNumRef):
                    # print(f"DEBUG: Found IntNumRef for {value_name}: {mlir_value.expr.as_long()}")
                    return mlir_value.expr.as_long()
                # Check if it's a constant boolean
                elif isinstance(mlir_value.expr, z3.BoolRef):
                    # Try to get concrete boolean value
                    try:
                        # For BoolVal(True/False), we can check
                        if mlir_value.expr.decl().kind() == z3.Z3_OP_TRUE:
                            return True
                        elif mlir_value.expr.decl().kind() == z3.Z3_OP_FALSE:
                            return False
                    except:
                        pass

        # Check if it's an integer constant
        try:
            val = int(operand)
            # print(f"DEBUG: operand '{operand}' is integer constant: {val}")
            return val
        except ValueError:
            # Check if it's a variable name without '%'
            concrete = state.get_concrete_value(operand)
            if concrete is not None:
                # print(f"DEBUG: Found concrete value for {operand}: {concrete}")
                return concrete

            mlir_value = state.get_value(operand)
            if mlir_value and mlir_value.expr is not None:
                if isinstance(mlir_value.expr, z3.IntNumRef):
                    return mlir_value.expr.as_long()
                elif isinstance(mlir_value.expr, z3.BoolRef):
                    try:
                        if mlir_value.expr.decl().kind() == z3.Z3_OP_TRUE:
                            return True
                        elif mlir_value.expr.decl().kind() == z3.Z3_OP_FALSE:
                            return False
                    except:
                        pass

        # print(f"DEBUG: No concrete value found for operand '{operand}'")
        return None
