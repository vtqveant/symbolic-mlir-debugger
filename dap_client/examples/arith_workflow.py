"""Example of arithmetic workflow testing via DAP client.

This script demonstrates how to use the DAP client to test
arithmetic operations through the DAP protocol.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dap_client.core.client import DAPClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_mlir_content(operation_type: str) -> str:
    """Create MLIR content for different arithmetic operations."""
    operations = {
        "add": "arith.addi %a, %b : i32",
        "sub": "arith.subi %a, %b : i32",
        "mul": "arith.muli %a, %b : i32",
        "div": "arith.divsi %a, %b : i32",
        "rem": "arith.remsi %a, %b : i32",
        "cmp": "arith.cmpi slt, %a, %b : i32",
    }

    op = operations.get(operation_type, "arith.addi %a, %b : i32")

    return f"""// {operation_type.upper()} operation test
module {{
  func.func @{operation_type}_test(%a: i32, %b: i32) -> i32 {{
    %result = {op}
    return %result : i32
  }}
}}
"""


def test_single_operation(operation_type: str):
    """Test a single arithmetic operation via DAP."""
    print(f"\n{'='*60}")
    print(f"Testing {operation_type.upper()} operation")
    print(f"{'='*60}")

    # Create temporary MLIR file
    content = create_mlir_content(operation_type)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
        f.write(content)
        mlir_path = f.name

    try:
        # Connect to DAP server
        print(f"\n1. Connecting to DAP server...")
        with DAPClient() as client:
            print("   Connected successfully!")

            # Initialize session
            print(f"\n2. Initializing session...")
            result = client.initialize(
                adapter_id="mlir-debugger", client_id=f"{operation_type}-test-client"
            )
            print(f"   Initialized: {result}")

            # Launch program
            print(f"\n3. Launching MLIR program...")
            result = client.launch(program=mlir_path, no_debug=False)
            print(f"   Program launched: {result}")

            # Set breakpoint
            print(f"\n4. Setting breakpoint...")
            source = {"path": mlir_path}
            breakpoints = [{"line": 4}]  # Operation line
            result = client.set_breakpoints(source=source, breakpoints=breakpoints)
            print(f"   Breakpoints set: {result}")

            # Configuration done
            print(f"\n5. Configuration done...")
            result = client.configuration_done()
            print(f"   Configuration complete: {result}")

            # Continue execution
            print(f"\n6. Continuing execution...")
            result = client.continue_execution(thread_id=1)
            print(f"   Execution continued: {result}")

            # Get stack trace
            print(f"\n7. Getting stack trace...")
            result = client.get_stacktrace(thread_id=1)
            print(f"   Stack trace: {result}")

            # Get variables
            print(f"\n8. Getting variables...")
            if result and "stackFrames" in result:
                frame_id = result["stackFrames"][0]["id"]
                scopes_result = client.get_scopes(frame_id)
                if scopes_result and "scopes" in scopes_result:
                    for scope in scopes_result["scopes"]:
                        vars_result = client.get_variables(scope["variablesReference"])
                        print(f"   Variables in scope: {vars_result}")

            print(f"\n9. {operation_type.upper()} operation test completed successfully!")
            return True

    except Exception as e:
        print(f"\nError during {operation_type} test: {e}")
        logger.exception("Test failed")
        return False

    finally:
        # Clean up temporary file
        os.unlink(mlir_path)


def test_complex_arithmetic():
    """Test complex arithmetic expression with multiple operations."""
    print(f"\n{'='*60}")
    print("Testing complex arithmetic expression")
    print(f"{'='*60}")

    content = """// Complex arithmetic expression test
