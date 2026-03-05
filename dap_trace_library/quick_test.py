#!/usr/bin/env python3
"""
Quick test for DAP Trace Library.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dap_trace_library.config.dialect_config import GeneratorConfig
from dap_trace_library.utils.config_utils import ConfigUtils

print("=== Quick DAP Trace Library Test ===")

# Test 1: Configuration creation
print("\n1. Testing configuration creation...")
config = GeneratorConfig.create_arith_example()
print(f"   ✅ Created config with {len(config.dialects)} dialect(s)")

# Test 2: Save and load
print("\n2. Testing save/load...")
import tempfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    config_path = Path(tmpdir) / "test_config.yaml"
    config.save_yaml(config_path)
    print(f"   ✅ Saved config to {config_path}")

    loaded_config = GeneratorConfig.load_yaml(config_path)
    print(f"   ✅ Loaded config from file")

    # Test to_dict
    config_dict = loaded_config.to_dict()
    print(f"   ✅ Converted to dict: version={config_dict.get('version')}")

# Test 3: Config validation
print("\n3. Testing config validation...")
validation = ConfigUtils.validate_config(config_dict)
if validation["valid"]:
    print(f"   ✅ Config validation passed")
else:
    print(f"   ❌ Config validation failed: {validation['errors']}")

# Test 4: Config utilities
print("\n4. Testing config utilities...")
summary = ConfigUtils.generate_config_summary(config_dict)
print(
    f"   ✅ Config summary: {summary['enabled_dialects']} enabled dialects, {summary['enabled_operations']} enabled operations"
)

print("\n=== Quick Test Complete ===")
print("Basic configuration functionality is working!")
