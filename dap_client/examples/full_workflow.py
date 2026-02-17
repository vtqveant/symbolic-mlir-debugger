#!/usr/bin/env python3
"""
Full workflow demonstration for automated DAP client testing.

This script demonstrates the complete workflow:
1. Generate test cases from an MLIR program using symbolic execution
2. Save generated test scripts to JSON files
3. Execute the generated test scripts using the test runner
4. Generate a comprehensive test report

Requirements:
- DAP server script available (debugger/dap_server.py)
- MLIR program to test (default: conditional_branch.mlir)
"""

import sys
from pathlib import Path

# Add project root to Python path (two levels up from this file)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json  # noqa: E402
import logging  # noqa: E402

from dap_client.generator.test_case_generator import TestCaseGenerator  # noqa: E402
from dap_client.generator.path_aware_generator import PathAwareGenerator  # noqa: E402
from dap_client.runner.orchestrator import TestOrchestrator  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_test_cases(program_path: str, output_dir: str = "generated_tests") -> list:
    """Generate test cases from MLIR program.

    Args:
        program_path: Path to MLIR program
        output_dir: Directory to save generated test scripts

    Returns:
        List of paths to generated test scripts
    """
    print("=" * 60)
    print("Step 1: Generating test cases from program")
    print("=" * 60)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    test_script_paths = []

    # Use basic generator
    print(f"\nUsing basic test case generator for: {program_path}")
    generator = TestCaseGenerator()

    if not generator.connect():
        print("ERROR: Failed to connect to DAP server")
        print("Make sure the DAP server script is available (debugger/dap_server.py)")
        return []

    try:
        # Generate test scripts
        test_scripts = generator.generate_from_program(
            program_path=program_path, max_paths=5, test_name=Path(program_path).stem
        )

        # Save each test script
        for i, test_script in enumerate(test_scripts):
            output_file = output_path / f"test_{i:03d}_{Path(program_path).stem}.json"
            with open(output_file, "w") as f:
                json.dump(test_script, f, indent=2)

            test_script_paths.append(str(output_file))
            print(f"  Generated: {output_file.name}")

        print(f"\nGenerated {len(test_scripts)} test scripts")

        # Try path-aware generator if Z3 is available
        print("\nTrying path-aware generator (requires Z3)...")
        try:
            path_aware_generator = PathAwareGenerator()

            if path_aware_generator.connect():
                # Generate targeted test cases for first two paths
                targeted_scripts = path_aware_generator.generate_from_program(
                    program_path=program_path,
                    max_paths=2,  # Target first two paths
                    test_name=f"{Path(program_path).stem}_targeted",
                )

                for i, test_script in enumerate(targeted_scripts):
                    output_file = output_path / f"targeted_{i:03d}_{Path(program_path).stem}.json"
                    with open(output_file, "w") as f:
                        json.dump(test_script, f, indent=2)

                    test_script_paths.append(str(output_file))
                    print(f"  Generated (targeted): {output_file.name}")

                print(f"\nGenerated {len(targeted_scripts)} targeted test scripts")
        except ImportError:
            print("  Z3 not available, skipping path-aware generation")
        except Exception as e:
            print(f"  Path-aware generator failed: {e}")

    finally:
        generator.disconnect()

    return test_script_paths


def run_test_cases(test_script_paths: list, output_file: str = "test_report.json") -> dict:
    """Run test cases and generate report.

    Args:
        test_script_paths: List of paths to test scripts
        output_file: Path to save test report

    Returns:
        Test report dictionary
    """
    print("\n" + "=" * 60)
    print("Step 2: Running test cases")
    print("=" * 60)

    if not test_script_paths:
        print("No test scripts to run")
        return {}

    # Create orchestrator for parallel execution
    orchestrator = TestOrchestrator()

    # Run tests using orchestrator
    print(f"\nRunning {len(test_script_paths)} test scripts...")
    report = orchestrator.run_test_files(
        test_files=test_script_paths,
        parallel=True,
    )

    # Save report
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nTest report saved to: {output_file}")

    # Print summary
    print("\nTest Results Summary:")
    print("-" * 40)
    print(f"Total tests run: {report.get('total_tests', 0)}")
    print(f"Passed: {report.get('passed_tests', 0)}")
    print(f"Failed: {report.get('failed_tests', 0)}")
    success_rate = report.get("success_rate", 0) * 100
    print(f"Success rate: {success_rate:.1f}%")

    # Print detailed results
    print("\nDetailed Results:")
    print("-" * 40)
    for test_result in report.get("results", []):
        status = "✓ PASS" if test_result.get("success") else "✗ FAIL"
        print(f"{status}: {test_result.get('name', 'Unknown')}")
        if not test_result.get("success") and test_result.get("error"):
            print(f"     Error: {test_result.get('error')}")

    return report


