#!/usr/bin/env python3
"""
Dialect configuration system for DAP trace generation.

This module provides dialect-agnostic configuration for MLIR dialects,
extending beyond the arithmetic-specific configuration.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class DialectType(Enum):
    """Supported MLIR dialect types."""

    ARITH = "arith"
    MEMREF = "memref"
    VECTOR = "vector"
    SCALAR = "scalar"
    CUSTOM = "custom"


class OperationCategory(Enum):
    """Categories of operations within a dialect."""

    ARITHMETIC = "arithmetic"
    LOGICAL = "logical"
    COMPARISON = "comparison"
    CONVERSION = "conversion"
    CONTROL_FLOW = "control_flow"
    MEMORY = "memory"
    VECTOR = "vector"
    CUSTOM = "custom"


@dataclass
class OperationConfig:
    """Configuration for a single MLIR operation."""

    name: str
    """Operation name (e.g., 'addi', 'cmpi')."""

    dialect: str
    """Dialect name (e.g., 'arith', 'memref')."""

    category: OperationCategory
    """Operation category."""

    enabled: bool = True
    """Whether this operation is enabled for testing."""

    parameters: Dict[str, Any] = field(default_factory=dict)
    """Operation-specific parameters."""

    constraints: List[str] = field(default_factory=list)
    """Z3 constraints for this operation. Must be boolean expressions (e.g., 'a + b != 0', 'b != 0', 'a > b')."""

    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    """Predefined test cases for this operation."""

    bitwidths: List[int] = field(default_factory=lambda: [32, 64])
    """Supported bit widths."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "dialect": self.dialect,
            "category": self.category.value,
            "enabled": self.enabled,
            "parameters": self.parameters,
            "constraints": self.constraints,
            "test_cases": self.test_cases,
            "bitwidths": self.bitwidths,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationConfig":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            dialect=data["dialect"],
            category=OperationCategory(data["category"]),
            enabled=data.get("enabled", True),
            parameters=data.get("parameters", {}),
            constraints=data.get("constraints", []),
            test_cases=data.get("test_cases", []),
            bitwidths=data.get("bitwidths", [32, 64]),
        )


@dataclass
class DialectConfig:
    """Configuration for an entire MLIR dialect."""

    name: str
    """Dialect name."""

    dialect_type: DialectType
    """Type of dialect."""

    operations: List[OperationConfig] = field(default_factory=list)
    """Operations in this dialect."""

    enabled: bool = True
    """Whether this dialect is enabled for testing."""

    generation_settings: Dict[str, Any] = field(default_factory=dict)
    """Generation settings specific to this dialect."""

    validation_settings: Dict[str, Any] = field(default_factory=dict)
    """Validation settings specific to this dialect."""

    def get_operation(self, name: str) -> Optional[OperationConfig]:
        """Get operation by name."""
        for op in self.operations:
            if op.name == name and op.enabled:
                return op
        return None

    def get_enabled_operations(self) -> List[OperationConfig]:
        """Get all enabled operations."""
        return [op for op in self.operations if op.enabled]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "dialect_type": self.dialect_type.value,
            "enabled": self.enabled,
            "operations": [op.to_dict() for op in self.operations],
            "generation_settings": self.generation_settings,
            "validation_settings": self.validation_settings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialectConfig":
        """Create from dictionary."""
        operations = [
            OperationConfig.from_dict(op_data) for op_data in data.get("operations", [])
        ]

        return cls(
            name=data["name"],
            dialect_type=DialectType(data.get("dialect_type", "custom")),
            operations=operations,
            enabled=data.get("enabled", True),
            generation_settings=data.get("generation_settings", {}),
            validation_settings=data.get("validation_settings", {}),
        )


