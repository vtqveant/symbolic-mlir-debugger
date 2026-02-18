#!/usr/bin/env python3
"""Debug constraints issue."""

import sys
sys.path.insert(0, '.')

from dap_client.core.client import DAPClient
import json

def test_constraints():
    """Test symbolic constraints."""
    client = DAPClient()
    
    if not client.connect():
        print("Failed to connect")
        return
    
    try:
        # Initialize
        result = client.initialize(adapter_id='mlir-debugger', client_id='test-constraints')
        print(f"Initialize: {result.get('success', 'no success key')}")
        
        # Enable symbolic mode
        result = client.symbolic_set_mode(enabled=True)
        print(f"Symbolic mode: {result}")
        
        # Launch program
        result = client.launch(program='debugger/fixtures/conditional_branch.mlir', no_debug=True)
        print(f"Launch: {result}")
        
        # Evaluate a
        result = client.symbolic_evaluate(expression='a', frame_id=0)
        print(f"Evaluate a: {result}")
        
        # Evaluate b  
        result = client.symbolic_evaluate(expression='b', frame_id=0)
        print(f"Evaluate b: {result}")
        
        # Explore paths
        result = client.symbolic_explore_paths(max_paths=1)
        print(f"Explore paths: {result}")
        print(f"  Total paths: {result.get('totalPaths', 'N/A')}")
        print(f"  Paths: {result.get('paths', [])}")
        
        # Get constraints
        result = client.symbolic_get_constraints()
        print(f"Get constraints: {result}")
        print(f"  Count: {result.get('count', 'N/A')}")
        print(f"  Constraints: {result.get('constraints', [])}")
        
        # Disconnect
        result = client.disconnect(terminate_debuggee=True)
        print(f"Disconnect: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    test_constraints()