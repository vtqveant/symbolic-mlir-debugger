# Symbolic MLIR Debugger

[![CI](https://github.com/vtqveant/symbolic-mlir-debugger/actions/workflows/ci.yml/badge.svg)](https://github.com/vtqveant/symbolic-mlir-debugger/actions/workflows/ci.yml)

A symbolic and concolic execution engine for MLIR with an agent-facing feedback API and
Debug Adapter Protocol (DAP) support.

## What it does

- Parses an MLIR subset (func, arith, cf, scf, affine, memref, tensor, vector, linalg,
  shape, bufferization, emitc) into an interpreter model.
- Executes programs concretely and concolically, explores feasible paths with Z3, and
  reports inputs, path conditions, and return values.
- Produces one-shot JSON feedback for automated coding loops, including parse/execution
  diagnostics, compiler-validation results, and unsupported-operation warnings.
- Exposes the same engine through a stdio DAP server and a Python DAP client.

The authoritative plan, decisions, and task history live in the hosted tm service at
https://www.eventflow.ru (see `AGENTS.md`). Old design/plan files are not kept in the
repository.

## Install

Python 3.9+ is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e . --no-deps
```

## Quick start

```bash
# Structured feedback for an automated coding loop
smlir analyze debugger/fixtures/conditional_branch.mlir --json

# Human-readable summary
smlir analyze debugger/fixtures/conditional_branch.mlir

# Explicit inputs and deterministic path exploration
smlir analyze debugger/fixtures/simple_add.mlir --input a=5 --input b=3 --seed 0

# Interactive DAP adapter
python -m debugger dap

# DAP client example (launches the adapter automatically)
python dap_client/examples/basic_session.py
```

`python -m debugger analyze ...` is equivalent to `smlir analyze ...`. The Python API is
`debugger.agent.analyze_file()` / `analyze_text()`.

## Agent feedback contract

Reports are JSON-serializable and versioned (`schema_version`). A report contains:

- `status`: `ok` or `error`
- `function` and `summary` (path count, truncation, seed, compiler source,
  unsupported-operation count)
- `diagnostics`: parse, execution, path, limit, input, io, or validation issues with
  severity/line/operation when available
- `paths`: feasible paths with concrete inputs, path conditions, and return values

Compiler validation is local-first: `mlir-opt` is used when installed, with an in-tree
fallback only when requested. No network service is required.

## Architecture

```
debugger/              parser, interpreter, Z3 paths, DAP adapter, agent API
dap_client/            Python DAP client, generators, runners, examples
dap_trace_library/     trace execution/validation adapters (no generation layer)
scripts/mlir_validation/  hermetic CI/pre-commit validation helpers
```

## Tests

```bash
python -m pytest
```

The suite is configured in `pyproject.toml` and includes `debugger/tests`,
`dap_client/tests`, and `dap_trace_library/tests`.

## Limitations

- This is not a complete MLIR/LLVM compiler; it interprets a supported subset.
- Dialect coverage is intentionally incremental. Unsupported operations are reported as
  warnings, and results may be incomplete.
- Remote MCP/LSP validation is opt-in and never on the default path.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.txt](NOTICE.txt). The vendored parser is based on
pymlir; see [LICENSE-PYMLIR.txt](LICENSE-PYMLIR.txt).
