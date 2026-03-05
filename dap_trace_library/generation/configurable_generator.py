#!/usr/bin/env python3
"""
Configurable generator for DAP trace generation.

This module generalizes the existing configurable_arith_generator.py
to work with any MLIR dialect, not just arithmetic.
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from .base_generator import BaseGenerator
from .z3_generator import Z3Generator
from ..config.dialect_config import GeneratorConfig, DialectConfig, OperationConfig

logger = logging.getLogger(__name__)


class ConfigurableGenerator(BaseGenerator):
    """Configurable generator for multiple MLIR dialects."""

    def __init__(self, config: GeneratorConfig):
        """Initialize configurable generator."""
        super().__init__(config)
        self.z3_generator = Z3Generator()

        # Load dialect-specific templates
        self.templates = self._load_templates()

        # Track generated files by dialect
        self.generated_by_dialect = {}

    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load dialect-specific templates.

        Returns:
            Dictionary of templates by dialect
        """
        templates = {}

        for dialect in self.config.get_enabled_dialects():
            dialect_name = dialect.name
            templates[dialect_name] = {
                "mlir_template": dialect.generation_settings.get(
                    "mlir_template", self._get_default_template(dialect)
                ),
                "trace_template": dialect.generation_settings.get(
                    "trace_template", self._get_default_trace_template(dialect)
                ),
                "variable_mapping": dialect.generation_settings.get(
                    "variable_mapping", {"a": "value_a", "b": "value_b"}
                ),
            }

        return templates

    def _get_default_template(self, dialect: DialectConfig) -> str:
        """Get default MLIR template for a dialect.

        Args:
            dialect: Dialect configuration

        Returns:
            Default MLIR template string
        """
        if dialect.dialect_type.value == "arith":
            return """module {{
  func.func @test_{op_name}() {{
    %0 = arith.constant {value_a} : i{bitwidth}
    %1 = arith.constant {value_b} : i{bitwidth}
    %2 = arith.{op_name} %0, %1 : i{bitwidth}
    return
  }}
}}"""
        elif dialect.dialect_type.value == "memref":
            return """module {{
  func.func @test_{op_name}() {{
    %0 = memref.alloc() : memref<{size}x{bitwidth}>
    %1 = memref.alloc() : memref<{size}x{bitwidth}>
    %2 = {dialect}.{op_name} %0, %1 : memref<{size}x{bitwidth}>
    memref.dealloc %0 : memref<{size}x{bitwidth}>
    memref.dealloc %1 : memref<{size}x{bitwidth}>
    return
  }}
}}"""
        else:
            # Generic template for unknown dialects
            return """module {{
  func.func @test_{dialect}_{op_name}() {{
    // TODO: Implement {dialect}.{op_name} test
    return
  }}
}}"""

    def _get_default_trace_template(self, dialect: DialectConfig) -> Dict[str, Any]:
        """Get default DAP trace template for a dialect.

        Args:
            dialect: Dialect configuration

        Returns:
            Default trace template dictionary
        """
        return {
            "session": [
                {
                    "command": "initialize",
                    "arguments": {
                        "adapterID": "mlir-debugger",
                        "clientID": "test-{dialect}-{op_name}",
                    },
                    "expect": {"success": True},
                },
                {
                    "command": "symbolic/setMode",
                    "arguments": {"enabled": True},
                    "expect": {"success": True},
                },
                {
                    "command": "launch",
                    "arguments": {"program": "{program_path}", "noDebug": True},
                    "expect": {"success": True},
                },
                {
                    "command": "disconnect",
                    "arguments": {"terminateDebuggee": True},
                    "expect": {"success": True},
                },
            ]
        }

    def generate_mlir_snippet(self, operation: OperationConfig, values: Dict[str, Any]) -> str:
        """Generate MLIR code snippet for an operation.

        Args:
            operation: Operation configuration
            values: Concrete values for variables

        Returns:
            MLIR code as string
        """
        dialect_name = operation.dialect
        template_info = self.templates.get(dialect_name, {})
        template = template_info.get("mlir_template", "")

        if not template:
            template = self._get_default_template(self.config.get_dialect(dialect_name))

        # Prepare template variables
        template_vars = {
            "dialect": dialect_name,
            "op_name": operation.name,
            "bitwidth": values.get("bitwidth", 32),
            "size": values.get("size", 10),
        }

        # Add operation-specific parameters
        template_vars.update(operation.parameters)

        # Add concrete values with proper mapping
        variable_mapping = template_info.get("variable_mapping", {})
        for var_name, var_value in values.items():
            if var_name in variable_mapping:
                template_var_name = variable_mapping[var_name]
                template_vars[template_var_name] = var_value
            else:
                template_vars[var_name] = var_value

        # Render template
        try:
            return template.format(**template_vars)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            # Fallback to simple template
            return f"module {{\n  func.func @test_{operation.name}() {{\n    // {operation.dialect}.{operation.name} with values {values}\n    return\n  }}\n}}"

    def generate_dap_trace(
        self, operation: OperationConfig, mlir_path: Path, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate DAP trace for an operation.

        Args:
            operation: Operation configuration
            mlir_path: Path to MLIR file
            values: Concrete values for variables

        Returns:
            DAP trace as dictionary
        """
        dialect_name = operation.dialect
        template_info = self.templates.get(dialect_name, {})
        trace_template = template_info.get("trace_template", {})

        if not trace_template:
            trace_template = self._get_default_trace_template(self.config.get_dialect(dialect_name))

        # Create base trace
        trace = {
            "name": f"{dialect_name}_{operation.name}",
            "program": str(mlir_path),
            "description": f"Test for {dialect_name}.{operation.name}",
            "dialect": dialect_name,
            "operation": operation.name,
            "concrete_inputs": values,
            "constraints": operation.constraints,
            "z3_generated": self.z3_generator.is_available() and operation.constraints,
            "session": [],
        }

        # Start with template session
        if "session" in trace_template:
            for session_item in trace_template["session"]:
                # Render template variables in session item
                rendered_item = self._render_session_item(
                    session_item, operation, mlir_path, values
                )
                trace["session"].append(rendered_item)

        # Add concrete input setting commands if values exist
        if values:
            for var_name, var_value in values.items():
                trace["session"].insert(
                    2,
                    {  # Insert after setMode
                        "command": "symbolic/setInput",
                        "arguments": {"variable": var_name, "value": var_value},
                        "expect": {"success": True},
                    },
                )

        # Add path exploration if symbolic mode is enabled
        for i, item in enumerate(trace["session"]):
            if item.get("command") == "symbolic/setMode":
                # Insert explorePaths after setMode
                trace["session"].insert(
                    i + 1,
                    {
                        "command": "symbolic/explorePaths",
                        "arguments": {"maxPaths": 1},
                        "expect": {"success": True},
                    },
                )
                break

        return trace

    def _render_session_item(
        self,
        item: Dict[str, Any],
        operation: OperationConfig,
        mlir_path: Path,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Render template variables in a session item.

        Args:
            item: Session item dictionary
            operation: Operation configuration
            mlir_path: Path to MLIR file
            values: Concrete values

        Returns:
            Rendered session item
        """
        import copy

        rendered_item = copy.deepcopy(item)

        # Template variables
        template_vars = {
            "dialect": operation.dialect,
            "op_name": operation.name,
            "program_path": str(mlir_path),
            "values": values,
        }

        # Render arguments if they contain template variables
        if "arguments" in rendered_item:
            arguments = rendered_item["arguments"]
            if isinstance(arguments, dict):
                for key, value in arguments.items():
                    if isinstance(value, str):
                        try:
                            rendered_item["arguments"][key] = value.format(**template_vars)
                        except KeyError:
                            pass  # Keep original value

        # Render expect if it contains template variables
        if "expect" in rendered_item:
            expect = rendered_item["expect"]
            if isinstance(expect, dict):
                for key, value in expect.items():
                    if isinstance(value, str):
                        try:
                            rendered_item["expect"][key] = value.format(**template_vars)
                        except KeyError:
                            pass  # Keep original value

        return rendered_item

    def get_concrete_values(self, operation: OperationConfig) -> List[Dict[str, Any]]:
        """Get concrete values for an operation.

        Uses Z3 if available and configured, otherwise falls back
        to predefined test cases or simple defaults.

        Args:
            operation: Operation configuration

        Returns:
            List of dictionaries with concrete values
        """
        # Try Z3 first if available and constraints exist
        if (
            self.z3_generator.is_available()
            and operation.constraints
            and self.config.generation_settings.get("use_z3", True)
        ):

            solutions = []
            max_solutions = self.config.generation_settings.get("max_solutions_per_constraint", 3)

            for constraint in operation.constraints:
                constraint_solutions = self.z3_generator.generate_for_constraint(
                    constraint, max_solutions=max_solutions
                )
                solutions.extend(constraint_solutions)

            # Deduplicate and add operation-specific parameters
            unique_solutions = []
            seen = set()
            for solution in solutions:
                # Add bitwidth if specified
                if operation.bitwidths:
                    for bitwidth in operation.bitwidths:
                        enhanced_solution = solution.copy()
                        enhanced_solution["bitwidth"] = bitwidth

                        solution_tuple = tuple(sorted(enhanced_solution.items()))
                        if solution_tuple not in seen:
                            seen.add(solution_tuple)
                            unique_solutions.append(enhanced_solution)
                else:
                    solution_tuple = tuple(sorted(solution.items()))
                    if solution_tuple not in seen:
                        seen.add(solution_tuple)
                        unique_solutions.append(solution)

            if unique_solutions:
                logger.info(f"Generated {len(unique_solutions)} Z3 solutions for {operation.name}")
                return unique_solutions

        # Use predefined test cases
        if operation.test_cases:
            logger.info(
                f"Using {len(operation.test_cases)} predefined test cases for {operation.name}"
            )
            return operation.test_cases

        # Fallback to simple defaults
        logger.info(f"Using default values for {operation.name}")
        defaults = []

        for bitwidth in operation.bitwidths:
            defaults.append({"a": 1, "b": 2, "bitwidth": bitwidth})

        return defaults if defaults else [{"a": 1, "b": 2}]

    def generate_all(self) -> Dict[str, Any]:
        """Generate MLIR and DAP traces for all enabled operations.

        Returns:
            Generation results with statistics
        """
        logger.info("Starting configurable DAP trace generation")

        # Initialize dialect tracking
        for dialect in self.config.get_enabled_dialects():
            self.generated_by_dialect[dialect.name] = {
                "operations": [],
                "mlir_files": 0,
                "traces": 0,
            }

        # Call parent implementation
        result = super().generate_all()

        # Add dialect-specific statistics
        result["dialect_statistics"] = self.generated_by_dialect

        return result

    def generate_for_operation(self, operation: OperationConfig) -> List[Dict[str, Any]]:
        """Generate MLIR and DAP traces for a single operation.

        Args:
            operation: Operation configuration

        Returns:
            List of generated test information dictionaries
        """
        tests = super().generate_for_operation(operation)

        # Update dialect tracking
        if operation.dialect in self.generated_by_dialect:
            self.generated_by_dialect[operation.dialect]["operations"].append(operation.name)
            self.generated_by_dialect[operation.dialect]["mlir_files"] += len(tests)
            self.generated_by_dialect[operation.dialect]["traces"] += len(tests)

        return tests
