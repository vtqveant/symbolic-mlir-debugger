#!/usr/bin/env python3
"""
Path-aware test case generator for symbolic MLIR debugging.

Generates test cases targeting specific execution paths or branch conditions.
Uses Z3 solver to generate inputs satisfying specific constraints.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    import z3

    Z3_AVAILABLE = True
except ImportError:
    z3 = None
    Z3_AVAILABLE = False
    logging.warning("Z3 not available, path-aware generation limited")

from .test_case_generator import TestCaseGenerator

logger = logging.getLogger(__name__)


class PathAwareGenerator(TestCaseGenerator):
    """Generate test cases targeting specific paths or branch conditions."""

    def __init__(
        self,
        debugger_path: Optional[str] = None,
        timeout: int = 30,
        read_timeout: int = 10,
    ):
        """Initialize path-aware generator.

        Args:
            debugger_path: Path to DAP server script. If None, auto-detected.
            timeout: Connection timeout
            read_timeout: Read timeout
        """
        super().__init__(debugger_path, timeout, read_timeout)
        self.z3_solver = None
        if Z3_AVAILABLE:
            self.z3_solver = z3.Solver()

    def generate_for_branch_condition(
        self,
        program_path: str,
        condition_expr: str,
        test_name: Optional[str] = None,
        max_attempts: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate test cases satisfying a specific branch condition.

        Args:
            program_path: Path to MLIR program
            condition_expr: Z3 expression string for the branch condition
            test_name: Base name for test scripts
            max_attempts: Maximum attempts to find satisfying inputs

        Returns:
            List of generated test scripts
        """
        if not Z3_AVAILABLE:
            logger.error("Z3 not available, cannot generate for branch condition")
            return []

        test_name = test_name or Path(program_path).stem
        test_scripts = []

        try:
            # Parse condition expression
            condition = self._parse_z3_expression(condition_expr)
            if condition is None:
                logger.error(f"Failed to parse condition: {condition_expr}")
                return []

            # Use Z3 to find inputs satisfying condition
            inputs_list = self._find_inputs_for_condition(
                condition=condition,
                max_attempts=max_attempts,
            )

            if not inputs_list:
                logger.warning(f"No inputs found for condition: {condition_expr}")
                return []

            # Generate test script for each input set
            for i, inputs in enumerate(inputs_list):
                test_script = self._create_test_script_for_inputs(
                    program_path=program_path,
                    inputs=inputs,
                    condition_expr=condition_expr,
                    test_name=f"{test_name}_branch_{i}",
                    input_index=i,
                )
                test_scripts.append(test_script)

            return test_scripts

        except Exception as e:
            logger.error(f"Failed to generate test cases for branch condition: {e}")
            return []

    def generate_edge_cases(
        self,
        program_path: str,
        variable_ranges: Dict[str, Tuple[int, int]],
        test_name: Optional[str] = None,
        num_cases: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate test cases for edge cases of variable ranges.

        Args:
            program_path: Path to MLIR program
            variable_ranges: Dictionary mapping variable names to (min, max) ranges
            test_name: Base name for test scripts
            num_cases: Number of edge cases to generate per variable

        Returns:
            List of generated test scripts
        """
        if not Z3_AVAILABLE:
            logger.error("Z3 not available, cannot generate edge cases")
            return []

        test_name = test_name or Path(program_path).stem
        test_scripts = []

        try:
            # Generate edge values for each variable
            edge_values = self._generate_edge_values(variable_ranges, num_cases)

            # Generate test scripts for each combination
            for i, inputs in enumerate(edge_values):
                test_script = self._create_test_script_for_inputs(
                    program_path=program_path,
                    inputs=inputs,
                    condition_expr="edge_case",
                    test_name=f"{test_name}_edge_{i}",
                    input_index=i,
                )
                test_scripts.append(test_script)

            return test_scripts

        except Exception as e:
            logger.error(f"Failed to generate edge case test cases: {e}")
            return []

    def _parse_z3_expression(self, expr_str: str) -> Optional[z3.ExprRef]:
        """Parse a Z3 expression string.

        Args:
            expr_str: Z3 expression string

        Returns:
            Parsed Z3 expression or None if parsing fails
        """
        if not Z3_AVAILABLE:
            return None

        try:
            # Simple parsing: assume expression uses integer variables
            # For now, just create a placeholder
            # In a real implementation, would parse the expression properly
            return z3.Bool(expr_str)
        except Exception as e:
            logger.error(f"Failed to parse Z3 expression '{expr_str}': {e}")
            return None

    def _find_inputs_for_condition(
        self,
        condition: z3.ExprRef,
        max_attempts: int = 5,
    ) -> List[Dict[str, int]]:
        """Find input values satisfying a Z3 condition.

        Args:
            condition: Z3 expression to satisfy
            max_attempts: Maximum number of attempts

        Returns:
            List of input dictionaries
        """
        if not Z3_AVAILABLE:
            return []

        inputs_list = []
        solver = z3.Solver()
        solver.add(condition)

        for attempt in range(max_attempts):
            if solver.check() == z3.sat:
                model = solver.model()
                inputs = {}

                # Extract integer values from model
                for decl in model.decls():
                    if decl.arity() == 0 and isinstance(model[decl], z3.IntNumRef):
                        var_name = decl.name()
                        var_value = model[decl].as_long()
                        inputs[var_name] = var_value

                if inputs:
                    inputs_list.append(inputs)

                    # Block this solution to find another
                    block = []
                    for decl in model.decls():
                        if decl.arity() == 0:
                            block.append(decl() != model[decl])
                    if block:
                        solver.add(z3.Or(block))
                else:
                    break
            else:
                break

        return inputs_list

    def _generate_edge_values(
        self,
        variable_ranges: Dict[str, Tuple[int, int]],
        num_cases: int,
    ) -> List[Dict[str, int]]:
        """Generate edge values for variables.

        Args:
            variable_ranges: Dictionary mapping variable names to (min, max) ranges
            num_cases: Number of edge cases per variable

        Returns:
            List of input dictionaries with edge values
        """
        edge_values = []
        variables = list(variable_ranges.keys())

        if not variables:
            return edge_values

        # Generate combinations of edge values
        import itertools

        # For each variable, generate edge values (min, max, near min, near max, zero)
        variable_edge_lists = {}
        for var_name, (vmin, vmax) in variable_ranges.items():
            edges = []
            edges.append(vmin)  # minimum
            edges.append(vmax)  # maximum
            if vmin < 0 < vmax:
                edges.append(0)  # zero if in range
            if vmin + 1 <= vmax:
                edges.append(vmin + 1)  # just above min
            if vmax - 1 >= vmin:
                edges.append(vmax - 1)  # just below max
            # Add random values if needed
            import random

            for _ in range(num_cases - len(edges)):
                edges.append(random.randint(vmin, vmax))

            variable_edge_lists[var_name] = edges[:num_cases]

        # Generate combinations (cartesian product)
        combinations = list(itertools.product(*variable_edge_lists.values()))

        # Convert to dictionaries
        for combo in combinations[: num_cases * 2]:  # Limit total combinations
            inputs = {}
            for var_name, value in zip(variables, combo):
                inputs[var_name] = value
            edge_values.append(inputs)

        return edge_values

    def _create_test_script_for_inputs(
        self,
        program_path: str,
        inputs: Dict[str, int],
        condition_expr: str,
        test_name: str,
        input_index: int,
    ) -> Dict[str, Any]:
        """Create a test script for specific inputs.

        Args:
            program_path: Path to MLIR program
            inputs: Concrete input values
            condition_expr: Condition that inputs satisfy
            test_name: Name for the test script
            input_index: Index of the input set

        Returns:
            Test script dictionary
        """
        # Build session steps
        session_steps = [
            {
                "command": "initialize",
                "arguments": {
                    "adapterID": "mlir-debugger",
                    "clientID": f"test-{test_name}",
                },
                "expect": {"success": True},
            },
            {
                "command": "symbolic/setMode",
                "arguments": {"enabled": True},
                "expect": {"success": True},
            },
            {
                "command": "launch",
                "arguments": {
                    "program": program_path,
                    "noDebug": True,
                },
                "expect": {"success": True},
            },
        ]

        # Add symbolic evaluation for each input variable
        for var_name, var_value in inputs.items():
            session_steps.append(
                {
                    "command": "symbolic/evaluate",
                    "arguments": {
                        "expression": var_name,
                        "frameId": 0,
                    },
                    "expect": {
                        "success": True,
                        # Note: we can't guarantee the exact value due to symbolic nature
                    },
                }
            )

        # Add constraint validation
        session_steps.append(
            {
                "command": "symbolic/getConstraints",
                "arguments": {},
                "expect": {
                    "success": True,
                    # At least one constraint should exist
                    "count": {"min": 1},
                },
            }
        )

        # Disconnect
        session_steps.append(
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True},
            }
        )

        test_script = {
            "name": test_name,
            "program": program_path,
            "description": f"Test for inputs satisfying: {condition_expr}",
            "input_set": {
                "index": input_index,
                "inputs": inputs,
                "condition": condition_expr,
            },
            "session": session_steps,
        }

        return test_script

    def generate_memory_model_tests(
        self,
        program_path: str,
        test_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate test cases targeting memory model operations.

        This method focuses on generating tests for programs that involve
        memory operations (loads, stores, allocations).

        Args:
            program_path: Path to MLIR program
            test_name: Base name for test scripts

        Returns:
            List of generated test scripts
        """
        # For now, delegate to general path exploration
        # In a real implementation, would analyze the program to identify
        # memory operations and generate targeted tests
        logger.info("Generating memory model tests (using general path exploration)")
        return self.generate_from_program(
            program_path=program_path,
            max_paths=5,
            test_name=test_name or f"{Path(program_path).stem}_memory",
        )
