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

## Rationale

This project provides a concrete implementation that bridges symbolic execution, MLIR compilation, and automated debugging for AI-driven code generation workflows. The current codebase delivers:

### 1. Automated Feedback for Agentic AI Code Generation
**Current Implementation:**
- **DAP-based debugging automation**: Full Debug Adapter Protocol implementation (`debugger/dap_server.py`) enables programmatic control of debugging sessions
- **Test generation and execution**: Automated test case generation (`dap_client/generator/test_case_generator.py`) and execution (`dap_client/runner/orchestrator.py`)
- **End-to-end workflows**: Complete examples (`dap_client/examples/full_workflow.py`) demonstrating automated testing pipelines
- **Structured feedback**: JSON-based test scripts with validation against schemas (`dap_client/schema/`)

**How it helps:** AI coding agents can programmatically launch debugging sessions, generate tests, and receive structured feedback without manual intervention.

### 2. MLIR-Centric Symbolic Execution Engine
**Current Implementation:**
- **MLIR parser and interpreter**: Complete MLIR text parser (`debugger/parser/`) and execution engine (`debugger/interpreter/`)
- **Symbolic execution core**: Z3-based symbolic execution (`debugger/interpreter/symbolic_evaluator.py`) transforming MLIR operations to SMT constraints
- **Path exploration**: Automated execution path discovery (`debugger/interpreter/path_explorer.py`)
- **Concolic execution**: Mixed concrete-symbolic execution with state management

**How it helps:** Provides a working symbolic execution engine specifically designed for MLIR, enabling formal analysis of MLIR programs that can target diverse hardware backends.

### 3. Extensible DAP Protocol for Debugging Automation
**Current Implementation:**
- **Standard DAP compliance**: Full stdin/stdout DAP server with Content-Length headers
- **Symbolic debugging extensions**: Custom DAP commands (`symbolic/setMode`, `symbolic/evaluate`, `symbolic/explorePaths`, `symbolic/getConstraints`)
- **Capabilities advertising**: DAP server correctly advertises symbolic debugging features (PR #96)
- **Client library**: Complete Python DAP client (`dap_client/core/client.py`) for easy integration

**How it helps:** Enables integration with existing DAP-compatible tools (IDEs, CI systems) while providing specialized symbolic debugging capabilities.

### 4. Practical Hardware-Aware Development Foundation
**Current Implementation:**
- **Dialect-extensible architecture**: Modular design allowing addition of hardware-specific MLIR dialects
- **Memory model framework**: Foundation for hardware-specific memory models (`debugger/interpreter/memory.py`)
- **Constraint propagation**: Symbolic constraints that can incorporate hardware-specific limitations
- **Fixture-based testing**: Test programs (`debugger/fixtures/`) demonstrating hardware-relevant patterns

**How it helps:** Provides the architectural foundation for incorporating hardware constraints, with working examples that can be extended for specific hardware targets.

### 5. Production-Ready Integration Points
**Current Implementation:**
- **Comprehensive test suite**: Unit and integration tests covering parser, interpreter, and DAP layers
- **CI/CD pipeline**: GitHub Actions workflow with linting and testing across Python versions
- **Documentation**: Working examples, API documentation, and now this rationale
- **Modular packaging**: Well-structured Python packages with clear dependencies

**How it helps:** The project is not just a research prototype but a production-ready system that can be integrated into larger toolchains, extended for specific use cases, and maintained over time.

### Current Limitations & Explicit Non-Goals
- **Not a complete compiler**: Focuses on debugging and analysis, not code generation
- **Limited dialect support**: Currently handles arithmetic, control flow, and basic memory operations
- **No hardware-specific backends**: Provides framework but not concrete hardware implementations
- **Research-oriented**: Prioritizes correctness and extensibility over performance optimization

This codebase delivers a working, extensible system that addresses real needs in automated code verification while providing clear extension points for future hardware-specific and AI-integration work.

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
Automatically explore all feasible execution paths through MLIR programs, identifying edge cases and boundary conditions.

### Automated Test Generation
Generate concrete test inputs that exercise different execution paths, improving test coverage.

### Bug Detection & Verification
Detect potential bugs through symbolic execution and verify program properties using SMT solving.

### MLIR Dialect Development
Test new MLIR dialects and operations with symbolic execution to ensure correctness.

## Getting Started

### Prerequisites
- Python 3.8+
- Z3 theorem prover (`pip install z3-solver`)
- MLIR text files to debug

### Installation
```bash
# Clone repository
git clone https://github.com/vtqveant/symbolic-mlir-debugger.git
cd symbolic-mlir-debugger

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
cd debugger
python -m pytest                         # Run all tests
python -m pytest tests/test_parser.py    # Run parser tests
python -m pytest -m interpreter          # Run interpreter tests
```

## DAP Client Architecture

The Symbolic MLIR Debugger uses the Debug Adapter Protocol (DAP) for communication between the debugger and clients. The DAP client connects directly to the DAP server via stdio (stdin/stdout), following the standard DAP protocol.

### **Architecture:**

```
┌─────────────────┐    stdin/stdout    ┌─────────────────┐
│   DAP Client    │ ◄────────────────► │  DAP Server     │
│  (dap_client/)  │   (DAP Protocol)   │ (dap_server.py) │
└─────────────────┘                    └─────────────────┘
```

### **Key Components:**

1. **DAP Server** (`debugger/dap_server.py`):
   - Uses **stdin/stdout** (standard DAP protocol with Content-Length headers)
   - Processes DAP requests and sends responses
   - Implements symbolic debugging capabilities
   - Automatically launched as a subprocess by the DAP client

2. **DAP Client** (`dap_client/`):
   - Uses **stdio connection** (stdin/stdout pipes) to communicate with DAP server
   - Automatically launches the DAP server as a subprocess
   - Manages the complete lifecycle of the debug session

### **Using the DAP Client:**

The DAP client automatically launches the DAP server and manages the connection:

```python
from dap_client.core.client import DAPClient

# Client automatically launches DAP server as subprocess
with DAPClient() as client:
    client.initialize(adapter_id="mlir-debugger")
    client.launch(program="example.mlir")
    # ... rest of debugging session
```

### **Configuration Options:**

You can customize the DAP client behavior:

```python
# Custom DAP server path or timeout settings
client = DAPClient(
    debugger_path="/custom/path/dap_server.py",  # Default: auto-detected
    timeout=30,      # Connection timeout in seconds
    read_timeout=10  # Read timeout in seconds
)
```

### **Testing the Setup:**

```bash
# Run basic example (automatically starts DAP server)
python dap_client/examples/basic_session.py

# Run full workflow demonstration
python dap_client/examples/full_workflow.py --program debugger/fixtures/conditional_branch.mlir
```

See [`dap_client/README.md`](dap_client/README.md) for detailed documentation on using the DAP client.

## Extending the Debugger

### Adding New Dialects
Register new MLIR dialects by extending the dialect registry and implementing operation handlers.

### Custom Memory Models
Implement custom memory models for specialized hardware or memory architectures.

### Hardware-Specific Extensions
Add hardware-specific constraints and operation semantics for target architectures.

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
