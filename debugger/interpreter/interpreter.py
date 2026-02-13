#!/usr/bin/env python3
"""
Symbolic and concolic interpreters for MLIR programs.
"""

import random
from typing import Dict, List, Optional, Any, Tuple
import z3

from .models import MLIRFunction, SymbolicState
from .operations import operation_from_dict
from .dialects import get_handler
from .control_flow import ControlFlowExecutor
from .state_manager import StateManager


class SymbolicInterpreter:
    """Symbolic interpreter for MLIR functions."""

    def __init__(self):
        self.solver = z3.Solver()
        self.cf_executor = ControlFlowExecutor()
        self.state_manager = StateManager()

    def _try_execute_with_registry(
        self, op: Any, state: SymbolicState, func: MLIRFunction
    ) -> bool:
        """Try to execute operation using dialect registry.

        Returns True if operation was handled by registry, False otherwise.
        """
        # Operations that should be handled by legacy elif branches
        # (e.g., control flow that needs state forking)
        legacy_ops = {"cf.cond_br", "cf.br"}

        # Determine operation type (full name) for both dict and Operation objects
        if isinstance(op, dict):
            op_type = op.get("op")
            # Convert dict to Operation if needed
            op_obj = operation_from_dict(op)
        else:
            # op is already an Operation object
            op_obj = op
            op_type = f"{op_obj.dialect}.{op_obj.name}"

        if op_type in legacy_ops:
            print(f"DEBUG: Skipping registry for legacy op {op_type}")
            return False

        try:
            # Try to get handler
            handler = get_handler(op_obj.full_name)
            if handler:
                print(
                    f"DEBUG: Registry handler found for {op_obj.full_name}, handler={handler.__class__.__name__}"
                )
                handler.execute_symbolic(op_obj, state, func, self)
                print(f"DEBUG: Handler executed successfully for {op_obj.full_name}")
                return True
            else:
                print(f"DEBUG: No handler found for {op_obj.full_name}")
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

        # Convert dict to Operation if needed
        if isinstance(op, dict):
            op_obj = operation_from_dict(op)
        else:
            op_obj = op

        op_type = f"{op_obj.dialect}.{op_obj.name}"

        if op_type == "cf.cond_br":
            self.cf_executor.execute_conditional_branch(op_obj, state, func, self)

        elif op_type == "cf.br":
            self.cf_executor.execute_unconditional_branch(op_obj, state, func, self)

        elif op_type == "builtin.return":
            # Function return
            if hasattr(op_obj, "value") and op_obj.value is not None:
                ret_expr = self._get_operand_expr(op_obj.value, state)
                state.set_value(
                    "return",
                    ret_expr,
                    op_obj.result_type if hasattr(op_obj, "result_type") else None,
                )
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

        # Determine operation type (full name) for both dict and Operation objects
        if isinstance(op, dict):
            op_type = op.get("op")
            # Convert dict to Operation if needed
            op_obj = operation_from_dict(op)
        else:
            # op is already an Operation object
            op_obj = op
            op_type = f"{op_obj.dialect}.{op_obj.name}"

        if op_type in legacy_ops:
            print(f"DEBUG concolic: Skipping registry for legacy op {op_type}")
            return False

        try:
            # Try to get handler
            handler = get_handler(op_obj.full_name)
            if handler:
                print(
                    f"DEBUG concolic: Registry handler found for {op_obj.full_name}, handler={handler.__class__.__name__}"
                )
                handler.execute_concolic(op_obj, state, func, self)
                print(
                    f"DEBUG concolic: Handler executed successfully for {op_obj.full_name}"
                )
                return True
            else:
                print(f"DEBUG concolic: No handler found for {op_obj.full_name}")
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
            print(
                f"DEBUG explore_paths: states count={len(states)}, completed_states count={len(completed_states)}"
            )
            if not completed_states:
                print("DEBUG explore_paths: no completed states, skipping")
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

        # Convert dict to Operation if needed
        if isinstance(op, dict):
            op_obj = operation_from_dict(op)
        else:
            op_obj = op

        super()._execute_operation(op_obj, state, func)

    def _try_concrete_evaluation(
        self, op: Dict[str, Any], state: SymbolicState
    ) -> Optional[Any]:
        """Try to evaluate operation concretely."""
        op_type = op.get("op")

        if op_type == "arith.constant":
            return int(op["value"])

        elif op_type == "arith.addi":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs + rhs

        elif op_type == "arith.subi":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs - rhs

        elif op_type == "arith.muli":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs * rhs

        elif op_type == "arith.divi":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None and rhs != 0:
                return int(lhs / rhs)  # truncate towards zero

        elif op_type == "arith.cmpi":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            pred = op["pred"]

            if lhs is not None and rhs is not None:
                if pred == "slt":
                    return lhs < rhs
                elif pred == "sle":
                    return lhs <= rhs
                elif pred == "sgt":
                    return lhs > rhs
                elif pred == "sge":
                    return lhs >= rhs
                elif pred == "eq":
                    return lhs == rhs
                elif pred == "ne":
                    return lhs != rhs

        # Shape operations
        elif op_type == "shape.const_size":
            # Try to get value from op["value"] or from attributes
            if "value" in op:
                return int(op["value"])
            elif "attributes" in op:
                # Use parsed attribute value
                attr_dict = op["attributes"]
                return attr_dict.get("value", 0)
            return 0  # Default value

        elif op_type == "shape.add":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs + rhs

        elif op_type == "shape.div":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None and rhs != 0:
                return int(lhs / rhs)  # truncate towards zero

        elif op_type == "shape.const_shape":
            # shape.const_shape creates a shape tensor
            # For concrete evaluation, we need to parse the shape attribute
            # Format: shape = dense<[42, 100, 200]> : tensor<3xindex>
            # For now, return a placeholder list
            if "shape" in op:
                # shape is a list of dimension values (strings)
                # Try to evaluate each dimension concretely
                shape_dims = []
                for dim in op["shape"]:
                    concrete_dim = self._get_concrete_operand(dim, state)
                    if concrete_dim is not None:
                        shape_dims.append(concrete_dim)
                    else:
                        # If any dimension is symbolic, can't evaluate concretely
                        return None
                return tuple(shape_dims)  # Return as tuple for hashability
            return None

        elif op_type == "shape.get_extent":
            # shape.get_extent extracts dimension from shape
            # lhs = shape, rhs = index
            shape_val = self._get_concrete_operand(op["lhs"], state)
            index_val = self._get_concrete_operand(op["rhs"], state)
            if shape_val is not None and index_val is not None:
                # shape_val should be a tuple/list from shape.const_shape
                if isinstance(shape_val, tuple) and 0 <= index_val < len(shape_val):
                    return shape_val[index_val]
            return None

        # Vector operations
        elif op_type == "vector.broadcast":
            # operand may be in "value" (generic parser) or "source" (specialized)
            source_key = "value" if "value" in op else "source"
            source_val = self._get_concrete_operand(op[source_key], state)
            if source_val is not None:
                return source_val  # For now, return scalar value

        elif op_type == "vector.bitcast":
            # operand may be in "value" (generic parser) or "source" (specialized)
            source_key = "value" if "value" in op else "source"
            source_val = self._get_concrete_operand(op[source_key], state)
            if source_val is not None:
                return source_val  # For now, return scalar value

        elif op_type == "vector.fma":
            # operands may be in lhs/rhs/acc (specialized) or "operands" list (generic parser)
            lhs_val = None
            rhs_val = None
            acc_val = None

            if "lhs" in op:
                lhs_val = self._get_concrete_operand(op["lhs"], state)
                rhs_val = self._get_concrete_operand(op["rhs"], state)
                acc_val = self._get_concrete_operand(op["acc"], state)
            else:
                operands = op.get("operands", [])
                if len(operands) >= 3:
                    lhs_val = self._get_concrete_operand(operands[0], state)
                    rhs_val = self._get_concrete_operand(operands[1], state)
                    acc_val = self._get_concrete_operand(operands[2], state)

            if lhs_val is not None and rhs_val is not None and acc_val is not None:
                return lhs_val * rhs_val + acc_val  # FMA: lhs * rhs + acc

        # Bufferization operations
        elif op_type == "bufferization.alloc_tensor":
            # alloc_tensor creates a new tensor - can't evaluate concretely
            return None

        elif op_type == "bufferization.to_buffer":
            # Convert tensor to buffer - return tensor value if concrete
            tensor_val = self._get_concrete_operand(op["tensor"], state)
            if tensor_val is not None:
                return tensor_val

        elif op_type == "bufferization.to_tensor":
            # Convert buffer to tensor - return buffer value if concrete
            buffer_val = self._get_concrete_operand(op["buffer"], state)
            if buffer_val is not None:
                return buffer_val

        elif op_type == "bufferization.clone":
            # Clone creates a copy - return source value if concrete
            src_val = self._get_concrete_operand(op["src"], state)
            if src_val is not None:
                return src_val

        # EmitC operations
        elif op_type == "emitc.constant":
            # value may be in "value" key or in attributes
            value = None
            if "value" in op:
                value = op["value"]
            elif "attributes" in op:
                # Use parsed attribute value
                attr = op["attributes"]
                value = attr.get("value")
            # Parse constant value - could be integer or other types
            if value is not None:
                try:
                    return int(value)
                except ValueError:
                    return None
            return None

        elif op_type == "emitc.add":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs + rhs

        elif op_type == "emitc.cmp":
            # predicate may be in "predicate" key or in attributes
            predicate = None
            if "predicate" in op:
                predicate = op["predicate"]
            elif "attributes" in op:
                attr = op["attributes"]
                # Use parsed attribute value
                predicate = attr.get("predicate")
            if predicate is None:
                return None
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                # EmitC predicates can be strings like "eq", "ne", "lt", "le", "gt", "ge"
                # or integer codes: 0=eq, 1=ne, 2=lt, 3=le, 4=gt, 5=ge, 6=three_way
                pred_str = str(predicate)
                if pred_str == "slt" or pred_str == "2":  # signed less than (integer 2)
                    return lhs < rhs
                elif pred_str == "sle" or pred_str == "3":  # signed less than or equal
                    return lhs <= rhs
                elif pred_str == "sgt" or pred_str == "4":  # signed greater than
                    return lhs > rhs
                elif (
                    pred_str == "sge" or pred_str == "5"
                ):  # signed greater than or equal
                    return lhs >= rhs
                elif pred_str == "eq" or pred_str == "0":  # equal
                    return lhs == rhs
                elif pred_str == "ne" or pred_str == "1":  # not equal
                    return lhs != rhs
                elif pred_str == "lt":  # less than (string)
                    return lhs < rhs
                elif pred_str == "le":  # less than or equal
                    return lhs <= rhs
                elif pred_str == "gt":  # greater than
                    return lhs > rhs
                elif pred_str == "ge":  # greater than or equal
                    return lhs >= rhs

        elif op_type == "emitc.conditional":
            # Handle both named keys and operands list
            if "condition" in op and "true_value" in op and "false_value" in op:
                cond_val = self._get_concrete_operand(op["condition"], state)
                true_val = self._get_concrete_operand(op["true_value"], state)
                false_val = self._get_concrete_operand(op["false_value"], state)
            elif "operands" in op and len(op["operands"]) >= 3:
                cond_val = self._get_concrete_operand(op["operands"][0], state)
                true_val = self._get_concrete_operand(op["operands"][1], state)
                false_val = self._get_concrete_operand(op["operands"][2], state)
            else:
                return None
            if cond_val is not None and true_val is not None and false_val is not None:
                return true_val if cond_val else false_val

        elif op_type == "emitc.cast":
            # Handle both dialect-specific "operand" and generic "value"
            operand_key = "operand" if "operand" in op else "value"
            operand_val = self._get_concrete_operand(op[operand_key], state)
            if operand_val is not None:
                return operand_val  # Cast doesn't change value for concrete integers

        elif op_type == "emitc.assign":
            rhs_val = self._get_concrete_operand(op["rhs"], state)
            if rhs_val is not None:
                return rhs_val

        elif op_type == "emitc.bitwise_and":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs & rhs

        elif op_type == "emitc.bitwise_or":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs | rhs

        elif op_type == "emitc.bitwise_xor":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs ^ rhs

        elif op_type == "emitc.bitwise_left_shift":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs << rhs

        elif op_type == "emitc.bitwise_right_shift":
            lhs = self._get_concrete_operand(op["lhs"], state)
            rhs = self._get_concrete_operand(op["rhs"], state)
            if lhs is not None and rhs is not None:
                return lhs >> rhs

        elif op_type == "emitc.bitwise_not":
            operand_val = self._get_concrete_operand(op["operand"], state)
            if operand_val is not None:
                return ~operand_val

        return None

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
