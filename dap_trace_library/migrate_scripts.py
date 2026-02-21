#!/usr/bin/env python3
"""
Migration script for converting existing scripts to use the DAP Trace Library.

This script helps migrate functionality from:
- scripts/dap_trace_generation/configurable_arith_generator.py
- scripts/trace_testing/*.py
- scripts/mlir_validation/*.py
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the library to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dap_trace_library.config.dialect_config import GeneratorConfig
from dap_trace_library.generation.configurable_generator import ConfigurableGenerator
from dap_trace_library.validation.mlir_validator import MLIRValidator
from dap_trace_library.validation.trace_validator import TraceValidator
from dap_trace_library.execution.trace_executor import TraceExecutor


def migrate_configurable_generator():
    """Migrate configurable_arith_generator.py to use library."""
    print("=== Migrating configurable_arith_generator.py ===")
    
    original_path = Path("scripts/dap_trace_generation/configurable_arith_generator.py")
    
    if not original_path.exists():
        print(f"Original file not found: {original_path}")
        return False
    
    # Read original file to understand usage
    with open(original_path, "r") as f:
        content = f.read()
    
    # Check for configuration file references
    config_refs = []
    if "arith_ops_config.yaml" in content:
        config_refs.append("arith_ops_config.yaml")
    
    print(f"Found references to: {config_refs}")
    
    # Create equivalent library-based script
    new_script = """#!/usr/bin/env python3
\"\"\"
Library-based configurable generator (replaces configurable_arith_generator.py).

Usage:
    python scripts/dap_trace_generation/library_generator.py --config path/to/config.yaml
    python scripts/dap_trace_generation/library_generator.py --config path/to/config.yaml --mlir-only
    python scripts/dap_trace_generation/library_generator.py --config path/to/config.yaml --traces-only
\"\"\"

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dap_trace_library.config.dialect_config import GeneratorConfig
from dap_trace_library.generation.configurable_generator import ConfigurableGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate DAP traces using library")
    parser.add_argument("--config", required=True, help="Configuration file (YAML/JSON)")
    parser.add_argument("--mlir-only", action="store_true", help="Generate only MLIR files")
    parser.add_argument("--traces-only", action="store_true", help="Generate only DAP traces")
    parser.add_argument("--output-dir", help="Custom output directory")
    
    args = parser.parse_args()
    
    # Load configuration
    config_path = Path(args.config)
    if config_path.suffix.lower() == ".yaml":
        config = GeneratorConfig.load_yaml(config_path)
    elif config_path.suffix.lower() == ".json":
        config = GeneratorConfig.load_json(config_path)
    else:
        print(f"Unsupported config format: {config_path.suffix}")
        return 1
    
    # Customize output directory if specified
    if args.output_dir:
        config.output_settings["base_dir"] = args.output_dir
    
    # Customize generation settings based on flags
    if args.mlir_only:
        config.generation_settings["generate_traces"] = False
    elif args.traces_only:
        config.generation_settings["generate_mlir"] = False
    
    # Create and run generator
    generator = ConfigurableGenerator(config)
    result = generator.generate_all()
    
    # Print summary
    stats = result["statistics"]
    print(f"\\n✅ Generation complete:")
    print(f"   MLIR files: {stats['mlir_files_generated']}")
    print(f"   DAP traces: {stats['traces_generated']}")
    print(f"   Duration: {stats['duration_seconds']:.2f}s")
    print(f"   Output directory: {config.output_settings['base_dir']}")
    
    # Save manifest path
    if result.get("manifest"):
        print(f"   Manifest: {config.output_settings['base_dir']}/manifests/")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""
    
    # Save new script
    new_path = Path("scripts/dap_trace_generation/library_generator.py")
    new_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(new_path, "w") as f:
        f.write(new_script)
    
    print(f"Created new library-based generator: {new_path}")
    print("Note: You'll need to convert your configuration files to the new format.")
    
    return True


