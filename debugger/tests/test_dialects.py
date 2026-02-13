"""Dialect-specific parsing tests."""

import pytest
from pathlib import Path


@pytest.mark.dialect
def test_affine_example_parsing(parser, dialect_examples_dir):
    """Test parsing of affine dialect examples."""
    affine_file = dialect_examples_dir / "affine_example.mlir"
    assert affine_file.exists()

    functions = parser.parse_file(str(affine_file))
    assert len(functions) == 2

    expected_functions = {
        "affine_for_example",
        "affine_memref_example",
    }
    assert set(functions.keys()) == expected_functions

    # Check each function has expected operations
    for name, func in functions.items():
        assert len(func.basic_blocks) == 1
        bb = list(func.basic_blocks.values())[0]
        assert len(bb.operations) > 0
        # Should contain affine operations
        affine_ops = [op for op in bb.operations if op.full_name.startswith("affine.")]
        assert len(affine_ops) > 0


@pytest.mark.dialect
def test_func_example_parsing(parser, dialect_examples_dir):
    """Test parsing of func dialect examples."""
    func_file = dialect_examples_dir / "func_example.mlir"
    assert func_file.exists()

    functions = parser.parse_file(str(func_file))
    assert len(functions) == 3

    expected_functions = {"add", "caller", "process_buffer"}
    assert set(functions.keys()) == expected_functions

    # Check func.call operation in caller function
    caller_func = functions["caller"]
    caller_bb = list(caller_func.basic_blocks.values())[0]
    caller_ops = [op.full_name for op in caller_bb.operations]
    assert "func.call" in caller_ops


@pytest.mark.dialect
def test_linalg_example_parsing(parser, dialect_examples_dir):
    """Test parsing of linalg dialect examples."""
    linalg_file = dialect_examples_dir / "linalg_example.mlir"
    assert linalg_file.exists()

    functions = parser.parse_file(str(linalg_file))
    assert len(functions) == 3

    expected_functions = {"linalg_generic_example", "matmul", "batch_matmul"}
    assert set(functions.keys()) == expected_functions

    # Check linalg operations
    for name, func in functions.items():
        bb = list(func.basic_blocks.values())[0]
        linalg_ops = [op for op in bb.operations if op.full_name.startswith("linalg.")]
        assert len(linalg_ops) > 0


@pytest.mark.dialect
@pytest.mark.parametrize(
    "filename,expected_func_count",
    [
        ("affine_example.mlir", 2),
        ("func_example.mlir", 3),
        ("linalg_example.mlir", 3),
    ],
)
def test_dialect_files_exist_and_parsable(
    parser, dialect_examples_dir, filename, expected_func_count
):
    """Parameterized test for dialect example files."""
    filepath = dialect_examples_dir / filename
    assert filepath.exists(), f"File {filename} not found"

    functions = parser.parse_file(str(filepath))
    assert len(functions) == expected_func_count

    # Ensure all functions have at least one basic block
    for name, func in functions.items():
        assert len(func.basic_blocks) > 0
        # Each basic block should have operations
        for bb in func.basic_blocks.values():
            assert len(bb.operations) > 0
