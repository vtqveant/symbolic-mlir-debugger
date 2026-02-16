# Symbolic MLIR DAP Client

A Python DAP (Debug Adapter Protocol) client for automated testing of the Symbolic MLIR Debugger.

## Overview

This module provides a comprehensive DAP client implementation that can communicate with the MLIR debugger DAP server.
It serves as the foundation for automated testing and programmable debugging workflows.

## Features

- **Complete DAP Protocol Support**: Implements all core DAP commands
- **Modular Architecture**: Clear separation of concerns with dedicated modules
- **Socket Communication**: Robust socket-based connection management
- **Session Management**: Full debug session lifecycle support
- **Event Handling**: Support for DAP events
- **Test Script Validation**: JSON schema validation for test scripts

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

## Usage

### Basic Session

```python
from core.client import DAPClient

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
from schema import load_test_script

test_script = load_test_script("examples/test_script.json")
```

### Symbolic Debugging Example

```python
from core.client import DAPClient

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
