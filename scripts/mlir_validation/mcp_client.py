#!/usr/bin/env python3
"""
MCP client for MLIR validation.
Communicates with MCP server via SSE to validate MLIR code.
"""

import json
import requests
import time
from typing import Dict, Any, Optional


class MCPClient:
    """Client for MCP server communication via SSE."""
    
    def __init__(self, base_url: str = "https://mcp.eventflow.ru"):
        self.base_url = base_url.rstrip('/')
        self.sse_url = f"{self.base_url}/sse"
        
    def validate_mlir(self, mlir_code: str, uri: str = "file:///test.mlir") -> Dict[str, Any]:
        """
        Validate MLIR code using MCP server via SSE.
        
        Note: This is a simplified implementation that uses HTTP POST
        to the SSE endpoint with a single request-response pattern.
        In production, this would use proper SSE client with streaming.
        """
        try:
            # For simplicity, we'll use a direct HTTP POST to the SSE endpoint
            # with a simplified MCP message format
            response = requests.post(
                self.sse_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "validate_mlir",
                        "arguments": {
                            "mlir_code": mlir_code,
                            "uri": uri
                        }
                    },
                    "id": 1
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # If response is not JSON, it might be SSE stream
                    # For now, return error
                    return {"error": "Invalid response format from MCP server"}
            else:
                print(f"MCP validation failed: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            print(f"MCP validation error: {e}")
            return {"error": str(e)}
    
    def check_mlir_syntax(self, mlir_code: str, uri: str = "file:///test.mlir") -> Dict[str, Any]:
        """
        Check MLIR syntax using MCP server.
        """
        try:
            response = requests.post(
                self.sse_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "check_mlir_syntax",
                        "arguments": {
                            "mlir_code": mlir_code,
                            "uri": uri
                        }
                    },
                    "id": 2
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"error": "Invalid response format from MCP server"}
            else:
                print(f"MCP syntax check failed: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            print(f"MCP syntax check error: {e}")
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        """Test connection to MCP server."""
        try:
            # Simple connection test
            response = requests.get(self.sse_url, timeout=10.0)
            # SSE endpoint might return 200 or 405 or other status
            # Just check if we get any response
            return response.status_code < 500
        except Exception as e:
            print(f"Connection test error: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Test the client
    client = MCPClient()
    
    # Test connection
    print("Testing MCP server connection...")
    if client.test_connection():
        print("✓ Connected to MCP server")
    else:
        print("✗ Failed to connect to MCP server")
        exit(1)
    
    # Test MLIR validation
    test_mlir = """module {
  func.func @main() -> i32 {
    %c1 = arith.constant 1 : i32
    %c2 = arith.constant 2 : i32
    %sum = arith.addi %c1, %c2 : i32
    return %sum : i32
  }
}"""
    
    print("\nTesting MLIR validation...")
    result = client.validate_mlir(test_mlir)
    
    if "error" in result:
        print(f"✗ Validation error: {result['error']}")
    else:
        print(f"✓ Validation successful")
        if "diagnostics" in result and result["diagnostics"]:
            print(f"  Found {len(result['diagnostics'])} diagnostics")
            for diag in result["diagnostics"]:
                print(f"  - {diag.get('message', 'Unknown diagnostic')}")
        else:
            print("  No diagnostics found (code is valid)")