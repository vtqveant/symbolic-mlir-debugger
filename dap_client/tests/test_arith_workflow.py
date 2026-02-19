"""DAP-based workflow tests for arithmetic operations.

This module tests arithmetic operations through the DAP client interface,
ensuring the full workflow works from connection to execution.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest

from dap_client.core.client import DAPClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_mlir_file(content: str) -> str:
    """Create a temporary MLIR file with given content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
        f.write(content)
        return f.name


class TestArithmeticWorkflow:
    """Test arithmetic operations workflow via DAP client."""

    @pytest.fixture
    def simple_add_mlir(self):
        """Create a simple addition MLIR test file."""
        content = """// Simple addition test
module {
  func.func @add(%a: i32, %b: i32) -> i32 {
    %result = arith.addi %a, %b : i32
    return %result : i32
  }
}
"""
        path = create_test_mlir_file(content)
        yield path
        os.unlink(path)

    @pytest.fixture
    def arithmetic_ops_mlir(self):
        """Create MLIR file with multiple arithmetic operations."""
        content = """// Multiple arithmetic operations test
module {
  func.func @compute(%a: i32, %b: i32) -> i32 {
    %add = arith.addi %a, %b : i32
    %sub = arith.subi %a, %b : i32
    %mul = arith.muli %a, %b : i32
    %div = arith.divsi %a, %b : i32
    %result = arith.addi %add, %sub : i32
    %final = arith.subi %result, %div : i32
    return %final : i32
  }
}
"""
        path = create_test_mlir_file(content)
        yield path
        os.unlink(path)

    @pytest.fixture
    def edge_cases_mlir(self):
        """Create MLIR file with edge cases (zero, negative numbers)."""
        content = """// Edge cases test
module {
  func.func @edge_cases(%a: i32, %b: i32) -> i32 {
    // Test with zero
    %zero = arith.constant 0 : i32
    %add_zero = arith.addi %a, %zero : i32
    
    // Test with negative
    %neg_one = arith.constant -1 : i32
    %mul_neg = arith.muli %a, %neg_one : i32
    
    // Combined operation
    %result = arith.addi %add_zero, %mul_neg : i32
    return %result : i32
  }
}
"""
        path = create_test_mlir_file(content)
        yield path
        os.unlink(path)

    def test_simple_addition_workflow(self, simple_add_mlir):
        """Test simple addition workflow via DAP client."""
        logger.info("Testing simple addition workflow...")

        try:
            # Connect to DAP server
            with DAPClient() as client:
                logger.info("Connected to DAP server")

                # Initialize session
                result = client.initialize(
                    adapter_id="mlir-debugger", client_id="arith-test-client"
                )
                logger.info(f"Session initialized: {result}")

                # Launch program
                result = client.launch(program=simple_add_mlir, no_debug=False)
                logger.info(f"Program launched: {result}")

                # Set breakpoints (if needed)
                source = {"path": simple_add_mlir}
                breakpoints = [{"line": 4}]  # Line with arith.addi
                result = client.set_breakpoints(source=source, breakpoints=breakpoints)
                logger.info(f"Breakpoints set: {result}")

                # Configuration done
                result = client.configuration_done()
                logger.info(f"Configuration done: {result}")

                # Continue execution
                result = client.continue_execution(thread_id=1)
                logger.info(f"Execution continued: {result}")

                # Get threads
                result = client.get_threads()
                logger.info(f"Threads: {result}")

                # Disconnect
                result = client.disconnect()
                logger.info(f"Disconnected: {result}")

                # Test passed
                assert True

        except Exception as e:
            logger.error(f"Test failed: {e}")
            pytest.fail(f"Simple addition workflow test failed: {e}")

    def test_multiple_arithmetic_operations(self, arithmetic_ops_mlir):
        """Test workflow with multiple arithmetic operations."""
        logger.info("Testing multiple arithmetic operations workflow...")

        try:
            with DAPClient() as client:
                logger.info("Connected to DAP server")

                # Initialize session
                result = client.initialize(
                    adapter_id="mlir-debugger", client_id="arith-multi-test-client"
                )
                logger.info(f"Session initialized: {result}")

                # Launch program
                result = client.launch(program=arithmetic_ops_mlir, no_debug=False)
                logger.info(f"Program launched: {result}")

                # Set breakpoints at each arithmetic operation
                source = {"path": arithmetic_ops_mlir}
                breakpoints = [
                    {"line": 4},  # arith.addi
                    {"line": 5},  # arith.subi
                    {"line": 6},  # arith.muli
                    {"line": 7},  # arith.divsi
                    {"line": 8},  # arith.addi
                    {"line": 9},  # arith.subi
                ]
                result = client.set_breakpoints(source=source, breakpoints=breakpoints)
                logger.info(f"Breakpoints set: {result}")

                # Configuration done
                result = client.configuration_done()
                logger.info(f"Configuration done: {result}")

                # Continue execution through all breakpoints
                for i in range(len(breakpoints)):
                    result = client.continue_execution(thread_id=1)
                    logger.info(f"Execution continued (step {i+1}): {result}")

                    # Get stack trace to see current position
                    result = client.get_stacktrace(thread_id=1)
                    logger.info(f"Stack trace: {result}")

                # Disconnect
                result = client.disconnect()
                logger.info(f"Disconnected: {result}")

                # Test passed
                assert True

        except Exception as e:
            logger.error(f"Test failed: {e}")
            pytest.fail(f"Multiple arithmetic operations test failed: {e}")

    def test_edge_cases_workflow(self, edge_cases_mlir):
        """Test arithmetic operations with edge cases."""
        logger.info("Testing edge cases workflow...")

        try:
            with DAPClient() as client:
                logger.info("Connected to DAP server")

                # Initialize session
                result = client.initialize(
                    adapter_id="mlir-debugger", client_id="arith-edge-test-client"
                )
                logger.info(f"Session initialized: {result}")

                # Launch program
                result = client.launch(program=edge_cases_mlir, no_debug=False)
                logger.info(f"Program launched: {result}")

                # Set breakpoints
                source = {"path": edge_cases_mlir}
                breakpoints = [
                    {"line": 5},  # arith.addi with zero
                    {"line": 8},  # arith.muli with negative
                    {"line": 11},  # final arith.addi
                ]
                result = client.set_breakpoints(source=source, breakpoints=breakpoints)
                logger.info(f"Breakpoints set: {result}")

                # Configuration done
                result = client.configuration_done()
                logger.info(f"Configuration done: {result}")

                # Continue execution
                result = client.continue_execution(thread_id=1)
                logger.info(f"Execution continued: {result}")

                # Disconnect
                result = client.disconnect()
                logger.info(f"Disconnected: {result}")

                # Test passed
                assert True

        except Exception as e:
            logger.error(f"Test failed: {e}")
            pytest.fail(f"Edge cases workflow test failed: {e}")

    def test_symbolic_arithmetic_workflow(self, arithmetic_ops_mlir):
        """Test symbolic execution of arithmetic operations via DAP."""
        logger.info("Testing symbolic arithmetic workflow...")

        try:
            with DAPClient() as client:
                logger.info("Connected to DAP server")

                # Initialize session
                result = client.initialize(
                    adapter_id="mlir-debugger", client_id="arith-symbolic-test-client"
                )
                logger.info(f"Session initialized: {result}")

                # Launch program
                result = client.launch(program=arithmetic_ops_mlir, no_debug=False)
                logger.info(f"Program launched: {result}")

                # Set breakpoint
                source = {"path": arithmetic_ops_mlir}
                breakpoints = [{"line": 4}]  # First arithmetic operation
                result = client.set_breakpoints(source=source, breakpoints=breakpoints)
                logger.info(f"Breakpoints set: {result}")

                # Configuration done
                result = client.configuration_done()
                logger.info(f"Configuration done: {result}")

                # Continue to breakpoint
                result = client.continue_execution(thread_id=1)
                logger.info(f"Execution continued to breakpoint: {result}")

                # Enable symbolic mode
                result = client.symbolic_set_mode(enabled=True)
                logger.info(f"Symbolic mode enabled: {result}")

                # Evaluate symbolic expression
                result = client.symbolic_evaluate(expression="%a + %b", frame_id=0)
                logger.info(f"Symbolic evaluation result: {result}")

                # Explore execution paths
                result = client.symbolic_explore_paths(max_paths=5)
                logger.info(f"Path exploration result: {result}")

                # Get constraints
                result = client.symbolic_get_constraints()
                logger.info(f"Constraints: {result}")

                # Disable symbolic mode
                result = client.symbolic_set_mode(enabled=False)
                logger.info(f"Symbolic mode disabled: {result}")

                # Disconnect
                result = client.disconnect()
                logger.info(f"Disconnected: {result}")

                # Test passed
                assert True

        except Exception as e:
            logger.error(f"Test failed: {e}")
            pytest.fail(f"Symbolic arithmetic workflow test failed: {e}")


if __name__ == "__main__":
    # Run tests directly for debugging
    test = TestArithmeticWorkflow()

    # Create temporary MLIR files
    import tempfile

    # Test 1: Simple addition
    simple_add = """// Simple addition test
module {
  func.func @add(%a: i32, %b: i32) -> i32 {
    %result = arith.addi %a, %b : i32
    return %result : i32
  }
}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
        f.write(simple_add)
        simple_add_path = f.name

    try:
        print("Test 1: Simple addition workflow")
        test.test_simple_addition_workflow(simple_add_path)
        print("Test 1 passed!")
    except Exception as e:
        print(f"Test 1 failed: {e}")
    finally:
        os.unlink(simple_add_path)

    print("\nAll tests completed!")