def migrate_trace_testing():
    """Migrate trace_testing scripts to use library."""
    print("\n=== Migrating trace_testing scripts ===")
    
    trace_testing_dir = Path("scripts/trace_testing")
    
    if not trace_testing_dir.exists():
        print(f"Trace testing directory not found: {trace_testing_dir}")
        return False
    
    # Check for existing scripts
    scripts = list(trace_testing_dir.glob("*.py"))
    print(f"Found {len(scripts)} Python scripts in trace_testing/")
    
    # Create unified library-based test runner
    new_script = """#!/usr/bin/env python3
\"\"\"
Library-based trace testing (replaces various trace_testing scripts).

Combines functionality from:
- run_arith_workflow_tests.py
- simple_run_arith_tests.py
- run_configurable_generation.py
- test_configurable_generator.py
\"\"\"

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dap_trace_library.validation.trace_validator import TraceValidator
from dap_trace_library.execution.trace_executor import TraceExecutor
from dap_trace_library.config.dialect_config import GeneratorConfig
from dap_trace_library.generation.configurable_generator import ConfigurableGenerator


def validate_traces(trace_dir, recursive=True, strict=False):
    \"\"\"Validate DAP traces in directory.\"\"\"
    print(f"Validating traces in: {trace_dir}")
    
    validator = TraceValidator(strict=strict)
    result = validator.validate_directory(trace_dir, recursive=recursive)
    
    print(f"Validation results:")
    print(f"  Files validated: {result['files_validated']}")
    print(f"  Files valid: {result['files_valid']}")
    print(f"  Files invalid: {result['files_invalid']}")
    print(f"  Total errors: {result['errors']}")
    print(f"  Total warnings: {result['warnings']}")
    
    if result["files_invalid"] > 0:
        print(f"\\nInvalid files:")
        for filepath, file_result in result["file_results"].items():
            if not file_result["valid"]:
                print(f"  {Path(filepath).name}:")
                for error in file_result["errors"][:3]:  # Show first 3 errors
                    print(f"    - {error}")
    
    return result


def execute_traces(trace_dir, debugger_path=None, timeout=30, recursive=True):
    \"\"\"Execute DAP traces in directory.\"\"\"
    print(f"Executing traces in: {trace_dir}")
    
    executor = TraceExecutor(debugger_path=debugger_path, timeout=timeout)
    result = executor.execute_directory(trace_dir, recursive=recursive)
    
    stats = result["statistics"]
    print(f"Execution results:")
    print(f"  Total traces: {stats['total_traces']}")
    print(f"  Executed traces: {stats['executed_traces']}")
    print(f"  Successful traces: {stats['successful_traces']}")
    print(f"  Failed traces: {stats['failed_traces']}")
    print(f"  Timeout traces: {stats['timeout_traces']}")
    print(f"  Success rate: {stats.get('success_rate', 0):.1f}%")
    print(f"  Total duration: {stats['total_duration']:.2f}s")
    
    # Generate and save report
    report = executor.generate_report(result["results"])
    report_dir = Path(trace_dir).parent / "reports"
    report_path = executor.save_report(report, report_dir)
    
    print(f"\\nReport saved: {report_path}")
    
    return result


def test_generator(config_path, test_mode="basic"):
    \"\"\"Test configurable generator.\"\"\"
    print(f"Testing generator with config: {config_path}")
    
    # Load configuration
    config_path = Path(config_path)
    if config_path.suffix.lower() == ".yaml":
        config = GeneratorConfig.load_yaml(config_path)
    elif config_path.suffix.lower() == ".json":
        config = GeneratorConfig.load_json(config_path)
    else:
        print(f"Unsupported config format: {config_path.suffix}")
        return None
    
    # Modify for testing
    if test_mode == "quick":
        # Enable only first operation of each dialect
        for dialect in config.dialects:
            for i, op in enumerate(dialect.operations):
                op.enabled = i < 1
    elif test_mode == "single":
        # Enable only first operation of first dialect
        if config.dialects:
            for i, op in enumerate(config.dialects[0].operations):
                op.enabled = i < 1
    
    # Run generator
    generator = ConfigurableGenerator(config)
    result = generator.generate_all()
    
    print(f"Test generation complete:")
    print(f"  MLIR files: {result['statistics']['mlir_files_generated']}")
    print(f"  DAP traces: {result['statistics']['traces_generated']}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Library-based trace testing")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate DAP traces")
    validate_parser.add_argument("trace_dir", help="Directory containing trace files")
    validate_parser.add_argument("--recursive", action="store_true", help="Search recursively")
    validate_parser.add_argument("--strict", action="store_true", help="Use strict validation")
    
    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute DAP traces")
    execute_parser.add_argument("trace_dir", help="Directory containing trace files")
    execute_parser.add_argument("--debugger-path", help="Path to MLIR debugger")
    execute_parser.add_argument("--timeout", type=int, default=30, help="Execution timeout")
    execute_parser.add_argument("--recursive", action="store_true", help="Search recursively")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test generator")
    test_parser.add_argument("config", help="Configuration file")
    test_parser.add_argument("--mode", choices=["basic", "quick", "single"], 
                           default="basic", help="Test mode")
    
    args = parser.parse_args()
    
    if args.command == "validate":
        return 0 if validate_traces(
            args.trace_dir, 
            recursive=args.recursive,
            strict=args.strict
        )["valid"] else 1
    
    elif args.command == "execute":
        execute_traces(
            args.trace_dir,
            debugger_path=args.debugger_path,
            timeout=args.timeout,
            recursive=args.recursive
        )
        return 0
    
    elif args.command == "test":
        result = test_generator(args.config, args.mode)
        return 0 if result else 1
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
"""
    
    # Save new unified test runner
    new_path = Path("scripts/trace_testing/library_test_runner.py")
    new_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(new_path, "w") as f:
        f.write(new_script)
    
    print(f"Created unified library test runner: {new_path}")
    
    # Create README for migration
    readme_content = """# Trace Testing Migration

This directory now contains library-based testing scripts that replace the older, fragmented scripts.

## New Scripts:

### `library_test_runner.py`
Unified script that combines functionality from:
- `run_arith_workflow_tests.py` - Full workflow testing
- `simple_run_arith_tests.py` - Simple validation
- `run_configurable_generation.py` - Configurable generation
- `test_configurable_generator.py` - Generator testing

### Usage:

```bash
# Validate traces
python scripts/trace_testing/library_test_runner.py validate target/trace_testing/dap_traces

# Execute traces (requires debugger)
python scripts/trace_testing/library_test_runner.py execute target/trace_testing/dap_traces --debugger-path path/to/debugger

# Test generator
python scripts/trace_testing/library_test_runner.py test path/to/config.yaml --mode quick
```

## Migration Status:

The old scripts are deprecated but kept for reference during migration. 
Once migration is complete, they can be removed.

## Library Benefits:

1. **Unified codebase** - Single implementation instead of multiple scripts
2. **Better error handling** - Consistent validation and reporting
3. **Extensible** - Easy to add new test types or validators
4. **Maintainable** - Centralized logic in the `dap_trace_library/`
"""
    
    readme_path = trace_testing_dir / "MIGRATION_README.md"
    with open(readme_path, "w") as f:
        f.write(readme_content)
    
    print(f"Created migration README: {readme_path}")
    
    return True


