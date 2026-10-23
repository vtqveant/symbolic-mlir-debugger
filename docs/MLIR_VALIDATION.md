# MLIR Validation

Validation is local-first. Core analysis never requires a network service.

## Adapter

`debugger/compiler.py` provides `validate_mlir_text()` and `validate_mlir_file()`.

Order of preference:

1. A local `mlir-opt` (auto-detected, or set `SMD_MLIR_OPT`).
2. An explicitly configured remote endpoint (opt-in).
3. The in-tree parser, only when `fallback_to_internal=True` or `--strict` is used.

`mlir-opt` diagnostics are normalized to:

```json
{"severity": "error", "kind": "validation", "message": "...", "line": 2,
 "operation": null, "source": "mlir-opt"}
```

The agent report records the selected adapter in `summary.compiler`; validation issues
appear alongside parse/execution diagnostics.

## Agent and CLI

```bash
smlir analyze program.mlir --json
```

No network call is made by default. Passing `endpoint=` to the API enables remote
validation explicitly.

## CI and pre-commit

- `scripts/mlir_validation/validate_mlir_ci.py`
- `scripts/mlir_validation/validate_mlir_precommit.py`

Both use a local `mlir-opt` when available. Without it, validation is skipped by default
to keep CI hermetic; pass `--strict` to use the in-tree parser as a blocking fallback.

## Limitations

The in-tree parser covers the project's supported dialect subset, not all of MLIR. Install
`mlir-opt` for authoritative syntax/verifier diagnostics.
