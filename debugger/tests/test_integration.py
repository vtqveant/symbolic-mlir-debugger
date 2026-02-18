#!/usr/bin/env python3
"""
Integration tests for multi-dialect debugging with DAP server.
"""

import os

import pytest
from dap_server import MLIRDebugSession


@pytest.mark.integration
def test_shape_dialect_variables(test_data_dir):
    """Test variable formatting for shape dialect operations."""
    session = MLIRDebugSession()
    program = test_data_dir / "shape_example.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), [])

    # Get variables after launch (at entry)
    variables = session.get_variables()

    # Should have no variables at entry (no concrete execution yet)
    # Actually, launch doesn't execute, just parses
    # Let's step a few times
    for i in range(3):
        session.step_next()

    variables = session.get_variables()
    print(f"Shape dialect variables after 3 steps: {len(variables)}")

    # Check variable formatting
    for var in variables:
        print(f"  {var['name']}: {var.get('value', '?')} ({var.get('type', 'unknown')})")
        if "presentationHint" in var:
            print(f"    hint: {var['presentationHint']}")

    # Basic assertion - should have some variables
    assert len(variables) > 0


@pytest.mark.integration
def test_memory_debugging(test_data_dir):
    """Test memory cell inspection in debugger."""
    session = MLIRDebugSession()
    program = test_data_dir / "memref_basic.mlir"
    if not os.path.exists(program):
        pytest.skip(f"Test file not found: {program}")

    session.launch(str(program), [])

    # Step through all operations
    for i in range(4):
        session.step_next()

    variables = session.get_variables()

    # Find memory region
    memory_regions = [v for v in variables if v.get("type") == "memory_region"]
    assert len(memory_regions) == 1, f"Expected 1 memory region, got {len(memory_regions)}"

    mem_region = memory_regions[0]
    assert mem_region["variablesReference"] > 0, "Memory region should have variablesReference > 0"

    # Test expansion
    ref_id = mem_region["variablesReference"]
    children = session.get_variable_children(ref_id)
    assert len(children) == 1, f"Expected 1 memory cell, got {len(children)}"

    cell = children[0]
    assert cell["name"] == "mem[0]", f"Expected cell name 'mem[0]', got {cell['name']}"
    assert cell["value"] == "5", f"Expected cell value '5', got {cell['value']}"
    assert cell["variablesReference"] == 0, "Memory cell should be leaf node"

    print(f"Memory debugging test passed: {mem_region['name']} with {len(children)} cells")


@pytest.mark.integration
def test_multi_dialect_debugging(test_data_dir):
    """Test debugging across multiple dialects."""
    # Create a simple multi-dialect test program
    test_mlir = """
module {
  func.func @test(%a: i32, %b: i32) -> i32 {
    // arith operation
    %sum = arith.addi %a, %b : i32

    // memref allocation and store
    %mem = memref.alloc() : memref<5xi32>
    %idx = arith.constant 0 : index
    memref.store %sum, %mem[%idx] : memref<5xi32>

    // load and return
    %result = memref.load %mem[%idx] : memref<5xi32>
    return %result : i32
  }
}
"""

    # Write temporary file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
        f.write(test_mlir)
        temp_file = f.name

    try:
        session = MLIRDebugSession()
        session.launch(temp_file, ["a=10", "b=20"])

        # Step through execution
        step_results = []
        for i in range(6):  # alloc, store, load, return
            stopped = session.step_next()
            step_results.append(stopped)

            # Check variables at each step
            variables = session.get_variables()
            print(f"\nStep {i}: {len(variables)} variables")
            for var in variables[:3]:  # Show first few
                print(f"  {var['name']}: {var.get('value', '?')}")

        # Verify final result
        variables = session.get_variables()
        result_vars = [v for v in variables if v["name"] == "result"]
        if result_vars:
            assert (
                result_vars[0]["value"] == "30"
            ), f"Expected result=30, got {result_vars[0]['value']}"

        print(f"Multi-dialect debugging test passed")

    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    # Run tests directly

    test_dir = os.path.join(os.path.dirname(__file__), "..", "tests")
    test_data_dir = type(
        "obj", (object,), {"__truediv__": lambda self, x: os.path.join(test_dir, x)}
    )()

    print("Testing shape dialect...")
    test_shape_dialect_variables(test_data_dir)

    print("\nTesting memory debugging...")
    test_memory_debugging(test_data_dir)

    print("\nTesting multi-dialect debugging...")
    test_multi_dialect_debugging(test_data_dir)
