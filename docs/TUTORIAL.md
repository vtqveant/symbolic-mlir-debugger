# Symbolic MLIR Debugger - Tutorial

A comprehensive, step-by-step tutorial for using the Symbolic MLIR Debugger.

## 📋 Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Setting Up Your Environment](#setting-up-your-environment)
4. [Your First Debugging Session](#your-first-debugging-session)
5. [Understanding the DAP Protocol](#understanding-the-dap-protocol)
6. [Symbolic Debugging Basics](#symbolic-debugging-basics)
7. [Test Generation](#test-generation)
8. [Advanced Topics](#advanced-topics)
9. [Troubleshooting](#troubleshooting)

## 1. Introduction

The Symbolic MLIR Debugger is a powerful tool for analyzing MLIR (Multi-Level Intermediate Representation) programs through symbolic execution. It transforms MLIR operations into SMT constraints using the Z3 solver, enabling:

- **Path exploration**: Discover all feasible execution paths
- **Test generation**: Create concrete test cases automatically
- **Bug detection**: Find potential issues through symbolic analysis
- **Verification**: Prove program properties using SMT solving

## 2. Architecture Overview

### Core Components

```
┌─────────────────┐    stdin/stdout    ┌─────────────────┐    TCP 5678    ┌─────────────────┐
│   DAP Client    │ ◄────────────────► │  TCP Wrapper    │ ◄────────────► │   Your Code     │
│  (dap_client/)  │   (DAP Protocol)   │ (server.py)     │   (Socket)     │                 │
└─────────────────┘                    └─────────────────┘                └─────────────────┘
                                         │
                                         ▼ stdin/stdout
                                 ┌─────────────────┐
                                 │  DAP Server     │
                                 │ (dap_server.py) │
                                 └─────────────────┘
```

### Key Directories
- `debugger/` - Core debugger implementation
- `dap_client/` - DAP client library and examples
- `debugger/fixtures/` - Example MLIR programs
- `dap_client/examples/` - Usage examples

## 3. Setting Up Your Environment

### 3.1 Installation
Follow the [QUICKSTART.md](../QUICKSTART.md) for the fastest setup.

### 3.2 Verify Installation
```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
python -c "import z3; print('Z3 installed:', z3.get_version_string())"
python -c "import jsonschema; print('jsonschema installed')"

# Run a simple test
cd debugger
python -m pytest tests/test_parser.py -v
```

### 3.3 Understanding the Project Structure
```bash
symbolic-mlir-debugger/
├── README.md          # Main documentation
├── QUICKSTART.md      # Quick start guide (this file)
├── debugger/          # Core debugger implementation
│   ├── dap_server.py      # DAP server (stdin/stdout)
│   ├── fixtures/          # Example MLIR programs
│   └── tests/            # Test suite
├── dap_client/        # DAP client library
│   ├── core/             # Core client implementation
│   ├── examples/         # Usage examples
│   ├── integration/      # Integration utilities
│   └── tests/           # Client tests
└── docs/              # Documentation (this directory)
```

## 4. Your First Debugging Session

### 4.1 Start the TCP Wrapper
The DAP server uses stdin/stdout protocol, but clients expect TCP. The TCP wrapper bridges this gap:

```bash
# Terminal 1 - Start the wrapper
python dap_client/integration/server.py --debug
```

You should see:
```
✅ TCP wrapper listening on localhost:5678
✅ DAP server subprocess started
✅ Ready for DAP client connections
```

### 4.2 Run the Basic Example
```bash
# Terminal 2 - Run basic example
python dap_client/examples/basic_session.py
```

### 4.3 What Happens
The basic example:
1. Connects to the TCP wrapper on port 5678
2. Initializes a DAP session
3. Launches an MLIR program (`debugger/fixtures/simple_add.mlir`)
4. Sets a breakpoint
5. Starts execution

### 4.4 Expected Output
```
DAP Client Basic Session Example
==================================================

1. Connecting to DAP server...
   Connected successfully!

2. Initializing session...
   Initialized: {'success': True, ...}

3. Launching program...
   Launched: {'success': True, ...}

4. Setting breakpoints...
   Breakpoints set: {'success': True, ...}

5. Configuration done...
   Configuration complete: {'success': True, ...}
```

## 5. Understanding the DAP Protocol

### 5.1 Why the TCP Wrapper is Needed
- **DAP Server**: Uses stdin/stdout (standard DAP protocol)
- **DAP Client**: Expects TCP socket connection
- **TCP Wrapper**: Bridges stdin/stdout ↔ TCP

### 5.2 Manual Communication (Advanced)
You can communicate directly with the DAP server:

```bash
# Start DAP server directly
python debugger/dap_server.py

# Then send DAP messages via stdin
# Format: Content-Length: <length>\r\n\r\n<json>
```

### 5.3 Using the DAP Client Programmatically
```python
from dap_client.core.client import DAPClient

# Connect to TCP wrapper (not directly to DAP server)
with DAPClient(host="localhost", port=5678) as client:
    # Initialize session
    client.initialize(adapter_id="mlir-debugger", client_id="my-client")
    
    # Launch program
    client.launch(program="debugger/fixtures/simple_add.mlir")
    
    # Set breakpoints
    client.set_breakpoints(
        source={"path": "debugger/fixtures/simple_add.mlir"},
        breakpoints=[{"line": 1}]
    )
    
    # Start execution
    client.configuration_done()
```

## 6. Symbolic Debugging Basics

### 6.1 Enabling Symbolic Mode
```python
from dap_client.core.client import DAPClient

with DAPClient(host="localhost", port=5678) as client:
    client.initialize(adapter_id="mlir-debugger")
    client.launch(program="debugger/fixtures/conditional_branch.mlir")
    
    # Enable symbolic debugging
    client.symbolic_set_mode(enabled=True)
    
    # Evaluate symbolic expression
    result = client.symbolic_evaluate(expression="%a < %b", frame_id=0)
    print(f"Symbolic evaluation: {result}")
    
    # Explore execution paths
    paths = client.symbolic_explore_paths(max_paths=10)
    print(f"Found {len(paths)} execution paths")
    
    # Get current constraints
    constraints = client.symbolic_get_constraints()
    print(f"Current constraints: {constraints}")
```

### 6.2 Understanding Symbolic Execution
Symbolic execution treats program inputs as symbolic variables rather than concrete values. The debugger:

1. **Tracks constraints** on symbolic variables
2. **Explores all feasible paths** through the program
3. **Generates concrete test cases** for each path
4. **Detects infeasible paths** using SMT solving

### 6.3 Example: Conditional Branch Analysis
Consider this MLIR program:
```mlir
func.func @conditional(%arg0: i32, %arg1: i32) -> i32 {
  %cmp = arith.cmpi slt, %arg0, %arg1 : i32
  cond_br %cmp, ^true, ^false
^true:
  %result = arith.addi %arg0, %arg1 : i32
  return %result : i32
^false:
  %result2 = arith.subi %arg0, %arg1 : i32
  return %result2 : i32
}
```

The symbolic debugger will:
1. Treat `%arg0` and `%arg1` as symbolic variables
2. Explore both branches (true and false)
3. Generate constraints: `%arg0 < %arg1` for true branch, `%arg0 >= %arg1` for false branch
4. Create concrete test cases satisfying each constraint

## 7. Test Generation

### 7.1 Automated Test Generation
The DAP client includes powerful test generators:

```python
from dap_client.generator.test_case_generator import TestCaseGenerator

generator = TestCaseGenerator(host="localhost", port=5678)
generator.connect()

# Generate test cases from MLIR program
test_scripts = generator.generate_from_program(
    program_path="debugger/fixtures/conditional_branch.mlir",
    max_paths=5
)

# Save generated tests
for i, test_script in enumerate(test_scripts):
    with open(f"test_case_{i}.json", "w") as f:
        import json
        json.dump(test_script, f, indent=2)
```

### 7.2 Path-Aware Test Generation
```python
from dap_client.generator.path_aware_generator import PathAwareTestCaseGenerator

generator = PathAwareTestCaseGenerator(host="localhost", port=5678)
generator.connect()

# Generate tests targeting specific paths
targeted_tests = generator.generate_targeted_tests(
    program_path="debugger/fixtures/nested_conditional.mlir",
    target_path_ids=[0, 1, 2]  # Target specific execution paths
)
```

### 7.3 Test Execution
```python
from dap_client.runner.test_runner import TestRunner

runner = TestRunner(host="localhost", port=5678)

# Run a single test
result = runner.run_test("test_case_0.json")
print(f"Test result: {result['success']}")

# Run multiple tests in parallel
from dap_client.runner.orchestrator import TestOrchestrator

orchestrator = TestOrchestrator(
    host="localhost",
    port=5678,
    max_parallel_sessions=3
)

results = orchestrator.run_tests([
    "test_case_0.json",
    "test_case_1.json",
    "test_case_2.json"
])

report = orchestrator.generate_report(results)
print(f"Test report: {report}")
```

## 8. Advanced Topics

### 8.1 Custom Dialect Support
The debugger supports extending with custom MLIR dialects. See `debugger/dialects/` for examples.

### 8.2 Memory Model Configuration
Configure custom memory models for specialized hardware.

### 8.3 Hardware-Specific Constraints
Add constraints for target architectures.

### 8.4 Performance Optimization
- Use path merging to reduce state explosion
- Configure solver timeouts
- Enable parallel execution

## 9. Troubleshooting

### Common Issues

#### Issue: "Connection refused" when connecting DAP client
**Solution:** Make sure TCP wrapper is running:
```bash
python dap_client/integration/server.py
```

#### Issue: DAP client connects but commands fail
**Solution:** Check DAP server logs (wrapper captures stderr):
```bash
python dap_client/integration/server.py --debug
```

#### Issue: Symbolic debugging not working
**Solution:** Ensure Z3 is installed:
```bash
pip install z3-solver
```

#### Issue: MLIR program fails to parse
**Solution:** Check MLIR syntax and supported dialects.

### Debugging Tips

1. **Enable debug logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Check TCP wrapper status**:
```python
from dap_client.integration.server import DAPServerWrapper
wrapper = DAPServerWrapper()
wrapper.start()
print(f"Status: {wrapper.get_status()}")
```

3. **Test DAP communication manually**:
```bash
# Use netcat to send raw DAP messages
echo -e 'Content-Length: 45\r\n\r\n{"command":"initialize","type":"request"}' | nc localhost 5678
```

## 🎓 Next Steps

Now that you've completed this tutorial:

1. **Explore the examples** in `dap_client/examples/`
2. **Read the API documentation** in `docs/API.md`
3. **Check out the test suite** to understand testing patterns
4. **Try creating your own MLIR programs** and debug them
5. **Extend the debugger** with custom dialects or memory models

## 📚 Additional Resources

- [MLIR Documentation](https://mlir.llvm.org/)
- [Debug Adapter Protocol Specification](https://microsoft.github.io/debug-adapter-protocol/)
- [Z3 Theorem Prover](https://github.com/Z3Prover/z3)
- [Project GitHub Repository](https://github.com/vtqveant/symbolic-mlir-debugger)

---

**Need help?** Check the [GitHub Issues](https://github.com/vtqveant/symbolic-mlir-debugger/issues) or create a new issue with your question.