# Symbolic MLIR DAP Client

A Python DAP (Debug Adapter Protocol) client for automated testing of the Symbolic MLIR Debugger.

## Overview

This module provides a comprehensive DAP client implementation that can communicate with the MLIR debugger DAP server.
It serves as the foundation for automated testing and programmable debugging workflows.

## Communication Protocol

The DAP client uses **TCP communication** (port 5678) to connect to the DAP server. The server itself uses **stdio** (stdin/stdout) to communicate with its parent process.

### Protocol Overview

1. **DAP Server** (`debugger/dap_server.py`):
   - Reads DAP messages from `stdin`
   - Sends responses via `stdout`
   - Uses standard DAP protocol with Content-Length headers

2. **TCP Wrapper** (`dap_client/integration/server.py`):
   - Starts the DAP server as a subprocess
   - Listens on TCP port (default: 5678)
   - Forwards data between TCP socket and subprocess stdin/stdout
   - Provides a complete TCP interface for the DAP server

3. **DAP Client** (`dap_client/core/client.py`):
   - Connects via TCP socket to the wrapper
   - Sends/receives DAP messages over TCP
   - Implements all DAP commands

**Important**: You **must** use the TCP wrapper when connecting the DAP client. The DAP server is not designed to accept connections directly from a network client.

## Features

- **Complete DAP Protocol Support**: Implements all core DAP commands
- **Modular Architecture**: Clear separation of concerns with dedicated modules
- **Socket Communication**: Robust socket-based connection management
- **Session Management**: Full debug session lifecycle support
- **Event Handling**: Support for DAP events
- **Test Script Validation**: JSON schema validation for test scripts
- **TCP Wrapper**: Production-ready TCP interface for the DAP server

 ## Architecture

```
dap_client/
├── core/
│   ├── client.py          # Main DAP client class
│   ├── connection.py      # Socket connection management
│   └── session.py         # Debug session management
├── protocol/
│   ├── protocol.py        # DAP protocol definitions
│   ├── messages.py        # Request/response/event classes
│   └── constants.py       # DAP constants
├── schema/
│   ├── validation.py      # JSON schema validation
│   └── test_script_schema.json
├── generator/             # Automated test case generation
│   ├── test_case_generator.py       # Basic test case generator
│   ├── path_aware_generator.py      # Z3-based path-aware generator
│   └── __init__.py
├── runner/                # Test execution and orchestration
│   ├── test_runner.py     # Test script runner
│   ├── orchestrator.py    # Parallel test orchestration
│   └── __init__.py
├── integration/           # Integration testing
│   ├── server.py          # TCP wrapper for DAP server
│   ├── test_tcp_integration.py   # TCP integration tests
│   ├── test_pipe_integration.py  # Pipe integration tests
│   └── __init__.py
├── examples/
│   ├── basic_session.py           # Basic usage example
│   ├── test_script.json           # Example test script
│   ├── symbolic_test_script.json  # Symbolic debugging example
│   ├── path_exploration_test.json # Path exploration example
│   ├── constraint_generation_test.json # Constraint extraction example
│   └── full_workflow.py           # Complete workflow demonstration
└── tests/
    ├── test_client.py     # Unit tests for client
    ├── test_connection.py # Unit tests for connection
    └── test_protocol.py   # Unit tests for protocol
```

## TCP Wrapper

The TCP wrapper (`dap_client/integration/server.py`) is a critical component that bridges the gap between the DAP server's stdio interface and the DAP client's TCP interface.

### Why Do You Need the TCP Wrapper?

The DAP server (`debugger/dap_server.py`) is designed to run as a subprocess that communicates via **stdin/stdout**. It's not designed to accept network connections directly.

The DAP client (`dap_client/core/client.py`) expects to connect via **TCP socket**. It's not designed to communicate via pipes.

The TCP wrapper solves this mismatch by:
1. Starting the DAP server as a subprocess
2. Listening on a TCP port (default: 5678)
3. Forwarding data between the TCP socket and the subprocess stdin/stdout

### Starting the TCP Wrapper

#### Using the command-line interface:

```bash
cd dap_client
python integration/server.py --host localhost --port 5678 --debug
```

#### Using the Python API:

