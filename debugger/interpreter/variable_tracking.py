#!/usr/bin/env python3
"""
Symbolic variable tracking for MLIR symbolic debugging.

Tracks symbolic variables and their constraints.
"""

from typing import Dict, List, Any, Optional


class SymbolicVariableTracker:
    """Track symbolic variables and their constraints."""

    def __init__(self):
        """Initialize symbolic variable tracker."""
        self.variables = {}
        self.constraints = []

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
        """Get all tracked variables."""
        return self.variables

    def get_constraints(self) -> List[str]:
        """Get all constraints."""
        return self.constraints

    def add_constraint(self, constraint: str):
        """Add a constraint."""
        self.constraints.append(constraint)

    def clear_constraints(self):
        """Clear all constraints."""
        self.constraints = []
