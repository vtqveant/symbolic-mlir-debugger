# Symbolic MLIR Debugger

A symbolic execution engine for MLIR programs with Debug Adapter Protocol (DAP) support.

## Phase 1: Foundation

### Goals

1. Implement basic symbolic interpreter for MLIR core dialects (func, arith, scf, cf)
2. Map MLIR operations to Z3 expressions
3. Handle control flow with path forking
4. Support simple arithmetic and branching

### Directory Structure

- `tests/`: MLIR test programs
- `src/`: Python implementation
- `results/`: Execution results and logs

### Test Programs

1. `simple_add.mlir`: Basic arithmetic addition
2. `conditional_branch.mlir`: Conditional branching (max function)
3. `simple_loop.mlir`: Simple loop (sum of first n numbers)

### Dependencies

- Python 3.8+
- Z3 Python bindings (`z3-solver`)
- (Optional) MLIR Python bindings

### Usage

```bash
cd symbolic_mlir_debugger
python src/symbolic_interpreter.py tests/simple_add.mlir
```

### Next Steps

- Implement MLIR parser for text format
- Create symbolic execution engine with Z3 integration
- Add support for more MLIR dialects
- Integrate with MLIR Python bindings when available
- Implement DAP server for debugging interface

### Documentation

- Z3 Programming: https://z3prover.github.io/papers/programmingz3.html
