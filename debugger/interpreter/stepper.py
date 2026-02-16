#!/usr/bin/env python3
"""
Stepper for pausable execution of MLIR programs.

Supports concrete mode execution (single path) with breakpoints and stepping.
"""

from typing import Dict, List, Optional, Any, cast

import z3
import logging

from .debug_utils import get_variable_summary
from .interpreter import ConcolicInterpreter
from .models import SymbolicState, LoopContext

logger = logging.getLogger(__name__)
from .operations import (
    Operation,
    LoopOperation,
    ConditionalBranchOperation,
    ReturnOperation,
)
from .parser import MLIRParser


class ExecutionStepper:
    """Stepper for pausable execution of MLIR programs.

    Supports concrete mode execution (single path) with breakpoints and stepping.
    """

    def __init__(self, mlir_file: str, concrete_inputs: Optional[Dict[str, int]] = None, symbolic_mode: bool = False):
        """Initialize stepper with MLIR file and concrete inputs."""
        self.mlir_file = mlir_file
        self.concrete_inputs = concrete_inputs or {}
        self.symbolic_mode = symbolic_mode

        # Parse MLIR file
        self.parser = MLIRParser()
        self.functions = self.parser.parse_file(mlir_file)
        if not self.functions:
            raise ValueError(f"No functions found in {mlir_file}")

        # Assume first function for now
        self.func_name = next(iter(self.functions))
        self.func = self.functions[self.func_name]

        # Interpreter for executing operations
        self.interpreter = ConcolicInterpreter()

        # Execution state
        self.current_state = None
        self.current_block_label = None
        self.current_op_index = 0  # Index within current block
        self.breakpoints = set()  # Set of line numbers
        self.paused = True  # Start paused
        # Branch tracking
        self.last_branch_decision = None
        self.branch_history = []  # List of recent branch decisions
        # Loop execution state
        self.loop_stack = []  # Stack of active loops
        self.current_loop = None  # Top of loop stack
        # Symbolic variable tracking
        self.symbolic_variables = {}
        self.symbolic_constraints = []

        # Initialize execution state
        self._initialize_state()

        if symbolic_mode:
            logger.info("Symbolic debugging mode enabled")

    def _initialize_state(self):
        """Initialize the execution state with concrete inputs."""
        # Create initial state with entry block
        initial_state = SymbolicState(pc=list(self.func.basic_blocks.keys())[0])

        # Set symbolic variables and concrete values for function arguments
        for arg_name, arg_type in self.func.args:
            clean_name = arg_name[1:] if arg_name.startswith("%") else arg_name
            sym_var = z3.Int(clean_name)
            initial_state.set_value(clean_name, sym_var, arg_type)

            if clean_name in self.concrete_inputs:
                initial_state.set_concrete_value(clean_name, self.concrete_inputs[clean_name])

        self.current_state = initial_state
        self.current_block_label = initial_state.pc
        self.current_op_index = 0
        self.paused = True
        self.last_branch_decision = None
        self.branch_history = []
        self.loop_stack = []
        self.current_loop = None

    def get_successors(self, block_label: str) -> List[str]:
        """Get successor blocks for given block label."""
        return self.func.cfg.edges.get(block_label, [])

    def get_predecessors(self, block_label: str) -> List[str]:
        """Get predecessor blocks for given block label."""
        return self.func.cfg.predecessors.get(block_label, [])

    def get_cfg_edges(self) -> Dict[str, List[str]]:
        """Get all CFG edges."""
        return self.func.cfg.edges

    def get_current_successors(self) -> List[str]:
        """Get successor blocks for current block."""
        if self.current_block_label is None:
            return []
        return self.get_successors(self.current_block_label)

    def _ensure_cfg_computed(self):
        """Ensure CFG dominators and exits are computed."""
        # Compute exits if not already
        if not self.func.cfg.exits:
            self.func.cfg.compute_exits()
        # Compute dominators if not already
        if not self.func.cfg.dominators:
            self.func.cfg.compute_dominators()

    def _enter_loop(self, op: LoopOperation) -> bool:
        """Enter a loop (scf.for) for stepping.

        Sets up loop state if bounds are concrete.
        Returns True if loop was entered, False if bounds are symbolic
        (loop cannot be stepped through).
        """
        assert self.current_state is not None
        state = cast(SymbolicState, self.current_state)
        # Get concrete bounds
        lb = self.interpreter._get_concrete_operand(op.lb, state) if op.lb else None
        ub = self.interpreter._get_concrete_operand(op.ub, state) if op.ub else None
        step = self.interpreter._get_concrete_operand(op.step, state) if op.step else None

        if lb is None or ub is None or step is None:
            # Symbolic bounds - cannot step through loop
            return False

        # Get induction variable name (strip % if present)
        iv = op.index if op.index else ""
        iv_name = iv[1:] if iv.startswith("%") else iv

        # Get iteration argument if present
        iter_arg = op.iter_arg if op.iter_arg else ""
        iter_arg_name = iter_arg[1:] if iter_arg.startswith("%") else iter_arg
        init = op.init if op.init else ""
        result_type = op.result_type if op.result_type else "i32"

        # Get body operations
        body_ops = op.body
        if not body_ops:
            # Empty loop body
            body_ops = []

        # Create loop context
        loop_context = LoopContext(
            op=op,
            iv_name=iv_name,
            lb=lb,
            ub=ub,
            step=step,
            iter_arg_name=iter_arg_name,
            init=init,
            body_ops=body_ops,
            current_iteration=0,
            iv_value=lb,
            iter_arg_value=self.interpreter._get_concrete_operand(init, state) if init else None,
            body_op_index=-1,  # -1 indicates not yet started iteration
            line=op.line,
        )

        self.loop_stack.append(loop_context)
        self.current_loop = loop_context

        # Set initial induction variable value in state
        state.set_value(iv_name, z3.Int(iv_name), "index")  # placeholder
        state.set_concrete_value(iv_name, lb)

        # Set iteration argument value if present
        if iter_arg_name and init:
            init_val = self.interpreter._get_concrete_operand(init, state)
            if init_val is not None:
                state.set_value(iter_arg_name, z3.Int(iter_arg_name), result_type)
                state.set_concrete_value(iter_arg_name, init_val)

        print(
            f"STEPPER entered loop: {iv_name} = {lb} to {ub} step {step}, {len(body_ops)} body ops"
        )
        return True

    def _exit_loop(self) -> None:
        """Exit current loop (loop completed or skipped)."""
        if not self.loop_stack:
            return
        loop = self.loop_stack.pop()
        self.current_loop = self.loop_stack[-1] if self.loop_stack else None
        print(f"STEPPER exited loop: {loop.iv_name} = {loop.iv_value}")

    def _step_in_loop(self) -> Dict[str, Any]:
        """Execute next step within current loop.

        Returns location after step. If loop completes, exits loop and
        returns location of operation after loop.
        """
        assert self.current_state is not None
        state = cast(SymbolicState, self.current_state)
        if not self.current_loop:
            # Should not happen
            return self.get_current_location()

        loop = self.current_loop

        # If body_op_index is -1, we haven't started iteration yet
        if loop.body_op_index == -1:
            loop.body_op_index = 0

        # Check if loop iteration is complete (iv reached or exceeded ub)
        print(
            f"STEPPER loop check: iv={loop.iv_value}, ub={loop.ub}, step={loop.step}, iter={loop.current_iteration}, body_idx={loop.body_op_index}"
        )
        if (loop.step > 0 and loop.iv_value >= loop.ub) or (
            loop.step < 0 and loop.iv_value <= loop.ub
        ):
            # Loop completed
            # Set loop result value (dest) if any
            dest = loop.op.dest
            if dest and loop.iter_arg_value is not None:
                # Strip leading % if present
                dest_name = dest[1:] if dest.startswith("%") else dest
                # The loop result is the final iteration argument value
                state.set_concrete_value(dest_name, loop.iter_arg_value)
                # Also set symbolic value
                state.set_value(dest_name, z3.Int(dest_name), loop.op.result_type or "i32")

            self._exit_loop()
            # Move past the scf.for operation in parent block
            self.current_op_index += 1
            # Continue with next operation after loop in parent block
            return self.get_current_location()

        # Check if we're at the start of a new iteration
        if loop.body_op_index == 0:
            print(
                f"STEPPER loop iteration {loop.current_iteration}: {loop.iv_name} = {loop.iv_value}"
            )

        # Execute next body operation if any
        if loop.body_op_index < len(loop.body_ops):
            body_op = loop.body_ops[loop.body_op_index]
            # Execute the body operation
            self._execute_single_operation(body_op, state)

            # Check if operation was scf.yield (end of loop body)
            if body_op.dialect == "scf" and body_op.name == "yield":
                # Yield value becomes next iteration argument
                yield_val = self.interpreter._get_concrete_operand(
                    body_op.value if body_op.value else "", state
                )
                if yield_val is not None:
                    loop.iter_arg_value = yield_val
                    if loop.iter_arg_name:
                        state.set_concrete_value(loop.iter_arg_name, yield_val)

                # Move to next iteration
                loop.current_iteration += 1
                loop.iv_value = loop.lb + loop.current_iteration * loop.step
                loop.body_op_index = 0

                # Update induction variable in state
                state.set_concrete_value(loop.iv_name, loop.iv_value)
            else:
                # Not yield, advance to next body operation
                loop.body_op_index += 1
        else:
            # No body operations (empty loop) - advance iteration
            loop.current_iteration += 1
            loop.iv_value = loop.lb + loop.current_iteration * loop.step
            loop.body_op_index = 0
            state.set_concrete_value(loop.iv_name, loop.iv_value)

        return self.get_current_location()

    def get_control_flow_info(self) -> Dict[str, Any]:
        """Get control flow information for current execution state."""
        # Ensure CFG data is computed
        self._ensure_cfg_computed()

        info = {
            "current_block": self.current_block_label,
            "successors": self.get_current_successors(),
            "predecessors": (
                self.get_predecessors(self.current_block_label) if self.current_block_label else []
            ),
            "last_branch": self.last_branch_decision,
            "branch_history": self.branch_history[-10:],  # last 10 branches,
        }
        # Add loop context if inside a loop
        if self.current_loop:
            info["current_loop"] = {
                "iv_name": self.current_loop.iv_name,
                "lb": self.current_loop.lb,
                "ub": self.current_loop.ub,
                "step": self.current_loop.step,
                "current_iteration": self.current_loop.current_iteration,
                "iv_value": self.current_loop.iv_value,
                "iter_arg_name": self.current_loop.iter_arg_name,
                "iter_arg_value": self.current_loop.iter_arg_value,
                "body_op_index": self.current_loop.body_op_index,
                "line": self.current_loop.line,
            }
            info["loop_stack_depth"] = len(self.loop_stack)
        # Add CFG edges for current block
        if self.current_block_label:
            info["cfg_edges"] = self.func.cfg.edges
        return info

    def set_breakpoints(self, lines: List[int]):
        """Set breakpoints at given line numbers."""
        self.breakpoints = set(lines)
        return len(self.breakpoints)

    def get_current_location(self) -> Dict[str, Any]:
        """Get current execution location (file, line, block, operation)."""
        if self.current_block_label is None:
            return {
                "file": self.mlir_file,
                "line": 0,
                "column": 0,
                "block": None,
                "operation": None,
            }

        # Check if we're inside a loop and should show loop body operation
        current_op = None
        current_op_index = self.current_op_index
        current_block = self.current_block_label

        if self.current_loop is not None and 0 <= self.current_loop.body_op_index < len(
            self.current_loop.body_ops
        ):
            # Inside loop with a current body operation
            current_op = self.current_loop.body_ops[self.current_loop.body_op_index]
            current_op_index = self.current_loop.body_op_index
            # Block remains the parent block containing the scf.for
        else:
            # Not in loop or between iterations, use block operation
            block = self.func.get_basic_block(self.current_block_label)
            if not block or self.current_op_index >= len(block.operations):
                return {
                    "file": self.mlir_file,
                    "line": 0,
                    "column": 0,
                    "block": self.current_block_label,
                    "operation": None,
                }
            current_op = block.operations[self.current_op_index]
            current_op_index = self.current_op_index

        line = current_op.line
        file = self.mlir_file
        column = 0

        return {
            "file": file,
            "line": line,
            "column": column,
            "block": current_block,
            "operation": current_op.full_name if current_op else None,
            "operation_index": current_op_index,
        }

    def get_variables(self) -> Dict[str, Any]:
        """Get current variable values (concrete and symbolic)."""
        if not self.current_state:
            return {}
        assert self.current_state is not None

        variables = {}
        # Get all values from state
        for name, mlir_value in self.current_state.values.items():
            var_info = {"name": name, "type": mlir_value.type}

            # Try to get concrete value from state
            concrete = self.current_state.get_concrete_value(name)
            if concrete is not None:
                var_info["concrete_value"] = concrete
            elif mlir_value.expr is not None:
                # Try to extract concrete value from expression
                try:
                    if isinstance(mlir_value.expr, z3.IntNumRef):
                        var_info["concrete_value"] = mlir_value.expr.as_long()
                    elif isinstance(mlir_value.expr, z3.BoolRef):
                        # Check if it's a constant boolean
                        if mlir_value.expr.decl().kind() == z3.Z3_OP_TRUE:
                            var_info["concrete_value"] = True
                        elif mlir_value.expr.decl().kind() == z3.Z3_OP_FALSE:
                            var_info["concrete_value"] = False
                except Exception:
                    pass

            # Add symbolic expression if available
            if mlir_value.expr is not None:
                var_info["symbolic_expr"] = str(mlir_value.expr)

            # Create formatted summary using debug_utils
            summary = get_variable_summary(
                name=name,
                value=mlir_value.expr,
                value_type=mlir_value.type,
                concrete_value=concrete,
            )
            var_info.update(summary)

            variables[name] = var_info

        # Add memory entries from memory model
        memory_entries = self.current_state.memory_model.get_all_memory_entries()
        for memref_name, entries in memory_entries.items():
            if not entries:
                # Still show allocated memrefs
                if memref_name in self.current_state.memory_model.shapes:
                    shape = self.current_state.memory_model.shapes[memref_name]
                    dtype = self.current_state.memory_model.dtypes.get(memref_name, "unknown")
                    region_summary = {
                        "name": f"{memref_name} (memory)",
                        "value": f"shape={shape}, dtype={dtype}",
                        "type": "memory_region",
                        "presentationHint": "data",
                        "_memory_region": True,
                        "_memref_name": memref_name,
                    }
                    variables[f"{memref_name}_memory"] = region_summary
                continue

            # Create a summary for the memory region
            shape = self.current_state.memory_model.shapes.get(memref_name, ())
            dtype = self.current_state.memory_model.dtypes.get(memref_name, "unknown")
            region_summary = {
                "name": f"{memref_name} (memory)",
                "value": f"{len(entries)} entries, shape={shape}, dtype={dtype}",
                "type": "memory_region",
                "presentationHint": "data",
                "_memory_region": True,
                "_memref_name": memref_name,
            }
            variables[f"{memref_name}_memory"] = region_summary

            # Add individual entries (could be many)
            for entry in entries:
                indices = entry["indices"]
                # Skip sentinel for symbolic stores
                if indices == (-1,):
                    continue

                cell_key = f"{memref_name}{''.join(f'[{i}]' for i in indices)}"
                cell_summary = get_variable_summary(
                    name=cell_key,
                    value=entry["symbolic_expr"],
                    value_type=dtype,
                    concrete_value=entry["concrete_value"],
                )
                cell_summary["_memory_cell"] = True
                cell_summary["_memory_indices"] = indices
                variables[cell_key] = cell_summary

        # Add tensor memory entries from tensor memory model
        tensor_entries = self.current_state.tensor_memory_model.get_all_memory_entries()
        for tensor_name, entries in tensor_entries.items():
            if not entries:
                # Still show allocated tensors
                if tensor_name in self.current_state.tensor_memory_model.shapes:
                    shape = self.current_state.tensor_memory_model.shapes[tensor_name]
                    dtype = self.current_state.tensor_memory_model.dtypes.get(
                        tensor_name, "unknown"
                    )
                    region_summary = {
                        "name": f"{tensor_name} (tensor)",
                        "value": f"shape={shape}, dtype={dtype}",
                        "type": "tensor_region",
                        "presentationHint": "data",
                        "_tensor_region": True,
                        "_tensor_name": tensor_name,
                    }
                    variables[f"{tensor_name}_tensor"] = region_summary
                continue

            # Create a summary for the tensor region
            shape = self.current_state.tensor_memory_model.shapes.get(tensor_name, ())
            dtype = self.current_state.tensor_memory_model.dtypes.get(tensor_name, "unknown")
            region_summary = {
                "name": f"{tensor_name} (tensor)",
                "value": f"{len(entries)} entries, shape={shape}, dtype={dtype}",
                "type": "tensor_region",
                "presentationHint": "data",
                "_tensor_region": True,
                "_tensor_name": tensor_name,
            }
            variables[f"{tensor_name}_tensor"] = region_summary

            # Add individual entries (could be many)
            for entry in entries:
                indices = entry["indices"]
                # Skip sentinel for symbolic stores
                if indices == (-1,):
                    continue

                cell_key = f"{tensor_name}{''.join(f'[{i}]' for i in indices)}"
                cell_summary = get_variable_summary(
                    name=cell_key,
                    value=entry["symbolic_expr"],
                    value_type=dtype,
                    concrete_value=entry["concrete_value"],
                )
                cell_summary["_tensor_cell"] = True
                cell_summary["_tensor_indices"] = indices
                variables[cell_key] = cell_summary

        # Add path conditions as special variable
        if self.current_state.path_condition:
            path_cond_strs = [str(pc) for pc in self.current_state.path_condition]
            variables["$pathConditions"] = {
                "name": "$pathConditions",
                "value": f"{len(path_cond_strs)} constraints",
                "type": "path_conditions",
                "presentationHint": "data",
                "_skip_dap": False,  # Show in DAP
                "constraints": path_cond_strs,
            }

        # Add memory map summary using memory model
        memref_counts = {}
        for memref_name in self.current_state.memory_model.shapes:
            entries = memory_entries.get(memref_name, [])
            # Count only concrete cells (not sentinel (-1,) indices)
            concrete_count = sum(1 for e in entries if e["indices"] != (-1,))
            memref_counts[memref_name] = concrete_count

        if memref_counts:
            mem_summary = ", ".join(
                f"{memref}: {count} cells" for memref, count in memref_counts.items()
            )
            variables["$memoryMap"] = {
                "name": "$memoryMap",
                "value": mem_summary,
                "type": "memory_map",
                "presentationHint": "data",
                "_skip_dap": False,
                "details": memref_counts,
            }

        # Add tensor map summary using tensor memory model
        tensor_counts = {}
        for tensor_name in self.current_state.tensor_memory_model.shapes:
            entries = tensor_entries.get(tensor_name, [])
            # Count only concrete cells (not sentinel (-1,) indices)
            concrete_count = sum(1 for e in entries if e["indices"] != (-1,))
            tensor_counts[tensor_name] = concrete_count

        if tensor_counts:
            tensor_summary = ", ".join(
                f"{tensor}: {count} cells" for tensor, count in tensor_counts.items()
            )
            variables[""] = {
                "name": "",
                "value": tensor_summary,
                "type": "tensor_map",
                "presentationHint": "data",
                "_skip_dap": False,
                "details": tensor_counts,
            }

        # Add control flow information
        cf_info = self.get_control_flow_info()
        value = f"block {cf_info['current_block']}, {len(cf_info['successors'])} successors"
        if "current_loop" in cf_info:
            loop = cf_info["current_loop"]
            value += f", loop {loop['iv_name']}={loop['iv_value']}/{loop['ub']}"
        variables["$control_flow"] = {
            "name": "$control_flow",
            "value": value,
            "type": "control_flow",
            "presentationHint": "data",
            "_skip_dap": False,
            "details": cf_info,
        }

        return variables

    def step_next(self) -> Dict[str, Any]:
        """Execute next operation and return new location.

        Returns location after execution (could be same block, different block,
        or None if execution terminated).
        """
        if self.current_state is None or self.current_state.pc is None:
            # Execution terminated
            self.paused = True
            return self.get_current_location()
        assert self.current_state is not None and self.current_state.pc is not None
        state = cast(SymbolicState, self.current_state)
        assert state.pc is not None

        # Track symbolic variables in symbolic mode
        if self.symbolic_mode and hasattr(self.interpreter, 'symbolic_state'):
            # Track symbolic variables
            for var_name, value in self.interpreter.symbolic_state.variables.items():
                # This would be tracked by variable_tracker
                pass

        # If we're currently inside a loop, step within loop body
        if self.current_loop is not None:
            return self._step_in_loop()

        # Get current block
        block = self.func.get_basic_block(state.pc)
        if not block:
            # Invalid block
            state.pc = None
            self.paused = True
            return self.get_current_location()

        # Check if we're at a valid operation index
        if self.current_op_index >= len(block.operations):
            # At end of block - this shouldn't happen normally
            # Could happen if we just entered a new block with no operations?
            # For now, try to move to next block (but need terminator)
            self.current_state.pc = None
            self.paused = True
            return self.get_current_location()

        # Get the current operation
        op = block.operations[self.current_op_index]

        # Handle scf.for specially: enter loop if bounds are concrete
        if op.dialect == "scf" and op.name == "for" and self.current_loop is None:
            # Try to enter the loop
            if isinstance(op, LoopOperation):
                if self._enter_loop(cast(LoopOperation, op)):
                    # Loop entered successfully - don't execute the operation
                    # Return current location (still at scf.for line)
                    return self.get_current_location()
                else:
                    # Could not enter loop (symbolic bounds) - execute as normal operation
                    # This will use the interpreter's loop unrolling
                    pass

        # Store old pc to detect if operation changed block
        old_pc = state.pc

        # Execute the operation
        self._execute_single_operation(op, state)

        # Check if we're still in the same block
        if state.pc == old_pc:
            # Same block - move to next operation
            self.current_op_index += 1

            # Check if we've reached end of block
            if self.current_op_index >= len(block.operations):
                # At end of block but no terminator? This shouldn't happen
                # For safety, stop execution
                state.pc = None
                self.paused = True
            else:
                # Check breakpoint on next operation
                next_op = block.operations[self.current_op_index]
                if next_op.line in self.breakpoints:
                    self.paused = True
        else:
            # Block changed (or terminated)
            # _execute_single_operation already updated current_block_label and current_op_index
            # Check breakpoint on first operation of new block if any
            if state.pc is not None:
                new_block = self.func.get_basic_block(state.pc)
                if new_block and new_block.operations:
                    first_op = new_block.operations[0]
                    if first_op.line in self.breakpoints:
                        self.paused = True

        return self.get_current_location()

    def run_until_breakpoint(self) -> Dict[str, Any]:
        """Run execution until hitting a breakpoint or program termination."""
        self.paused = False

        while not self.paused:
            if self.current_state is None or self.current_state.pc is None:
                self.paused = True
                break
            state = cast(SymbolicState, self.current_state)

            block = self.func.get_basic_block(state.pc)
            if not block or self.current_op_index >= len(block.operations):
                state.pc = None
                self.paused = True
                break

            # Check breakpoint on current operation
            op = block.operations[self.current_op_index]
            if op.line in self.breakpoints:
                self.paused = True
                break

            # Execute step
            self.step_next()

        return self.get_current_location()

    def _execute_single_operation(self, op: Operation, state: SymbolicState):
        """Execute a single operation using concolic execution.

        Uses the ConcolicInterpreter's _execute_operation_concolic method
        which handles concrete evaluation of conditions and arithmetic.
        """
        # Store old pc to detect block transitions
        old_pc = state.pc

        # Execute the operation using concolic interpreter
        print(f"STEPPER executing op: {op.full_name}")
        self.interpreter._execute_operation_concolic(op, state, self.func)

        # Post-processing: ensure concrete values for return operation
        if isinstance(op, ReturnOperation):
            # Try to get concrete value for the return operand
            operand = op.value
            print(f"STEPPER return op, operand={operand}")
            if operand:
                concrete_val = self.interpreter._get_concrete_operand(operand, state)
                print(f"STEPPER concrete_val={concrete_val}")
                if concrete_val is not None:
                    state.set_concrete_value("return", concrete_val)
                    print(f"STEPPER set concrete return value {concrete_val}")

        # Check if this operation caused a block transition
        if state.pc != old_pc:
            # Block transition occurred
            # Record branch decision if operation is a branch
            if op.dialect == "cf" and op.name in ("cond_br", "br"):
                branch_info = {
                    "operation": op.full_name,
                    "from_block": old_pc,
                    "to_block": state.pc,
                    "line": op.line,
                }
                if op.name == "cond_br" and isinstance(op, ConditionalBranchOperation):
                    # Determine which branch was taken
                    true_block = op.true_block
                    false_block = op.false_block
                    if state.pc == true_block:
                        branch_info["taken_branch"] = "true"
                    elif state.pc == false_block:
                        branch_info["taken_branch"] = "false"
                    else:
                        branch_info["taken_branch"] = "unknown"
                    # Try to get concrete condition value
                    cond_operand = op.cond
                    if cond_operand:
                        concrete_cond = self.interpreter._get_concrete_operand(cond_operand, state)
                        branch_info["condition_value"] = concrete_cond
                else:  # cf.br
                    branch_info["taken_branch"] = "unconditional"

                self.last_branch_decision = branch_info
                self.branch_history.append(branch_info)
                # Log branch decision
                if op.name == "cond_br":
                    print(
                        f"STEPPER conditional branch: {old_pc} -> {state.pc} (condition={branch_info.get('condition_value', 'unknown')})"
                    )
                else:
                    print(f"STEPPER unconditional branch: {old_pc} -> {state.pc}")
                # Limit history size
                if len(self.branch_history) > 100:
                    self.branch_history.pop(0)

            # Update our tracking variables
            self.current_block_label = state.pc
            self.current_op_index = 0  # Start at first operation in new block
        # Note: if state.pc is None, execution terminated (e.g., return)

    def _evaluate_operand_concrete(self, operand: str, state: SymbolicState) -> int:
        """Evaluate operand to concrete integer value."""
        # Check if it's an SSA value
        if operand.startswith("%"):
            value_name = operand[1:]
            concrete = state.get_concrete_value(value_name)
            if concrete is not None:
                return concrete

            # Try to get from symbolic value
            mlir_value = state.get_value(value_name)
            if mlir_value and mlir_value.expr is not None:
                if isinstance(mlir_value.expr, z3.IntNumRef):
                    return mlir_value.expr.as_long()

        # Check if it's an integer constant
        try:
            return int(operand)
        except ValueError:
            # Try as variable name without '%'
            concrete = state.get_concrete_value(operand)
            if concrete is not None:
                return concrete

            raise ValueError(f"Cannot evaluate operand concretely: {operand}")

    def pause(self):
        """Pause execution."""
        self.paused = True

    def resume(self):
        """Resume execution (alias for run_until_breakpoint)."""
        return self.run_until_breakpoint()

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of execution state."""
        location = self.get_current_location()
        variables = self.get_variables()

        return {
            "paused": self.paused,
            "location": location,
            "variables": variables,
            "function": self.func_name,
            "breakpoints": list(self.breakpoints),
        }
