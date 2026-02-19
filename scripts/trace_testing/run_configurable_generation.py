#!/usr/bin/env python3
"""
Demonstration script for configurable arithmetic generator.
"""

import os
import sys
from pathlib import Path


def main():
    """Run configurable generator demonstration."""
    print("Configurable Arithmetic Generator Demonstration")
    print("=" * 60)

    # Check if config file exists
    config_path = Path("target/trace_testing/arith_ops_config.yaml")
    if not config_path.exists():
        print(f"ERROR: Configuration file not found at {config_path}")
        print("Please ensure the configuration file exists.")
        return 1

    # Check if generator script exists
    generator_path = Path("scripts/dap_trace_generation/configurable_arith_generator.py")
    if not generator_path.exists():
        print(f"ERROR: Generator script not found at {generator_path}")
        print("Please ensure the generator script exists.")
        return 1

    print(f"Configuration file: {config_path}")
    print(f"Generator script: {generator_path}")
    print()

    # Show available commands
    print("Available commands:")
    print(
        "1. python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml"
    )
    print(
        "2. python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --mlir-only"
    )
    print(
        "3. python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --traces-only"
    )
    print(
        "4. python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --dry-run"
    )
    print()

    # Show configuration summary
    try:
        import yaml

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        enabled_ops = [op["name"] for op in config["operations"] if op.get("enabled", False)]
        disabled_ops = [op["name"] for op in config["operations"] if not op.get("enabled", False)]

        print("Configuration Summary:")
        print(f"  Dialect: {config['dialect']}")
        print(f"  Total operations: {len(config['operations'])}")
        print(f"  Enabled operations: {len(enabled_ops)}")
        print(f"  Disabled operations: {len(disabled_ops)}")
        print()

        print("Enabled operations (first 10):")
        for op in enabled_ops[:10]:
            print(f"  - {op}")
        if len(enabled_ops) > 10:
            print(f"  ... and {len(enabled_ops) - 10} more")
        print()

        print("Generation settings:")
        settings = config.get("generation_settings", {})
        for key, value in list(settings.items())[:5]:
            print(f"  {key}: {value}")
        if len(settings) > 5:
            print(f"  ... and {len(settings) - 5} more settings")
        print()

    except Exception as e:
        print(f"Warning: Could not parse configuration: {e}")
        print()

    # Show expected output structure
    print("Expected output structure:")
    print("  target/trace_testing/arith_ops_config.yaml          # Configuration")
    print("  target/trace_testing/arith_ops_documentation.md     # Documentation")
    print("  target/trace_testing/test_artifacts/mlir/arith/  # MLIR files")
    print("  target/trace_testing/generated_tests/arith_comprehensive/  # DAP traces")
    print("  target/trace_testing/manifest/arith_test_manifest.json     # Manifest")
    print("  target/trace_testing/docs/arith_test_coverage.md           # Coverage report")
    print("  target/trace_testing/docs/test_artifact_guide.md           # Usage guide")
    print()

    # Run test to verify everything works
    print("Running verification test...")
    test_script = Path("scripts/test_configurable_generator.py")
    if test_script.exists():
        import subprocess

        result = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Verification test passed")
        else:
            print("✗ Verification test failed")
            print(result.stderr)
    else:
        print("Warning: Test script not found")

    print()
    print("To generate tests, run:")
    print(
        "  python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