```python
from dap_client.integration.server import DAPServerWrapper

wrapper = DAPServerWrapper(host="localhost", port=5678)

if wrapper.start():
    print(f"TCP wrapper running on localhost:5678")
    # Do something with the wrapper...
    # wrapper.wait_for_connection()  # Wait for a client to connect

    # Keep running until stopped
    while wrapper.is_alive():
        import time
        time.sleep(1)

wrapper.stop()
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | str | "localhost" | Host to bind to |
| `port` | int | 5678 | TCP port to listen on |
| `debugger_path` | str | auto-detected | Path to DAP server script |
| `debug` | bool | False | Enable debug logging |

### Health Checks

The wrapper provides several health check methods:

```python
# Check if wrapper is running
if wrapper.is_alive():
    print("Wrapper is alive")

# Wait for a client connection (with timeout)
connected = wrapper.wait_for_connection(timeout=10.0)
if connected:
    print("Client connected")
```

### Error Handling

The wrapper provides detailed error messages:

```python
if wrapper.start():
    # Success
else:
    # Failed to start
    # Check logs for detailed error information
```

Common errors:
- **Port already in use**: Specify a different port with `--port`
- **DAP server not found**: Check `debugger_path` is correct
- **Permission denied**: Run with appropriate permissions for the port

### TCP Wrapper Internals

The wrapper uses two forwarding threads:
- **TCP → Subprocess**: Reads from TCP socket and writes to subprocess stdin
- **Subprocess → TCP**: Reads from subprocess stdout and writes to TCP socket

Both threads are daemon threads and will terminate when the main process exits.

### Logging

The wrapper supports different log levels:

```bash
# Info level (default)
python integration/server.py --host localhost --port 5678

# Debug level (verbose)
python integration/server.py --host localhost --port 5678 --debug
```

Log output includes:
- Client connection events
- Forwarding status
- Subprocess events
- Error messages with stack traces

 ## Core DAP Commands

Implemented commands:

### Basic Debugging Commands
- `initialize` - Initialize debug session
- `launch` - Launch MLIR program
- `setBreakpoints` - Set breakpoints in source
- `configurationDone` - Signal configuration complete
- `continue` - Continue execution (requires threadId)
- `disconnect` - Disconnect from debug server

### Symbolic Debugging Commands
- `symbolic/setMode` - Enable/disable symbolic debugging mode
- `symbolic/evaluate` - Evaluate symbolic expression
- `symbolic/explorePaths` - Explore execution paths symbolically
- `symbolic/getConstraints` - Retrieve current path constraints

## Installation

```bash
cd dap_client
pip install -e .
```

## TCP Wrapper Server

**Important**: The DAP client expects a **TCP connection** on port 5678, but the DAP server (`debugger/dap_server.py`) uses **stdin/stdout** (standard DAP protocol). You need the TCP wrapper server to bridge between them.

### **Starting the TCP Wrapper:**

```bash
# From repository root
python dap_client/integration/server.py --host localhost --port 5678

# With debug logging
python dap_client/integration/server.py --host localhost --port 5678 --debug
```

### **Programmatic Usage:**

```python
from dap_client.integration.server import DAPServerWrapper

# Start wrapper
wrapper = DAPServerWrapper(host="localhost", port=5678)
if wrapper.start():
    print("TCP wrapper running")
    
    # Wait for client connection
    if wrapper.wait_for_connection(timeout=10.0):
        print("Client connected")
    
    # ... use DAP client ...
    
    # Stop when done
    wrapper.stop()
```

### **Wrapper Features:**
- **Automatic DAP server startup**: Starts `debugger/dap_server.py` as subprocess
- **Bidirectional forwarding**: TCP ↔ stdin/stdout
- **Connection management**: Handles multiple client connections
- **Health monitoring**: `wrapper.is_alive()` checks status
- **Configurable**: Custom host, port, and debugger path

### **Without Wrapper (Direct stdin/stdout):**
If you want to communicate directly with the DAP server (not recommended for most users):
```bash
python debugger/dap_server.py
# Then send DAP protocol messages via stdin, read responses from stdout
```

## Usage

**Important**: Before using the DAP client, you must start the TCP wrapper to expose the DAP server via TCP.

### Step 1: Start the TCP Wrapper

```bash
# Terminal 1 - Start the wrapper
cd dap_client
python integration/server.py --host localhost --port 5678
```

### Step 2: Use the DAP Client

#### Basic Session

```python
from dap_client.core.client import DAPClient

