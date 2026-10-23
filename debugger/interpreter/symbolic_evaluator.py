#!/usr/bin/env python3
"""
Symbolic expression evaluator for MLIR symbolic debugging.

Provides ability to evaluate symbolic expressions using Z3 solver.
"""

import logging
from typing import Any

import z3

from .safe_eval import ExpressionError, safe_eval

logger = logging.getLogger(__name__)


class SymbolicExpressionEvaluator:
    """Evaluate symbolic expressions using Z3 solver."""

    def __init__(self, stepper=None):
        """Initialize symbolic expression evaluator.

        Args:
            stepper: ExecutionStepper instance for accessing current symbolic state.
                     If None, must be set via set_stepper before calling evaluate().
        """
        self.stepper = stepper
        self.solver = z3.Solver()

    def set_stepper(self, stepper):
        """Set the execution stepper for expression evaluation."""
        self.stepper = stepper

    def evaluate(self, expression: str) -> Any:
        """Evaluate a symbolic expression using current symbolic state.

        Args:
            expression: String expression to evaluate

        Returns:
            Evaluation result (string representation of Z3 expression or value)
        """
        if self.stepper is None:
            return "No stepper set"

        if not hasattr(self.stepper, "current_state") or self.stepper.current_state is None:
            return "No execution state available"

        state = self.stepper.current_state

        try:
            expression = expression.strip()
            if expression == "":
                return "Empty expression"

            # Get all symbolic variables from current state
            variables = {}
            concrete_values = {}
            for name, mlir_value in state.values.items():
                if mlir_value.expr is not None:
                    variables[name] = mlir_value.expr
                # Also track concrete values if available
                concrete_val = state.get_concrete_value(name)
                if concrete_val is not None:
                    concrete_values[name] = concrete_val

            # Try to evaluate using Z3 with current path constraints
            self.solver = z3.Solver()

            # Add current path conditions to solver
            for condition in state.path_condition:
                self.solver.add(condition)

            # Create Z3 variables for all symbolic variables
            z3_vars = {}
            for name, expr in variables.items():
                if isinstance(expr, z3.ExprRef):
                    # Use existing Z3 expression
                    z3_vars[name] = expr
                else:
                    # Create fresh variable
                    z3_vars[name] = z3.Int(name)

            # Try to parse the expression as a Z3 expression
            # Simple approach: evaluate with Z3's eval method
            # First, check if expression is a single variable
            if expression in z3_vars:
                var_expr = z3_vars[expression]
                # Try to get concrete value from solver
                self.solver.push()
                result = self.solver.check()
                if result == z3.sat:
                    model = self.solver.model()
                    if var_expr in model:
                        val = model[var_expr]
                        self.solver.pop()
                        return str(val)
                self.solver.pop()
                # Fallback to symbolic expression
                return str(var_expr)

            # Evaluate with Z3 expressions where available. The safe evaluator
            # supports only arithmetic/comparison/boolean operations and a small
            # function allow-list; it never executes arbitrary Python.
            env = dict(concrete_values)
            env.update(z3_vars)
            try:
                result = safe_eval(expression, env)
                if isinstance(result, z3.ExprRef):
                    result = z3.simplify(result)
                return str(result)
            except ExpressionError:
                return f"Expression '{expression}' (symbolic)"

        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            return f"Error evaluating '{expression}': {e}"
