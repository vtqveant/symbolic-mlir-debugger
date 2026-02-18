#!/usr/bin/env python3
"""
Test case generator for symbolic MLIR debugging.

Generates automated test scripts by exploring execution paths using
symbolic debugging capabilities of the DAP server.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..core.client import DAPClient

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """Generate test cases by exploring symbolic execution paths."""

    def __init__(
        self,
        debugger_path: Optional[str] = None,
        timeout: int = 30,
        read_timeout: int = 10,
    ):
        """Initialize test case generator.

        Args:
            debugger_path: Path to DAP server script. If None, auto-detected.
            timeout: Connection timeout
            read_timeout: Read timeout
        """
        self.debugger_path = debugger_path
        self.timeout = timeout
        self.read_timeout = read_timeout
        self.client: Optional[DAPClient] = None

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
            # Connect using context manager or directly
            # We'll use connect method
            return self.client.connect()
        except Exception as e:
            logger.error(f"Failed to connect to DAP server: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from DAP server."""
        if self.client:
            self.client.close()
            self.client = None

    def generate_from_program(
        self,
        program_path: str,
        max_paths: int = 10,
        test_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate test scripts from program by exploring execution paths.

        Args:
            program_path: Path to MLIR program
            max_paths: Maximum number of paths to explore
            test_name: Base name for test scripts (defaults to program stem)

        Returns:
            List of generated test scripts (as dictionaries)
        """
        if not self.client:
            raise RuntimeError("Not connected to DAP server")

        if not Path(program_path).exists():
            raise FileNotFoundError(f"Program not found: {program_path}")

        test_name = test_name or Path(program_path).stem
        test_scripts = []

        try:
            # Initialize session
            logger.info(f"Initializing debug session for {program_path}")
            self.client.initialize(
                adapter_id="mlir-debugger",
                client_id="test-case-generator",
            )

            # Enable symbolic debugging
            logger.info("Enabling symbolic debugging mode")
            self.client.symbolic_set_mode(enabled=True)

            # Launch program (no debug to avoid breakpoints)
            logger.info(f"Launching program: {program_path}")
            self.client.launch(program=program_path, no_debug=True)

            # Explore execution paths
            logger.info(f"Exploring up to {max_paths} execution paths")
            explore_result = self.client.symbolic_explore_paths(max_paths=max_paths)

            paths = explore_result.get("paths", [])
            logger.info(f"Found {len(paths)} execution paths")

            # Generate test script for each path
            for i, path_info in enumerate(paths):
                test_script = self._create_test_script_for_path(
                    program_path=program_path,
                    path_info=path_info,
                    test_name=f"{test_name}_path_{i}",
                    path_index=i,
                )
                test_scripts.append(test_script)

            # Also create a comprehensive test script that exercises all paths
            if len(paths) > 1:
                comprehensive_script = self._create_comprehensive_test_script(
                    program_path=program_path,
                    paths=paths,
                    test_name=f"{test_name}_comprehensive",
                )
                test_scripts.append(comprehensive_script)

            return test_scripts

        except Exception as e:
            logger.error(f"Failed to generate test cases: {e}")
            raise

    def _create_test_script_for_path(
        self,
        program_path: str,
        path_info: Dict[str, Any],
        test_name: str,
        path_index: int,
    ) -> Dict[str, Any]:
        """Create a test script for a specific execution path.

        Args:
            program_path: Path to MLIR program
            path_info: Path information from symbolic/explorePaths
            test_name: Name for the test script
            path_index: Index of the path

        Returns:
            Test script dictionary
        """
        # Extract inputs from path info
        inputs = path_info.get("inputs", {})
        path_condition = path_info.get("path_condition", [])
        return_value = path_info.get("return_value")

        # Build session steps
        session_steps = [
            {
                "command": "initialize",
                "arguments": {
                    "adapter_id": "mlir-debugger",
                    "client_id": f"test-{test_name}",
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
                "arguments": {
                    "program": program_path,
                    "noDebug": True,
                },
                "expect": {"success": True},
            },
        ]

        # Add symbolic evaluation steps for each input variable
        for var_name, var_value in inputs.items():
            session_steps.append(
                {
                    "command": "symbolic/evaluate",
                    "arguments": {
                        "expression": var_name,
                        "frameId": 0,
                    },
                    "expect": {
                        "success": True,
                        # We could add value validation here
                    },
                }
            )

        # Add path exploration validation
        session_steps.append(
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": 1},
                "expect": {
                    "success": True,
                    "totalPaths": 1,
                },
            }
        )

        # Note: constraint retrieval removed because getConstraints returns
        # constraints from current state, not from explored path.
        # To validate constraints, use path_condition from path_info.

        # Disconnect
        session_steps.append(
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True},
            }
        )

        test_script = {
            "name": test_name,
            "program": program_path,
            "description": f"Test for execution path {path_index}",
            "path_info": {
                "index": path_index,
                "inputs": inputs,
                "path_condition": path_condition,
                "return_value": return_value,
            },
            "session": session_steps,
        }

        return test_script

    def _create_comprehensive_test_script(
        self,
        program_path: str,
        paths: List[Dict[str, Any]],
        test_name: str,
    ) -> Dict[str, Any]:
        """Create a comprehensive test script covering multiple paths.

        Args:
            program_path: Path to MLIR program
            paths: List of path information
            test_name: Name for the test script

        Returns:
            Test script dictionary
        """
        session_steps = [
            {
                "command": "initialize",
                "arguments": {
                    "adapter_id": "mlir-debugger",
                    "client_id": f"test-{test_name}",
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
                "arguments": {
                    "program": program_path,
                    "noDebug": True,
                },
                "expect": {"success": True},
            },
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": len(paths)},
                "expect": {
                    "success": True,
                    "totalPaths": len(paths),
                },
            },
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True},
            },
        ]

        test_script = {
            "name": test_name,
            "program": program_path,
            "description": f"Comprehensive test covering {len(paths)} execution paths",
            "path_count": len(paths),
            "session": session_steps,
        }

        return test_script

    def save_test_scripts(
        self,
        test_scripts: List[Dict[str, Any]],
        output_dir: str = "generated_tests",
    ) -> List[str]:
        """Save generated test scripts to files.

        Args:
            test_scripts: List of test script dictionaries
            output_dir: Directory to save test scripts

        Returns:
            List of saved file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for i, test_script in enumerate(test_scripts):
            file_name = f"{test_script['name']}.json"
            file_path = output_path / file_name

            with open(file_path, "w") as f:
                json.dump(test_script, f, indent=2)

            saved_files.append(str(file_path))
            logger.info(f"Saved test script: {file_path}")

        return saved_files

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