@dataclass
class GeneratorConfig:
    """Main generator configuration."""

    version: str = "1.0"
    """Configuration version."""

    dialects: List[DialectConfig] = field(default_factory=list)
    """Configured dialects."""

    output_settings: Dict[str, Any] = field(
        default_factory=lambda: {
            "base_dir": "target/trace_testing",
            "mlir_artifacts_dir": "mlir_artifacts",
            "dap_traces_dir": "dap_traces",
            "manifest_dir": "manifests",
            "reports_dir": "reports",
        }
    )
    """Output directory settings."""

    generation_settings: Dict[str, Any] = field(
        default_factory=lambda: {
            "generate_mlir": True,
            "generate_traces": True,
            "validate_mlir": True,
            "validate_traces": True,
            "use_z3": True,
            "max_solutions_per_constraint": 3,
            "timeout_seconds": 30,
        }
    )
    """Generation settings."""

    validation_settings: Dict[str, Any] = field(
        default_factory=lambda: {
            "validate_syntax": True,
            "validate_semantics": True,
            "validate_paths": True,
            "strict_mode": False,
        }
    )
    """Validation settings."""

    def get_dialect(self, name: str) -> Optional[DialectConfig]:
        """Get dialect by name."""
        for dialect in self.dialects:
            if dialect.name == name and dialect.enabled:
                return dialect
        return None

    def get_enabled_dialects(self) -> List[DialectConfig]:
        """Get all enabled dialects."""
        return [dialect for dialect in self.dialects if dialect.enabled]

    def get_enabled_operations(self) -> List[OperationConfig]:
        """Get all enabled operations across all dialects."""
        operations = []
        for dialect in self.get_enabled_dialects():
            operations.extend(dialect.get_enabled_operations())
        return operations

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "dialects": [dialect.to_dict() for dialect in self.dialects],
            "output_settings": self.output_settings,
            "generation_settings": self.generation_settings,
            "validation_settings": self.validation_settings,
        }

    def save_yaml(self, path: Union[str, Path]) -> None:
        """Save configuration to YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = {
            "version": self.version,
            "dialects": [dialect.to_dict() for dialect in self.dialects],
            "output_settings": self.output_settings,
            "generation_settings": self.generation_settings,
            "validation_settings": self.validation_settings,
        }

        with open(path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)

    def save_json(self, path: Union[str, Path]) -> None:
        """Save configuration to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = {
            "version": self.version,
            "dialects": [dialect.to_dict() for dialect in self.dialects],
            "output_settings": self.output_settings,
            "generation_settings": self.generation_settings,
            "validation_settings": self.validation_settings,
        }

        with open(path, "w") as f:
            json.dump(config_dict, f, indent=2)

    @classmethod
    def load_yaml(cls, path: Union[str, Path]) -> "GeneratorConfig":
        """Load configuration from YAML file."""
        path = Path(path)

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        dialects = [
            DialectConfig.from_dict(dialect_data)
            for dialect_data in data.get("dialects", [])
        ]

        return cls(
            version=data.get("version", "1.0"),
            dialects=dialects,
            output_settings=data.get("output_settings", {}),
            generation_settings=data.get("generation_settings", {}),
            validation_settings=data.get("validation_settings", {}),
        )

    @classmethod
    def load_json(cls, path: Union[str, Path]) -> "GeneratorConfig":
        """Load configuration from JSON file."""
        path = Path(path)

        with open(path, "r") as f:
            data = json.load(f)

        dialects = [
            DialectConfig.from_dict(dialect_data)
            for dialect_data in data.get("dialects", [])
        ]

        return cls(
            version=data.get("version", "1.0"),
            dialects=dialects,
            output_settings=data.get("output_settings", {}),
            generation_settings=data.get("generation_settings", {}),
            validation_settings=data.get("validation_settings", {}),
        )

    @classmethod
    def create_arith_example(cls) -> "GeneratorConfig":
        """Create example configuration for arithmetic dialect."""
        arith_operations = [
            OperationConfig(
                name="addi",
                dialect="arith",
                category=OperationCategory.ARITHMETIC,
                constraints=["a + b != 0"],
                parameters={"commutative": True},
            ),
            OperationConfig(
                name="subi",
                dialect="arith",
                category=OperationCategory.ARITHMETIC,
                constraints=["a - b != 0"],
            ),
            OperationConfig(
                name="muli",
                dialect="arith",
                category=OperationCategory.ARITHMETIC,
                constraints=["a * b != 0"],
                parameters={"commutative": True},
            ),
            OperationConfig(
                name="divi",
                dialect="arith",
                category=OperationCategory.ARITHMETIC,
                constraints=["b != 0"],
            ),
            OperationConfig(
                name="cmpi",
                dialect="arith",
                category=OperationCategory.COMPARISON,
                constraints=["a > b", "a < b", "a == b"],
                parameters={"predicate": ["eq", "ne", "slt", "sle", "sgt", "sge"]},
            ),
            OperationConfig(
                name="andi",
                dialect="arith",
                category=OperationCategory.LOGICAL,
                constraints=["a != 0", "b != 0"],
            ),
            OperationConfig(
                name="ori",
                dialect="arith",
                category=OperationCategory.LOGICAL,
                constraints=["a != 0", "b != 0"],
            ),
            OperationConfig(
                name="xori",
                dialect="arith",
                category=OperationCategory.LOGICAL,
                constraints=["a != 0", "b != 0"],
            ),
        ]

        arith_dialect = DialectConfig(
            name="arith",
            dialect_type=DialectType.ARITH,
            operations=arith_operations,
            generation_settings={
                "mlir_template": "module {{\n  func.func @test_{op_name}() {{\n    %0 = arith.constant {value_a} : i{bitwidth}\n    %1 = arith.constant {value_b} : i{bitwidth}\n    %2 = arith.{op_name} %0, %1 : i{bitwidth}\n    return\n  }}\n}}"  # noqa: E501
            },
        )

        return cls(
            version="1.0",
            dialects=[arith_dialect],
            output_settings={
                "base_dir": "target/trace_testing",
                "mlir_artifacts_dir": "mlir_artifacts",
                "dap_traces_dir": "dap_traces",
                "manifest_dir": "manifests",
                "reports_dir": "reports",
            },
            generation_settings={
                "generate_mlir": True,
                "generate_traces": True,
                "validate_mlir": True,
                "validate_traces": True,
                "use_z3": True,
                "max_solutions_per_constraint": 3,
                "timeout_seconds": 30,
            },
        )
