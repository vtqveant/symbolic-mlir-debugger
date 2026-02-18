#!/usr/bin/env python3
"""Test parser fix for bufferization.alloc_tensor with parentheses."""

import sys
import importlib

# Clear any cached parser modules
modules_to_clear = [
    "debugger.parser.dialects.bufferization",
    "debugger.parser.dialect",
    "debugger.parser.parser",
    "debugger.parser.parser_transformer",
]

for module_name in modules_to_clear:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Now import fresh
from debugger.parser import parse_string

# Test the fixture
with open("debugger/fixtures/bufferization_example.mlir", "r") as f:
    content = f.read()

print("Testing bufferization_example.mlir...")
try:
    mlir_file = parse_string(content)
    print("✅ Parser SUCCESS with parentheses")
    print(f"  Modules: {len(mlir_file.modules)}")
except Exception as e:
    print(f"❌ Parser FAILED: {e}")

# Test simple version
print("\nTesting test_simple_bufferization.mlir...")
with open("test_simple_bufferization.mlir", "r") as f:
    content = f.read()

try:
    mlir_file = parse_string(content)
    print("✅ Parser SUCCESS with parentheses")
    print(f"  Modules: {len(mlir_file.modules)}")
except Exception as e:
    print(f"❌ Parser FAILED: {e}")

# Also test without parentheses (should fail MLIR LSP)
print("\nTesting test_bufferization_no_parens.mlir...")
with open("test_bufferization_no_parens.mlir", "r") as f:
    content = f.read()

try:
    mlir_file = parse_string(content)
    print("✅ Parser SUCCESS without parentheses")
    print(f"  Modules: {len(mlir_file.modules)}")
except Exception as e:
    print(f"❌ Parser FAILED without parentheses: {e}")
