# MLIR Syntax Validation

This document describes the MLIR syntax validation tools integrated into the symbolic-mlir-debugger project.

## Overview

The project now includes comprehensive MLIR syntax validation using the official MLIR Language Server Protocol (LSP) via a REST API wrapper. This ensures that all MLIR code in the repository follows correct syntax before it's used in tests or production.

## Validation Tools

### 1. CI Pipeline Integration (`mlir-validation.yml`)

**Location**: `.github/workflows/mlir-validation.yml`

**Purpose**: Automatically validates MLIR syntax on:
- Push to `main` or `develop` branches
- Pull requests
- Daily schedule (00:00 UTC)
- Manual trigger

**Features**:
- Validates all `.mlir` files in the repository
- Validates embedded MLIR in Python test files
- Creates detailed validation reports
- Comments on PRs with validation failures
- Uploads validation reports as artifacts

**Usage**: Automatically runs as part of GitHub Actions.

### 2. Pre-commit Hook (`validate_mlir_precommit.py`)

**Location**: `scripts/mlir_validation/validate_mlir_precommit.py`

**Purpose**: Validates MLIR syntax before commits to catch errors early.

**Features**:
- Validates only staged/changed files for speed
- Supports both `.mlir` files and embedded MLIR in Python
- Provides detailed error messages with line numbers
- Integrates with `pre-commit` framework

**Setup**:
```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Run on staged files only (default)
git commit  # hooks run automatically
```

**Configuration**: See `.pre-commit-config.yaml`

### 3. Monitoring Script (`mlir_monitoring.py`)

**Location**: `/root/.openclaw/workspace/mlir_monitoring.py` (external tool)

**Purpose**: Periodic monitoring of MLIR syntax health.

**Features**:
- Comprehensive validation of entire repository
- JSON output for integration with monitoring systems
- Command-line interface for automation
- Exit codes for success/failure

**Usage**:
```bash
python3 mlir_monitoring.py /path/to/repository
```

### 4. CI Validation Script (`validate_mlir_ci.py`)

**Location**: `scripts/mlir_validation/validate_mlir_ci.py`

**Purpose**: Core validation logic used by CI and pre-commit.

**Features**:
- Validates all MLIR files and embedded code
- Clear console output with success/failure indicators
- JSON report generation
- Used by both CI and pre-commit tools

**Standalone Usage**:
```bash
python3 scripts/mlir_validation/validate_mlir_ci.py
```

## LSP Server

All validation tools use the MLIR LSP wrapper API:

**Endpoint**: `https://api.niche-robotics.tech/api/v1/diagnostics`

**Source**: `agentic-playground` repository (`.opencode/skills/mlir-lsp-server/`)

**Capabilities**:
- Official MLIR language server diagnostics
- Line and character position information
- Support for all MLIR dialects
- Fast validation (~0.2 seconds per file)

## Validation Scope

### Files Validated:

1. **All `.mlir` files** in the repository (excluding `.venv/` and `__pycache__/`)
2. **Python test files** with embedded MLIR:
   - `debugger/tests/test_advanced_dap.py`
   - `debugger/tests/test_debug.py`
   - `debugger/tests/test_integration.py`
   - `debugger/tests/test_interpreter.py`
   - `debugger/tests/test_memory_ops.py`
   - `debugger/tests/test_operations.py`
   - `debugger/tests/test_parser.py`

### Common Issues Detected:

1. **Type mismatches**: Using `i32` where `index` is required (e.g., memref operations)
2. **Syntax errors**: Missing parentheses, brackets, or colons
3. **Invalid operations**: Using unsupported operations or dialects
4. **Block argument issues**: Incorrect `cf.br` syntax with block arguments

## Integration with Development Workflow

### For Developers:

1. **Pre-commit**: Automatic validation before each commit
2. **CI**: Automatic validation on PRs and pushes
3. **Manual**: Run `python3 scripts/mlir_validation/validate_mlir_ci.py` anytime

### For CI/CD:

1. **Pull Requests**: Validation runs automatically, comments on failures
2. **Main Branch**: Daily validation ensures ongoing syntax health
3. **Artifacts**: Validation reports saved for debugging

### For Monitoring:

1. **Periodic checks**: Use `mlir_monitoring.py` for scheduled validation
2. **Health metrics**: Track validation success/failure rates
3. **Alerting**: Set up alerts for syntax regression

## Troubleshooting

### Common Problems:

1. **LSP Server Unavailable**:
   - Check network connectivity
   - Verify API endpoint is accessible
   - Check `agentic-playground` repository status

2. **False Positives**:
   - Some dynamic MLIR generation (f-strings) may trigger false positives
   - Use dictionary templates instead of f-strings for MLIR in tests
   - See `test_parser.py` for examples

3. **Performance Issues**:
   - Pre-commit hook validates only staged files
   - CI runs in parallel with other checks
   - Large files may timeout; increase timeout in scripts

### Debugging:

1. **Run validation manually**:
   ```bash
   python3 scripts/mlir_validation/validate_mlir_ci.py
   ```

2. **Check specific files**:
   ```bash
   python3 scripts/mlir_validation/validate_mlir_precommit.py -- path/to/file.mlir
   ```

3. **View detailed report**:
   - CI: Download `mlir-validation-report` artifact
   - Pre-commit: Error output in console
   - Monitoring: JSON output file

## Best Practices

1. **Write valid MLIR**: Use the LSP during development to catch errors early
2. **Test MLIR separately**: Validate MLIR syntax before running complex tests
3. **Update tests when fixing**: When fixing MLIR syntax, update test assertions if needed
4. **Monitor regularly**: Use scheduled validation to catch regressions
5. **Document changes**: Update this document when adding new validation features

## Future Enhancements

1. **Local LSP Server**: Run MLIR LSP locally for offline validation
2. **Editor Integration**: Integrate with VS Code, Neovim, etc.
3. **Custom Rules**: Add project-specific validation rules
4. **Performance Optimization**: Cache validation results for unchanged files
5. **Integration with other tools**: Combine with linters, formatters, etc.

## Related Resources

- [MLIR Language Reference](https://mlir.llvm.org/docs/LangRef/)
- [MLIR LSP Server](https://github.com/llvm/llvm-project/tree/main/mlir/tools/mlir-lsp-server)
- [agentic-playground MLIR LSP Skill](https://github.com/vtqveant/agentic-playground/tree/main/.opencode/skills/mlir-lsp-server)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pre-commit Framework](https://pre-commit.com/)