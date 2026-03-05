#!/usr/bin/env python3
"""
DAP trace format validation module.

This module validates DAP trace files for correct format and structure,
replacing functionality from trace_testing scripts.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import jsonschema

logger = logging.getLogger(__name__)


class TraceValidator:
    """DAP trace format validator."""

    # JSON schema for DAP trace validation
    DAP_TRACE_SCHEMA = {
        "type": "object",
        "required": ["name", "program", "session"],
        "properties": {
            "name": {"type": "string"},
            "program": {"type": "string"},
            "description": {"type": "string"},
            "dialect": {"type": "string"},
            "operation": {"type": "string"},
            "concrete_inputs": {"type": "object"},
            "constraints": {"type": "array", "items": {"type": "string"}},
            "z3_generated": {"type": "boolean"},
            "session": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["command", "expect"],
                    "properties": {
                        "command": {"type": "string"},
                        "arguments": {"type": "object"},
                        "expect": {"type": "object"},
                    },
                },
            },
        },
    }

    # Valid DAP commands (based on DAP specification and extensions)
    VALID_COMMANDS = {
        # Standard DAP commands
        "initialize",
        "launch",
        "attach",
        "disconnect",
        "terminate",
        "restart",
        "setBreakpoints",
        "setFunctionBreakpoints",
        "setExceptionBreakpoints",
        "configurationDone",
        "continue",
        "next",
        "stepIn",
        "stepOut",
        "stepBack",
        "reverseContinue",
        "restartFrame",
        "goto",
        "pause",
        "stackTrace",
        "scopes",
        "variables",
        "setVariable",
        "source",
        "threads",
        "terminateThreads",
        "modules",
        "loadedSources",
        "evaluate",
        "setExpression",
        "stepInTargets",
        "gotoTargets",
        "completions",
        "exceptionInfo",
        "readMemory",
        "writeMemory",
        "disassemble",
        # Custom symbolic debugging extensions
        "symbolic/setMode",
        "symbolic/setInput",
        "symbolic/explorePaths",
        "symbolic/getPath",
        "symbolic/getConstraints",
        "symbolic/solve",
        "symbolic/stepSymbolic",
        "symbolic/getModel",
        "symbolic/reset",
    }

    def __init__(self, strict: bool = False):
        """Initialize trace validator.

        Args:
            strict: Whether to use strict validation (all commands must be valid)
        """
        self.strict = strict
        self.schema_validator = jsonschema.Draft7Validator(self.DAP_TRACE_SCHEMA)

    def validate_file(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """Validate a single DAP trace file.

        Args:
            filepath: Path to DAP trace file

        Returns:
            Validation results dictionary
        """
        filepath = Path(filepath)

        if not filepath.exists():
            return {
                "valid": False,
                "errors": [f"File not found: {filepath}"],
                "warnings": [],
                "file": str(filepath),
            }

        # Read and parse JSON
        try:
            with open(filepath, "r") as f:
                trace_data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "errors": [f"Invalid JSON: {e}"],
                "warnings": [],
                "file": str(filepath),
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to read file: {e}"],
                "warnings": [],
                "file": str(filepath),
            }

        return self.validate_trace(trace_data, str(filepath))

    def validate_trace(self, trace_data: Dict[str, Any], source: str = "unknown") -> Dict[str, Any]:
        """Validate DAP trace data.

        Args:
            trace_data: DAP trace dictionary
            source: Source identifier for error reporting

        Returns:
            Validation results dictionary
        """
        errors = []
        warnings = []

        # 1. Validate against JSON schema
        schema_errors = list(self.schema_validator.iter_errors(trace_data))
        for error in schema_errors:
            errors.append(f"Schema validation error at {error.json_path}: {error.message}")

        # 2. Validate session commands
        if "session" in trace_data:
            session = trace_data["session"]

            for i, session_item in enumerate(session):
                # Check required fields
                if "command" not in session_item:
                    errors.append(f"Session item {i}: Missing 'command' field")
                    continue

                if "expect" not in session_item:
                    errors.append(f"Session item {i}: Missing 'expect' field")
                    continue

                command = session_item["command"]

                # Check if command is valid
                if self.strict and command not in self.VALID_COMMANDS:
                    warnings.append(f"Session item {i}: Unknown command '{command}'")

                # Validate command-specific requirements
                command_errors = self._validate_command(command, session_item, i)
                errors.extend(command_errors)

        # 3. Check program file exists (if path is relative)
        if "program" in trace_data:
            program_path = Path(trace_data["program"])
            if not program_path.is_absolute():
                # Check relative to current directory
                if not program_path.exists():
                    warnings.append(f"Program file not found: {program_path}")

        # 4. Validate concrete_inputs structure
        if "concrete_inputs" in trace_data:
            concrete_inputs = trace_data["concrete_inputs"]
            if not isinstance(concrete_inputs, dict):
                errors.append("concrete_inputs must be a dictionary")
            else:
                for key, value in concrete_inputs.items():
                    if not isinstance(key, str):
                        errors.append(f"concrete_inputs key must be string: {key}")
                    if not isinstance(value, (int, float, str, bool)):
                        warnings.append(f"concrete_inputs value may be invalid type: {key}={value}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "source": source,
            "trace_name": trace_data.get("name", "unknown"),
        }

    def _validate_command(
        self, command: str, session_item: Dict[str, Any], index: int
    ) -> List[str]:
        """Validate a specific DAP command.

        Args:
            command: Command name
            session_item: Session item dictionary
            index: Session item index

        Returns:
            List of error messages
        """
        errors = []

        # Command-specific validation
        if command == "initialize":
            if "arguments" not in session_item:
                errors.append(f"Session item {index}: 'initialize' requires arguments")
            else:
                args = session_item["arguments"]
                if "adapterID" not in args:
                    errors.append(f"Session item {index}: 'initialize' requires adapterID")

        elif command == "launch":
            if "arguments" not in session_item:
                errors.append(f"Session item {index}: 'launch' requires arguments")
            else:
                args = session_item["arguments"]
                if "program" not in args:
                    errors.append(f"Session item {index}: 'launch' requires program")

        elif command == "symbolic/setInput":
            if "arguments" not in session_item:
                errors.append(f"Session item {index}: 'symbolic/setInput' requires arguments")
            else:
                args = session_item["arguments"]
                if "variable" not in args:
                    errors.append(f"Session item {index}: 'symbolic/setInput' requires variable")
                if "value" not in args:
                    errors.append(f"Session item {index}: 'symbolic/setInput' requires value")

        elif command == "symbolic/explorePaths":
            if "arguments" not in session_item:
                errors.append(f"Session item {index}: 'symbolic/explorePaths' requires arguments")
            else:
                args = session_item["arguments"]
                if "maxPaths" not in args:
                    errors.append(
                        f"Session item {index}: 'symbolic/explorePaths' requires maxPaths"
                    )

        # Validate expect field
        if "expect" in session_item:
            expect = session_item["expect"]
            if not isinstance(expect, dict):
                errors.append(f"Session item {index}: 'expect' must be a dictionary")
            elif "success" not in expect:
                warnings.append(f"Session item {index}: 'expect' should contain 'success' field")

        return errors

    def validate_directory(
        self, directory: Union[str, Path], recursive: bool = True
    ) -> Dict[str, Any]:
        """Validate all DAP trace files in a directory.

        Args:
            directory: Directory path
            recursive: Whether to search recursively

        Returns:
            Validation results with file-level details
        """
        directory = Path(directory)

        if not directory.exists():
            return {
                "valid": False,
                "errors": [f"Directory not found: {directory}"],
                "files_validated": 0,
                "files_valid": 0,
                "files_invalid": 0,
                "file_results": {},
            }

        # Find JSON trace files
        pattern = "**/*.json" if recursive else "*.json"
        trace_files = list(directory.glob(pattern))

        logger.info(f"Found {len(trace_files)} trace files in {directory}")

        file_results = {}
        total_errors = 0
        total_warnings = 0

        for filepath in trace_files:
            # Skip non-trace JSON files (check if they look like DAP traces)
            try:
                with open(filepath, "r") as f:
                    content = f.read(100)  # Read first 100 chars
                    if '"session"' not in content and '"command"' not in content:
                        continue  # Not a DAP trace file
            except:
                continue

            result = self.validate_file(filepath)
            file_results[str(filepath)] = result

            if result["valid"]:
                total_warnings += len(result["warnings"])
            else:
                total_errors += len(result["errors"])
                total_warnings += len(result["warnings"])

        # Calculate statistics
        files_valid = sum(1 for r in file_results.values() if r["valid"])
        files_invalid = len(file_results) - files_valid

        return {
            "valid": total_errors == 0,
            "errors": total_errors,
            "warnings": total_warnings,
            "files_validated": len(file_results),
            "files_valid": files_valid,
            "files_invalid": files_invalid,
            "file_results": file_results,
        }

    def validate_trace_execution(
        self, trace_data: Dict[str, Any], executor: Any = None
    ) -> Dict[str, Any]:
        """Validate trace execution semantics.

        This is a higher-level validation that checks if the trace
        makes semantic sense (e.g., commands are in logical order).

        Args:
            trace_data: DAP trace dictionary
            executor: Optional trace executor for deeper validation

        Returns:
            Validation results with semantic errors/warnings
        """
        errors = []
        warnings = []

        if "session" not in trace_data:
            errors.append("Trace has no session")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "semantic_errors": errors,
                "semantic_warnings": warnings,
            }

        session = trace_data["session"]

        # Check command sequence makes sense
        command_sequence = [item.get("command", "") for item in session]

        # 1. Should start with initialize
        if not command_sequence or command_sequence[0] != "initialize":
            warnings.append("Trace should start with 'initialize' command")

        # 2. Should end with disconnect or terminate
        last_command = command_sequence[-1] if command_sequence else ""
        if last_command not in ["disconnect", "terminate"]:
            warnings.append("Trace should end with 'disconnect' or 'terminate'")

        # 3. Check for required command pairs
        has_launch = "launch" in command_sequence or "attach" in command_sequence
        if not has_launch:
            errors.append("Trace must contain 'launch' or 'attach' command")

        # 4. Check symbolic commands make sense
        if "symbolic/setInput" in command_sequence:
            if "symbolic/setMode" not in command_sequence:
                warnings.append("symbolic/setInput used without symbolic/setMode")

        if "symbolic/explorePaths" in command_sequence:
            if "symbolic/setMode" not in command_sequence:
                warnings.append("symbolic/explorePaths used without symbolic/setMode")

        # 5. Check command order constraints
        for i, command in enumerate(command_sequence):
            if command == "symbolic/setInput":
                # Should be after setMode
                if "symbolic/setMode" in command_sequence[:i]:
                    setmode_index = command_sequence[:i].index("symbolic/setMode")
                    if i - setmode_index > 10:  # Arbitrary threshold
                        warnings.append(
                            f"symbolic/setInput far from symbolic/setMode (items {setmode_index} -> {i})"
                        )
                else:
                    warnings.append(
                        f"symbolic/setInput at position {i} without preceding symbolic/setMode"
                    )

        # 6. If executor is provided, do deeper validation
        if executor:
            try:
                # Try to simulate execution
                simulation_result = self._simulate_execution(trace_data, executor)
                if not simulation_result.get("valid", True):
                    errors.extend(simulation_result.get("errors", []))
                    warnings.extend(simulation_result.get("warnings", []))
            except Exception as e:
                warnings.append(f"Execution simulation failed: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "semantic_errors": errors,
            "semantic_warnings": warnings,
            "command_sequence": command_sequence,
        }

    def _simulate_execution(self, trace_data: Dict[str, Any], executor: Any) -> Dict[str, Any]:
        """Simulate trace execution for validation.

        Args:
            trace_data: DAP trace dictionary
            executor: Trace executor instance

        Returns:
            Simulation results
        """
        # This is a placeholder for actual execution simulation
        # In a real implementation, this would use the executor
        # to validate that commands can actually be executed

        return {"valid": True, "errors": [], "warnings": ["Execution simulation not implemented"]}
