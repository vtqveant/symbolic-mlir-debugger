#!/usr/bin/env python3
"""
Base generator class for DAP trace generation.

This module provides the foundation for dialect-agnostic
MLIR snippet and DAP trace generation.
"""

import abc
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from ..config.dialect_config import GeneratorConfig, DialectConfig, OperationConfig

logger = logging.getLogger(__name__)


class BaseGenerator(abc.ABC):
    """Abstract base class for all generators."""

    def __init__(self, config: GeneratorConfig):
        """Initialize generator with configuration."""
        self.config = config
        self.base_dir = Path.cwd()

        # Setup output directories
        self.output_settings = config.output_settings
        self.setup_directories()

        # Statistics
        self.stats = {
            "total_operations": 0,
            "enabled_operations": 0,
            "mlir_files_generated": 0,
            "traces_generated": 0,
            "validation_passed": 0,
            "validation_failed": 0,
            "start_time": datetime.utcnow().isoformat() + "Z",
            "end_time": None,
            "duration_seconds": None,
        }

        # Manifest
        self.manifest = {
            "test_suite": "dap_trace_library",
            "version": self.config.version,
            "generated_at": self.stats["start_time"],
            "config_file": None,  # Will be set if loaded from file
            "mlir_artifacts_dir": str(self.mlir_dir),
            "dap_traces_dir": str(self.trace_dir),
            "dialects": [],
            "tests": [],
        }

    def setup_directories(self) -> None:
        """Create output directories."""
        base_output_dir = self.base_dir / self.output_settings["base_dir"]

        self.mlir_dir = base_output_dir / self.output_settings["mlir_artifacts_dir"]
        self.trace_dir = base_output_dir / self.output_settings["dap_traces_dir"]
        self.manifest_dir = base_output_dir / self.output_settings["manifest_dir"]
        self.reports_dir = base_output_dir / self.output_settings["reports_dir"]

        # Create directories
        self.mlir_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @abc.abstractmethod
    def generate_mlir_snippet(self, operation: OperationConfig, values: Dict[str, Any]) -> str:
        """Generate MLIR code snippet for an operation.

        Args:
            operation: Operation configuration
            values: Concrete values for variables

        Returns:
            MLIR code as string
        """
        pass

    @abc.abstractmethod
    def generate_dap_trace(
        self, operation: OperationConfig, mlir_path: Union[str, Path], values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate DAP trace for an operation.

        Args:
            operation: Operation configuration
            mlir_path: Path to MLIR file
            values: Concrete values for variables

        Returns:
            DAP trace as dictionary
        """
        pass

    def save_mlir_file(self, content: str, filename: str) -> Path:
        """Save MLIR content to file.

        Args:
            content: MLIR code
            filename: Output filename

        Returns:
            Path to saved file
        """
        filepath = self.mlir_dir / filename
        filepath.write_text(content)
        logger.info(f"Saved MLIR file: {filepath}")
        self.stats["mlir_files_generated"] += 1
        return filepath

    def save_dap_trace(self, trace: Dict[str, Any], filename: str) -> Path:
        """Save DAP trace to file.

        Args:
            trace: DAP trace dictionary
            filename: Output filename

        Returns:
            Path to saved file
        """
        import json

        filepath = self.trace_dir / filename
        with open(filepath, "w") as f:
            json.dump(trace, f, indent=2)
        logger.info(f"Saved DAP trace: {filepath}")
        self.stats["traces_generated"] += 1
        return filepath

    def generate_for_operation(self, operation: OperationConfig) -> List[Dict[str, Any]]:
        """Generate MLIR and DAP traces for a single operation.

        Args:
            operation: Operation configuration

        Returns:
            List of generated test information dictionaries
        """
        tests = []

        # Get concrete values for this operation
        concrete_values_list = self.get_concrete_values(operation)

        for i, values in enumerate(concrete_values_list):
            # Generate MLIR snippet
            mlir_content = self.generate_mlir_snippet(operation, values)

            # Save MLIR file
            mlir_filename = f"{operation.dialect}_{operation.name}_{i:03d}.mlir"
            mlir_path = self.save_mlir_file(mlir_content, mlir_filename)

            # Generate DAP trace
            trace = self.generate_dap_trace(operation, mlir_path, values)

            # Save DAP trace
            trace_filename = f"{operation.dialect}_{operation.name}_{i:03d}.json"
            trace_path = self.save_dap_trace(trace, trace_filename)

            # Record test information
            test_info = {
                "operation": operation.name,
                "dialect": operation.dialect,
                "mlir_file": str(mlir_path),
                "trace_file": str(trace_path),
                "concrete_values": values,
                "constraints": operation.constraints,
            }
            tests.append(test_info)

            # Add to manifest
            self.manifest["tests"].append(test_info)

        return tests

    def get_concrete_values(self, operation: OperationConfig) -> List[Dict[str, Any]]:
        """Get concrete values for an operation.

        This method can be overridden to use different value generation
        strategies (Z3, random, predefined, etc.).

        Args:
            operation: Operation configuration

        Returns:
            List of dictionaries with concrete values
        """
        # Default implementation uses predefined test cases
        if operation.test_cases:
            return operation.test_cases

        # Fallback to simple default values
        return [{"a": 1, "b": 2}]

    def generate_all(self) -> Dict[str, Any]:
        """Generate MLIR and DAP traces for all enabled operations.

        Returns:
            Generation results with statistics
        """
        logger.info("Starting DAP trace generation")

        enabled_dialects = self.config.get_enabled_dialects()
        enabled_operations = self.config.get_enabled_operations()

        self.stats["total_operations"] = sum(
            len(dialect.operations) for dialect in self.config.dialects
        )
        self.stats["enabled_operations"] = len(enabled_operations)

        logger.info(f"Enabled dialects: {[d.name for d in enabled_dialects]}")
        logger.info(f"Enabled operations: {self.stats['enabled_operations']}")

        all_tests = []

        for dialect in enabled_dialects:
            dialect_tests = []

            for operation in dialect.get_enabled_operations():
                logger.info(f"Generating for {dialect.name}.{operation.name}")

                try:
                    tests = self.generate_for_operation(operation)
                    dialect_tests.extend(tests)

                    # Update manifest with dialect info
                    if dialect.name not in self.manifest["dialects"]:
                        self.manifest["dialects"].append(dialect.name)

                except Exception as e:
                    logger.error(f"Failed to generate for {dialect.name}.{operation.name}: {e}")
                    self.stats["validation_failed"] += 1

            all_tests.extend(dialect_tests)

        # Finalize statistics
        self.stats["end_time"] = datetime.utcnow().isoformat() + "Z"
        start_dt = datetime.fromisoformat(self.stats["start_time"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(self.stats["end_time"].replace("Z", "+00:00"))
        self.stats["duration_seconds"] = (end_dt - start_dt).total_seconds()

        # Save manifest
        self.save_manifest()

        # Generate report
        report = self.generate_report()

        logger.info(
            f"Generation complete: {self.stats['mlir_files_generated']} MLIR files, "
            f"{self.stats['traces_generated']} DAP traces"
        )

        return {
            "success": True,
            "statistics": self.stats,
            "tests": all_tests,
            "manifest": self.manifest,
            "report": report,
        }

    def save_manifest(self) -> Path:
        """Save generation manifest to file.

        Returns:
            Path to saved manifest
        """
        import json

        manifest_filename = f"manifest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        manifest_path = self.manifest_dir / manifest_filename

        with open(manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

        logger.info(f"Saved manifest: {manifest_path}")
        return manifest_path

    def generate_report(self) -> Dict[str, Any]:
        """Generate generation report.

        Returns:
            Report dictionary
        """
        report = {
            "generation_summary": {
                "start_time": self.stats["start_time"],
                "end_time": self.stats["end_time"],
                "duration_seconds": self.stats["duration_seconds"],
                "total_operations": self.stats["total_operations"],
                "enabled_operations": self.stats["enabled_operations"],
                "mlir_files_generated": self.stats["mlir_files_generated"],
                "traces_generated": self.stats["traces_generated"],
                "validation_passed": self.stats["validation_passed"],
                "validation_failed": self.stats["validation_failed"],
            },
            "dialect_coverage": {},
            "operation_coverage": {},
        }

        # Calculate coverage
        for dialect in self.config.get_enabled_dialects():
            enabled_ops = dialect.get_enabled_operations()
            total_ops = len(dialect.operations)

            report["dialect_coverage"][dialect.name] = {
                "enabled_operations": len(enabled_ops),
                "total_operations": total_ops,
                "coverage_percentage": (len(enabled_ops) / total_ops * 100) if total_ops > 0 else 0,
            }

            for operation in enabled_ops:
                report["operation_coverage"][f"{dialect.name}.{operation.name}"] = {
                    "enabled": operation.enabled,
                    "category": operation.category.value,
                    "test_cases": len(operation.test_cases),
                    "constraints": len(operation.constraints),
                }

        # Save report to file
        import json

        report_filename = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.reports_dir / report_filename

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Saved report: {report_path}")

        return report
