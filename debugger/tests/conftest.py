"""Pytest configuration and fixtures for symbolic MLIR debugger tests."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from interpreter.parser import MLIRParser
from interpreter.interpreter import SymbolicInterpreter, ConcolicInterpreter


@pytest.fixture
def parser() -> MLIRParser:
    """Fixture providing a fresh parser instance."""
    return MLIRParser()


@pytest.fixture
def symbolic_interpreter() -> SymbolicInterpreter:
    """Fixture providing a fresh symbolic interpreter instance."""
    return SymbolicInterpreter()


@pytest.fixture
def concolic_interpreter() -> ConcolicInterpreter:
    """Fixture providing a fresh concolic interpreter instance."""
    return ConcolicInterpreter()


@pytest.fixture
def test_data_dir() -> Path:
    """Fixture providing path to test data directory."""
    return project_root / "fixtures"


@pytest.fixture
def dialect_examples_dir() -> Path:
    """Fixture providing path to dialect examples directory."""
    return project_root / "fixtures"


def load_mlir_file(path: Path) -> str:
    """Helper function to load MLIR file content."""
    with open(path, "r") as f:
        return f.read()


@pytest.fixture
def load_mlir():
    """Fixture providing MLIR file loading function."""
    return load_mlir_file
