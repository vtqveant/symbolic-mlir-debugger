#!/usr/bin/env python3
"""
Example usage of the DAP Trace Library.

This script demonstrates how to use the library for:
1. Configuration management
2. DAP trace generation
3. Validation
4. Execution
"""

import sys
from pathlib import Path

# Add the library to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dap_trace_library.config.dialect_config import GeneratorConfig
from dap_trace_library.generation.configurable_generator import ConfigurableGenerator
from dap_trace_library.validation.mlir_validator import MLIRValidator
from dap_trace_library.validation.trace_validator import TraceValidator
from dap_trace_library.execution.trace_executor import TraceExecutor


def example_configuration():
    """Example 1: Configuration management."""
    print("=== Example 1: Configuration Management ===")
    
    # Create example configuration
    config = GeneratorConfig.create_arith_example()
    
    # Save to file
    config.save_yaml("example_config.yaml")
    print(f"Saved example configuration to: example_config.yaml")
    
    # Load from file
    loaded_config = GeneratorConfig.load_yaml("example_config.yaml")
    print(f"Loaded configuration with {len(loaded_config.dialects)} dialects")
    
    # List enabled operations
    enabled_ops = loaded_config.get_enabled_operations()
    print(f"Enabled operations: {len(enabled_ops)}")
    for op in enabled_ops[:5]:  # Show first 5
        print(f"  - {op.dialect}.{op.name}")
    if len(enabled_ops) > 5:
        print(f"  ... and {len(enabled_ops) - 5} more")
    
    print()


def example_generation():
    """Example 2: DAP trace generation."""
    print("=== Example 2: DAP Trace Generation ===")
    
    # Create configuration
    config = GeneratorConfig.create_arith_example()
    
    # Limit to a few operations for demonstration
    for dialect in config.dialects:
        if dialect.name == "arith":
            # Enable only first 3 operations
            for i, op in enumerate(dialect.operations):
                op.enabled = i < 3
    
    # Create generator
    generator = ConfigurableGenerator(config)
    
    # Generate traces
    print("Generating DAP traces...")
    result = generator.generate_all()
    
    stats = result["statistics"]
    print(f"Generation complete:")
    print(f"  MLIR files generated: {stats['mlir_files_generated']}")
    print(f"  DAP traces generated: {stats['traces_generated']}")
    print(f"  Duration: {stats['duration_seconds']:.2f}s")
    
    # Show generated files
    if result.get("tests"):
        print(f"\nGenerated tests:")
        for test in result["tests"][:3]:  # Show first 3
            print(f"  - {test['operation']}: {test['mlir_file']}")
        if len(result["tests"]) > 3:
            print(f"  ... and {len(result['tests']) - 3} more")
    
    print()


def example_validation():
    """Example 3: Validation."""
    print("=== Example 3: Validation ===")
    
    # First generate some test files
    config = GeneratorConfig.create_arith_example()
    for dialect in config.dialects:
        if dialect.name == "arith":
            for i, op in enumerate(dialect.operations):
                op.enabled = i < 2  # Enable only 2 operations
    
    generator = ConfigurableGenerator(config)
    result = generator.generate_all()
    
    # Validate MLIR files
    print("Validating MLIR files...")
    mlir_validator = MLIRValidator()
    
    mlir_dir = Path("target/trace_testing/mlir_artifacts")
    if mlir_dir.exists():
        mlir_result = mlir_validator.validate_directory(mlir_dir, recursive=False)
        print(f"MLIR validation: {mlir_result['files_valid']}/{mlir_result['files_validated']} files valid")
    
    # Validate DAP traces
    print("Validating DAP traces...")
    trace_validator = TraceValidator()
    
    trace_dir = Path("target/trace_testing/dap_traces")
    if trace_dir.exists():
        trace_result = trace_validator.validate_directory(trace_dir, recursive=False)
        print(f"DAP trace validation: {trace_result['files_valid']}/{trace_result['files_validated']} files valid")
        
        if trace_result.get("file_results"):
            for filepath, file_result in list(trace_result["file_results"].items())[:2]:
                print(f"  {Path(filepath).name}: {'VALID' if file_result['valid'] else 'INVALID'}")
                if not file_result["valid"] and file_result["errors"]:
                    print(f"    Errors: {file_result['errors'][0]}")
    
    print()


def example_execution():
    """Example 4: Trace execution."""
    print("=== Example 4: Trace Execution ===")
    
    # First generate test files
    config = GeneratorConfig.create_arith_example()
    for dialect in config.dialects:
        if dialect.name == "arith":
            for i, op in enumerate(dialect.operations):
                op.enabled = i < 1  # Enable only 1 operation
    
    generator = ConfigurableGenerator(config)
    result = generator.generate_all()
    
    # Execute traces (simulated - would need actual debugger)
    print("Note: Actual execution requires MLIR debugger binary.")
    print("This example shows the execution interface.")
    
    executor = TraceExecutor(timeout=10)
    
    trace_dir = Path("target/trace_testing/dap_traces")
    if trace_dir.exists():
        # List generated traces
        trace_files = list(trace_dir.glob("*.json"))
        print(f"Found {len(trace_files)} trace files")
        
        if trace_files:
            # Show what execution would do
            print(f"Would execute: {trace_files[0].name}")
            print("(Set debugger_path in TraceExecutor for actual execution)")
    
    print()


def example_integrated_workflow():
    """Example 5: Integrated workflow."""
    print("=== Example 5: Integrated Workflow ===")
    
    print("Complete workflow:")
    print("1. Create configuration")
    print("2. Generate MLIR artifacts and DAP traces")
    print("3. Validate syntax and format")
    print("4. Execute traces")
    print("5. Generate reports")
    print()
    
    # Create comprehensive configuration
    config = GeneratorConfig.create_arith_example()
    
    # Customize settings
    config.generation_settings["use_z3"] = True
    config.generation_settings["max_solutions_per_constraint"] = 2
    
    config.output_settings["base_dir"] = "target/demo_workflow"
    
    print(f"Configuration ready:")
    print(f"  Output directory: {config.output_settings['base_dir']}")
    print(f"  Use Z3: {config.generation_settings['use_z3']}")
    print(f"  Dialects: {[d.name for d in config.dialects]}")
    
    # The actual workflow would continue with:
    # 1. generator = ConfigurableGenerator(config)
    # 2. generation_result = generator.generate_all()
    # 3. validation_result = validator.validate_directory(...)
    # 4. execution_result = executor.execute_directory(...)
    # 5. report = executor.generate_report(...)
    
    print("\nWorkflow demonstration complete.")
    print("See individual examples for detailed usage.")


def main():
    """Run all examples."""
    print("DAP Trace Library - Example Usage\n")
    
    try:
        example_configuration()
        example_generation()
        example_validation()
        example_execution()
        example_integrated_workflow()
        
        print("\n✅ All examples completed successfully!")
        print("\nGenerated files are in target/ directories.")
        print("Clean up with: rm -rf target/")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())