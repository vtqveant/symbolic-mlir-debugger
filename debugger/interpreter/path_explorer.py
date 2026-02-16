#!/usr/bin/env python3
"""
Path exploration for MLIR symbolic debugging.

Explores all possible execution paths through symbolic execution.
"""

from typing import Dict, List, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class PathExplorer:
    """Explore all possible execution paths."""

    def __init__(self, stepper=None):
        """Initialize path explorer.

        Args:
            stepper: ExecutionStepper instance for accessing interpreter and function.
                     If None, must be set via set_stepper before calling explore().
        """
        self.stepper = stepper
        self.paths = []

    def set_stepper(self, stepper):
        """Set the execution stepper for path exploration."""
        self.stepper = stepper

    def explore(self, max_paths: int = 10) -> List[Dict[str, Any]]:
        """Explore execution paths using concolic execution.

        Args:
            max_paths: Maximum number of paths to explore

        Returns:
            List of paths with their details, formatted for DAP response.
            Each path contains: inputs, path_condition, return_value, depth, branches
        """
        if self.stepper is None:
            logger.error("PathExplorer: No stepper set, cannot explore paths")
            return []

        if not hasattr(self.stepper, "interpreter") or self.stepper.interpreter is None:
            logger.error("PathExplorer: Stepper has no interpreter")
            return []

        if not hasattr(self.stepper, "func") or self.stepper.func is None:
            logger.error("PathExplorer: Stepper has no function")
            return []

        interpreter = self.stepper.interpreter
        func = self.stepper.func

        # Use concolic interpreter's explore_paths method
        if not hasattr(interpreter, "explore_paths"):
            logger.error("PathExplorer: Interpreter does not have explore_paths method")
            return []

        try:
            # Get real paths from concolic interpreter
            real_paths = interpreter.explore_paths(func, max_paths)

            # Transform to DAP-friendly format (compatible with mock format)
            self.paths = []
            for i, path in enumerate(real_paths):
                # Convert Z3 expressions to strings for JSON serialization
                path_condition_strs = [
                    str(cond) for cond in path.get("path_condition", [])
                ]
                return_value = path.get("return_value")
                return_value_str = (
                    str(return_value) if return_value is not None else None
                )

                # Extract branch decisions from path conditions
                branches = self._extract_branches_from_conditions(path_condition_strs)
                path_decisions = branches  # path is list of branch decisions

                # Create DAP path info
                path_info = {
                    "path": path_decisions,
                    "depth": len(path_condition_strs),
                    "branches": branches,
                    # Additional debug information
                    "path_id": i,
                    "inputs": path.get("inputs", {}),
                    "path_condition": path_condition_strs,
                    "return_value": return_value_str,
                }
                self.paths.append(path_info)

            return self.paths[:max_paths]

        except Exception as e:
            logger.error(f"Path exploration failed: {e}")
            return []

    def _extract_branches_from_conditions(
        self, conditions: List[str]
    ) -> List[Dict[str, Any]]:
        """Extract branch information from path conditions."""
        branches = []
        for i, condition in enumerate(conditions):
            # Parse condition to determine branch direction
            # For now, create simple branch info
            branch_info = {
                "branch_index": i,
                "condition": condition,
                "taken": True,  # All conditions in path condition are satisfied (taken)
            }
            branches.append(branch_info)
        return branches

    def get_all_paths(self) -> List[Dict[str, Any]]:
        """Get all explored paths."""
        return self.paths