module {
  func.func @complex_expr(%a: i32, %b: i32, %c: i32) -> i32 {
    %add = arith.addi %a, %b : i32
    %sub = arith.subi %b, %c : i32
    %mul = arith.muli %add, %sub : i32
    %div = arith.divsi %mul, %a : i32
    %result = arith.addi %div, %c : i32
    return %result : i32
  }
}
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
        f.write(content)
        mlir_path = f.name

    try:
        print(f"\n1. Connecting to DAP server...")
        with DAPClient() as client:
            print("   Connected successfully!")

            print(f"\n2. Initializing session...")
            result = client.initialize(
                adapter_id="mlir-debugger", client_id="complex-arith-test-client"
            )
            print(f"   Initialized: {result}")

            print(f"\n3. Launching MLIR program...")
            result = client.launch(program=mlir_path, no_debug=False)
            print(f"   Program launched: {result}")

            # Set breakpoints at each operation
            print(f"\n4. Setting breakpoints...")
            source = {"path": mlir_path}
            breakpoints = [
                {"line": 4},  # arith.addi
                {"line": 5},  # arith.subi
                {"line": 6},  # arith.muli
                {"line": 7},  # arith.divsi
                {"line": 8},  # final arith.addi
            ]
            result = client.set_breakpoints(source=source, breakpoints=breakpoints)
            print(f"   Breakpoints set: {result}")

            print(f"\n5. Configuration done...")
            result = client.configuration_done()
            print(f"   Configuration complete: {result}")

            # Step through each operation
            print(f"\n6. Stepping through operations...")
            for i in range(len(breakpoints)):
                result = client.continue_execution(thread_id=1)
                print(f"   Step {i+1}: Execution continued to breakpoint {i+1}")

                # Get current stack frame
                stack_result = client.get_stacktrace(thread_id=1)
                if stack_result and "stackFrames" in stack_result:
                    frame = stack_result["stackFrames"][0]
                    print(f"     Current operation: line {frame.get('line', 'N/A')}")

            print(f"\n7. Complex arithmetic test completed successfully!")
            return True

    except Exception as e:
        print(f"\nError during complex arithmetic test: {e}")
        logger.exception("Test failed")
        return False

    finally:
        os.unlink(mlir_path)


def test_symbolic_arithmetic():
    """Test symbolic execution of arithmetic operations."""
    print(f"\n{'='*60}")
    print("Testing symbolic arithmetic execution")
    print(f"{'='*60}")

    content = """// Symbolic arithmetic test
module {
  func.func @symbolic_test(%a: i32, %b: i32) -> i32 {
    %cmp = arith.cmpi slt, %a, %b : i32
    %select = arith.select %cmp, %a, %b : i32
    %result = arith.addi %select, %a : i32
    return %result : i32
  }
}
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
        f.write(content)
        mlir_path = f.name

    try:
        print(f"\n1. Connecting to DAP server...")
        with DAPClient() as client:
            print("   Connected successfully!")

            print(f"\n2. Initializing session...")
            result = client.initialize(
                adapter_id="mlir-debugger", client_id="symbolic-arith-test-client"
            )
            print(f"   Initialized: {result}")

            print(f"\n3. Launching MLIR program...")
            result = client.launch(program=mlir_path, no_debug=False)
            print(f"   Program launched: {result}")

            # Set breakpoint
            print(f"\n4. Setting breakpoint...")
            source = {"path": mlir_path}
            breakpoints = [{"line": 4}]  # First operation
            result = client.set_breakpoints(source=source, breakpoints=breakpoints)
            print(f"   Breakpoints set: {result}")

            print(f"\n5. Configuration done...")
            result = client.configuration_done()
            print(f"   Configuration complete: {result}")

            # Continue to breakpoint
            print(f"\n6. Continuing to breakpoint...")
            result = client.continue_execution(thread_id=1)
            print(f"   Execution continued: {result}")

            # Enable symbolic mode
            print(f"\n7. Enabling symbolic mode...")
            result = client.symbolic_set_mode(enabled=True)
            print(f"   Symbolic mode enabled: {result}")

            # Evaluate symbolic expression
            print(f"\n8. Evaluating symbolic expression...")
            result = client.symbolic_evaluate(expression="%a < %b", frame_id=0)
            print(f"   Symbolic evaluation: {result}")

            # Explore paths
            print(f"\n9. Exploring execution paths...")
            result = client.symbolic_explore_paths(max_paths=3)
            print(f"   Path exploration: Found {len(result.get('paths', []))} paths")

            # Get constraints
            print(f"\n10. Getting constraints...")
            result = client.symbolic_get_constraints()
            print(f"   Constraints: {result}")

            print(f"\n11. Symbolic arithmetic test completed successfully!")
            return True

    except Exception as e:
        print(f"\nError during symbolic arithmetic test: {e}")
        logger.exception("Test failed")
        return False

    finally:
        os.unlink(mlir_path)


def run_concolic_test():
    """Run concolic testing with parameter variation."""
    print(f"\n{'='*60}")
    print("Running concolic testing with parameter variation")
    print(f"{'='*60}")

    content = """// Concolic arithmetic test