def generate_memory_model_tests(program_path: str, output_dir: str = "generated_tests") -> list:
    """Generate memory model test cases.

    Args:
        program_path: Path to MLIR program with memory operations
        output_dir: Directory to save generated test scripts

    Returns:
        List of paths to generated test scripts
    """
    print("\n" + "=" * 60)
    print("Step 3: Generating memory model test cases")
    print("=" * 60)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    test_script_paths = []

    # Use path-aware generator for memory tests
    try:
        generator = PathAwareGenerator()

        if not generator.connect():
            print("Failed to connect to DAP server for memory tests")
            return []

        try:
            # Generate memory model tests
            memory_tests = generator.generate_memory_model_tests(
                program_path=program_path, test_name=f"{Path(program_path).stem}_memory"
            )

            # Save each test script
            for i, test_script in enumerate(memory_tests):
                output_file = output_path / f"memory_{i:03d}_{Path(program_path).stem}.json"
                with open(output_file, "w") as f:
                    json.dump(test_script, f, indent=2)

                test_script_paths.append(str(output_file))
                print(f"  Generated (memory): {output_file.name}")

            print(f"\nGenerated {len(memory_tests)} memory model test scripts")

        finally:
            generator.disconnect()

    except ImportError:
        print("Z3 not available, skipping memory model test generation")
    except Exception as e:
        print(f"Memory model test generation failed: {e}")

    return test_script_paths


def main():
    """Main entry point for full workflow demonstration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Full workflow demonstration for automated DAP client testing"
    )
    parser.add_argument(
        "--program",
        default="../debugger/fixtures/conditional_branch.mlir",
        help="Path to MLIR program to test",
    )
    parser.add_argument(
        "--memory-program",
        default="../debugger/fixtures/memref_basic.mlir",
        help="Path to MLIR program with memory operations for memory model tests",
    )
    parser.add_argument(
        "--output-dir",
        default="generated_tests",
        help="Directory to save generated test scripts",
    )
    parser.add_argument(
        "--report-file", default="test_report.json", help="Path to save test report"
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip test generation, only run existing tests",
    )
    parser.add_argument(
        "--skip-memory", action="store_true", help="Skip memory model test generation"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Automated DAP Client Testing - Full Workflow Demonstration")
    print("=" * 60)

    test_script_paths = []

    # Step 1: Generate test cases
    if not args.skip_generation:
        # Generate regular test cases
        regular_tests = generate_test_cases(args.program, args.output_dir)
        test_script_paths.extend(regular_tests)

        # Generate memory model tests
        if not args.skip_memory and Path(args.memory_program).exists():
            memory_tests = generate_memory_model_tests(args.memory_program, args.output_dir)
            test_script_paths.extend(memory_tests)
        elif not args.skip_memory:
            print(f"\nMemory program not found: {args.memory_program}")
            print("Skipping memory model test generation")

    # If no test scripts were generated but output dir exists, use existing tests
    if not test_script_paths:
        output_path = Path(args.output_dir)
        if output_path.exists():
            test_script_paths = [str(p) for p in output_path.glob("*.json")]
            print(f"\nFound {len(test_script_paths)} existing test scripts in {args.output_dir}")

    # Step 2: Run test cases
    if test_script_paths:
        report = run_test_cases(test_script_paths, args.report_file)

        # Check overall success
        if report.get("failed", 0) == 0:
            print("\n" + "=" * 60)
            print("✓ All tests passed successfully!")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print(f"✗ {report.get('failed', 0)} test(s) failed")
            print("=" * 60)
            return 1
    else:
        print("\nNo test scripts to run. Exiting.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
