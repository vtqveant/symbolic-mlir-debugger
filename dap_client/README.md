# Symbolic MLIR DAP Client

A Python DAP (Debug Adapter Protocol) client for automated testing of the Symbolic MLIR Debugger.

## Overview

This module provides a comprehensive DAP client implementation that can communicate with the MLIR debugger DAP server.
It serves as the foundation for automated testing and programmable debugging workflows.

## Communication Protocol

The DAP client uses **stdio communication** (stdin/stdout pipes) to connect directly to the DAP server, following the standard Debug Adapter Protocol. The client automatically launches the DAP server as a subprocess and manages the complete lifecycle.

### Protocol Overview

1. **DAP Server** (`debugger/dap_server.py`):
   - Reads DAP messages from `stdin`
   - Sends responses via `stdout`
   - Uses standard DAP protocol with Content-Length headers
   - Implements symbolic debugging capabilities

2. **DAP Client** (`dap_client/core/client.py`):
   - Automatically launches the DAP server as a subprocess
   - Communicates via **stdio pipes** (stdin/stdout)
   - Manages the complete debug session lifecycle
   - Implements all DAP commands
   - Direct stdio communication, no network ports required

**Simplified Architecture**: The DAP client directly connects to the DAP server using stdio, simplifying deployment.

## Features

- **Complete DAP Protocol Support**: Implements all core DAP commands
- **Modular Architecture**: Clear separation of concerns with dedicated modules
- **Stdio Communication**: Direct stdio (stdin/stdout) connection to DAP server
- **Session Management**: Full debug session lifecycle support
- **Event Handling**: Support for DAP events
- **Test Script Validation**: JSON schema validation for test scripts
- **Automatic Server Management**: Launches and manages DAP server subprocess

 ## Architecture

```
dap_client/
├── core/
│   ├── client.py          # Main DAP client class
│   ├── stdio_connection.py # Stdio connection (active)
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
├── examples/
│   ├── basic_session.py           # Basic usage example
│   ├── test_script.json           # Example test script
│   ├── symbolic_test_script.json  # Symbolic debugging example
│   ├── path_exploration_test.json # Path exploration example
│   ├── constraint_generation_test.json # Constraint extraction example
│   └── full_workflow.py           # Complete workflow demonstration
└── tests/                # Test suite
    ├── integration/      # Integration testing
    │   ├── test_pipe_integration.py  # Pipe integration tests
    │   └── __init__.py
    ├── test_client.py     # Unit tests for client
    ├── test_stdio_connection.py # Unit tests for stdio connection
    └── test_protocol.py   # Unit tests for protocol
```

## Connection Architecture

The DAP client uses direct **stdio communication** (stdin/stdout pipes) to connect to the DAP server, simplifying the architecture and improving reliability.

### **Current Architecture:**

```
┌─────────────────┐    stdin/stdout    ┌─────────────────┐
│   DAP Client    │ ◄────────────────► │  DAP Server     │
│  (dap_client/)  │   (DAP Protocol)   │ (dap_server.py) │
└─────────────────┘                    └─────────────────┘
```

### **How It Works:**

1. **Automatic Server Launch**: The DAP client automatically starts the DAP server (`debugger/dap_server.py`) as a subprocess
2. **Stdio Communication**: The client communicates via stdin/stdout pipes using standard DAP protocol with Content-Length headers
3. **Lifecycle Management**: The client manages the complete lifecycle of the DAP server subprocess

### **Configuration Options:**

```python
from dap_client.core.client import DAPClient

# Customize connection settings
client = DAPClient(
    debugger_path="/custom/path/dap_server.py",  # Default: auto-detected
    timeout=30,      # Connection timeout in seconds
    read_timeout=10  # Read timeout in seconds
)
```



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

## Connection Setup

The DAP client uses direct **stdio communication** and automatically launches the DAP server as a subprocess.

### **Using the DAP Client:**

```python
from dap_client.core.client import DAPClient

# The client automatically starts the DAP server
with DAPClient() as client:
    # Initialize session
    client.initialize(adapter_id="mlir-debugger", client_id="automated-test")
    
    # Launch program
    client.launch(program="example.mlir", no_debug=False)
    
    # ... rest of debugging session
```

### **Configuration Options:**

```python
# Customize connection settings
client = DAPClient(
    debugger_path="/custom/path/dap_server.py",  # Default: auto-detected
    timeout=30,      # Connection timeout in seconds
    read_timeout=10  # Read timeout in seconds
)
```



## Usage

The DAP client automatically launches the DAP server as a subprocess and communicates via stdio (stdin/stdout).

#### Basic Session

```python
from dap_client.core.client import DAPClient

with DAPClient() as client:
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

with DAPClient() as client:
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
from generator.path_aware_generator import PathAwareGenerator

# Basic generator
generator = TestCaseGenerator()
generator.connect()
test_scripts = generator.generate_from_program(
    program_path="conditional_branch.mlir",
    max_paths=5
)

# Path-aware generator (requires Z3)
path_aware = PathAwareGenerator()
path_aware.connect()
targeted_tests = path_aware.generate_from_program(
    program_path="nested_conditional.mlir",
    max_paths=3
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
runner = TestRunner()
result = runner.run_test_file("test_script.json")

# Parallel test orchestration
orchestrator = TestOrchestrator(max_workers=3)

results = orchestrator.run_test_files([
    "test1.json",
    "test2.json",
    "test3.json"
])

report = orchestrator.get_summary()
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

Run the basic session example directly:

```bash
cd dap_client
python examples/basic_session.py
```

The example script:
1. Automatically launches the DAP server as a subprocess
2. Initializes a debug session
3. Launches an MLIR program
4. Sets and hits a breakpoint
5. Inspects variables
6. Cleanly shuts down the DAP server

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