module {
  func.func @concolic_test(%a: i32, %b: i32) -> i32 {
    %cmp = arith.cmpi sgt, %a, %b : i32
    %select = arith.select %cmp, %a, %b : i32
    %result = arith.muli %select, %a : i32
    return %result : i32
  }
}
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
        f.write(content)
        mlir_path = f.name

    try:
        # Test with different concrete inputs
        test_cases = [
            {"a": 5, "b": 3},
            {"a": 2, "b": 8},
            {"a": 0, "b": 0},
            {"a": -5, "b": 3},
            {"a": 10, "b": 10},
        ]

        all_passed = True

        for i, inputs in enumerate(test_cases):
            print(f"\nTest case {i+1}: a={inputs['a']}, b={inputs['b']}")

            try:
                with DAPClient() as client:
                    # Initialize
                    client.initialize(adapter_id="mlir-debugger", client_id=f"concolic-test-{i}")

                    # Launch with concrete inputs
                    client.launch(program=mlir_path, no_debug=False, **inputs)

                    # Set breakpoint
                    source = {"path": mlir_path}
                    client.set_breakpoints(source=source, breakpoints=[{"line": 4}])

                    client.configuration_done()

                    # Continue execution
                    result = client.continue_execution(thread_id=1)
                    print(f"  Execution result: {result}")

                    # Enable symbolic mode for path exploration
                    client.symbolic_set_mode(enabled=True)

                    # Explore paths
                    paths_result = client.symbolic_explore_paths(max_paths=2)
                    paths = paths_result.get("paths", [])
                    print(f"  Found {len(paths)} execution paths")

                    # Track execution paths
                    for j, path in enumerate(paths):
                        print(f"    Path {j+1}: {path.get('description', 'Unknown')}")

                    client.disconnect()

            except Exception as e:
                print(f"  Test case {i+1} failed: {e}")
                all_passed = False

        if all_passed:
            print(f"\nAll concolic test cases passed!")
        else:
            print(f"\nSome concolic test cases failed")

        return all_passed

    finally:
        os.unlink(mlir_path)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Arithmetic workflow testing via DAP client")
    parser.add_argument(
        "--operation",
        choices=["add", "sub", "mul", "div", "rem", "cmp"],
        help="Test specific arithmetic operation",
    )
    parser.add_argument("--complex", action="store_true", help="Test complex arithmetic expression")
    parser.add_argument(
        "--symbolic", action="store_true", help="Test symbolic arithmetic execution"
    )
    parser.add_argument(
        "--concolic", action="store_true", help="Run concolic testing with parameter variation"
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    results = []

    if args.operation:
        results.append(test_single_operation(args.operation))

    if args.complex or args.all:
        results.append(test_complex_arithmetic())

    if args.symbolic or args.all:
        results.append(test_symbolic_arithmetic())

    if args.concolic or args.all:
        results.append(run_concolic_test())

    # If no specific test selected, run a default set
    if not any([args.operation, args.complex, args.symbolic, args.concolic, args.all]):
        print("Running default test suite...")
        results.append(test_single_operation("add"))
        results.append(test_complex_arithmetic())
        results.append(test_symbolic_arithmetic())

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("All tests passed successfully!")
        return 0
    else:
        print(f"{total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
