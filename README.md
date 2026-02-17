# Symbolic MLIR Debugger

[![CI](https://github.com/vtqveant/symbolic-mlir-debugger/actions/workflows/ci.yml/badge.svg)](https://github.com/vtqveant/symbolic-mlir-debugger/actions/workflows/ci.yml)

<div align="center">
  <img src="mlir-debug-icon.jpg" alt="MLIR Debug Logo" width="200" height="200">
</div>

A symbolic and concolic execution engine for MLIR (Multi-Level Intermediate Representation) programs 
with Debug Adapter Protocol (DAP) support for automated human-free debugging.

## Overview

The Symbolic MLIR Debugger enables advanced debugging and analysis of MLIR programs through symbolic execution. 
It transforms MLIR operations into SMT constraints using the Z3 solver, allowing for path exploration, 
constraint solving, and automated test generation.

### Key Features

- **Symbolic & Concolic Execution**: Execute MLIR programs with symbolic inputs, exploring multiple execution paths simultaneously
- **SMT Integration**: Leverages Z3 theorem prover for constraint solving and path feasibility analysis
- **DAP Integration**: Extended DAP implementation for debugging automation with breakpoints, variable inspection, and step-through execution
- **Modular Architecture**: Extensible dialect support, memory models, and hardware descriptions
- **Path Exploration**: Automatically discovers and analyzes all feasible execution paths
- **Test Generation**: Generates concrete test cases covering different execution paths

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Coding Agent                          │
│                  (Debug Adapter Protocol)                   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                 Symbolic MLIR Debugger                      │
├─────────────────────────────────────────────────────────────┤
│  • Parser (MLIR text → AST)                                 │
│  • Symbolic Interpreter (MLIR → Z3 constraints)             │
│  • Concolic Engine (Mixed concrete/symbolic execution)      │
│  • Dialect Registry (Extensible operation handlers)         │
│  • State Manager (Path forking & merging)                   │
└─────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                     Z3 SMT Solver                           │
│               (Constraint solving & SAT)                    │
└─────────────────────────────────────────────────────────────┘
```

## Applications

### Execution Path Exploration
Discover all feasible execution paths through MLIR programs, identifying:
- Unreachable code segments
- Boundary conditions
- Path constraints and dependencies

### Automated Test Generation
Generate comprehensive test suites by:
- Solving path constraints to produce concrete inputs
- Covering different execution paths
- Creating regression tests for MLIR transformations

### Bug Detection & Verification
- Detect potential division-by-zero errors
- Identify array bounds violations
- Verify loop invariants and postconditions

### MLIR Dialect Development
- Test new MLIR dialects and operations
- Validate dialect lowering transformations
- Debug complex MLIR compilation pipelines

## Getting Started

### Prerequisites
- Python 3.8+
- Z3 solver (`pip install z3-solver`)

### Installation

```bash
# Clone the repository
git clone https://github.com/vtqveant/symbolic-mlir-debugger.git
cd symbolic-mlir-debugger

# Install Python dependencies
cd debugger
pip install -r requirements.txt
```

### Architecture Overview

The Symbolic MLIR Debugger uses the Debug Adapter Protocol (DAP) for debugging automation. It provides two communication modes:

1. **Stdio Mode** (for testing): The DAP server communicates via stdin/stdout with Content-Length headers
2. **TCP Mode** (for production use): The DAP client connects via TCP on port 5678

For most use cases, you'll use the **TCP wrapper** which starts the DAP server in a subprocess and exposes it via TCP.

### Running Tests

```bash
cd debugger
python -m pytest                         # Run all tests
python -m pytest tests/test_parser.py    # Run parser tests
python -m pytest -m interpreter          # Run interpreter tests
```

### Using the DAP Client

The DAP client is located in the `dap_client/` directory. It provides:
- Full DAP protocol implementation
- Socket-based communication with the server
- Test case generation and execution
- Symbolic debugging support

See [`dap_client/README.md`](dap_client/README.md) for detailed documentation on using the DAP client.

## Extending the Debugger

### Adding New Dialects
1. Create dialect file in `debugger/parser/dialects/`
2. Define operation classes inheriting from `DialectOp`
3. Implement symbolic execution handlers in `debugger/interpreter/dialects/`
4. Register the dialect in the appropriate `__init__.py` files

### Custom Memory Models
Override memory operations in `debugger/interpreter/memory.py` to implement:
- Different pointer semantics
- Custom allocation strategies
- Hardware-specific memory hierarchies

### Hardware-Specific Extensions
Implement backend-specific operations for:
- GPU/accelerator memory operations
- Complex SoC data paths
- Intra-core ILP synchronization constraints
- Vector/SIMD instructions
- Custom arithmetic types for quantized and mixed-precision computation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Third-Party Components:**
- pymlir parser (BSD 3-Clause License) - see [LICENSE-PYMLIR.txt](LICENSE-PYMLIR.txt)

Full attribution details in [NOTICE.txt](NOTICE.txt).

## Acknowledgments

- Based on pymlir from ETH Zurich's Scalable Parallel Computing Lab
- Relies on Debug Adapter Protocol from Microsoft
- Built with Z3 theorem prover from Microsoft Research
- MLIR community for the intermediate representation framework

## Contributing

Contributions are welcome! Please see the [AGENTS.md](AGENTS.md) file for development guidelines and code style conventions.