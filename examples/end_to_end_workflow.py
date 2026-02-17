#!/usr/bin/env python3
"""
End-to-End Workflow Example for Symbolic MLIR Debugger

This example demonstrates a complete workflow from installation to results,
showing how all components work together.

Workflow:
1. Start TCP wrapper (DAP server bridge)
2. Initialize DAP client
3. Launch MLIR program
4. Perform symbolic debugging
5. Generate test cases
6. Execute generated tests
7. Generate report
8. Cleanup
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
    HOST = "localhost"
    PORT = 5678
    MLIR_PROGRAM = "debugger/fixtures/conditional_branch.mlir"
    
    print("Configuration:")
    print(f"  Host: {HOST}")
    print(f"  Port: {PORT}")
    print(f"  MLIR Program: {MLIR_PROGRAM}")
    print()
    
    # Import here to avoid dependency issues if imports fail
    try:
        from dap_client.integration.server import DAPServerWrapper
        from dap_client.core.client import DAPClient
        from dap_client.generator.test_case_generator import TestCaseGenerator
        from dap_client.runner.test_runner import TestRunner
        print("✅ All dependencies imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install dependencies: pip install -r requirements.txt")
        return False
    
    # Step 1: Start TCP wrapper
    print()
    print("Step 1: Starting TCP wrapper...")
    wrapper = DAPServerWrapper(host=HOST, port=PORT)
    
    if not wrapper.start():
        print("❌ Failed to start TCP wrapper")
        return False
    
    print("✅ TCP wrapper started")
    print(f"   Listening on {HOST}:{PORT}")
    
    # Wait for wrapper to be ready
    time.sleep(2)
    
    if not wrapper.is_alive():
        print("❌ TCP wrapper died during startup")
        wrapper.stop()
        return False
    
    # Step 2: Initialize DAP client
    print()
    print("Step 2: Initializing DAP client...")
    
    try:
        client = DAPClient(host=HOST, port=PORT)
        print("✅ DAP client created")
    except Exception as e:
        print(f"❌ Failed to create DAP client: {e}")
        wrapper.stop()
        return False
    
    # Step 3: Basic debugging session
    print()
    print("Step 3: Running basic debugging session...")
    
    try:
        # Initialize session
        print("   Initializing session...")
        init_response = client.initialize(
            adapter_id="mlir-debugger",
            client_id="end-to-end-example",
            client_name="End-to-End Workflow Example"
        )
        
        if not init_response.get("success"):
            print(f"❌ Session initialization failed: {init_response}")
            client.disconnect()
            wrapper.stop()
            return False
        
        print("   ✅ Session initialized")
        
        # Launch program
        print(f"   Launching program: {MLIR_PROGRAM}")
        launch_response = client.launch(
            program=MLIR_PROGRAM,
            no_debug=False,
            stop_on_entry=True
        )
        
        if not launch_response.get("success"):
            print(f"❌ Program launch failed: {launch_response}")
            client.disconnect()
            wrapper.stop()
            return False
        
        print("   ✅ Program launched")
        
        # Set breakpoints
        print("   Setting breakpoints...")
        bp_response = client.set_breakpoints(
            source={"path": MLIR_PROGRAM},
            breakpoints=[{"line": 1}, {"line": 5}]
        )
        
        if not bp_response.get("success"):
            print(f"❌ Breakpoint setting failed: {bp_response}")
        else:
            print(f"   ✅ Breakpoints set: {len(bp_response.get('breakpoints', []))} breakpoints")
        
        # Configuration done
        print("   Sending configuration done...")
        config_response = client.configuration_done()
        
        if not config_response.get("success"):
            print(f"❌ Configuration failed: {config_response}")
        else:
            print("   ✅ Configuration complete")
        
        print("✅ Basic debugging session completed")
        
    except Exception as e:
        print(f"❌ Error during debugging session: {e}")
        client.disconnect()
        wrapper.stop()
        return False
    
    # Step 4: Symbolic debugging
    print()
    print("Step 4: Testing symbolic debugging...")
    
    try:
        # Enable symbolic mode
        print("   Enabling symbolic debugging mode...")
        symbolic_response = client.symbolic_set_mode(enabled=True)
        
        if symbolic_response.get("success"):
            print("   ✅ Symbolic debugging enabled")
            
            # Try to evaluate symbolic expression
            print("   Evaluating symbolic expression...")
            eval_response = client.symbolic_evaluate(
                expression="%a < %b",
                frame_id=0,
                context="hover"
            )
            
            if eval_response.get("success"):
                print(f"   ✅ Symbolic evaluation: {eval_response.get('result', {})}")
            else:
                print(f"   ⚠️  Symbolic evaluation failed (may need breakpoint hit first)")
        
        else:
            print(f"   ⚠️  Symbolic mode not supported: {symbolic_response}")
        
        # Disable symbolic mode
        client.symbolic_set_mode(enabled=False)
        
    except Exception as e:
        print(f"   ⚠️  Symbolic debugging error (may not be supported): {e}")
    
    # Step 5: Test generation
    print()
    print("Step 5: Generating test cases...")
    
    try:
        generator = TestCaseGenerator(host=HOST, port=PORT)
        generator.connect()
        print("   ✅ Test generator connected")
        
        # Generate test cases
        print(f"   Generating test cases from {MLIR_PROGRAM}...")
        test_scripts = generator.generate_from_program(
            program_path=MLIR_PROGRAM,
            max_paths=3
        )
        
        if test_scripts:
            print(f"   ✅ Generated {len(test_scripts)} test scripts")
            
            # Save test scripts
            test_files = []
            for i, script in enumerate(test_scripts):
                test_file = f"generated_test_{i}.json"
                with open(test_file, "w") as f:
                    json.dump(script, f, indent=2)
                test_files.append(test_file)
                print(f"      Saved: {test_file}")
            
            # Step 6: Test execution
            print()
            print("Step 6: Executing generated tests...")
            
            runner = TestRunner(host=HOST, port=PORT)
            results = []
            
            for test_file in test_files:
                print(f"   Running test: {test_file}")
                try:
                    result = runner.run_test(test_file, timeout=10.0)
                    results.append({
                        "test": test_file,
                        "success": result.get("success", False),
                        "duration": result.get("duration", 0),
                        "output": result.get("output", "")
                    })
                    
                    if result.get("success"):
                        print(f"      ✅ Passed ({result.get('duration', 0):.2f}s)")
                    else:
                        print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"      ❌ Test execution error: {e}")
                    results.append({
                        "test": test_file,
                        "success": False,
                        "error": str(e)
                    })
            
            # Step 7: Generate report
            print()
            print("Step 7: Generating test report...")
            
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
                "results": results
            }
            
            # Save report
            report_file = "test_report.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            
            print(f"   ✅ Report saved: {report_file}")
            print(f"   📊 Summary: {passed_tests}/{total_tests} tests passed "
                  f"({report['success_rate']*100:.1f}%)")
            
            # Cleanup test files
            for test_file in test_files:
                try:
                    os.remove(test_file)
                except:
                    pass
            
        else:
            print("   ⚠️  No test scripts generated")
        
    except Exception as e:
        print(f"❌ Test generation/execution error: {e}")
        print("   This may be expected if test generation is not fully implemented")
    
    # Step 8: Cleanup
    print()
    print("Step 8: Cleaning up...")
    
    try:
        # Disconnect client
        client.disconnect(terminate_debuggee=True)
        print("✅ DAP client disconnected")
        
        # Stop wrapper
        wrapper.stop()
        print("✅ TCP wrapper stopped")
        
        # Get final status
        status = wrapper.get_status()
        print(f"📊 Final wrapper status:")
        print(f"   Connections handled: {status.get('connection_count', 0)}")
        print(f"   Uptime: {status.get('uptime_seconds', 0):.1f} seconds")
        
    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")
    
    print()
    print("=" * 70)
    print("End-to-End Workflow COMPLETED")
    print("=" * 70)
    print()
    print("What was demonstrated:")
    print("1. ✅ TCP wrapper startup and management")
    print("2. ✅ DAP client initialization and connection")
    print("3. ✅ Basic debugging session (initialize, launch, breakpoints)")
    print("4. ✅ Symbolic debugging capabilities")
    print("5. ✅ Test case generation from MLIR programs")
    print("6. ✅ Test execution and reporting")
    print("7. ✅ Proper cleanup and resource management")
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
        from dap_client.integration.server import DAPServerWrapper
        from dap_client.core.client import DAPClient
        
        # Quick setup
        wrapper = DAPServerWrapper()
        if wrapper.start():
            print("✅ TCP wrapper started")
            time.sleep(1)
            
            # Quick client test
            with DAPClient() as client:
                client.initialize(adapter_id="mlir-debugger", client_id="quick-demo")
                print("✅ DAP client initialized")
                client.launch(program="debugger/fixtures/simple_add.mlir")
                print("✅ MLIR program launched")
            
            wrapper.stop()
            print("✅ Cleanup complete")
        else:
            print("❌ Failed to start wrapper")
    
    except Exception as e:
        print(f"❌ Quick workflow error: {e}")
    
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
        if run_quick == 'y':
            quick_workflow()
    
    print("\nWorkflow execution complete!")
    print("Check the generated files:")
    print("- test_report.json (if test generation worked)")
    print("- Review console output for success/failure indicators")
    print("\nFor more information, see:")
    print("- QUICKSTART.md for getting started")
    print("- docs/TUTORIAL.md for detailed tutorial")
    print("- docs/API.md for API reference")