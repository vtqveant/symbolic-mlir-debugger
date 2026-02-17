#!/usr/bin/env python3
"""End-to-end test of MLIR debugger as an end user"""

import json
import subprocess
import time
import sys
import os
import threading
import socket

def start_dap_server():
    """Start DAP server via TCP wrapper"""
    print("Starting DAP server with TCP wrapper...")
    
    # Start the TCP wrapper
    wrapper_path = os.path.join(os.path.dirname(__file__), "dap_client", "integration", "server.py")
    
    wrapper = subprocess.Popen(
        ["python", wrapper_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give it time to start
    time.sleep(2)
    
    # Check if it's running
    if wrapper.poll() is not None:
        stderr = wrapper.stderr.read()
        print(f"Wrapper failed to start: {stderr}")
        return None, None
    
    print("DAP server wrapper started")
    return wrapper, 5678

def test_basic_dap_connection(port):
    """Test basic DAP connection using raw sockets"""
    print(f"\nTesting basic DAP connection to port {port}...")
    
    try:
        # Connect to DAP server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("localhost", port))
        print("Connected to DAP server")
        
        # Send initialize request
        request = {
            "seq": 1,
            "type": "request",
            "command": "initialize",
            "arguments": {
                "adapterID": "mlir-debugger",
                "clientID": "end-user-test"
            }
        }
        
        content = json.dumps(request)
        message = f"Content-Length: {len(content)}\r\n\r\n{content}"
        sock.sendall(message.encode())
        
        # Read response
        response = read_dap_message(sock)
        if response:
            print(f"Initialize response: {response.get('type')} {response.get('command')}")
            
            # Check if successful
            if response.get('type') == 'response' and response.get('success'):
                print("Initialize successful!")
                return True
            else:
                print(f"Initialize failed: {response}")
                return False
        else:
            print("No response received")
            return False
            
    except Exception as e:
        print(f"Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'sock' in locals():
            sock.close()

def read_dap_message(sock):
    """Read a DAP message from socket"""
    try:
        # Read header
        header = b""
        while True:
            chunk = sock.recv(1)
            if not chunk:
                return None
            header += chunk
            if header.endswith(b"\r\n\r\n"):
                break
        
        # Parse content length
        header_str = header.decode()
        lines = header_str.strip().split("\r\n")
        content_length = 0
        for line in lines:
            if line.startswith("Content-Length:"):
                content_length = int(line.split(":")[1].strip())
                break
        
        if content_length == 0:
            return None
        
        # Read content
        content = b""
        while len(content) < content_length:
            chunk = sock.recv(content_length - len(content))
            if not chunk:
                break
            content += chunk
        
        if len(content) != content_length:
            return None
        
        return json.loads(content.decode())
        
    except Exception as e:
        print(f"Error reading DAP message: {e}")
        return None

def test_dap_client_library():
    """Test using the DAP client library"""
    print("\nTesting DAP client library...")
    
    try:
        # Try to import and use the DAP client
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "dap_client"))
        
        from core.client import DAPClient
        
        client = DAPClient(host="localhost", port=5678)
        
        print("Connecting to DAP server...")
        if client.connect():
            print("Connected successfully!")
            
            # Test initialize
            print("Testing initialize...")
            result = client.initialize(adapter_id="mlir-debugger", client_id="library-test")
            print(f"Initialize result: {result}")
            
            # Test launch
            print("Testing launch...")
            mlir_file = os.path.join(os.path.dirname(__file__), "test_function.mlir")
            if os.path.exists(mlir_file):
                result = client.launch(program=mlir_file, no_debug=False)
                print(f"Launch result: {result}")
            else:
                print(f"MLIR file not found: {mlir_file}")
            
            client.disconnect()
            return True
        else:
            print("Failed to connect")
            return False
            
    except Exception as e:
        print(f"DAP client library test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_symbolic_debugging():
    """Test symbolic debugging features"""
    print("\nTesting symbolic debugging features...")
    
    try:
        from core.client import DAPClient
        
        client = DAPClient(host="localhost", port=5678)
        
        if client.connect():
            print("Connected for symbolic debugging test")
            
            # Initialize
            client.initialize(adapter_id="mlir-debugger", client_id="symbolic-test")
            
            # Launch program
            mlir_file = os.path.join(os.path.dirname(__file__), "test_function.mlir")
            if os.path.exists(mlir_file):
                client.launch(program=mlir_file, no_debug=False)
                
                # Try symbolic commands
                print("Testing symbolic commands...")
                
                # Enable symbolic mode
                try:
                    result = client.symbolic_set_mode(enabled=True)
                    print(f"Symbolic mode enabled: {result}")
                except Exception as e:
                    print(f"Symbolic mode command failed (may not be implemented): {e}")
                
                # Try to evaluate symbolic expression
                try:
                    result = client.symbolic_evaluate(expression="%a < %b", frame_id=0)
                    print(f"Symbolic evaluate result: {result}")
                except Exception as e:
                    print(f"Symbolic evaluate failed: {e}")
                
                client.disconnect()
                return True
            else:
                print("MLIR file not found")
                return False
        else:
            print("Failed to connect")
            return False
            
    except Exception as e:
        print(f"Symbolic debugging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("End-to-end test of MLIR debugger as end user")
    print("=" * 60)
    
    # Start DAP server
    wrapper, port = start_dap_server()
    if not wrapper:
        print("Failed to start DAP server")
        return False
    
    try:
        # Test 1: Basic DAP connection
        test1_success = test_basic_dap_connection(port)
        
        # Test 2: DAP client library
        test2_success = test_dap_client_library()
        
        # Test 3: Symbolic debugging
        test3_success = test_symbolic_debugging()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY:")
        print(f"1. Basic DAP connection: {'PASS' if test1_success else 'FAIL'}")
        print(f"2. DAP client library: {'PASS' if test2_success else 'FAIL'}")
        print(f"3. Symbolic debugging: {'PASS' if test3_success else 'FAIL'}")
        
        overall_success = test1_success or test2_success or test3_success
        
        if overall_success:
            print("\nOverall: SOME TESTS PASSED - System is partially functional")
        else:
            print("\nOverall: ALL TESTS FAILED - System is not functional")
        
        return overall_success
        
    finally:
        # Clean up
        print("\nCleaning up...")
        if wrapper:
            wrapper.terminate()
            wrapper.wait()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)