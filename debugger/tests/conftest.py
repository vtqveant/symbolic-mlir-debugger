"""Pytest configuration and fixtures for symbolic MLIR debugger tests."""

import sys
from pathlib import Path

# Add repository root to Python path when pytest is invoked from elsewhere.
repo_root = Path(__file__).resolve().parents[2]
debugger_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

import pytest
from debugger.interpreter.parser import MLIRParser
from debugger.interpreter.interpreter import SymbolicInterpreter, ConcolicInterpreter


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
    return debugger_root / "fixtures"


@pytest.fixture
def dialect_examples_dir() -> Path:
    """Fixture providing path to dialect examples directory."""
    return debugger_root / "fixtures"


def load_mlir_file(path: Path) -> str:
    """Helper function to load MLIR file content."""
    with open(path, "r") as f:
        return f.read()


@pytest.fixture
def load_mlir():
    """Fixture providing MLIR file loading function."""
    return load_mlir_file
