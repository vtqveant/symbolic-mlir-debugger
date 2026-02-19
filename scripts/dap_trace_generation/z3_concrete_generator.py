#!/usr/bin/env python3
"""
Z3-based concrete value generator for MLIR test traces.

This script implements Issue #108: Generate actual Z3-based concrete values
for DAP test traces, replacing hard-coded tests with constraint-solving.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import z3

    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    logging.error("Z3 not available. Install with: pip install z3-solver")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Z3ConcreteGenerator:
    """Generate concrete values using Z3 constraint solver."""

    def __init__(self):
        """Initialize Z3 solver."""
        if not Z3_AVAILABLE:
            raise ImportError("Z3 not available")
        self.solver = z3.Solver()

    def generate_for_constraint(
        self, constraint_expr: str, max_solutions: int = 3
    ) -> List[Dict[str, int]]:
        """Generate concrete values satisfying a constraint expression.

        Args:
            constraint_expr: Z3 expression string (e.g., "a > b", "b != 0")
            max_solutions: Maximum number of solutions to generate

        Returns:
            List of dictionaries with concrete values
        """
        solutions = []

        try:
            # Parse the constraint expression
            # For simplicity, we'll handle common patterns
            if ">" in constraint_expr:
                # a > b
                a = z3.Int("a")
                b = z3.Int("b")
                self.solver.add(a > b)
                # Add reasonable bounds
                self.solver.add(a >= -100, a <= 100)
                self.solver.add(b >= -100, b <= 100)

            elif "<" in constraint_expr:
                # a < b
                a = z3.Int("a")
                b = z3.Int("b")
                self.solver.add(a < b)
                self.solver.add(a >= -100, a <= 100)
                self.solver.add(b >= -100, b <= 100)

            elif "==" in constraint_expr:
                # a == b
                a = z3.Int("a")
                b = z3.Int("b")
                self.solver.add(a == b)
                self.solver.add(a >= -100, a <= 100)
                self.solver.add(b >= -100, b <= 100)

            elif "!=" in constraint_expr:
                # b != 0 (for division safety)
                b = z3.Int("b")
                self.solver.add(b != 0)
                self.solver.add(b >= -100, b <= 100)
                # Also need 'a' for completeness
                a = z3.Int("a")
                self.solver.add(a >= -100, a <= 100)
            else:
                logger.warning(f"Unhandled constraint: {constraint_expr}")
                return solutions

            # Generate multiple solutions
            for _ in range(max_solutions):
                if self.solver.check() == z3.sat:
                    model = self.solver.model()
                    solution = {}

                    # Extract values
                    for decl in model.decls():
                        if decl.arity() == 0:  # Constant/variable
                            var_name = decl.name()
                            var_value = model[decl]
                            if isinstance(var_value, z3.IntNumRef):
                                solution[var_name] = var_value.as_long()

                    if solution:
                        solutions.append(solution)

                        # Block this solution to find another
                        block = []
                        for decl in model.decls():
                            if decl.arity() == 0:
                                block.append(decl() != model[decl])
                        if block:
                            self.solver.add(z3.Or(block))
                    else:
                        break
                else:
                    break

            # Reset solver for next use
            self.solver = z3.Solver()

        except Exception as e:
            logger.error(f"Failed to generate solutions for constraint '{constraint_expr}': {e}")

        return solutions

    def create_dap_trace(
        self, program_path: str, inputs: Dict[str, int], test_name: str, constraint: str
    ) -> Dict[str, Any]:
        """Create a DAP trace with concrete input values.

        Args:
            program_path: Path to MLIR program
            inputs: Dictionary of variable names to concrete values
            test_name: Name for the test
            constraint: Constraint that these values satisfy

        Returns:
            DAP trace dictionary
        """
        trace = {
            "name": test_name,
            "program": program_path,
            "description": f"Z3-generated test for constraint: {constraint}",
            "constraint_satisfied": constraint,
            "concrete_inputs": inputs,
            "session": [
                {
                    "command": "initialize",
                    "arguments": {"adapterID": "mlir-debugger", "clientID": f"test-z3-{test_name}"},
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
        for var_name, var_value in inputs.items():
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
                "arguments": {"program": program_path, "noDebug": True},
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


def generate_arithmetic_tests_with_z3():
    """Generate arithmetic test cases using Z3 constraint solving."""

    if not Z3_AVAILABLE:
        logger.error("Z3 not available. Cannot generate tests.")
        return []

    fixtures_dir = Path(__file__).parent.parent / "debugger" / "fixtures"
    output_dir = Path(__file__).parent.parent / "generated_tests"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clear existing generated tests
    for old_file in output_dir.glob("*.json"):
        old_file.unlink()
    logger.info("Cleared existing generated tests")

    generator = Z3ConcreteGenerator()
    all_traces = []

    # Define test cases for each MLIR fixture with their constraints
    test_cases = [
        {
            "fixture": "arith_conditional.mlir",
            "constraints": ["a > b", "a < b", "a == b"],
            "description": "Conditional arithmetic with branches",
        },
        {
            "fixture": "arith_basic_ops.mlir",
            "constraints": ["b != 0"],  # Avoid division by zero
            "description": "Basic arithmetic operations",
        },
        {
            "fixture": "arith_edge_cases.mlir",
            "constraints": ["b != 0"],  # Division safety
            "description": "Edge case handling",
        },
        {
            "fixture": "arith_mixed_bitwidth.mlir",
            "constraints": ["b != 0"],  # Division safety
            "description": "Mixed bit-width operations",
        },
    ]

    for test_case in test_cases:
        fixture_name = test_case["fixture"]
        fixture_path = fixtures_dir / fixture_name

        if not fixture_path.exists():
            logger.warning(f"Fixture not found: {fixture_path}")
            continue

        logger.info(f"Generating tests for: {fixture_name}")

        for constraint in test_case["constraints"]:
            # Generate concrete values
            solutions = generator.generate_for_constraint(constraint, max_solutions=2)

            if not solutions:
                logger.warning(f"No solutions found for constraint: {constraint}")
                continue

            # Create DAP traces for each solution
            for i, solution in enumerate(solutions):
                test_name = f"arith_{fixture_name.replace('.mlir', '')}_{constraint.replace(' ', '_').replace('!=', 'neq')}_{i}"

                trace = generator.create_dap_trace(
                    program_path=str(fixture_path),
                    inputs=solution,
                    test_name=test_name,
                    constraint=constraint,
                )

                all_traces.append((test_name, trace))
                logger.info(f"  Generated: {test_name} with inputs {solution}")

    # Save all traces
    saved_files = []
    for test_name, trace in all_traces:
        output_file = output_dir / f"{test_name}.json"
        with open(output_file, "w") as f:
            json.dump(trace, f, indent=2)
        saved_files.append(str(output_file))

    # Create manifest
    # Collect all constraints used
    all_constraints = []
    for test_case in test_cases:
        all_constraints.extend(test_case["constraints"])

    manifest = {
        "generated_with_z3": True,
        "total_tests": len(saved_files),
        "test_files": [Path(f).name for f in saved_files],
        "constraints_used": list(set(all_constraints)),
        "note": "Generated with actual Z3 constraint solving per Issue #108",
    }

    manifest_path = output_dir / "z3_generated_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Generated {len(saved_files)} Z3-based test traces")
    logger.info(f"Manifest saved to: {manifest_path}")

    return saved_files


def main():
    """Main function."""
    logger.info("Starting Z3-based concrete value generation (Issue #108)...")

    try:
        saved_files = generate_arithmetic_tests_with_z3()

        if saved_files:
            logger.info("Successfully generated Z3-based test traces!")
            logger.info(f"Total files: {len(saved_files)}")

            # Show example of generated content
            if saved_files:
                with open(saved_files[0], "r") as f:
                    example = json.load(f)
                logger.info(f"Example trace has {len(example.get('session', []))} commands")
                logger.info(f"Concrete inputs: {example.get('concrete_inputs', {})}")

            return 0
        else:
            logger.error("No test traces were generated")
            return 1

    except Exception as e:
        logger.error(f"Failed to generate tests: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
