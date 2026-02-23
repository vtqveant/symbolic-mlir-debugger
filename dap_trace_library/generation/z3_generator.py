#!/usr/bin/env python3
"""
Z3-based concrete value generator.

This module provides Z3 constraint solving for generating concrete
values for MLIR operations, re-implementing the functionality
that was removed in PR #115 cleanup.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from .base_generator import BaseGenerator
from ..config.dialect_config import OperationConfig

logger = logging.getLogger(__name__)


class Z3Generator:
    """Z3 constraint solver for concrete value generation."""

    def __init__(self):
        """Initialize Z3 solver."""
        try:
            import z3

            self.z3 = z3
            self.available = True
            self.solver = z3.Solver()
            logger.info("Z3 solver initialized successfully")
        except ImportError:
            self.available = False
            logger.error("Z3 not available. Install with: pip install z3-solver")

    def is_available(self) -> bool:
        """Check if Z3 is available."""
        return self.available

    def generate_for_constraint(
        self,
        constraint_expr: str,
        max_solutions: int = 3,
        variable_bounds: Dict[str, tuple] = None,
    ) -> List[Dict[str, int]]:
        """Generate concrete values satisfying a constraint expression.

        Args:
            constraint_expr: Z3 expression string (e.g., "a > b", "b != 0")
            max_solutions: Maximum number of solutions to generate
            variable_bounds: Optional bounds for variables as {var_name: (min, max)}

        Returns:
            List of dictionaries with concrete values
        """
        if not self.available:
            logger.error("Z3 not available")
            return []

        solutions = []

        try:
            # Parse variables from constraint expression
            variables = self._extract_variables(constraint_expr)

            # Create Z3 variables
            z3_vars = {}
            for var_name in variables:
                z3_vars[var_name] = self.z3.Int(var_name)

            # Parse constraint
            constraint = self._parse_constraint(constraint_expr, z3_vars)
            if constraint is None:
                logger.warning(f"Could not parse constraint: {constraint_expr}")
                return solutions

            # Ensure constraint is boolean (Z3 solver requires boolean constraints)
            # If constraint is arithmetic (e.g., "a + b"), treat as "expr != 0"
            if not isinstance(constraint, self.z3.BoolRef):
                try:
                    constraint = constraint != 0
                except Exception as e:
                    logger.error(f"Failed to convert arithmetic constraint to boolean: {e}")
                    return solutions

            # Add constraint to solver
            self.solver.add(constraint)

            # Add bounds for variables
            default_bounds = (-100, 100)
            for var_name, z3_var in z3_vars.items():
                bounds = (
                    variable_bounds.get(var_name, default_bounds)
                    if variable_bounds
                    else default_bounds
                )
                self.solver.add(z3_var >= bounds[0])
                self.solver.add(z3_var <= bounds[1])

            # Generate multiple solutions
            for _ in range(max_solutions):
                if self.solver.check() == self.z3.sat:
                    model = self.solver.model()
                    solution = {}

                    # Extract values
                    for var_name, z3_var in z3_vars.items():
                        var_value = model[z3_var]
                        if isinstance(var_value, self.z3.IntNumRef):
                            solution[var_name] = var_value.as_long()

                    if solution:
                        solutions.append(solution)

                        # Block this solution to find another
                        block = []
                        for var_name, z3_var in z3_vars.items():
                            var_value = model[z3_var]
                            if isinstance(var_value, self.z3.IntNumRef):
                                block.append(z3_var != var_value)

                        if block:
                            self.solver.add(self.z3.Or(block))
                    else:
                        break
                else:
                    break

            # Reset solver for next use
            self.solver = self.z3.Solver()

        except Exception as e:
            logger.error(f"Failed to generate solutions for constraint '{constraint_expr}': {e}")

        return solutions

    def _extract_variables(self, constraint_expr: str) -> List[str]:
        """Extract variable names from constraint expression.

        Simple extraction for common patterns.
        """
        variables = set()

        # Common patterns
        import re

        # Match variable names (single letters or simple names)
        var_pattern = r"\b([a-zA-Z][a-zA-Z0-9_]*)\b"
        matches = re.findall(var_pattern, constraint_expr)

        # Filter out keywords
        keywords = {"and", "or", "not", "true", "false", "sat", "unsat"}
        for match in matches:
            if match not in keywords and not match.isdigit():
                variables.add(match)

        # If no variables found, use default
        if not variables:
            variables = {"a", "b"}

        return list(variables)

    def _parse_constraint(self, constraint_expr: str, z3_vars: Dict[str, Any]) -> Optional[Any]:
        """Parse constraint expression into Z3 expression.

        Args:
            constraint_expr: Constraint expression string
            z3_vars: Dictionary of Z3 variable objects

        Returns:
            Z3 expression or None if parsing fails
        """
        try:
            # Simple constraint patterns
            if ">" in constraint_expr:
                parts = constraint_expr.split(">")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)
                    if left is not None and right is not None:
                        return left > right

            elif "<" in constraint_expr:
                parts = constraint_expr.split("<")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)
                    if left is not None and right is not None:
                        return left < right

            elif "==" in constraint_expr:
                parts = constraint_expr.split("==")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)
                    if left is not None and right is not None:
                        return left == right

            elif "!=" in constraint_expr:
                parts = constraint_expr.split("!=")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)
                    if left is not None and right is not None:
                        return left != right

            elif "+" in constraint_expr:
                parts = constraint_expr.split("+")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)
                    if left is not None and right is not None:
                        return left + right

            elif "-" in constraint_expr:
                parts = constraint_expr.split("-")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)
                    if left is not None and right is not None:
                        return left - right

            elif "*" in constraint_expr:
                parts = constraint_expr.split("*")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)
                    if left is not None and right is not None:
                        return left * right

            elif "/" in constraint_expr:
                parts = constraint_expr.split("/")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)
                    if left is not None and right is not None:
                        return left / right

            # Try to evaluate as Python expression
            try:
                # Create local namespace with Z3 variables
                local_vars = {}
                for var_name, z3_var in z3_vars.items():
                    local_vars[var_name] = z3_var

                # Add Z3 functions
                local_vars.update(
                    {
                        "And": self.z3.And,
                        "Or": self.z3.Or,
                        "Not": self.z3.Not,
                        "Implies": self.z3.Implies,
                        "If": self.z3.If,
                    }
                )

                # Evaluate expression
                result = eval(constraint_expr, {"__builtins__": {}}, local_vars)
                return result

            except Exception as eval_error:
                logger.warning(f"Could not evaluate constraint '{constraint_expr}': {eval_error}")
                return None

        except Exception as e:
            logger.error(f"Error parsing constraint '{constraint_expr}': {e}")
            return None

    def _parse_expression(self, expr: str, z3_vars: Dict[str, Any]) -> Optional[Any]:
        """Parse simple expression into Z3 expression.

        Args:
            expr: Expression string
            z3_vars: Dictionary of Z3 variable objects

        Returns:
            Z3 expression or integer value
        """
        expr = expr.strip()

        # Check if it's a variable
        if expr in z3_vars:
            return z3_vars[expr]

        # Check if it's an integer
        try:
            return int(expr)
        except ValueError:
            pass

        # Check if it's a simple arithmetic expression
        for op in ["+", "-", "*", "/"]:
            if op in expr:
                parts = expr.split(op)
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), z3_vars)
                    right = self._parse_expression(parts[1].strip(), z3_vars)

                    if left is not None and right is not None:
                        if op == "+":
                            return left + right
                        elif op == "-":
                            return left - right
                        elif op == "*":
                            return left * right
                        elif op == "/":
                            return left / right

        # Unknown expression
        logger.warning(f"Could not parse expression: {expr}")
        return None


class Z3ConcreteGenerator(BaseGenerator):
    """Generator that uses Z3 for concrete value generation."""

    def __init__(self, config):
        """Initialize Z3-based generator."""
        super().__init__(config)
        self.z3_generator = Z3Generator()

        # Check Z3 availability
        if not self.z3_generator.is_available():
            logger.warning("Z3 not available. Using fallback value generation.")

    def get_concrete_values(self, operation: OperationConfig) -> List[Dict[str, Any]]:
        """Get concrete values using Z3 constraint solving.

        Args:
            operation: Operation configuration

        Returns:
            List of dictionaries with concrete values
        """
        # Use Z3 if available and constraints are defined
        if (
            self.z3_generator.is_available()
            and operation.constraints
            and self.config.generation_settings.get("use_z3", True)
        ):
            all_solutions = []
            max_solutions = self.config.generation_settings.get("max_solutions_per_constraint", 3)

            for constraint in operation.constraints:
                solutions = self.z3_generator.generate_for_constraint(
                    constraint, max_solutions=max_solutions
                )
                all_solutions.extend(solutions)

            # Deduplicate solutions
            unique_solutions = []
            seen = set()
            for solution in all_solutions:
                # Create hashable representation
                solution_tuple = tuple(sorted(solution.items()))
                if solution_tuple not in seen:
                    seen.add(solution_tuple)
                    unique_solutions.append(solution)

            if unique_solutions:
                logger.info(f"Generated {len(unique_solutions)} Z3 solutions for {operation.name}")
                return unique_solutions

        # Fallback to parent implementation
        return super().get_concrete_values(operation)

    def generate_mlir_snippet(self, operation: OperationConfig, values: Dict[str, Any]) -> str:
        """Generate MLIR code snippet for an operation.

        This is a placeholder implementation that should be overridden
        by dialect-specific generators.

        Args:
            operation: Operation configuration
            values: Concrete values for variables

        Returns:
            MLIR code as string
        """
        # Default template for arithmetic operations
        template = """module {{
  func.func @test_{op_name}() {{
    %0 = arith.constant {value_a} : i32
    %1 = arith.constant {value_b} : i32
    %2 = arith.{op_name} %0, %1 : i32
    return
  }}
}}"""

        # Extract values
        value_a = values.get("a", 1)
        value_b = values.get("b", 2)

        return template.format(op_name=operation.name, value_a=value_a, value_b=value_b)

    def generate_dap_trace(
        self, operation: OperationConfig, mlir_path: Path, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate DAP trace for an operation.

        Args:
            operation: Operation configuration
            mlir_path: Path to MLIR file
            values: Concrete values for variables

        Returns:
            DAP trace as dictionary
        """
        trace = {
            "name": f"{operation.dialect}_{operation.name}_z3",
            "program": str(mlir_path),
            "description": f"Z3-generated test for {operation.dialect}.{operation.name}",
            "constraints": operation.constraints,
            "concrete_inputs": values,
            "z3_generated": self.z3_generator.is_available(),
            "session": [
                {
                    "command": "initialize",
                    "arguments": {
                        "adapterID": "mlir-debugger",
                        "clientID": f"test-{operation.dialect}-{operation.name}",
                    },
                    "expect": {"success": True},
                },
                {
                    "command": "symbolic/setMode",
                    "arguments": {"enabled": True},
                    "expect": {"success": True},
                },
            ],
        }

        # Add concrete input setting commands
        for var_name, var_value in values.items():
            trace["session"].append(
                {
                    "command": "symbolic/setInput",
                    "arguments": {"variable": var_name, "value": var_value},
                    "expect": {"success": True},
                }
            )

        # Add launch command
        trace["session"].append(
            {
                "command": "launch",
                "arguments": {"program": str(mlir_path), "noDebug": True},
                "expect": {"success": True},
            }
        )

        # Add path exploration
        trace["session"].append(
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": 1},
                "expect": {"success": True},
            }
        )

        # Add disconnect
        trace["session"].append(
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True},
            }
        )

        return trace
