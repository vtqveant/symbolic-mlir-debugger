# Symbolic MLIR DAP Client

A Python DAP (Debug Adapter Protocol) client for automated testing of the Symbolic MLIR Debugger.

## Overview

This module provides a comprehensive DAP client implementation that can communicate with the MLIR debugger DAP server. It serves as the foundation for automated testing and programmable debugging workflows.

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
├── examples/
│   ├── basic_session.py   # Basic usage example
│   └── test_script.json   # Example test script
└── tests/
    ├── test_client.py     # Unit tests for client
    ├── test_connection.py # Unit tests for connection
    └── test_protocol.py   # Unit tests for protocol
```

## Core DAP Commands

Implemented commands:
- `initialize` - Initialize debug session
- `launch` - Launch MLIR program
- `setBreakpoints` - Set breakpoints in source
- `configurationDone` - Signal configuration complete
- `continue` - Continue execution (requires threadId)
- `disconnect` - Disconnect from debug server

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

## License

MIT License

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting PRs.
