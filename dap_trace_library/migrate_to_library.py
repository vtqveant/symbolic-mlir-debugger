#!/usr/bin/env python3
"""
Migration script for converting existing scripts to use the DAP Trace Library.

This script helps migrate functionality from existing scripts to the new
unified library system as per Issue #116.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dap_trace_library.utils.logging_utils import LoggingUtils
from dap_trace_library.utils.file_utils import FileUtils
from dap_trace_library.utils.config_utils import ConfigUtils

logger = LoggingUtils.setup_module_logging(__name__)


class LibraryMigrator:
    """Migrate existing scripts to use DAP Trace Library."""
    
    def __init__(self, project_root: Path = None):
        """Initialize migrator.
        
        Args:
            project_root: Project root directory
        """
        if project_root is None:
            project_root = Path.cwd()
        
        self.project_root = Path(project_root)
        self.library_root = self.project_root / "dap_trace_library"
        
        # Migration mapping
        self.migration_map = self._create_migration_map()
        
        logger.info(f"Initialized migrator for project: {self.project_root}")
    
    def _create_migration_map(self) -> Dict[str, Dict[str, Any]]:
        """Create mapping of old scripts to new library modules.
        
        Returns:
            Migration mapping dictionary
        """
        return {
            # dap_trace_generation scripts
            "scripts/dap_trace_generation/configurable_arith_generator.py": {
                "module": "generation.configurable_generator",
                "class": "ConfigurableGenerator",
                "functionality": "Main generator for DAP traces",
                "status": "needs_conversion",
                "new_path": "scripts/dap_trace_generation/library_generator.py"
            },
            
            # trace_testing scripts
            "scripts/trace_testing/run_arith_workflow_tests.py": {
                "module": "execution.trace_executor",
                "class": "TraceExecutor",
                "functionality": "Execute DAP traces",
                "status": "needs_conversion",
                "new_path": "scripts/trace_testing/library_test_runner.py"
            },
            "scripts/trace_testing/simple_run_arith_tests.py": {
                "module": "validation.trace_validator",
                "class": "TraceValidator",
                "functionality": "Validate DAP trace format",
                "status": "needs_conversion",
                "new_path": "scripts/trace_testing/library_test_runner.py"
            },
            "scripts/trace_testing/run_configurable_generation.py": {
                "module": "generation.configurable_generator",
                "class": "ConfigurableGenerator",
                "functionality": "Run configurable generation",
                "status": "needs_conversion",
                "new_path": "scripts/trace_testing/library_test_runner.py"
            },
            "scripts/trace_testing/test_configurable_generator.py": {
                "module": "generation.configurable_generator",
                "class": "ConfigurableGenerator",
                "functionality": "Test generator functionality",
                "status": "needs_conversion",
                "new_path": "scripts/trace_testing/library_test_runner.py"
            },
            "scripts/trace_testing/end_to_end_workflow.py": {
                "module": "execution.trace_executor",
                "class": "TraceExecutor",
                "functionality": "End-to-end workflow testing",
                "status": "needs_conversion",
                "new_path": "scripts/trace_testing/library_test_runner.py"
            },
            "scripts/trace_testing/update_arith_manifest.py": {
                "module": "generation.base_generator",
                "class": "BaseGenerator",
                "functionality": "Update generation manifest",
                "status": "needs_conversion",
                "new_path": "scripts/trace_testing/library_test_runner.py"
            },
            
            # mlir_validation scripts
            "scripts/validate_mlir_ci.py": {
                "module": "validation.mlir_validator",
                "class": "MLIRValidator",
                "functionality": "CI validation of MLIR files",
                "status": "needs_conversion",
                "new_path": "scripts/mlir_validation/library_validator.py"
            },
            "scripts/validate_mlir_precommit.py": {
                "module": "validation.mlir_validator",
                "class": "MLIRValidator",
                "functionality": "Pre-commit validation",
                "status": "needs_conversion",
                "new_path": "scripts/mlir_validation/library_validator.py"
            },
            
            # Configuration files
            "config/arith_ops_config.yaml": {
                "module": "config.dialect_config",
                "class": "GeneratorConfig",
                "functionality": "Arithmetic ops configuration",
                "status": "needs_conversion",
                "new_path": "config/library_config.yaml"
            }
        }
    
    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current script state.
        
        Returns:
            Analysis results
        """
        analysis = {
            "total_scripts": 0,
            "found_scripts": [],
            "missing_scripts": [],
            "script_sizes": {},
            "migration_status": {}
        }
        
        for script_path, migration_info in self.migration_map.items():
            full_path = self.project_root / script_path
            
            analysis["total_scripts"] += 1
            
            if full_path.exists():
                size = full_path.stat().st_size
                analysis["found_scripts"].append(script_path)
                analysis["script_sizes"][script_path] = size
                analysis["migration_status"][script_path] = "exists"
            else:
                analysis["missing_scripts"].append(script_path)
                analysis["migration_status"][script_path] = "missing"
        
        # Calculate total size
        total_size = sum(analysis["script_sizes"].values())
        analysis["total_size_kb"] = total_size / 1024
        
        logger.info(f"Analysis complete: {len(analysis['found_scripts'])}/{analysis['total_scripts']} scripts found")
        return analysis
    
    def create_library_generator(self) -> Path:
        """Create library-based generator script.
        
        Returns:
            Path to created script
        """
        script_content = '''#!/usr/bin/env python3
"""
Library-based configurable generator (replaces configurable_arith_generator.py).

Usage:
    python scripts/dap_trace_generation/library_generator.py --config path/to/config.yaml
    python scripts/dap_trace_generation/library_generator.py --config path/to/config.yaml --mlir-only
    python scripts/dap_trace_generation/library_generator.py --config path/to/config.yaml --traces-only
"""

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
    parser.add_argument("--validate", action="store_true", help="Validate generated files")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
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
    
    if not args.validate:
        config.generation_settings["validate_mlir"] = False
        config.generation_settings["validate_traces"] = False
    
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
    
    if result.get("dialect_statistics"):
        for dialect, d_stats in result["dialect_statistics"].items():
            print(f"   {dialect}: {d_stats['mlir_files']} MLIR, {d_stats['traces']} traces")
    
    # Save manifest path
    if result.get("manifest"):
        print(f"   Manifest: {config.output_settings['base_dir']}/manifests/")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
        
        output_path = self.project_root / "scripts/dap_trace_generation/library_generator.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            f.write(script_content)
        
        # Make executable
        output_path.chmod(0o755)
        
        logger.info(f"Created library generator: {output_path}")
        return output_path
    
    def create_library_test_runner(self) -> Path:
        """Create library-based test runner script.
        
        Returns:
            Path to created script
        """
        script_content = '''#!/usr/bin/env python3
