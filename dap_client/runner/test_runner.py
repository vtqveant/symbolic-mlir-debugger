#!/usr/bin/env python3
"""
Test runner for automated DAP client testing.

Executes test scripts and validates results against expectations.
Supports both concrete and symbolic debugging commands.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional

from ..core.client import DAPClient
from ..schema import load_test_script, TestScript

logger = logging.getLogger(__name__)


class TestRunner:
    """Execute test scripts and validate results."""

    def __init__(
        self,
        debugger_path: Optional[str] = None,
        timeout: int = 30,
        read_timeout: int = 10,
    ):
        """Initialize test runner.

        Args:
            debugger_path: Path to DAP server script. If None, auto-detected.
            timeout: Connection timeout
            read_timeout: Read timeout
        """
        self.debugger_path = debugger_path
        self.timeout = timeout
        self.read_timeout = read_timeout
        self.client: Optional[DAPClient] = None
        self.results: List[Dict[str, Any]] = []

    def connect(self) -> bool:
        """Connect to DAP server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = DAPClient(
                debugger_path=self.debugger_path,
                timeout=self.timeout,
                read_timeout=self.read_timeout,
            )
            return self.client.connect()
        except Exception as e:
            logger.error(f"Failed to connect to DAP server: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from DAP server."""
        if self.client:
            self.client.close()
            self.client = None

    def run_test_script(
        self,
        test_script_data: Dict[str, Any],
        script_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a single test script.

        Args:
            test_script_data: Test script dictionary
            script_path: Optional path to the test script file

        Returns:
            Test execution results
        """
        if not self.client:
            raise RuntimeError("Not connected to DAP server")

        test_script = TestScript(test_script_data, script_path)
        test_name = test_script.name
        program_path = test_script.program

        logger.info(f"Running test: {test_name}")
        logger.info(f"Program: {program_path}")

        start_time = time.time()
        test_result = {
            "name": test_name,
            "program": program_path,
            "script_path": script_path,
            "start_time": start_time,
            "steps": [],
            "success": False,
            "error": None,
        }

        try:
            # Execute each session step
            for step_index, step in enumerate(test_script.session_steps):
                step_result = self._execute_step(step, step_index)
                test_result["steps"].append(step_result)

                # Check if step failed
                if not step_result.get("success", True):
                    test_result["error"] = f"Step {step_index} failed: {step_result.get('error')}"
                    break

            # Determine overall test success
            all_steps_success = all(step.get("success", True) for step in test_result["steps"])
            test_result["success"] = all_steps_success

            if test_result["success"]:
                logger.info(f"Test passed: {test_name}")
            else:
                logger.error(f"Test failed: {test_name}")

        except Exception as e:
            test_result["success"] = False
            test_result["error"] = str(e)
            logger.error(f"Test execution error: {e}")

        test_result["end_time"] = time.time()
        test_result["duration"] = test_result["end_time"] - start_time

        self.results.append(test_result)
        return test_result

    def _execute_step(self, step: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """Execute a single test script step.

        Args:
            step: Step dictionary with command, arguments, expect
            step_index: Index of the step

        Returns:
            Step execution result
        """
        command = step["command"]
        arguments = step.get("arguments", {})
        expect = step.get("expect", {})

        logger.debug(f"Executing step {step_index}: {command}")

        step_result = {
            "step_index": step_index,
            "command": command,
            "arguments": arguments,
            "expect": expect,
            "success": False,
            "result": None,
            "error": None,
        }

        try:
            # Execute command via DAP client
            result = self._execute_command(command, arguments)
            step_result["result"] = result

            # Validate result against expectations
            validation_result = self._validate_result(result, expect)
            step_result["success"] = validation_result["success"]
            step_result["validation_details"] = validation_result

            if not step_result["success"]:
                step_result["error"] = validation_result.get("error")
                logger.warning(
                    f"Step {step_index} validation failed: {validation_result.get('error')}"
                )
            else:
                logger.debug(f"Step {step_index} executed successfully")

        except Exception as e:
            step_result["success"] = False
            step_result["error"] = str(e)
            logger.error(f"Step {step_index} execution error: {e}")

        return step_result

    def _execute_command(self, command: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a DAP command via the client.

        Args:
            command: DAP command name
            arguments: Command arguments

        Returns:
            Command result
        """
        if not self.client:
            raise RuntimeError("Not connected to DAP server")

        # Map command to client method
        if command == "initialize":
            return self.client.initialize(**arguments)
        elif command == "launch":
            return self.client.launch(**arguments)
        elif command == "setBreakpoints":
            return self.client.set_breakpoints(**arguments)
        elif command == "configurationDone":
            return self.client.configuration_done()
        elif command == "continue":
            return self.client.continue_execution(**arguments)
        elif command == "disconnect":
            return self.client.disconnect(**arguments)
        elif command == "symbolic/setMode":
            return self.client.symbolic_set_mode(**arguments)
        elif command == "symbolic/evaluate":
            return self.client.symbolic_evaluate(**arguments)
        elif command == "symbolic/explorePaths":
            return self.client.symbolic_explore_paths(**arguments)
        elif command == "symbolic/getConstraints":
            return self.client.symbolic_get_constraints()
        else:
            raise ValueError(f"Unsupported command: {command}")

    def _validate_result(self, result: Dict[str, Any], expect: Dict[str, Any]) -> Dict[str, Any]:
        """Validate command result against expectations.

        Args:
            result: Command result dictionary
            expect: Expectations dictionary

        Returns:
            Validation result with success flag and details
        """
        validation = {
            "success": True,
            "errors": [],
            "details": {},
        }

        # Check success expectation
        expected_success = expect.get("success")
        if expected_success is not None:
            actual_success = result.get("success", True)  # Default to True if not specified
            if actual_success != expected_success:
                validation["success"] = False
                validation["errors"].append(
                    f"Expected success={expected_success}, got {actual_success}"
                )
            validation["details"]["success"] = {
                "expected": expected_success,
                "actual": actual_success,
                "match": actual_success == expected_success,
            }

        # Check breakpoints expectation
        expected_breakpoints = expect.get("breakpoints")
        if expected_breakpoints is not None:
            actual_breakpoints = result.get("breakpoints", [])
            # Simple validation: check count and basic properties
            if len(actual_breakpoints) != len(expected_breakpoints):
                validation["success"] = False
                validation["errors"].append(
                    f"Expected {len(expected_breakpoints)} breakpoints, "
                    f"got {len(actual_breakpoints)}"
                )
            else:
                # Check each breakpoint
                for i, (expected_bp, actual_bp) in enumerate(
                    zip(expected_breakpoints, actual_breakpoints)
                ):
                    if expected_bp.get("verified") is not None:
                        if actual_bp.get("verified") != expected_bp["verified"]:
                            validation["success"] = False
                            validation["errors"].append(
                                f"Breakpoint {i}: expected verified={expected_bp['verified']}, "
                                f"got {actual_bp.get('verified')}"
                            )

            validation["details"]["breakpoints"] = {
                "expected_count": len(expected_breakpoints),
                "actual_count": len(actual_breakpoints),
                "match": len(actual_breakpoints) == len(expected_breakpoints),
            }

        # Check symbolic command expectations
        # For symbolic/explorePaths: check totalPaths
        expected_total_paths = expect.get("totalPaths")
        if expected_total_paths is not None:
            actual_total_paths = result.get("totalPaths")
            if actual_total_paths is not None:
                if isinstance(expected_total_paths, dict) and "min" in expected_total_paths:
                    # Minimum expectation
                    if actual_total_paths < expected_total_paths["min"]:
                        validation["success"] = False
                        validation["errors"].append(
                            f"Expected at least {expected_total_paths['min']} paths, "
                            f"got {actual_total_paths}"
                        )
                else:
                    # Exact expectation
                    if actual_total_paths != expected_total_paths:
                        validation["success"] = False
                        validation["errors"].append(
                            f"Expected {expected_total_paths} paths, got {actual_total_paths}"
                        )

                validation["details"]["totalPaths"] = {
                    "expected": expected_total_paths,
                    "actual": actual_total_paths,
                    "match": actual_total_paths == expected_total_paths,
                }

        # For symbolic/getConstraints: check count
        expected_constraint_count = expect.get("count")
        if expected_constraint_count is not None:
            actual_constraint_count = result.get("count")
            if actual_constraint_count is not None:
                if (
                    isinstance(expected_constraint_count, dict)
                    and "min" in expected_constraint_count
                ):
                    # Minimum expectation
                    if actual_constraint_count < expected_constraint_count["min"]:
                        validation["success"] = False
                        validation["errors"].append(
                            f"Expected at least {expected_constraint_count['min']} constraints, "
                            f"got {actual_constraint_count}"
                        )
                else:
                    # Exact expectation
                    if actual_constraint_count != expected_constraint_count:
                        validation["success"] = False
                        validation["errors"].append(
                            f"Expected {expected_constraint_count} constraints, "
                            f"got {actual_constraint_count}"
                        )

                validation["details"]["constraint_count"] = {
                    "expected": expected_constraint_count,
                    "actual": actual_constraint_count,
                    "match": actual_constraint_count == expected_constraint_count,
                }

        # Add result summary
        validation["details"]["result_summary"] = {
            "keys": list(result.keys()) if result else [],
        }

        return validation

    def run_test_file(self, test_script_path: str) -> Dict[str, Any]:
        """Run a test script from file.

        Args:
            test_script_path: Path to test script JSON file

        Returns:
            Test execution results
        """
        test_script = load_test_script(test_script_path)
        return self.run_test_script(test_script, test_script_path)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all test executions.

        Returns:
            Summary dictionary
        """
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests

        total_duration = sum(r.get("duration", 0) for r in self.results)

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "total_duration": total_duration,
            "results": self.results,
        }

    def save_results(self, output_path: str = "test_results.json") -> str:
        """Save test results to JSON file.

        Args:
            output_path: Path to output JSON file

        Returns:
            Path to saved file
        """
        summary = self.get_summary()

        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Results saved to {output_path}")
        return output_path

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
