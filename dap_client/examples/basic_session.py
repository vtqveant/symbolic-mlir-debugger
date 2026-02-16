"""Basic usage example for DAP client"""

import logging
import sys

from core.client import DAPClient
from schema import load_test_script

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def basic_session_example():
    """Basic DAP client usage example"""
    print("DAP Client Basic Session Example")
    print("=" * 50)

    try:
        # Connect to DAP server
        print("\n1. Connecting to DAP server...")
        with DAPClient(host="localhost", port=5678) as client:
            print("   Connected successfully!")

            # Initialize session
            print("\n2. Initializing session...")
            result = client.initialize(
                adapter_id="mlir-debugger", client_id="automated-test-client"
            )
            print(f"   Initialized: {result}")

            # Launch program
            print("\n3. Launching MLIR program...")
            program = "examples/arithmetic.mlir"
            result = client.launch(program=program, no_debug=False)
            print(f"   Program launched: {result}")

            # Set breakpoints
            print("\n4. Setting breakpoints...")
            source = {"path": program}
            breakpoints = [{"line": 10}, {"line": 15}]
            result = client.set_breakpoints(source=source, breakpoints=breakpoints)
            print(f"   Breakpoints set: {result}")

            # Configuration done
            print("\n5. Configuration done...")
            result = client.configuration_done()
            print(f"   Configuration complete: {result}")

            # Continue execution
            print("\n6. Continuing execution...")
            result = client.continue_execution(thread_id=1)
            print(f"   Execution continued: {result}")

            print("\n7. Session completed successfully!")
            return True

    except Exception as e:
        print(f"\nError: {e}")
        logger.exception("Session failed")
        return False


def test_script_example():
    """Example using test script"""
    print("\nTest Script Example")
    print("=" * 50)

    try:
        # Load test script
        test_script_path = "dap_client/examples/test_script.json"
        test_script = load_test_script(test_script_path)
        print(f"Loaded test script: {test_script['name']}")

        # Execute test script
        with DAPClient(host="localhost", port=5678) as client:
            print("\nExecuting test script...")

            for step in test_script["session"]:
                command = step["command"]
                print(f"\n  Step: {command}")

                if command == "initialize":
                    result = client.initialize(**step["arguments"])
                elif command == "launch":
                    result = client.launch(**step["arguments"])
                elif command == "setBreakpoints":
                    result = client.set_breakpoints(**step["arguments"])
                elif command == "configurationDone":
                    result = client.configuration_done()
                elif command == "continue":
                    result = client.continue_execution(**step["arguments"])
                elif command == "disconnect":
                    result = client.disconnect()

                print(f"    Result: {result}")

        print("\nTest script executed successfully!")
        return True

    except Exception as e:
        print(f"\nError: {e}")
        logger.exception("Test script execution failed")
        return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="DAP Client Example")
    parser.add_argument("--test-script", action="store_true", help="Run test script example")
    args = parser.parse_args()

    if args.test_script:
        success = test_script_example()
    else:
        success = basic_session_example()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
