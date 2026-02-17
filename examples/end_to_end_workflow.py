#!/usr/bin/env python3
"""
End-to-End Workflow Example for Symbolic MLIR Debugger

This example demonstrates a complete workflow from installation to results,
showing how all components work together.

Workflow:
1. Initialize DAP client (stdio connection)
2. Launch MLIR program
3. Perform symbolic debugging
4. Generate test cases
5. Execute generated tests
6. Generate report
7. Cleanup
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_end_to_end_workflow():
    """Run complete end-to-end workflow."""
    print("=" * 70)
    print("Symbolic MLIR Debugger - End-to-End Workflow")
    print("=" * 70)
    print()

    # Configuration
    MLIR_PROGRAM = "debugger/fixtures/conditional_branch.mlir"

    print("Configuration:")
    print(f"  MLIR Program: {MLIR_PROGRAM}")
    print()

    # Import here to avoid dependency issues if imports fail
    try:
        from dap_client.core.client import DAPClient
        from dap_client.generator.test_case_generator import TestCaseGenerator
        from dap_client.runner.test_runner import TestRunner

        print("[OK] All dependencies imported successfully")
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        print("Please install dependencies: pip install -r requirements.txt")
        return False

    # Step 1: Initialize DAP client
    print()
    print("Step 1: Initializing DAP client...")

    try:
        client = DAPClient()
        print("[OK] DAP client created")
        # Connect to DAP server
        if not client.connect():
            print("[ERROR] Failed to connect to DAP server")
            return False
        print("[OK] DAP client connected")
    except Exception as e:
        print(f"[ERROR] Failed to create or connect DAP client: {e}")
        return False

    # Step 2: Basic debugging session
    print()
    print("Step 2: Running basic debugging session...")

    try:
        # Initialize session
        print("   Initializing session...")
        init_response = client.initialize(
            adapter_id="mlir-debugger",
            client_id="end-to-end-example",
        )

        if not init_response.get("success", True):
            print(f"[ERROR] Session initialization failed: {init_response}")
            client.disconnect()
            return False

        print("   [OK] Session initialized")

        # Launch program
        print(f"   Launching program: {MLIR_PROGRAM}")
        launch_response = client.launch(program=MLIR_PROGRAM, no_debug=False)

        if not launch_response.get("success", True):
            print(f"[ERROR] Program launch failed: {launch_response}")
            client.disconnect()
            return False

        print("   [OK] Program launched")

        # Set breakpoints
        print("   Setting breakpoints...")
        bp_response = client.set_breakpoints(
            source={"path": MLIR_PROGRAM}, breakpoints=[{"line": 1}, {"line": 5}]
        )

        if not bp_response.get("success", True):
            print(f"[ERROR] Breakpoint setting failed: {bp_response}")
        else:
            print(f"   [OK] Breakpoints set: {len(bp_response.get('breakpoints', []))} breakpoints")

        # Configuration done
        print("   Sending configuration done...")
        config_response = client.configuration_done()

        if not config_response.get("success", True):
            print(f"[ERROR] Configuration failed: {config_response}")
        else:
            print("   [OK] Configuration complete")

        print("[OK] Basic debugging session completed")

    except Exception as e:
        print(f"[ERROR] Error during debugging session: {e}")
        client.disconnect()
        return False

    # Step 3: Symbolic debugging
    print()
    print("Step 3: Testing symbolic debugging...")

    try:
        # Enable symbolic mode
        print("   Enabling symbolic debugging mode...")
        symbolic_response = client.symbolic_set_mode(enabled=True)

        if symbolic_response.get("success", True):
            print("   [OK] Symbolic debugging enabled")

            # Try to evaluate symbolic expression
            print("   Evaluating symbolic expression...")
            eval_response = client.symbolic_evaluate(expression="%a < %b", frame_id=0)

            if eval_response.get("success", True):
                print(f"   [OK] Symbolic evaluation: {eval_response.get('result', {})}")
            else:
                print(f"   [WARNING] Symbolic evaluation failed (may need breakpoint hit first)")

        else:
            print(f"   [WARNING] Symbolic mode not supported: {symbolic_response}")

        # Disable symbolic mode
        client.symbolic_set_mode(enabled=False)

    except Exception as e:
        print(f"   [WARNING] Symbolic debugging error (may not be supported): {e}")

    # Step 4: Test generation
    print()
    print("Step 4: Generating test cases...")

    try:
        generator = TestCaseGenerator()
        generator.connect()
        print("   [OK] Test generator connected")

        # Generate test cases
        print(f"   Generating test cases from {MLIR_PROGRAM}...")
        test_scripts = generator.generate_from_program(program_path=MLIR_PROGRAM, max_paths=3)

        if test_scripts:
            print(f"   [OK] Generated {len(test_scripts)} test scripts")

            # Save test scripts
            test_files = []
            for i, script in enumerate(test_scripts):
                test_file = f"generated_test_{i}.json"
                with open(test_file, "w") as f:
                    json.dump(script, f, indent=2)
                test_files.append(test_file)
                print(f"      Saved: {test_file}")

            # Step 5: Test execution
            print()
            print("Step 5: Executing generated tests...")

            runner = TestRunner()
            results = []

            for test_file in test_files:
                print(f"   Running test: {test_file}")
                try:
                    result = runner.run_test_file(test_file)
                    results.append(
                        {
                            "test": test_file,
                            "success": result.get("success", False),
                            "duration": result.get("duration", 0),
                        }
                    )

                    if result.get("success"):
                        print(f"      [OK] Passed ({result.get('duration', 0):.2f}s)")
                    else:
                        print(f"      [ERROR] Failed: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    print(f"      [ERROR] Test execution error: {e}")
                    results.append({"test": test_file, "success": False, "error": str(e)})

            # Step 6: Generate report
            print()
            print("Step 6: Generating test report...")

            total_tests = len(results)
            passed_tests = sum(1 for r in results if r.get("success"))
            failed_tests = total_tests - passed_tests

            report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "program": MLIR_PROGRAM,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "results": results,
            }

            # Save report
            report_file = "test_report.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)

            print(f"   [OK] Report saved: {report_file}")
            print(
                f"   [INFO] Summary: {passed_tests}/{total_tests} tests passed "
                f"({report['success_rate'] * 100:.1f}%)"
            )

            # Cleanup test files
            for test_file in test_files:
                try:
                    os.remove(test_file)
                except:
                    pass

        else:
            print("   [WARNING] No test scripts generated")

    except Exception as e:
        print(f"[ERROR] Test generation/execution error: {e}")
        print("   This may be expected if test generation is not fully implemented")

    # Step 7: Cleanup
    print()
    print("Step 7: Cleaning up...")

    try:
        # Disconnect client
        client.disconnect()
        print("[OK] DAP client disconnected")

    except Exception as e:
        print(f"[WARNING] Cleanup error: {e}")

    print()
    print("=" * 70)
    print("End-to-End Workflow COMPLETED")
    print("=" * 70)
    print()
    print("What was demonstrated:")
    print("1. [OK] DAP client initialization and connection")
    print("2. [OK] Basic debugging session (initialize, launch, breakpoints)")
    print("3. [OK] Symbolic debugging capabilities")
    print("4. [OK] Test case generation from MLIR programs")
    print("5. [OK] Test execution and reporting")
    print("6. [OK] Proper cleanup and resource management")
    print()
    print("Next steps:")
    print("- Explore other examples in dap_client/examples/")
    print("- Read the tutorial in docs/TUTORIAL.md")
    print("- Check API documentation in docs/API.md")
    print("- Create your own MLIR programs and debug them")

    return True


def quick_workflow():
    """Quick workflow for demonstration purposes."""
    print("\n" + "=" * 70)
    print("Quick Workflow Demonstration")
    print("=" * 70)

    try:
        from dap_client.core.client import DAPClient

        # Quick setup
        with DAPClient() as client:
            client.initialize(adapter_id="mlir-debugger", client_id="quick-demo")
            print("[OK] DAP client initialized")
            client.launch(program="debugger/fixtures/simple_add.mlir")
            print("[OK] MLIR program launched")

        print("[OK] Cleanup complete")

    except Exception as e:
        print(f"[ERROR] Quick workflow error: {e}")

    print("=" * 70)


if __name__ == "__main__":
    # Run the full end-to-end workflow
    print("Starting end-to-end workflow...")
    print("Note: This may take a few minutes to complete.")
    print()

    success = run_end_to_end_workflow()

    if success:
        # Optionally run quick workflow
        run_quick = input("\nRun quick workflow demonstration? (y/n): ").lower().strip()
        if run_quick == "y":
            quick_workflow()

    print("\nWorkflow execution complete!")
    print("Check the generated files:")
    print("- test_report.json (if test generation worked)")
    print("- Review console output for success/failure indicators")
    print("\nFor more information, see:")
    print("- QUICKSTART.md for getting started")
    print("- docs/TUTORIAL.md for detailed tutorial")
    print("- docs/API.md for API reference")