"""
Library-based trace testing (replaces various trace_testing scripts).

Combines functionality from:
- run_arith_workflow_tests.py
- simple_run_arith_tests.py
- run_configurable_generation.py
- test_configurable_generator.py
- end_to_end_workflow.py
- update_arith_manifest.py
"""

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
from dap_trace_library.validation.mlir_validator import MLIRValidator


def validate_traces(trace_dir, recursive=True, strict=False):
    """Validate DAP traces in directory."""
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
    """Execute DAP traces in directory."""
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
    """Test configurable generator."""
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


def validate_mlir(mlir_dir, recursive=True):
    """Validate MLIR files."""
    print(f"Validating MLIR files in: {mlir_dir}")
    
    validator = MLIRValidator()
    result = validator.validate_directory(mlir_dir, recursive=recursive)
    
    print(f"MLIR validation results:")
    print(f"  Files validated: {result['files_validated']}")
    print(f"  Files valid: {result['files_valid']}")
    print(f"  Files invalid: {result['files_invalid']}")
    print(f"  Total errors: {result['errors']}")
    print(f"  Total warnings: {result['warnings']}")
    
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
    
    # MLIR validation command
    mlir_parser = subparsers.add_parser("mlir", help="Validate MLIR files")
    mlir_parser.add_argument("mlir_dir", help="Directory containing MLIR files")
    mlir_parser.add_argument("--recursive", action="store_true", help="Search recursively")
    
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
