# Scripts

Only the hermetic MLIR validation helpers remain.

## `mlir_validation/`

- `validate_mlir_ci.py`: validate repository `.mlir` files and embedded MLIR blocks.
- `validate_mlir_precommit.py`: staged-file validation entry point.

Both use a local `mlir-opt` when available. Without it they skip by default so CI and
pre-commit stay offline; pass `--strict` to use the in-tree parser as a blocking fallback.

```bash
python scripts/mlir_validation/validate_mlir_ci.py
python scripts/mlir_validation/validate_mlir_precommit.py --staged
```

The active agent feedback path is `smlir analyze`. Trace execution/validation lives in
`dap_trace_library`; old trace-generation, trace-testing, and coding-subagent scripts were
removed as dead/duplicate code.

See `AGENTS.md` and tm epic `SMD` for current work.
