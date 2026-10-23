# Symbolic MLIR Debugger Engine

This package contains the MLIR parser, concrete/concolic interpreter, Z3 path
exploration, and the stdio DAP adapter.

## Layout

- `parser/`: vendored pymlir fork and dialect definitions.
- `interpreter/`: parser adapter, operation handlers, state model, stepper, concolic
  interpreter, path exploration, and memory models.
- `tests/`: unit, parser, interpreter, concolic, memory, and DAP tests.
- `fixtures/`: MLIR programs used by tests and examples.
- `dap_server.py`: stdio DAP server used by `dap_client`.

The old `src/` and `tests/` command examples in earlier revisions are obsolete.

## Entry points

From the repository root (activate `.venv` first):

```bash
# Structured, actionable feedback for automated coding
python -m debugger analyze debugger/fixtures/conditional_branch.mlir --json

# Interactive DAP server over stdio
python -m debugger dap
```

The Python API is `debugger.agent.analyze_file()` / `analyze_text()`. The DAP client
remains the supported automation path for interactive sessions. See the repository
`AGENTS.md` for the tm workflow and the authoritative milestone plan.
