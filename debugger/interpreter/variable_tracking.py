#!/usr/bin/env python3
"""
Symbolic variable tracking for MLIR symbolic debugging.

Tracks symbolic variables and their constraints.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SymbolicVariableTracker:
    """Track symbolic variables and their constraints."""

    def __init__(self, stepper=None):
        """Initialize symbolic variable tracker.

        Args:
            stepper: ExecutionStepper instance for accessing current symbolic state.
                     If None, must be set via set_stepper before calling get_variables().
        """
        self.stepper = stepper
        self.variables = {}
        self.constraints = []

    def set_stepper(self, stepper):
        """Set the execution stepper for variable tracking."""
        self.stepper = stepper

    def track_variable(self, name: str, value: Any, constraint: Optional[str] = None):
        """Track a symbolic variable.

        Args:
            name: Variable name
            value: Symbolic value
            constraint: Optional constraint expression
        """
        self.variables[name] = {
            "value": str(value),
            "constraint": constraint,
        }

    def get_variables(self) -> Dict[str, Any]:
        """Get all tracked variables from current symbolic state."""
        if self.stepper is None:
            logger.warning("SymbolicVariableTracker: No stepper set, returning empty variables")
            return self.variables

        if not hasattr(self.stepper, "current_state") or self.stepper.current_state is None:
            logger.warning("SymbolicVariableTracker: No current state, returning empty variables")
            return self.variables

        state = self.stepper.current_state
        self.variables = {}

        # Extract variables from symbolic state
        for name, mlir_value in state.values.items():
            value_str = str(mlir_value.expr) if mlir_value.expr is not None else "unknown"
            var_type = mlir_value.type if hasattr(mlir_value, "type") else "unknown"
            concrete_val = state.get_concrete_value(name)

            var_info = {
                "value": value_str,
                "type": var_type,
                "concrete_value": concrete_val,
                "is_symbolic": mlir_value.expr is not None
                and not isinstance(mlir_value.expr, (int, float, bool)),
            }

            if concrete_val is not None:
                var_info["display_value"] = f"{concrete_val} (symbolic: {value_str})"
            else:
                var_info["display_value"] = value_str

            self.variables[name] = var_info

        return self.variables

    def get_constraints(self) -> List[str]:
        """Get all constraints from current symbolic state."""
        if self.stepper is None:
            logger.warning("SymbolicVariableTracker: No stepper set, returning empty constraints")
            return self.constraints

        if not hasattr(self.stepper, "current_state") or self.stepper.current_state is None:
            logger.warning("SymbolicVariableTracker: No current state, returning empty constraints")
            return self.constraints

        state = self.stepper.current_state
        self.constraints = [str(cond) for cond in state.path_condition]
        return self.constraints

    def add_constraint(self, constraint: str):
        """Add a constraint."""
        self.constraints.append(constraint)

    def clear_constraints(self):
        """Clear all constraints."""
        self.constraints = []
