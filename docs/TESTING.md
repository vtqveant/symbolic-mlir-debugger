# Symbolic MLIR Debugger - Testing Guide

Comprehensive guide to testing the Symbolic MLIR Debugger.

## 📋 Table of Contents
1. [Test Architecture](#test-architecture)
2. [Running Tests](#running-tests)
3. [Writing Tests](#writing-tests)
4. [Test Script Format](#test-script-format)
5. [Integration Testing](#integration-testing)
6. [Performance Testing](#performance-testing)
7. [Continuous Integration](#continuous-integration)
8. [Debugging Tests](#debugging-tests)

## 1. Test Architecture

### 1.1 Test Layers

```
┌─────────────────────────────────┐
│      Integration Tests          │
│  (DAP client ↔ DAP server)      │
├─────────────────────────────────┤
│        Unit Tests               │
│  (Individual components)        │
├─────────────────────────────────┤
│       Protocol Tests            │
│  (DAP message handling)         │
└─────────────────────────────────┘
```

### 1.2 Test Directories

```
symbolic-mlir-debugger/
├── debugger/tests/              # Core debugger tests
│   ├── test_parser.py           # MLIR parser tests
│   ├── test_interpreter.py      # Interpreter tests
│   ├── test_symbolic.py         # Symbolic execution tests
│   └── test_dap_server.py       # DAP server tests
├── dap_client/tests/            # DAP client tests
│   ├── test_client.py           # Client unit tests
│   ├── test_connection.py       # Connection tests
│   ├── test_protocol.py         # Protocol tests
│   └── test_integration.py      # Integration tests
└── test_scripts/                # Test script examples
    ├── basic_test.json          # Basic test script
    ├── symbolic_test.json       # Symbolic debugging test
    └── path_exploration_test.json # Path exploration test
```

## 2. Running Tests

### 2.1 Running All Tests

```bash
# From repository root
cd debugger
python -m pytest tests/ -v
```

### 2.2 Running Specific Test Categories

```bash
# Run parser tests only
python -m pytest tests/test_parser.py -v

# Run interpreter tests
python -m pytest tests/test_interpreter.py -v

# Run tests with marker
python -m pytest tests/ -m "parser or interpreter" -v

# Run DAP client tests
cd dap_client
python -m pytest tests/ -v
```

### 2.3 Test Output Options

```bash
# Verbose output
python -m pytest tests/ -v

# Show print statements
python -m pytest tests/ -s

# Stop on first failure
python -m pytest tests/ -x

# Run tests in parallel
python -m pytest tests/ -n auto
```

### 2.4 Coverage Reporting

```bash
# Generate coverage report
python -m pytest tests/ --cov=debugger --cov-report=html

# View coverage in browser
open htmlcov/index.html
```

## 3. Writing Tests

### 3.1 Unit Test Structure

```python
import pytest
from debugger.parser import parse_mlir

class TestParser:
    """Test MLIR parser functionality."""
    
    def test_parse_simple_function(self):
        """Test parsing a simple MLIR function."""
        mlir_code = """
        func.func @simple() -> i32 {
          %c1 = arith.constant 1 : i32
          return %c1 : i32
        }
        """
        
        ast = parse_mlir(mlir_code)
        
        # Assertions
        assert ast is not None
        assert ast.functions[0].name == "simple"
        assert len(ast.functions[0].body) == 2
    
    def test_parse_invalid_mlir(self):
        """Test parsing invalid MLIR raises appropriate error."""
        invalid_mlir = "invalid mlir code"
        
        with pytest.raises(ParseError) as exc_info:
            parse_mlir(invalid_mlir)
        
        assert "syntax error" in str(exc_info.value)
    
    @pytest.mark.parametrize("mlir_code,expected_function_count", [
        ("func.func @f1() {}", 1),
        ("func.func @f1() {}\nfunc.func @f2() {}", 2),
        ("", 0),
    ])
    def test_function_count(self, mlir_code, expected_function_count):
        """Test function counting with parameterized inputs."""
        ast = parse_mlir(mlir_code)
        assert len(ast.functions) == expected_function_count
```



### 3.3 Test Fixtures

```python
import pytest
import tempfile
import os

@pytest.fixture
def temp_mlir_file():
    """Create a temporary MLIR file for testing."""
    mlir_content = """
    func.func @test(%arg0: i32, %arg1: i32) -> i32 {
      %sum = arith.addi %arg0, %arg1 : i32
      return %sum : i32
    }
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mlir', delete=False) as f:
        f.write(mlir_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)

@pytest.fixture
def dap_client():
    """Create a DAP client for testing."""
    client = DAPClient()
    client.connect()
    yield client
    client.disconnect()

@pytest.fixture(scope="session")
def test_server():
    """Session-scoped test server."""
    from test_server import TestServer
    server = TestServer()
    server.start()
    yield server
    server.stop()
```

## 4. Test Script Format

### 4.1 Basic Test Script

```json
{
  "name": "Basic Arithmetic Test",
  "description": "Test basic arithmetic operations in MLIR",
  "setup": {
    "program": "debugger/fixtures/simple_add.mlir",
    "breakpoints": [
      {
        "source": {"path": "debugger/fixtures/simple_add.mlir"},
        "line": 1
      }
    ]
  },
  "steps": [
    {
      "command": "initialize",
      "params": {
        "adapter_id": "mlir-debugger",
        "client_id": "test-client"
      },
      "expected": {
        "success": true
      }
    },
    {
      "command": "launch",
      "params": {
        "program": "debugger/fixtures/simple_add.mlir",
        "no_debug": false
      },
      "expected": {
        "success": true
      }
    },
    {
      "command": "setBreakpoints",
      "params": {
        "source": {"path": "debugger/fixtures/simple_add.mlir"},
        "breakpoints": [{"line": 1}]
      },
      "expected": {
        "success": true,
        "breakpoints": [
          {
            "verified": true,
            "line": 1
          }
        ]
      }
    },
    {
      "command": "configurationDone",
      "params": {},
      "expected": {
        "success": true
      }
    }
  ],
  "cleanup": {
    "command": "disconnect",
    "params": {
      "terminateDebuggee": true
    }
  }
}
```

### 4.2 Symbolic Debugging Test Script

```json
{
  "name": "Symbolic Evaluation Test",
  "description": "Test symbolic expression evaluation",
  "setup": {
    "program": "debugger/fixtures/conditional_branch.mlir",
    "symbolic_mode": true
  },
  "steps": [
    {
      "command": "initialize",
      "params": {
        "adapter_id": "mlir-debugger",
        "client_id": "symbolic-test"
      }
    },
    {
      "command": "launch",
      "params": {
        "program": "debugger/fixtures/conditional_branch.mlir"
      }
    },
    {
      "command": "symbolic/setMode",
      "params": {
        "enabled": true
      },
      "expected": {
        "success": true
      }
    },
    {
      "command": "symbolic/evaluate",
      "params": {
        "expression": "%a < %b",
        "frame_id": 0,
        "context": "hover"
      },
      "expected": {
        "success": true,
        "result": {
          "type": "boolean",
          "value": "symbolic"
        }
      }
    }
  ]
}
```

### 4.3 Test Script Validation

Test scripts are validated against a JSON schema:

```python
from dap_client.schema import validate_test_script, load_test_script

# Load and validate
test_script = load_test_script("test_script.json")

# Validate manually
is_valid, errors = validate_test_script(test_script)
if not is_valid:
    print(f"Validation errors: {errors}")
```

## 5. Integration Testing





## 6. Performance Testing

### 6.1 Benchmark Tests

```python
import pytest
import time
from dap_client.core.client import DAPClient

@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmark tests."""
    
    def test_connection_latency(self, benchmark):
        """Benchmark connection establishment latency."""
        def connect_disconnect():
            client = DAPClient(timeout=5.0)
            client.connect()
            client.disconnect()
        
        benchmark(connect_disconnect)
    
    def test_command_throughput(self, benchmark):
        """Benchmark command throughput."""
        client = DAPClient()
        client.connect()
        client.initialize(adapter_id="mlir-debugger")
        
        def send_commands():
            for _ in range(10):
                client.launch(program="debugger/fixtures/simple_add.mlir")
        
        benchmark(send_commands)
        
        client.disconnect()
    
    def test_memory_usage(self):
        """Test memory usage during long sessions."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        clients = []
        for i in range(10):
            client = DAPClient()
            client.connect()
            clients.append(client)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Cleanup
        for client in clients:
            client.disconnect()
        
        # Assert reasonable memory usage
        assert memory_increase < 100 * 1024 * 1024  # Less than 100MB
```

### 6.2 Load Testing

```python
def test_concurrent_sessions():
    """Test multiple concurrent DAP sessions."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    
    results = []
    
    def run_session(session_id):
        """Run a single DAP session."""
        try:
            with DAPClient() as client:
                client.initialize(
                    adapter_id="mlir-debugger",
                    client_id=f"load-test-{session_id}"
                )
                client.launch(program="debugger/fixtures/simple_add.mlir")
                return True
        except Exception as e:
            return str(e)
    
    # Run 10 concurrent sessions
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_session, i) for i in range(10)]
        results = [f.result() for f in futures]
    
    # Check results
    successes = sum(1 for r in results if r is True)
    failures = sum(1 for r in results if r is not True)
    
    assert successes >= 8  # At least 80% success rate
    if failures > 0:
        print(f"Failures: {[r for r in results if r is not True]}")
```

## 7. Continuous Integration

### 7.1 GitHub Actions Configuration

The project includes `.github/workflows/ci.yml` for automated testing:

```yaml
name: CI

on:
  push:
    branches: [ main, staging-* ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        cd debugger
        python -m pytest tests/ -v --cov=debugger --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./debugger/coverage.xml
```

### 7.2 Test Matrix

```yaml
strategy:
  matrix:
    python-version: ['3.8', '3.9', '3.10', '3.11']
    os: [ubuntu-latest, macos-latest]
  
test:
  runs-on: ${{ matrix.os }}
  
  steps:
  - name: Test with Python ${{ matrix.python-version }}
    run: |
      python -m pytest tests/ -v
```

## 8. Debugging Tests

### 8.1 Common Test Issues

#### Issue: Tests hanging
**Solution:** Add timeouts:
```python
@pytest.mark.timeout(30)  # 30 second timeout
def test_slow_operation():
    # test code
```

#### Issue: Intermittent failures
**Solution