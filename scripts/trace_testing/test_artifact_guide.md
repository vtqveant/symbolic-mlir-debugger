# Test Artifact Usage Guide

## Overview
This guide explains how to use the generated MLIR artifacts and DAP traces for testing arithmetic dialect operations.

## File Structure
The generated test suite follows this structure:
- target/trace_testing/arith_ops_config.yaml - Configuration file
- target/trace_testing/test_artifacts/mlir/arith/ - Individual MLIR files organized by operation
- target/trace_testing/generated_tests/arith_comprehensive/ - DAP trace files
- target/trace_testing/manifest/arith_test_manifest.json - Test suite manifest
- docs/ - Documentation files

## Using MLIR Artifacts

### Individual Validation
```bash
# Validate a single MLIR file
python scripts/mlir_validation/validate_mlir_precommit.py target/trace_testing/test_artifacts/mlir/arith/addi/addi_basic_i32.mlir

# Validate all MLIR files
find target/trace_testing/test_artifacts/mlir/arith -name "*.mlir" -exec python scripts/mlir_validation/validate_mlir_precommit.py {} \;
```

### Manual Testing
```python
from mlir.ir import Context, Module
import mlir.dialects.arith as arith

# Load and parse MLIR file
with open("target/trace_testing/test_artifacts/mlir/arith/addi/addi_basic_i32.mlir", "r") as f:
    mlir_code = f.read()

with Context() as ctx:
    # Register dialects
    arith.register_dialect(ctx)
    
    # Parse module
    module = Module.parse(mlir_code, ctx)
    
    # Use the module for testing
```

## Using DAP Traces

### Running Individual Traces
```python
from dap_client.runner.test_runner import TestRunner
import json

# Load trace
with open("target/trace_testing/generated_tests/arith_comprehensive/addi/addi_basic_i32.json", "r") as f:
    trace_data = json.load(f)

# Create runner and execute
runner = TestRunner()
results = runner.run_tests(trace_data['test_cases'], "target/trace_testing/test_artifacts/mlir/arith/addi/addi_basic_i32.mlir")

# Check results
for i, result in enumerate(results):
    status = "PASS" if result['passed'] else "FAIL"
    print(f"Test case {i}: {status}")
```

### Batch Execution
```bash
# Run all traces (using existing script if available)
python scripts/run_arith_workflow_tests.py --traces-dir target/trace_testing/generated_tests/arith_comprehensive
```

## Using the Manifest

### Querying Test Suite
```python
import json

# Load manifest
with open("target/trace_testing/manifest/arith_test_manifest.json", "r") as f:
    manifest_data = json.load(f)

# Get all tests for a specific operation
addi_tests = [t for t in manifest_data['tests'] if t['operation'] == 'arith.addi']

# Get validated tests
validated_tests = [t for t in manifest_data['tests'] if t['validated']]

print(f"Total tests: {len(manifest_data['tests'])}")
print(f"Validated tests: {len(validated_tests)}")
```

### Coverage Analysis
```python
# Analyze operation coverage
operations = set(t['operation'] for t in manifest_data['tests'])
print(f"Operations covered: {len(operations)}")
```

## Regenerating Tests

### Full Regeneration
```bash
    python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml
```

### MLIR Only
```bash
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --mlir-only
```

### Traces Only
```bash
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --traces-only
```

## Custom Configuration

### Modifying Configuration
Edit `target/trace_testing/arith_ops_config.yaml` to:
1. Enable/disable operations
2. Adjust bitwidths
3. Modify constraints
4. Change generation settings

### Adding New Operations
1. Add operation definition to configuration
2. Ensure MLIR generation method exists
3. Regenerate tests

## Troubleshooting

### Common Issues
1. **MLIR validation fails**: Check MLIR syntax, ensure proper dialect registration
2. **DAP trace execution fails**: Verify DAP client setup, check test case format
3. **Missing operations**: Ensure operation is enabled in configuration

### Debugging
```bash
# Verbose output
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --verbose

# Dry run (no file generation)
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --dry-run
```

## Integration with CI
Add to your CI pipeline:
```yaml
- name: Generate and Test Arithmetic Operations
  run: |
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml
    python scripts/validate_test_suite.py --manifest target/trace_testing/manifest/arith_test_manifest.json
```

## Extending to Other Dialects
The same pattern can be applied to other MLIR dialects:
1. Create dialect documentation
2. Define configuration format
3. Implement generator script
4. Generate test artifacts

## Support
For issues or questions:
1. Check the manifest for validation status
2. Review generated documentation
3. Consult MLIR and DAP client documentation
