# Scripts Directory Organization

This directory contains utility scripts organized by purpose as per Issue #110.

## Directory Structure

### `dap_trace_generation/` - DAP trace generation scripts
- **`generate_arith_tests.py`** - Generate DAP test traces for arithmetic operations
  - Uses existing test_case_generator and path_aware_generator
- **`simple_generate_arith_tests.py`** - Simple DAP trace generation
  - Manual test file creation based on expected format
- **`z3_concrete_generator.py`** - Z3-based concrete value generation
  - Implements Issue #108: Generate actual Z3-based concrete values
- **`implement_issue_108.py`**, **`issue_108_solution.py`**, **`final_issue_108.py`**
  - Various implementations for Issue #108 (Z3 concrete value generation)

### `trace_testing/` - Trace-based testing scripts
- **`run_arith_workflow_tests.py`** - Run full workflow tests for arithmetic operations
  - Executes generated DAP traces and validates MLIR debugger
- **`simple_run_arith_tests.py`** - Simple test execution
  - Validates DAP trace format and execution

### `mlir_validation/` - MLIR validation scripts
- **`validate_mlir_ci.py`** - CI pipeline validation
  - Validates all MLIR files and embedded MLIR code in repository
- **`validate_mlir_precommit.py`** - Pre-commit hook validation
  - Validates only staged/changed MLIR files for speed
  - Used by `.pre-commit-config.yaml`

### `coding_subagents/` - Scripts used by coding subagents
- *(Currently empty - to be populated with subagent workflow scripts)*

## Usage Notes

### Pre-commit Hooks
- MLIR validation: `scripts/mlir_validation/validate_mlir_precommit.py`
- Configuration: `.pre-commit-config.yaml`

### DAP Trace Generation
- Main generator: `python scripts/dap_trace_generation/generate_arith_tests.py`
- Simple generator: `python scripts/dap_trace_generation/simple_generate_arith_tests.py`
- Z3 generator: `python scripts/dap_trace_generation/z3_concrete_generator.py`

### Trace Testing
- Full workflow: `python scripts/trace_testing/run_arith_workflow_tests.py`
- Simple testing: `python scripts/trace_testing/simple_run_arith_tests.py`

## Maintenance

When adding new scripts:
1. Place them in the appropriate subdirectory based on purpose
2. Update this README.md with description
3. Update any configuration files that reference the script

When removing scripts:
1. Remove from appropriate subdirectory
2. Update this README.md
3. Update any configuration files that referenced the script

## History

- **Issue #110**: Organized scripts by purpose (2026-02-19)
- Created subdirectories: `dap_trace_generation/`, `trace_testing/`, `mlir_validation/`, `coding_subagents/`
- Updated pre-commit configuration to reference new path