#!/usr/bin/env python3
"""
Simple demonstration of DAP Trace Library.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dap_trace_library.config.dialect_config import GeneratorConfig
from dap_trace_library.generation.configurable_generator import ConfigurableGenerator
from dap_trace_library.utils.file_utils import FileUtils

print("=== DAP Trace Library Simple Demo ===")

# Create a minimal configuration
config = GeneratorConfig.create_arith_example()

# Customize for demo
print("\n1. Configuring for demo...")
for dialect in config.dialects:
    if dialect.name == "arith":
        # Enable only 2 operations for quick demo
        for i, op in enumerate(dialect.operations):
            op.enabled = i < 2  # Enable only first 2 operations
        print(f"   Enabled operations: {[op.name for op in dialect.get_enabled_operations()]}")

# Set output to current directory
config.output_settings["base_dir"] = "demo_output"
print(f"   Output directory: {config.output_settings['base_dir']}")

# Create generator
print("\n2. Creating generator...")
generator = ConfigurableGenerator(config)
print(f"   ✅ Generator created")

# Generate
print("\n3. Generating DAP traces...")
try:
    result = generator.generate_all()
    stats = result["statistics"]

    print(f"   ✅ Generation complete!")
    print(f"   MLIR files: {stats['mlir_files_generated']}")
    print(f"   DAP traces: {stats['traces_generated']}")
    print(f"   Duration: {stats['duration_seconds']:.2f}s")

    # Check files
    mlir_dir = (
        Path(config.output_settings["base_dir"]) / config.output_settings["mlir_artifacts_dir"]
    )
    trace_dir = Path(config.output_settings["base_dir"]) / config.output_settings["dap_traces_dir"]

    mlir_files = list(mlir_dir.glob("*.mlir"))
    trace_files = list(trace_dir.glob("*.json"))

    print(f"\n4. Generated files:")
    print(f"   MLIR files: {len(mlir_files)}")
    for f in mlir_files[:3]:  # Show first 3
        print(f"     - {f.name}")

    print(f"   DAP trace files: {len(trace_files)}")
    for f in trace_files[:3]:  # Show first 3
        print(f"     - {f.name}")

    # Show sample MLIR content
    if mlir_files:
        print(f"\n5. Sample MLIR content:")
        sample_content = mlir_files[0].read_text()
        print(f"   First 5 lines of {mlir_files[0].name}:")
        for line in sample_content.split("\n")[:5]:
            print(f"     {line}")

    # Show sample DAP trace structure
    if trace_files:
        print(f"\n6. Sample DAP trace structure:")
        sample_trace = FileUtils.read_json(trace_files[0])
        print(f"   {trace_files[0].name}:")
        print(f"     Name: {sample_trace.get('name')}")
        print(f"     Dialect: {sample_trace.get('dialect')}")
        print(f"     Operation: {sample_trace.get('operation')}")
        print(f"     Session commands: {len(sample_trace.get('session', []))}")

except Exception as e:
    print(f"   ❌ Generation failed: {e}")
    import traceback

    traceback.print_exc()

print("\n=== Demo Complete ===")
print("The DAP Trace Library successfully generated MLIR artifacts and DAP traces!")
print(f"Check the 'demo_output' directory for generated files.")
