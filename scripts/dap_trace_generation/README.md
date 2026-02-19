# DAP Trace Generation Scripts

This directory contains scripts for generating DAP (Debug Adapter Protocol) test traces for MLIR operations.

## Script Organization

### Configurable Generators
- `configurable_arith_generator.py` - Configurable generator for arithmetic dialect operations

### Legacy Generators
- `generate_arith_tests.py` - Legacy arithmetic test generator
- `simple_generate_arith_tests.py` - Simple arithmetic test generator
- `z3_concrete_generator.py` - Z3-based concrete value generator

## Usage

### Configurable Arithmetic Generator
```bash
# Full generation
python scripts/dap_trace_generation/configurable_arith_generator.py --config config/arith_ops_config.yaml

# MLIR artifacts only
python scripts/dap_trace_generation/configurable_arith_generator.py --config config/arith_ops_config.yaml --mlir-only

# DAP traces only
python scripts/dap_trace_generation/configurable_arith_generator.py --config config/arith_ops_config.yaml --traces-only

# Custom directories
python scripts/dap_trace_generation/configurable_arith_generator.py --config config/arith_ops_config.yaml --mlir-dir test_artifacts/mlir/arith --trace-dir generated_tests/arith_comprehensive
```

### Legacy Generators
```bash
# Generate arithmetic tests
python generate_arith_tests.py

# Simple generation
python simple_generate_arith_tests.py

# Z3 concrete values
python z3_concrete_generator.py
```

## Configuration

### Arithmetic Dialect Configuration
The configurable generator uses `config/arith_ops_config.yaml` which defines:
- Enabled operations
- Bitwidths for each operation
- Constraints and edge cases
- Generation settings

### Backward Compatibility
The new configurable generator maintains backward compatibility with:
- Existing MLIR fixtures
- Existing DAP trace format
- Existing validation scripts
- Existing test runners

## Output Structure

### Generated Files
```
test_artifacts/mlir/arith/
  addi/
    addi_basic_i32.mlir
    addi_const_i32.mlir
    ...
  cmpi/
    cmpi_eq_i32.mlir
    ...
  ...

generated_tests/arith_comprehensive/
  addi/
    addi_basic_i32.json
    ...
  cmpi/
    cmpi_eq_i32.json
    ...
  ...

manifest/
  arith_test_manifest.json
```

### Manifest File
The manifest file (`arith_test_manifest.json`) contains:
- List of all generated tests
- Mapping between MLIR files and DAP traces
- Validation status
- Statistics and metadata

## Validation

### MLIR Validation
```bash
# Validate individual MLIR file
python scripts/mlir_validation/validate_mlir_precommit.py test_artifacts/mlir/arith/addi/addi_basic_i32.mlir

# Validate all MLIR files
find test_artifacts/mlir/arith -name "*.mlir" -exec python scripts/mlir_validation/validate_mlir_precommit.py {} \;
```

### DAP Trace Validation
DAP traces are validated by actually running them with the DAP client using existing test runners.

## Extending to Other Dialects

To add support for other MLIR dialects:

1. Create configuration file in `../config/`
2. Implement generator script following the same pattern
3. Add MLIR generation methods for new operations
4. Update documentation

## Testing

Run the test suite:
```bash
python ../test_configurable_generator.py
```

## Dependencies

- Python 3.8+
- PyYAML for configuration parsing
- MLIR LSP server for validation
- DAP client for trace execution
- Z3 for constraint solving (optional)

## Notes

- The configurable generator determines number of variations based on solver findings, not manual configuration
- All generated MLIR files are validated with MLIR LSP server
- All DAP traces are validated by actually running with DAP client
- Backward compatibility is maintained with existing scripts