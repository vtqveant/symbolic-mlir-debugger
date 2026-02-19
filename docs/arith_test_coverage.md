# Arithmetic Dialect Test Coverage Report

## Overview
- **Generated**: 2026-02-19T20:59:28.440227Z
- **Configuration**: arith_ops_config.yaml
- **Total Operations**: 30
- **Enabled Operations**: 30
- **Disabled Operations**: 0
- **Coverage Percentage**: 100.0%

## Statistics
- MLIR Files Generated: 282
- DAP Traces Generated: 6
- Validation Passed: 6
- Validation Failed: 0

## Enabled Operations
- **addi**: 0 test(s)
- **subi**: 0 test(s)
- **muli**: 1 test(s)
- **divsi**: 0 test(s)
- **divui**: 0 test(s)
- **remsi**: 0 test(s)
- **remui**: 0 test(s)
- **addf**: 0 test(s)
- **subf**: 0 test(s)
- **mulf**: 0 test(s)
- **divf**: 0 test(s)
- **cmpi**: 0 test(s)
- **cmpf**: 0 test(s)
- **constant**: 0 test(s)
- **extsi**: 0 test(s)
- **extui**: 0 test(s)
- **trunci**: 0 test(s)
- **sitofp**: 0 test(s)
- **uitofp**: 0 test(s)
- **fptosi**: 0 test(s)
- **fptoui**: 0 test(s)
- **andi**: 0 test(s)
- **ori**: 0 test(s)
- **xori**: 5 test(s)
- **shli**: 0 test(s)
- **shrsi**: 0 test(s)
- **shrui**: 0 test(s)
- **select**: 0 test(s)
- **index_cast**: 0 test(s)
- **bitcast**: 0 test(s)

## Disabled Operations

## Test Artifacts
- **MLIR Artifacts Directory**: test_artifacts/mlir/arith
- **DAP Traces Directory**: generated_tests/arith_comprehensive
- **Manifest File**: manifest/arith_test_manifest.json

## Validation Results
- **Total Validated**: 6
- **Pass Rate**: 100.0%

## Configuration Details
```yaml
dialect: arith
enabled_operations_count: 30
generation_settings: {'output_dir': 'generated_tests/arith_comprehensive', 'mlir_artifacts_dir': 'test_artifacts/mlir/arith', 'manifest_dir': 'manifest', 'include_edge_cases': True, 'use_z3_constraints': True, 'validation_level': 'strict', 'mlir_artifacts': True, 'max_traces_per_op': 10, 'solver_timeout_ms': 5000, 'max_paths_per_op': 20, 'validate_mlir': True, 'validate_traces': True, 'validation_timeout_ms': 10000, 'trace_format': 'json', 'manifest_format': 'json', 'documentation_format': 'markdown'}
```

## Next Steps
1. Review generated test artifacts
2. Run comprehensive test suite with DAP client
3. Extend coverage to other dialects
4. Update configuration as needed
