#!/usr/bin/env python3
"""
Generate DAP test traces for arithmetic operations.

This script uses the existing test_case_generator and path_aware_generator
to create comprehensive test cases for arithmetic operations.
"""

import json
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import from dap_client
from dap_client.generator.path_aware_generator import PathAwareGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_arithmetic_tests():
    """Generate test cases for all arithmetic MLIR fixtures."""

    # Define the arithmetic test fixtures
    fixtures_dir = Path(__file__).parent.parent / "debugger" / "fixtures"
    output_dir = Path(__file__).parent.parent / "generated_tests"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # List of arithmetic test files to generate
    arith_fixtures = [
        "arith_basic_ops.mlir",
        "arith_conditional.mlir",
        "arith_edge_cases.mlir",
        "arith_mixed_bitwidth.mlir",
        "arithmetic_ops.mlir",  # Existing fixture
    ]

    all_test_scripts = []

    # Use path-aware generator for Z3-based constraint solving
    with PathAwareGenerator() as generator:
        for fixture_name in arith_fixtures:
            fixture_path = fixtures_dir / fixture_name

            if not fixture_path.exists():
                logger.warning(f"Fixture not found: {fixture_path}")
                continue

            logger.info(f"Generating tests for: {fixture_name}")

            try:
                # Generate test cases using path exploration
                test_scripts = generator.generate_from_program(
                    program_path=str(fixture_path),
                    max_paths=5,  # Explore up to 5 paths per fixture
                    test_name=f"arith_{fixture_name.replace('.mlir', '')}",
                )

                all_test_scripts.extend(test_scripts)
                logger.info(f"Generated {len(test_scripts)} test scripts for {fixture_name}")

            except Exception as e:
                logger.error(f"Failed to generate tests for {fixture_name}: {e}")

    # Save all generated test scripts
    if all_test_scripts:
        saved_files = generator.save_test_scripts(
            test_scripts=all_test_scripts, output_dir=str(output_dir)
        )

        logger.info(f"Saved {len(saved_files)} test script files")

        # Create a manifest file listing all generated tests
        manifest = {
            "generated_tests": [
                {
                    "file": Path(f).name,
                    "path": f,
                    "fixture": Path(f).stem.replace("arith_", "").replace("_path_", "_"),
                }
                for f in saved_files
            ],
            "total_tests": len(saved_files),
            "fixtures_processed": len(arith_fixtures),
        }

        manifest_path = output_dir / "arith_tests_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest saved to: {manifest_path}")

        return saved_files
    else:
        logger.warning("No test scripts were generated")
        return []


def generate_targeted_edge_cases():
    """Generate targeted test cases for edge conditions using Z3 solver."""

    fixtures_dir = Path(__file__).parent.parent / "debugger" / "fixtures"
    output_dir = Path(__file__).parent.parent / "generated_tests"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    with PathAwareGenerator() as generator:
        # Generate edge cases for arithmetic operations
        edge_case_tests = []

        # Test division by zero avoidance
        logger.info("Generating edge case: division by zero avoidance")
        try:
            division_tests = generator.generate_for_branch_condition(
                program_path=str(fixtures_dir / "arith_edge_cases.mlir"),
                condition_expr="b != 0",  # Avoid division by zero
                test_name="arith_division_safe",
                max_attempts=3,
            )
            edge_case_tests.extend(division_tests)
        except Exception as e:
            logger.error(f"Failed to generate division tests: {e}")

        # Test overflow conditions
        logger.info("Generating edge case: overflow conditions")
        try:
            # For the edge_cases fixture, we want inputs that don't cause overflow
            overflow_tests = generator.generate_edge_cases(
                program_path=str(fixtures_dir / "arith_edge_cases.mlir"),
                variable_ranges={"a": (-100, 100), "b": (-50, 50)},
                test_name="arith_no_overflow",
                num_cases=3,
            )
            edge_case_tests.extend(overflow_tests)
        except Exception as e:
            logger.error(f"Failed to generate overflow tests: {e}")

        # Save edge case tests
        if edge_case_tests:
            saved_files = generator.save_test_scripts(
                test_scripts=edge_case_tests, output_dir=str(output_dir)
            )
            logger.info(f"Saved {len(saved_files)} edge case test files")
            return saved_files

    return []


def main():
    """Main function to generate arithmetic tests."""
    logger.info("Starting arithmetic test generation...")

    # Generate general arithmetic tests
    general_tests = generate_arithmetic_tests()

    # Generate targeted edge case tests
    edge_tests = generate_targeted_edge_cases()

    total_tests = len(general_tests) + len(edge_tests)

    logger.info("Test generation complete!")
    logger.info(f"Total test files generated: {total_tests}")
    logger.info(f"- General tests: {len(general_tests)}")
    logger.info(f"- Edge case tests: {len(edge_tests)}")

    if total_tests == 0:
        logger.error("No tests were generated. Check the logs for errors.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
