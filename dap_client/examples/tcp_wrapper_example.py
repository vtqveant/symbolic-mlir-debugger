#!/usr/bin/env python3
"""
Example demonstrating the use of TCP wrapper with DAP client.

This example shows:
1. Starting the TCP wrapper
2. Connecting with DAP client
3. Running a full debug session
4. Clean shutdown

Before running this script:
  1. Ensure you have an MLIR program to test (e.g., conditional_branch.mlir)
  2. Start the TCP wrapper in a separate terminal

Usage:
  # Terminal 1: Start the wrapper
  python integration/server.py --port 5678

  # Terminal 2: Run this example
  python examples/tcp_wrapper_example.py
"""

import sys
from pathlib import Path

# Add project root to Python path (three levels up from this file)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import argparse
import logging
import time

from dap_client.core.client import DAPClient
from dap_client.integration.server import DAPServerWrapper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class DAPExample:
    """Example class showing DAP client usage with TCP wrapper."""

    def __init__(self, host: str = "localhost", port: int = 5678):
        self.host = host
        self.port = port
        self.wrapper = None
        self.client = None
        self.fixture_path = None

    def find_fixture(self) -> bool:
        """Find a suitable MLIR fixture file."""
        # Try to find fixture in common locations
        possible_paths = [
            Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "simple_add.mlir",
            Path(__file__).parent.parent.parent
            / "debugger"
            / "fixtures"
            / "conditional_branch.mlir",
            Path(__file__).parent.parent.parent / "debugger" / "fixtures" / "basic.mlir",
        ]

        for path in possible_paths:
            if path.exists():
                self.fixture_path = path
                logger.info(f"Using fixture: {path}")
                return True

        logger.error(f"No fixture found. Tried: {possible_paths}")
        logger.info("Create an MLIR file in debugger/fixtures/ to test with.")
        return False

    def start_wrapper(self) -> bool:
        """Start the TCP wrapper."""
        logger.info(f"Starting TCP wrapper on {self.host}:{self.port}")

        self.wrapper = DAPServerWrapper(host=self.host, port=self.port)

        if not self.wrapper.start():
            logger.error("Failed to start DAP server wrapper")
            return False

        # Wait a moment for wrapper to initialize
        time.sleep(0.5)

        if not self.wrapper.is_alive():
            logger.error("DAP server wrapper is not running")
            return False

        logger.info(f"✓ TCP wrapper started (PID: {self.wrapper.process.pid})")
        return True

    def connect_client(self) -> bool:
        """Connect to the DAP client."""
        logger.info(f"Connecting DAP client to {self.host}:{self.port}")

        self.client = DAPClient(host=self.host, port=self.port)

        if not self.client.connect():
            logger.error("Failed to connect DAP client")
            return False

        logger.info("✓ DAP client connected")
        return True

    def initialize_session(self) -> bool:
        """Initialize a DAP session."""
        logger.info("Initializing DAP session")

        result = self.client.initialize(
            adapter_id="mlir-debugger",
            client_id="tcp-wrapper-example",
        )

        if not result:
            logger.error("Failed to initialize DAP session")
            return False

        # Check if initialize request succeeded
        # The result dictionary contains server capabilities
        logger.info("✓ DAP session initialized")
        return True

    def run_full_session(self) -> bool:
        """Run a full debug session."""
        if not self.fixture_path:
            logger.warning("No fixture found, skipping full session")
            return True

        logger.info("Running full debug session")

        # Step 1: Launch program
        logger.info("  Step 1: Launching program...")
        launch_result = self.client.launch(
            program=str(self.fixture_path),
            no_debug=False,
            args=["a=5", "b=3"],
        )

        if not launch_result:
            logger.error("Failed to launch program")
            return False

        logger.info("✓ Program launched")

        # Step 2: Set breakpoints
        logger.info("  Step 2: Setting breakpoints...")
        bp_result = self.client.set_breakpoints(
            source={"path": str(self.fixture_path)},
            breakpoints=[{"line": 10}],
        )

        if not bp_result:
            logger.error("Failed to set breakpoints")
            return False

        if "breakpoints" in bp_result:
            logger.info(f"✓ Breakpoints set: {len(bp_result['breakpoints'])}")

        # Step 3: Configuration done
        logger.info("  Step 3: Configuration done...")
        config_result = self.client.configuration_done()

        if not config_result:
            logger.error("Failed to complete configuration")
            return False

        logger.info("✓ Configuration complete")

        # Step 4: Continue execution (should hit breakpoint)
        logger.info("  Step 4: Continuing execution...")
        continue_result = self.client.continue_execution(thread_id=1)

        if not continue_result:
            logger.error("Failed to continue execution")
            return False

        logger.info("✓ Execution continued")

        # Step 5: Get stack trace
        logger.info("  Step 5: Getting stack trace...")
        stack_result = self.client.get_stack_trace(thread_id=1)

        if stack_result and "stackFrames" in stack_result:
            logger.info(f"✓ Stack trace retrieved ({len(stack_result['stackFrames'])} frames)")
            for i, frame in enumerate(stack_result["stackFrames"]):
                logger.info(
                    f"    Frame {i + 1}: {frame.get('name', 'unknown')} (line {frame.get('line', 0)})"
                )

        # Step 6: Get variables
        logger.info("  Step 6: Getting variables...")
        vars_result = self.client.get_variables(frame_id=0)

        if vars_result and "variables" in vars_result:
            logger.info(f"✓ Variables retrieved ({len(vars_result['variables'])} vars)")
            # Limit display to first 5
            for var in vars_result["variables"][:5]:
                logger.info(f"    {var.get('name', 'unknown')}: {var.get('value', '?')}")

        # Step 7: Disconnect
        logger.info("  Step 7: Disconnecting...")
        self.client.disconnect()

        logger.info("✓ Debug session completed successfully")
        return True

    def run_symbolic_session(self) -> bool:
        """Run a symbolic debugging session."""
        if not self.fixture_path:
            logger.warning("No fixture found, skipping symbolic session")
            return True

        logger.info("Running symbolic debugging session")

        # Step 1: Initialize
        if not self.initialize_session():
            logger.error("Failed to initialize session")
            return False

        # Step 2: Launch program
        logger.info("  Step 1: Launching program...")
        launch_result = self.client.launch(
            program=str(self.fixture_path),
            no_debug=False,
            args=["arg0=5"],
        )

        if not launch_result:
            logger.error("Failed to launch program")
            return False

        logger.info("✓ Program launched")

        # Step 3: Enable symbolic mode
        logger.info("  Step 2: Enabling symbolic debugging mode...")
        result = self.client.symbolic_set_mode(enabled=True)

        if not result:
            logger.error("Failed to enable symbolic mode")
            return False

        if result.get("symbolicMode"):
            logger.info("✓ Symbolic mode enabled")
        else:
            logger.warning("Symbolic mode not supported by server")

        # Step 4: Evaluate expression
        logger.info("  Step 3: Evaluating symbolic expression...")
        eval_result = self.client.symbolic_evaluate(
            expression="%arg0 > 0",
            frame_id=0,
        )

        if eval_result:
            logger.info(f"✓ Expression evaluated: {eval_result.get('result', 'N/A')}")

        # Step 5: Explore paths
        logger.info("  Step 4: Exploring execution paths...")
        paths_result = self.client.symbolic_explore_paths(
            max_paths=10,
            frame_id=0,
        )

        if paths_result:
            paths = paths_result.get("paths", [])
            logger.info(f"✓ Path exploration completed: {len(paths)} paths found")

        # Step 6: Get constraints
        logger.info("  Step 5: Getting path constraints...")
        constraints_result = self.client.symbolic_get_constraints()

        if constraints_result:
            constraints = constraints_result.get("constraints", [])
            logger.info(f"✓ Constraints retrieved: {len(constraints)} constraints")

        # Step 7: Disable symbolic mode
        logger.info("  Step 6: Disabling symbolic mode...")
        result = self.client.symbolic_set_mode(enabled=False)

        if result:
            logger.info("✓ Symbolic mode disabled")

        # Step 8: Disconnect
        logger.info("  Step 7: Disconnecting...")
        self.client.disconnect()

        logger.info("✓ Symbolic session completed successfully")
        return True

    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")

        # Disconnect client if connected
        if self.client and self.client.connected:
            self.client.disconnect()

        # Stop wrapper if running
        if self.wrapper and self.wrapper.is_alive():
            logger.info("Stopping TCP wrapper...")
            self.wrapper.stop()

        logger.info("Cleanup complete")

    def run(self, use_symbolic: bool = False) -> bool:
        """Run the example.

        Args:
            use_symbolic: If True, run symbolic debugging session

        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Start wrapper
            if not self.start_wrapper():
                return False

            # Step 2: Connect client
            if not self.connect_client():
                return False

            # Step 3: Find fixture
            if not self.find_fixture():
                logger.warning("No fixture found, running minimal session")
                # Still try to initialize and disconnect
                self.initialize_session()
                self.client.disconnect()
                return True

            # Step 4: Run session
            if use_symbolic:
                return self.run_symbolic_session()
            else:
                return self.run_full_session()

        except Exception as e:
            logger.error(f"Error in example: {e}", exc_info=True)
            return False
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Example demonstrating DAP client usage with TCP wrapper"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="TCP wrapper host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5678,
        help="TCP wrapper port (default: 5678)",
    )
    parser.add_argument(
        "--symbolic",
        action="store_true",
        help="Run symbolic debugging session",
    )
    parser.add_argument(
        "--fixture",
        help="Path to MLIR fixture file",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("DAP Client Example with TCP Wrapper")
    print("=" * 70)
    print(f"Connecting to wrapper at {args.host}:{args.port}")
    print("=" * 70)

    example = DAPExample(host=args.host, port=args.port)
    example.fixture_path = Path(args.fixture) if args.fixture else None

    success = example.run(use_symbolic=args.symbolic)

    print("=" * 70)
    if success:
        print("✓ Example completed successfully")
        print("=" * 70)
        return 0
    else:
        print("✗ Example failed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
