#!/usr/bin/env python3
"""
Example demonstrating TCP wrapper usage for DAP server communication.

This example shows:
1. How to start the TCP wrapper
2. How to use the DAP client with the wrapper
3. Proper cleanup procedures
"""

import time
import threading
from dap_client.integration.server import DAPServerWrapper
from dap_client.core.client import DAPClient

def run_tcp_wrapper_example():
    """Run complete example of TCP wrapper usage."""
    print("=" * 60)
    print("TCP Wrapper Example for DAP Server Communication")
    print("=" * 60)
    print()
    
    # Configuration
    HOST = "localhost"
    PORT = 5678
    MLIR_PROGRAM = "../debugger/fixtures/simple_add.mlir"  # Relative path from dap_client/
    
    print(f"Configuration:")
    print(f"  Host: {HOST}")
    print(f"  Port: {PORT}")
    print(f"  MLIR Program: {MLIR_PROGRAM}")
    print()
    
    # Step 1: Start TCP wrapper
    print("Step 1: Starting TCP wrapper...")
    wrapper = DAPServerWrapper(host=HOST, port=PORT)
    
    if not wrapper.start():
        print("❌ Failed to start TCP wrapper")
        return False
    
    print("✅ TCP wrapper started successfully")
    print(f"   Listening on {HOST}:{PORT}")
    print()
    
    # Step 2: Wait for wrapper to be ready
    print("Step 2: Waiting for DAP server to initialize...")
    time.sleep(2)  # Give DAP server time to start
    
    if not wrapper.is_alive():
        print("❌ TCP wrapper or DAP server died during startup")
        wrapper.stop()
        return False
    
    print("✅ DAP server is alive and ready")
    print()
    
    # Step 3: Use DAP client with wrapper
    print("Step 3: Connecting DAP client to TCP wrapper...")
    
    try:
        # Create DAP client (connects to TCP wrapper, not directly to DAP server)
        client = DAPClient(host=HOST, port=PORT)
        
        # Initialize session
        print("   Initializing DAP session...")
        response = client.initialize(
            adapter_id="mlir-debugger",
            client_id="tcp-wrapper-example"
        )
        print(f"   ✅ Session initialized: {response.get('success', False)}")
        
        # Launch MLIR program
        print(f"   Launching MLIR program: {MLIR_PROGRAM}")
        response = client.launch(
            program=MLIR_PROGRAM,
            no_debug=False
        )
        print(f"   ✅ Program launched: {response.get('success', False)}")
        
        # Set a breakpoint
        print("   Setting breakpoint at line 1...")
        response = client.set_breakpoints(
            source={"path": MLIR_PROGRAM},
            breakpoints=[{"line": 1}]
        )
        print(f"   ✅ Breakpoint set: {response.get('success', False)}")
        
        # Configuration done
        print("   Sending configuration done...")
        response = client.configuration_done()
        print(f"   ✅ Configuration done: {response.get('success', False)}")
        
        # Note: We can't continue without a threadId from the DAP server
        # This would normally come from a 'stopped' event
        
        print()
        print("✅ DAP client communication successful!")
        print("   The TCP wrapper correctly bridged:")
        print("     - DAP client (TCP) ↔ TCP wrapper ↔ DAP server (stdin/stdout)")
        
        # Disconnect
        print("   Disconnecting...")
        client.disconnect()
        print("   ✅ Disconnected")
        
    except Exception as e:
        print(f"❌ DAP client error: {e}")
        print("   Common issues:")
        print("   1. TCP wrapper not running")
        print("   2. DAP server failed to start")
        print("   3. MLIR program path incorrect")
        wrapper.stop()
        return False
    
    # Step 4: Cleanup
    print()
    print("Step 4: Cleaning up...")
    wrapper.stop()
    print("✅ TCP wrapper stopped")
    
    # Show final status
    status = wrapper.get_status()
    print()
    print("Final Status:")
    print(f"  Total connections: {status['connection_count']}")
    print(f"  Wrapper running: {status['running']}")
    print(f"  Subprocess alive: {status['subprocess_alive']}")
    
    print()
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    return True

def quick_start_example():
    """Quick start example showing minimal usage."""
    print("\n" + "=" * 60)
    print("Quick Start Example")
    print("=" * 60)
    
    # Minimal wrapper usage
    wrapper = DAPServerWrapper()
    
    print("Starting wrapper...")
    if wrapper.start():
        print(f"✅ Wrapper running on {wrapper.host}:{wrapper.port}")
        print("   Use with DAPClient:")
        print("   from dap_client.core.client import DAPClient")
        print(f"   client = DAPClient(host='{wrapper.host}', port={wrapper.port})")
        
        # Wait a bit then stop
        time.sleep(1)
        wrapper.stop()
        print("✅ Wrapper stopped")
    else:
        print("❌ Failed to start wrapper")
    
    print("=" * 60)

if __name__ == "__main__":
    # Run the full example
    success = run_tcp_wrapper_example()
    
    if success:
        # Run quick start example
        quick_start_example()
    
    print("\nSummary:")
    print("-" * 40)
    print("The TCP wrapper is REQUIRED for DAP client communication.")
    print("It bridges between:")
    print("  • DAP server (stdin/stdout protocol)")
    print("  • DAP client (TCP socket on port 5678)")
    print()
    print("Without the wrapper, DAP clients get 'Connection refused' errors.")
    print()
    print("Usage:")
    print("  python dap_client/integration/server.py")
    print("  # Then in your code:")
    print("  from dap_client.core.client import DAPClient")
    print("  client = DAPClient(host='localhost', port=5678)")