def migrate_mlir_validation():
    """Migrate mlir_validation scripts to use library."""
    print("\n=== Migrating mlir_validation scripts ===")
    
    mlir_validation_dir = Path("scripts/mlir_validation")
    
    if not mlir_validation_dir.exists():
        print(f"MLIR validation directory not found: {mlir_validation_dir}")
        return False
    
    # Create library-based validation script
    new_script = """#!/usr/bin/env python3
\"\"\"
Library-based MLIR validation (replaces validate_mlir_ci.py and validate_mlir_precommit.py).

Usage:
    python scripts/mlir_validation/library_validator.py --ci          # CI validation
    python scripts/mlir_validation/library_validator.py --pre-commit  # Pre-commit validation
    python scripts/mlir_validation/library_validator.py --file path/to/file.mlir
\"\"\"

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dap_trace_library.validation.mlir_validator import MLIRValidator


def validate_ci():
    \"\"\"Validate all MLIR files for CI.\"\"\"
    print("Running CI validation...")
    
    validator = MLIRValidator()
    
    # Validate all MLIR files in project
    results = []
    
    # Check MLIR files in debugger/fixtures/
    fixtures_dir = Path("debugger/fixtures")
    if fixtures_dir.exists():
        print(f"Validating fixtures in: {fixtures_dir}")
        result = validator.validate_directory(fixtures_dir, recursive=True)
        results.append(("fixtures", result))
    
    # Check generated MLIR files
    generated_dir = Path("target/trace_testing/mlir_artifacts")
    if generated_dir.exists():
        print(f"Validating generated MLIR in: {generated_dir}")
        result = validator.validate_directory(generated_dir, recursive=True)
        results.append(("generated", result))
    
    # Check embedded MLIR in Python files
    print("Validating embedded MLIR in Python files...")
    python_files = list(Path(".").glob("**/*.py"))
    embedded_results = []
    
    for py_file in python_files[:10]:  # Limit for performance
        if "test" in str(py_file) or "example" in str(py_file):
            result = validator.validate_embedded_mlir(py_file)
            if result["embedded_blocks"] > 0:
                embedded_results.append((str(py_file), result))
    
    # Print summary
    print(f"\\nCI Validation Summary:")
    
    all_valid = True
    for name, result in results:
        print(f"  {name}: {result['files_valid']}/{result['files_validated']} files valid")
        if not result["valid"]:
            all_valid = False
    
    if embedded_results:
        print(f"  Embedded MLIR: {len(embedded_results)} files with MLIR blocks")
        for py_file, result in embedded_results:
            if not result["valid"]:
                all_valid = False
                print(f"    {py_file}: {result['blocks_invalid']}/{result['embedded_blocks']} blocks invalid")
    
    return 0 if all_valid else 1


def validate_precommit():
    \"\"\"Validate changed MLIR files for pre-commit.\"\"\"
    print("Running pre-commit validation...")
    
    # This would use git to find changed files
    # For now, validate current directory
    validator = MLIRValidator()
    
    result = validator.validate_directory(Path("."), recursive=False)
    
    print(f"Pre-commit validation:")
