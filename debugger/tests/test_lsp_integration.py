"""LSP server integration tests."""

import pytest
import json

# Try to import requests, skip tests if not available
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# LSP server URL
LSP_SERVER_URL = "https://api.niche-robotics.tech/api/v1/diagnostics"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_REQUESTS, reason="requests module not installed")
def test_lsp_diagnostics_valid_mlir():
    """Test getting diagnostics for valid MLIR code."""
    valid_mlir = """module {
  func.func @add(%a: i32, %b: i32) -> i32 {
    %sum = arith.addi %a, %b : i32
    return %sum : i32
  }
}"""

    # GET request
    params = {"mlir_code": valid_mlir}
    response = requests.get(LSP_SERVER_URL, params=params, timeout=10)

    # Accept any 2xx status
    assert response.status_code in range(200, 300), (
        f"GET failed with status {response.status_code}"
    )
    result = response.json()
    assert isinstance(result, dict)

    # POST request
    headers = {"Content-Type": "application/json"}
    data = {"mlir_code": valid_mlir, "uri": "file:///test.mlir"}
    response = requests.post(LSP_SERVER_URL, json=data, headers=headers, timeout=10)

    assert response.status_code in range(200, 300), (
        f"POST failed with status {response.status_code}"
    )
    result = response.json()
    assert isinstance(result, dict)


@pytest.mark.integration
@pytest.mark.skipif(not HAS_REQUESTS, reason="requests module not installed")
def test_lsp_diagnostics_invalid_mlir():
    """Test getting diagnostics for invalid MLIR code."""
    invalid_mlir = """module {
  func.func @bad() -> i32 {
    %x = invalid.op %a : i32
    return %x : i32
  }
}"""

    # GET request
    params = {"mlir_code": invalid_mlir}
    response = requests.get(LSP_SERVER_URL, params=params, timeout=10)

    # Accept any 2xx status (server may return diagnostics with errors)
    assert response.status_code in range(200, 300), (
        f"GET failed with status {response.status_code}"
    )
    result = response.json()
    assert isinstance(result, dict)

    # POST request
    headers = {"Content-Type": "application/json"}
    data = {"mlir_code": invalid_mlir, "uri": "file:///test.mlir"}
    response = requests.post(LSP_SERVER_URL, json=data, headers=headers, timeout=10)

    assert response.status_code in range(200, 300), (
        f"POST failed with status {response.status_code}"
    )
    result = response.json()
    assert isinstance(result, dict)
