#!/usr/bin/env python3
"""
Configuration utilities for DAP trace library.

Configuration loading, validation, and management utilities.
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import jsonschema

logger = logging.getLogger(__name__)


class ConfigUtils:
    """Utility class for configuration management."""

    # JSON schema for configuration validation
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "dialects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "dialect_type": {"type": "string"},
                        "enabled": {"type": "boolean"},
                        "operations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "dialect": {"type": "string"},
                                    "category": {"type": "string"},
                                    "enabled": {"type": "boolean"},
                                    "parameters": {"type": "object"},
                                    "constraints": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "test_cases": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    },
                                    "bitwidths": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                    },
                                },
                                "required": ["name", "dialect", "category"],
                            },
                        },
                        "generation_settings": {"type": "object"},
                        "validation_settings": {"type": "object"},
                    },
                    "required": ["name", "dialect_type"],
                },
            },
            "output_settings": {"type": "object"},
            "generation_settings": {"type": "object"},
            "validation_settings": {"type": "object"},
        },
        "required": ["version", "dialects"],
    }

    @staticmethod
    def load_config(path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from file (YAML or JSON).

        Args:
            path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        suffix = path.suffix.lower()

        if suffix == ".yaml" or suffix == ".yml":
            with open(path, "r") as f:
                return yaml.safe_load(f)
        elif suffix == ".json":
            with open(path, "r") as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported configuration format: {suffix}")

    @staticmethod
    def save_config(config: Dict[str, Any], path: Union[str, Path]) -> Path:
        """Save configuration to file.

        Args:
            config: Configuration dictionary
            path: Output file path

        Returns:
            Path to saved file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        suffix = path.suffix.lower()

        if suffix == ".yaml" or suffix == ".yml":
            with open(path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
        elif suffix == ".json":
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
        else:
            # Default to YAML
            path = path.with_suffix(".yaml")
            with open(path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)

        logger.debug(f"Saved configuration to: {path}")
        return path

    @staticmethod
    def validate_config(
        config: Dict[str, Any], schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Validate configuration against schema.

        Args:
            config: Configuration dictionary
            schema: JSON schema (uses default if None)

        Returns:
            Validation results dictionary
        """
        if schema is None:
            schema = ConfigUtils.CONFIG_SCHEMA

        validator = jsonschema.Draft7Validator(schema)

        errors = list(validator.iter_errors(config))

        return {
            "valid": len(errors) == 0,
            "errors": [
                {
                    "path": list(error.path),
                    "message": error.message,
                    "validator": error.validator,
                    "validator_value": error.validator_value,
                }
                for error in errors
            ],
            "error_count": len(errors),
        }

    @staticmethod
    def validate_constraints_format(config: Dict[str, Any]) -> List[str]:
        """Validate constraint format in configuration.

        Checks that constraints are boolean expressions (contain comparison operators).

        Args:
            config: Configuration dictionary

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        comparison_ops = {"!=", "==", ">", "<", ">=", "<="}

        # Walk through dialects and operations
        for dialect_idx, dialect in enumerate(config.get("dialects", [])):
            for op_idx, operation in enumerate(dialect.get("operations", [])):
                constraints = operation.get("constraints", [])
                if not isinstance(constraints, list):
                    continue
                for const_idx, constraint in enumerate(constraints):
                    if not isinstance(constraint, str):
                        continue
                    constraint = constraint.strip()
                    if not any(op in constraint for op in comparison_ops):
                        errors.append(
                            f"Constraint '{constraint}' at "
                            f"dialect[{dialect_idx}].operations[{op_idx}].constraints[{const_idx}] "
                            f"does not contain comparison operator (==, !=, >, <, >=, <=). "
                            f"Constraints must be boolean expressions for Z3 solver."
                        )
        return errors

    @staticmethod
    def merge_configs(
        base_config: Dict[str, Any], override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two configurations (override takes precedence).

        Args:
            base_config: Base configuration
            override_config: Override configuration

        Returns:
            Merged configuration
        """
        import copy

        merged = copy.deepcopy(base_config)

        for key, value in override_config.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge dictionaries
                merged[key] = ConfigUtils.merge_configs(merged[key], value)
            else:
                # Overwrite or add new key
                merged[key] = value

        return merged

    @staticmethod
    def load_and_validate(path: Union[str, Path]) -> Dict[str, Any]:
        """Load and validate configuration.

        Args:
            path: Path to configuration file

        Returns:
            Tuple of (configuration, validation_results)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If configuration is invalid
        """
        config = ConfigUtils.load_config(path)
        validation = ConfigUtils.validate_config(config)

        if not validation["valid"]:
            error_messages = [
                f"{error['path']}: {error['message']}"
                for error in validation["errors"][:5]
            ]
            raise ValueError(f"Configuration invalid: {', '.join(error_messages)}")

        return config

    @staticmethod
    def create_default_config() -> Dict[str, Any]:
        """Create default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "version": "1.0",
            "dialects": [],
            "output_settings": {
                "base_dir": "target/trace_testing",
                "mlir_artifacts_dir": "mlir_artifacts",
                "dap_traces_dir": "dap_traces",
                "manifest_dir": "manifests",
                "reports_dir": "reports",
            },
            "generation_settings": {
                "generate_mlir": True,
                "generate_traces": True,
                "validate_mlir": True,
                "validate_traces": True,
                "use_z3": True,
                "max_solutions_per_constraint": 3,
                "timeout_seconds": 30,
            },
            "validation_settings": {
                "validate_syntax": True,
                "validate_semantics": True,
                "validate_paths": True,
                "strict_mode": False,
            },
        }

    @staticmethod
    def create_example_config(dialect_name: str = "arith") -> Dict[str, Any]:
        """Create example configuration for a dialect.

        Args:
            dialect_name: Dialect name

        Returns:
            Example configuration
        """
        config = ConfigUtils.create_default_config()

        if dialect_name == "arith":
            config["dialects"] = [
                {
                    "name": "arith",
                    "dialect_type": "arith",
                    "enabled": True,
                    "operations": [
                        {
                            "name": "addi",
                            "dialect": "arith",
                            "category": "arithmetic",
                            "enabled": True,
                            "constraints": ["a + b != 0"],
                            "parameters": {"commutative": True},
                            "bitwidths": [32, 64],
                        },
                        {
                            "name": "subi",
                            "dialect": "arith",
                            "category": "arithmetic",
                            "enabled": True,
                            "constraints": ["a - b != 0"],
                            "bitwidths": [32, 64],
                        },
                        {
                            "name": "muli",
                            "dialect": "arith",
                            "category": "arithmetic",
                            "enabled": True,
                            "constraints": ["a * b"],
                            "parameters": {"commutative": True},
                            "bitwidths": [32, 64],
                        },
                        {
                            "name": "divi",
                            "dialect": "arith",
                            "category": "arithmetic",
                            "enabled": True,
                            "constraints": ["b != 0"],
                            "bitwidths": [32, 64],
                        },
                    ],
                    "generation_settings": {
                        "mlir_template": "module {{\n  func.func @test_{op_name}() {{\n    %0 = arith.constant {value_a} : i{bitwidth}\n    %1 = arith.constant {value_b} : i{bitwidth}\n    %2 = arith.{op_name} %0, %1 : i{bitwidth}\n    return\n  }}\n}}"  # noqa: E501
                    },
                }
            ]

        return config

    @staticmethod
    def extract_dialect_config(
        config: Dict[str, Any], dialect_name: str
    ) -> Optional[Dict[str, Any]]:
        """Extract configuration for a specific dialect.

        Args:
            config: Full configuration
            dialect_name: Dialect name

        Returns:
            Dialect configuration or None if not found
        """
        for dialect in config.get("dialects", []):
            if dialect.get("name") == dialect_name:
                return dialect
        return None

    @staticmethod
    def extract_operation_config(
        config: Dict[str, Any], dialect_name: str, operation_name: str
    ) -> Optional[Dict[str, Any]]:
        """Extract configuration for a specific operation.

        Args:
            config: Full configuration
            dialect_name: Dialect name
            operation_name: Operation name

        Returns:
            Operation configuration or None if not found
        """
        dialect = ConfigUtils.extract_dialect_config(config, dialect_name)
        if not dialect:
            return None

        for operation in dialect.get("operations", []):
            if operation.get("name") == operation_name:
                return operation

        return None

    @staticmethod
    def update_config_value(
        config: Dict[str, Any], path: List[str], value: Any
    ) -> Dict[str, Any]:
        """Update a configuration value by path.

        Args:
            config: Configuration dictionary
            path: Path to value (e.g., ["dialects", 0, "enabled"])
            value: New value

        Returns:
            Updated configuration
        """
        import copy

        updated = copy.deepcopy(config)
        current = updated

        # Navigate to parent
        for key in path[:-1]:
            if isinstance(current, dict):
                current = current[key]
            elif isinstance(current, list) and isinstance(key, int):
                current = current[key]
            else:
                raise KeyError(f"Invalid path: {path}")

        # Set value
        last_key = path[-1]
        if isinstance(current, dict):
            current[last_key] = value
        elif isinstance(current, list) and isinstance(last_key, int):
            current[last_key] = value
        else:
            raise KeyError(f"Invalid path: {path}")

        return updated

    @staticmethod
    def get_config_value(
        config: Dict[str, Any], path: List[str], default: Any = None
    ) -> Any:
        """Get a configuration value by path.

        Args:
            config: Configuration dictionary
            path: Path to value
            default: Default value if path doesn't exist

        Returns:
            Configuration value or default
        """
        current = config

        for key in path:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and isinstance(key, int):
                if 0 <= key < len(current):
                    current = current[key]
                else:
                    return default
            else:
                return default

            if current is None:
                return default

        return current

    @staticmethod
    def generate_config_summary(config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Summary dictionary
        """
        dialects = config.get("dialects", [])

        enabled_dialects = [d for d in dialects if d.get("enabled", True)]
        enabled_operations = []

        for dialect in enabled_dialects:
            for operation in dialect.get("operations", []):
                if operation.get("enabled", True):
                    enabled_operations.append(
                        {
                            "dialect": dialect["name"],
                            "operation": operation["name"],
                            "category": operation.get("category", "unknown"),
                            "constraints": len(operation.get("constraints", [])),
                            "test_cases": len(operation.get("test_cases", [])),
                        }
                    )

        return {
            "version": config.get("version", "unknown"),
            "total_dialects": len(dialects),
            "enabled_dialects": len(enabled_dialects),
            "total_operations": sum(len(d.get("operations", [])) for d in dialects),
            "enabled_operations": len(enabled_operations),
            "enabled_operations_by_dialect": {
                d["name"]: len(
                    [op for op in d.get("operations", []) if op.get("enabled", True)]
                )
                for d in enabled_dialects
            },
            "generation_settings": config.get("generation_settings", {}),
            "output_settings": config.get("output_settings", {}),
        }

    @staticmethod
    def diff_configs(
        config1: Dict[str, Any], config2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find differences between two configurations.

        Args:
            config1: First configuration
            config2: Second configuration

        Returns:
            Differences dictionary
        """

        def _find_diff(d1, d2, path=""):
            diff = {}

            # Check keys in d1 not in d2
            for key in set(d1.keys()) - set(d2.keys()):
                diff[f"{path}.{key}" if path else key] = {
                    "type": "removed",
                    "value": d1[key],
                }

            # Check keys in d2 not in d1
            for key in set(d2.keys()) - set(d1.keys()):
                diff[f"{path}.{key}" if path else key] = {
                    "type": "added",
                    "value": d2[key],
                }

            # Check common keys
            for key in set(d1.keys()) & set(d2.keys()):
                new_path = f"{path}.{key}" if path else key

                if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                    nested_diff = _find_diff(d1[key], d2[key], new_path)
                    diff.update(nested_diff)
                elif d1[key] != d2[key]:
                    diff[new_path] = {
                        "type": "changed",
                        "old_value": d1[key],
                        "new_value": d2[key],
                    }

            return diff

        return _find_diff(config1, config2)
