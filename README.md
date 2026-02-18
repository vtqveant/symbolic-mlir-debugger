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

This project addresses several critical needs in modern AI-driven code generation and hardware-aware compilation:

### 1. Agentic AI Code Generation with Automated Feedback Loops
Code generation using Agentic AI requires automatically obtaining rich feedback and implementing feedback loops consisting of:
- **Code mutation and analysis** for iterative improvement
- **Compile-time diagnostics** for early error detection  
- **Functional testing** with comprehensive coverage
- **Profiling with realistic workloads** for performance optimization
- **Closed-loop refinement** where analysis results inform subsequent code generation

### 2. MLIR as Semantic Abstraction Layer
MLIR provides a powerful abstraction layer for program semantics and enables:
- **Hardware-aware compilation** through dialect mechanisms
- **Precise knowledge incorporation** of hardware design and constraints
- **Multi-level optimization** across different abstraction levels
- **Extensible operation semantics** for domain-specific computations
- **Portable performance** across diverse hardware targets

### 3. Symbolic Execution for Comprehensive Correctness
Symbolic execution enables setting comprehensive and verifiable correctness criteria:
- **Formal verification** of program properties
- **Path coverage guarantees** for test generation
- **Constraint-based validation** of hardware-specific invariants
- **Automated bug detection** through SMT solving
- **Operational environments** for coding agents with provable correctness

### 4. Custom Hardware Integration
Custom hardware (GPU, TPU, NPU, SoC, wafer-scale compute, etc.) is crucial for AI development. This system enables:
- **Hardware constraint incorporation** into symbolic debugging
- **Automated creation** of hardware-specific kernels and optimizations
- **Hybrid algorithm development** with hardware-aware transformations
- **Computation-communication overlap** optimizations (à la DeepSeek)
- **Software-hardware co-design** through formal constraints
- **ILP-related optimizations** with precise hardware modeling

### 5. DAP Extensions for Concolic Execution
Extensions of DAP with support for concolic execution provide:
- **Easy-to-use general method** for including concolic debugging in agentic workflows
- **Standardized interface** for debugging automation
- **Mixed concrete-symbolic execution** for practical verification
- **Integration with existing toolchains** through DAP protocol
- **Scalable debugging infrastructure** for large-scale code generation

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