with DAPClient(host="localhost", port=5678) as client:
    # Initialize session
    client.initialize(adapter_id="mlir-debugger", client_id="automated-test")

    # Launch program
    client.launch(program="example.mlir", no_debug=False)

    # Set breakpoints
    client.set_breakpoints(
        source={"path": "example.mlir"},
        breakpoints=[{"line": 10}]
    )

    # Configuration done
    client.configuration_done()

    # Continue execution
    client.continue_execution(thread_id=1)
```

 ### Test Script Example

```python
from dap_client.schema import load_test_script

test_script = load_test_script("examples/test_script.json")
```

### Symbolic Debugging Example

```python
from dap_client.core.client import DAPClient

with DAPClient(host="localhost", port=5678) as client:
    # Initialize and launch program
    client.initialize(adapter_id="mlir-debugger", client_id="symbolic-test")
    client.launch(program="conditional_branch.mlir", no_debug=False)
    
    # Enable symbolic debugging
    client.symbolic_set_mode(enabled=True)
    
    # Evaluate symbolic expression
    result = client.symbolic_evaluate(expression="%a < %b", frame_id=0)
    
    # Explore execution paths
    paths = client.symbolic_explore_paths(max_paths=10)
    
    # Get constraints
    constraints = client.symbolic_get_constraints()
    
    # Disable symbolic mode
    client.symbolic_set_mode(enabled=False)
```

### Automated Test Generation

The DAP client includes powerful test case generators:

```python
from generator.test_case_generator import TestCaseGenerator
from generator.path_aware_generator import PathAwareTestCaseGenerator

# Basic generator
generator = TestCaseGenerator(host="localhost", port=5678)
generator.connect()
test_scripts = generator.generate_from_program(
    program_path="conditional_branch.mlir",
    max_paths=5
)

# Path-aware generator (requires Z3)
path_aware = PathAwareTestCaseGenerator(host="localhost", port=5678)
path_aware.connect()
targeted_tests = path_aware.generate_targeted_tests(
    program_path="nested_conditional.mlir",
    target_path_ids=[0, 1, 2]
)

# Memory model tests
memory_tests = path_aware.generate_memory_model_tests(
    program_path="memref_basic.mlir"
)
```

### Test Execution and Orchestration

```python
from runner.test_runner import TestRunner
from runner.orchestrator import TestOrchestrator

# Single test runner
runner = TestRunner(host="localhost", port=5678)
result = runner.run_test("test_script.json")

# Parallel test orchestration
orchestrator = TestOrchestrator(
    host="localhost",
    port=5678,
    max_parallel_sessions=3
)

results = orchestrator.run_tests([
    "test1.json",
    "test2.json",
    "test3.json"
])

report = orchestrator.generate_report(results)
```

### Full Workflow Demonstration

See `examples/full_workflow.py` for a complete demonstration:

```bash
python examples/full_workflow.py --program conditional_branch.mlir
```

This script:
1. Generates test cases from an MLIR program using symbolic execution
2. Saves generated test scripts to JSON files
3. Executes the generated test scripts using the test runner
4. Generates a comprehensive test report in JSON format

### Quick Start Example

Here's a complete example showing how to use the TCP wrapper and DAP client together:

```bash
# Terminal 1: Start the TCP wrapper
cd dap_client
python integration/server.py --port 5678

# Terminal 2: Run the example
python examples/basic_session.py
```

The example script:
1. Starts the TCP wrapper
2. Connects to it with the DAP client
3. Initializes a debug session
4. Launches an MLIR program
5. Sets and hits a breakpoint
6. Inspects variables
7. Cleanly shuts down the wrapper

For more examples, see the `examples/` directory.

## Running Tests

```bash
cd dap_client
python -m pytest tests/ -v
```

## API Documentation

See the inline docstrings in each module for detailed API documentation.

 ## Requirements

- Python 3.8+
- jsonschema >= 4.0.0
- pytest (for testing)

### Optional Dependencies
- **z3-solver** >= 4.12.0: Required for path-aware test generation and memory model tests
  - Install with: `pip install z3-solver`

### Installation with All Dependencies

```bash
cd dap_client
pip install -e .[all]
```

## License

MIT License

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting PRs.
