# Symbolic MLIR Debugger - API Documentation

Complete API reference for the Symbolic MLIR Debugger.

## 📋 Table of Contents
1. [DAP Client API](#dap-client-api)
2. [TCP Wrapper API](#tcp-wrapper-api)
3. [Test Generation API](#test-generation-api)
4. [Test Runner API](#test-runner-api)
5. [Core Debugger API](#core-debugger-api)
6. [Utility Functions](#utility-functions)

## 1. DAP Client API

The DAP client provides a Python interface to communicate with the MLIR debugger DAP server.

### 1.1 DAPClient Class

**Location:** `dap_client.core.client.DAPClient`

**Description:** Main client class for DAP communication.

**Constructor:**
```python
DAPClient(host="localhost", port=5678, timeout=30.0)
```

**Parameters:**
- `host` (str): Server hostname (default: "localhost")
- `port` (int): Server port (default: 5678)
- `timeout` (float): Connection timeout in seconds (default: 30.0)

**Context Manager Usage:**
```python
with DAPClient(host="localhost", port=5678) as client:
    # Use client here
    # Connection automatically closed on exit
```

### 1.2 Basic Debugging Commands

#### `initialize()`
Initialize a debug session.

```python
response = client.initialize(
    adapter_id="mlir-debugger",
    client_id="your-client-id",
    client_name="Your Client Name",
    locale="en-US"
)
```

**Parameters:**
- `adapter_id` (str): Debug adapter identifier
- `client_id` (str): Client identifier
- `client_name` (str, optional): Human-readable client name
- `locale` (str, optional): Locale for messages

**Returns:** Dictionary with initialization response

#### `launch()`
Launch an MLIR program for debugging.

```python
response = client.launch(
    program="path/to/program.mlir",
    no_debug=False,
    stop_on_entry=True,
    args=None
)
```

**Parameters:**
- `program` (str): Path to MLIR program file
- `no_debug` (bool): If True, run without debugging
- `stop_on_entry` (bool): If True, stop at program entry
- `args` (list, optional): Command-line arguments for program

**Returns:** Dictionary with launch response

#### `set_breakpoints()`
Set breakpoints in source code.

```python
response = client.set_breakpoints(
    source={"path": "path/to/program.mlir"},
    breakpoints=[{"line": 10}, {"line": 20}],
    source_modified=False
)
```

**Parameters:**
- `source` (dict): Source file information
- `breakpoints` (list): List of breakpoint specifications
- `source_modified` (bool): If True, source has been modified

**Returns:** Dictionary with breakpoints response

#### `configuration_done()`
Signal that configuration is complete.

```python
response = client.configuration_done()
```

**Returns:** Dictionary with configuration done response

#### `continue_execution()`
Continue execution from current state.

```python
response = client.continue_execution(thread_id=1)
```

**Parameters:**
- `thread_id` (int): Thread ID to continue

**Returns:** Dictionary with continue response

#### `disconnect()`
Disconnect from debug server.

```python
response = client.disconnect(terminate_debuggee=False, restart=False)
```

**Parameters:**
- `terminate_debuggee` (bool): If True, terminate debuggee
- `restart` (bool): If True, restart debuggee

**Returns:** Dictionary with disconnect response

### 1.3 Symbolic Debugging Commands

#### `symbolic_set_mode()`
Enable or disable symbolic debugging mode.

```python
response = client.symbolic_set_mode(enabled=True)
```

**Parameters:**
- `enabled` (bool): Enable (True) or disable (False) symbolic mode

**Returns:** Dictionary with mode setting response

#### `symbolic_evaluate()`
Evaluate a symbolic expression.

```python
response = client.symbolic_evaluate(
    expression="%a + %b",
    frame_id=0,
    context="hover"
)
```

**Parameters:**
- `expression` (str): Expression to evaluate
- `frame_id` (int): Stack frame ID
- `context` (str): Evaluation context ("hover", "watch", "repl", "clipboard")

**Returns:** Dictionary with evaluation result

#### `symbolic_explore_paths()`
Explore execution paths symbolically.

```python
response = client.symbolic_explore_paths(
    max_paths=10,
    depth_limit=100
)
```

**Parameters:**
- `max_paths` (int): Maximum number of paths to explore
- `depth_limit` (int): Maximum exploration depth

**Returns:** Dictionary with path exploration results

#### `symbolic_get_constraints()`
Get current path constraints.

```python
response = client.symbolic_get_constraints()
```

**Returns:** Dictionary with current constraints

### 1.4 Event Handling

#### Event Callbacks
The client supports event callbacks for asynchronous DAP events:

```python
def on_stopped(event):
    print(f"Program stopped: {event}")

def on_output(event):
    print(f"Output: {event['body']['output']}")

client = DAPClient(host="localhost", port=5678)
client.register_callback("stopped", on_stopped)
client.register_callback("output", on_output)
```

**Supported Events:**
- `"stopped"`: Program execution stopped
- `"continued"`: Program execution continued
- `"output"`: Output produced
- `"breakpoint"`: Breakpoint hit
- `"exited"`: Program exited
- `"terminated"`: Debug session terminated

## 2. TCP Wrapper API

**Location:** `dap_client.integration.server.DAPServerWrapper`

**Description:** TCP wrapper that bridges stdin/stdout DAP server to TCP socket.

### 2.1 DAPServerWrapper Class

**Constructor:**
```python
DAPServerWrapper(
    host="localhost",
    port=5678,
    debugger_path=None
)
```

**Parameters:**
- `host` (str): Host to bind to (default: "localhost")
- `port` (int): Port to bind to (default: 5678)
- `debugger_path` (str, optional): Path to DAP server script

### 2.2 Methods

#### `start()`
Start DAP server subprocess and TCP wrapper.

```python
success = wrapper.start()
```

**Returns:** bool - True if started successfully

#### `stop()`
Stop DAP server wrapper and subprocess.

```python
wrapper.stop()
```

#### `is_alive()`
Check if wrapper and subprocess are alive.

```python
alive = wrapper.is_alive()
```

**Returns:** bool - True if wrapper is running

#### `get_status()`
Get detailed status of wrapper.

```python
status = wrapper.get_status()
```

**Returns:** dict - Status information including:
- `running`: Wrapper running state
- `subprocess_alive`: DAP server subprocess state
- `client_connected`: Client connection state
- `connection_count`: Total connections handled
- `host`: Bound host
- `port`: Bound port

#### `wait_for_connection()`
Wait for a client connection.

```python
connected = wrapper.wait_for_connection(timeout=30.0)
```

**Parameters:**
- `timeout` (float): Timeout in seconds

**Returns:** bool - True if client connected within timeout

### 2.3 Command Line Interface

```bash
# Basic usage
python dap_client/integration/server.py

# With options
python dap_client/integration/server.py --host 0.0.0.0 --port 9999 --debug

# Available options:
# --host: Host to bind to (default: localhost)
# --port: Port to bind to (default: 5678)
# --debug: Enable debug logging
```

## 3. Test Generation API

### 3.1 TestCaseGenerator Class

**Location:** `dap_client.generator.test_case_generator.TestCaseGenerator`

**Description:** Generate test cases from MLIR programs.

**Constructor:**
```python
TestCaseGenerator(host="localhost", port=5678)
```

**Methods:**

#### `connect()`
Connect to DAP server.

```python
generator.connect()
```

#### `generate_from_program()`
Generate test cases from MLIR program.

```python
test_scripts = generator.generate_from_program(
    program_path="path/to/program.mlir",
    max_paths=5,
    include_symbolic=True
)
```

**Parameters:**
- `program_path` (str): Path to MLIR program
- `max_paths` (int): Maximum paths to explore
- `include_symbolic` (bool): Include symbolic debugging tests

**Returns:** list - Generated test scripts

#### `generate_basic_tests()`
Generate basic test cases.

```python
test_scripts = generator.generate_basic_tests(
    program_path="path/to/program.mlir",
    num_tests=3
)
```

### 3.2 PathAwareTestCaseGenerator Class

**Location:** `dap_client.generator.path_aware_generator.PathAwareTestCaseGenerator`

**Description:** Generate path-aware test cases using Z3.

**Constructor:**
```python
PathAwareTestCaseGenerator(host="localhost", port=5678)
```

**Methods:**

#### `generate_targeted_tests()`
Generate tests targeting specific paths.

```python
tests = generator.generate_targeted_tests(
    program_path="path/to/program.mlir",
    target_path_ids=[0, 1, 2]
)
```

#### `generate_memory_model_tests()`
Generate memory model tests.

```python
tests = generator.generate_memory_model_tests(
    program_path="path/to/program.mlir"
)
```

#### `generate_coverage_tests()`
Generate tests for path coverage.

```python
tests = generator.generate_coverage_tests(
    program_path="path/to/program.mlir",
    coverage_goal=0.8  # 80% path coverage
)
```

## 4. Test Runner API

### 4.1 TestRunner Class

**Location:** `dap_client.runner.test_runner.TestRunner`

**Description:** Run test scripts against DAP server.

**Constructor:**
```python
TestRunner(host="localhost", port=5678)
```

**Methods:**

#### `run_test()`
Run a single test script.

```python
result = runner.run_test(
    test_script_path="test.json",
    timeout=60.0
)
```

**Parameters:**
- `test_script_path` (str): Path to test script JSON file
- `timeout` (float): Test timeout in seconds

**Returns:** dict - Test result including:
- `success`: Test passed (bool)
- `duration`: Execution time in seconds
- `output`: Test output
- `errors`: Any errors encountered

#### `run_tests()`
Run multiple test scripts.

```python
results = runner.run_tests(
    test_script_paths=["test1.json", "test2.json"],
    parallel=False
)
```

### 4.2 TestOrchestrator Class

**Location:** `dap_client.runner.orchestrator.TestOrchestrator`

**Description:** Orchestrate parallel test execution.

**Constructor:**
```python
TestOrchestrator(
    host="localhost",
    port=5678,
    max_parallel_sessions=3
)
```

**Methods:**

#### `run_tests()`
Run tests in parallel.

```python
results = orchestrator.run_tests([
    "test1.json",
    "test2.json",
    "test3.json"
])
```

#### `generate_report()`
Generate test execution report.

```python
report = orchestrator.generate_report(results)
```

**Returns:** dict - Report including:
- `total_tests`: Number of tests run
- `passed`: Number of tests passed
- `failed`: Number of tests failed
- `duration`: Total execution time
- `details`: Detailed results per test

## 5. Core Debugger API

### 5.1 DAP Server

**Location:** `debugger.dap_server`

**Description:** Main DAP server implementation.

**Usage:**
```bash
# Start DAP server directly (stdin/stdout)
python debugger/dap_server.py

# The server expects DAP protocol messages via stdin
# and sends responses via stdout
```

### 5.2 Symbolic Interpreter

**Location:** `debugger.interpreter`

**Description:** Symbolic execution engine.

**Key Components:**
- `SymbolicInterpreter`: Main interpreter class
- `SymbolicState`: Symbolic execution state
- `ConstraintSolver`: Z3-based constraint solver

### 5.3 Parser

**Location:** `debugger.parser`

**Description:** MLIR text parser.

**Usage:**
```python
from debugger.parser import parse_mlir

ast = parse_mlir("func.func @main() { return }")
```

## 6. Utility Functions

### 6.1 Schema Validation

**Location:** `dap_client.schema`

**Description:** JSON schema validation for test scripts.

**Usage:**
```python
from dap_client.schema import load_test_script, validate_test_script

# Load and validate test script
test_script = load_test_script("test.json")

# Validate manually
is_valid = validate_test_script(test_script)
```

### 6.2 Protocol Definitions

**Location:** `dap_client.protocol`

**Description:** DAP protocol message definitions.

**Classes:**
- `Request`: DAP request message
- `Response`: DAP response message
- `Event`: DAP event message
- `ProtocolError`: Protocol error exception

### 6.3 Connection Management

**Location:** `dap_client.core.connection`

**Description:** Socket connection management.

**Classes:**
- `DAPConnection`: Managed DAP connection
- `ConnectionError`: Connection error exception

## 🎯 Usage Examples

### Complete Workflow Example

```python
from dap_client.core.client import DAPClient
from dap_client.integration.server import DAPServerWrapper
from dap_client.generator.test_case_generator import TestCaseGenerator
from dap_client.runner.test_runner import TestRunner

# 1. Start TCP wrapper
wrapper = DAPServerWrapper()
wrapper.start()

# 2. Generate test cases
generator = TestCaseGenerator()
generator.connect()
test_scripts = generator.generate_from_program(
    program_path="example.mlir",
    max_paths=3
)

# 3. Run tests
runner = TestRunner()
results = []
for i, test_script in enumerate(test_scripts):
    # Save test script
    with open(f"test_{i}.json", "w") as f:
        import json
        json.dump(test_script, f, indent=2)
    
    # Run test
    result = runner.run_test(f"test_{i}.json")
    results.append(result)

# 4. Cleanup
wrapper.stop()

# 5. Report results
print(f"Tests run: {len(results)}")
print(f"Tests passed: {sum(1 for r in results if r['success'])}")
```

### Advanced Symbolic Debugging

```python
from dap_client.core.client import DAPClient

with DAPClient() as client:
    # Initialize and launch
    client.initialize(adapter_id="mlir-debugger")
    client.launch(program="complex.mlir")
    
    # Enable symbolic mode
    client.symbolic_set_mode(enabled=True)
    
    # Explore paths with custom constraints
    client.set_breakpoints(
        source={"path": "complex.mlir"},
        breakpoints=[{"line": 42}]
    )
    
    client.configuration_done()
    
    # Get symbolic information at breakpoint
    # (requires breakpoint to be hit first)
    
    # Disable symbolic mode
    client.symbolic_set_mode(enabled=False)
    
    client.disconnect()
```

## 📚 Additional Resources

- [Debug Adapter Protocol Specification](https://microsoft.github.io/debug-adapter-protocol/)
- [MLIR Documentation](https://mlir.llvm.org/)
- [Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html)

---

**Note:** This API documentation is automatically generated from code docstrings. For the most up-to-date information, check the inline documentation in the source code files.