#!/usr/bin/env python3
"""
MLIR syntax validation module.

This module provides MLIR syntax validation using the MLIR LSP server,
replacing the functionality from scripts/mlir_validation/.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import requests

logger = logging.getLogger(__name__)


class MLIRValidator:
    """MLIR syntax validator using LSP server."""

    def __init__(self, lsp_endpoint: str = None):
        """Initialize MLIR validator.

        Args:
            lsp_endpoint: Optional LSP server endpoint URL.
                         If None, uses local mlir-lsp-server.
        """
        self.lsp_endpoint = lsp_endpoint

        # Check if LSP server is available
        self.lsp_available = self._check_lsp_availability()

        if not self.lsp_available:
            logger.warning("MLIR LSP server not available. Syntax validation will be limited.")

    def _check_lsp_availability(self) -> bool:
        """Check if MLIR LSP server is available.

        Returns:
            True if LSP server is available
        """
        if self.lsp_endpoint:
            # Check remote endpoint
            try:
                response = requests.get(self.lsp_endpoint, timeout=5)
                return response.status_code == 200
            except requests.RequestException:
                return False
        else:
            # Check local mlir-lsp-server
            try:
                result = subprocess.run(
                    ["which", "mlir-lsp-server"], capture_output=True, text=True
                )
                return result.returncode == 0
            except Exception:
                return False

    def validate_file(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """Validate a single MLIR file.

        Args:
            filepath: Path to MLIR file

        Returns:
            Validation results dictionary
        """
        filepath = Path(filepath)

        if not filepath.exists():
            return {"valid": False, "errors": [f"File not found: {filepath}"], "warnings": []}

        # Read file content
        try:
            content = filepath.read_text()
        except Exception as e:
            return {"valid": False, "errors": [f"Failed to read file: {e}"], "warnings": []}

        return self.validate_content(content, str(filepath))

    def validate_content(self, content: str, filename: str = "unknown.mlir") -> Dict[str, Any]:
        """Validate MLIR content.

        Args:
            content: MLIR code as string
            filename: Optional filename for error reporting

        Returns:
            Validation results dictionary
        """
        if self.lsp_endpoint:
            return self._validate_remote(content, filename)
        else:
            return self._validate_local(content, filename)

    def _validate_remote(self, content: str, filename: str) -> Dict[str, Any]:
        """Validate using remote LSP server.

        Args:
            content: MLIR code
            filename: Filename for error reporting

        Returns:
            Validation results
        """
        try:
            # Prepare request
            request_data = {
                "method": "textDocument/diagnostic",
                "params": {
                    "textDocument": {
                        "uri": f"file:///{filename}",
                        "languageId": "mlir",
                        "version": 1,
                        "text": content,
                    }
                },
                "jsonrpc": "2.0",
                "id": 1,
            }

            # Send request
            response = requests.post(self.lsp_endpoint, json=request_data, timeout=30)

            if response.status_code != 200:
                return {
                    "valid": False,
                    "errors": [f"LSP server error: {response.status_code}"],
                    "warnings": [],
                }

            # Parse response
            result = response.json()

            if "error" in result:
                return {"valid": False, "errors": [f"LSP error: {result['error']}"], "warnings": []}

            # Extract diagnostics
            diagnostics = result.get("result", {}).get("items", [])

            errors = []
            warnings = []

            for diag in diagnostics:
                message = diag.get("message", "Unknown error")
                severity = diag.get("severity", 1)  # 1=Error, 2=Warning, 3=Info, 4=Hint

                if severity == 1:  # Error
                    errors.append(message)
                else:  # Warning or other
                    warnings.append(message)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "diagnostics": diagnostics,
            }

        except Exception as e:
            logger.error(f"Remote validation failed: {e}")
            return {"valid": False, "errors": [f"Validation error: {e}"], "warnings": []}

    def _validate_local(self, content: str, filename: str) -> Dict[str, Any]:
        """Validate using local mlir-lsp-server.

        Args:
            content: MLIR code
            filename: Filename for error reporting

        Returns:
            Validation results
        """
        if not self.lsp_available:
            return {"valid": False, "errors": ["MLIR LSP server not available"], "warnings": []}

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
                f.write(content)
                temp_path = f.name

            # Run mlir-lsp-server
            cmd = ["mlir-lsp-server", "--check", temp_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Parse output
            errors = []
            warnings = []

            if result.returncode != 0:
                # Parse stderr for errors
                for line in result.stderr.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("warning:"):
                        errors.append(line)
                    elif line.startswith("warning:"):
                        warnings.append(line[8:].strip())

            # Also check stdout for any output
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line:
                    if line.startswith("error:"):
                        errors.append(line[6:].strip())
                    elif line.startswith("warning:"):
                        warnings.append(line[8:].strip())

            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"valid": False, "errors": ["Validation timeout"], "warnings": []}
        except Exception as e:
            logger.error(f"Local validation failed: {e}")
            return {"valid": False, "errors": [f"Validation error: {e}"], "warnings": []}

    def validate_directory(
        self, directory: Union[str, Path], recursive: bool = True
    ) -> Dict[str, Any]:
        """Validate all MLIR files in a directory.

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

        # Find MLIR files
        pattern = "**/*.mlir" if recursive else "*.mlir"
        mlir_files = list(directory.glob(pattern))

        logger.info(f"Found {len(mlir_files)} MLIR files in {directory}")

        file_results = {}
        total_errors = 0
        total_warnings = 0

        for filepath in mlir_files:
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

    def validate_embedded_mlir(self, python_file: Union[str, Path]) -> Dict[str, Any]:
        """Validate MLIR code embedded in Python files.

        Args:
            python_file: Path to Python file

        Returns:
            Validation results
        """
        python_file = Path(python_file)

        if not python_file.exists():
            return {
                "valid": False,
                "errors": [f"File not found: {python_file}"],
                "embedded_blocks": 0,
                "block_results": {},
            }

        # Read Python file
        try:
            content = python_file.read_text()
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to read file: {e}"],
                "embedded_blocks": 0,
                "block_results": {},
            }

        # Extract MLIR blocks (triple-quoted strings containing 'module {')
        import re

        mlir_blocks = []

        # Pattern for triple-quoted strings
        pattern = r"(\"\"\"|\'\'\')(.*?)\1"

        for match in re.finditer(pattern, content, re.DOTALL):
            block_content = match.group(2)
            if "module {" in block_content or "func.func" in block_content:
                mlir_blocks.append(
                    {
                        "content": block_content,
                        "start_line": content[: match.start()].count("\n") + 1,
                        "end_line": content[: match.end()].count("\n") + 1,
                    }
                )

        logger.info(f"Found {len(mlir_blocks)} embedded MLIR blocks in {python_file}")

        block_results = {}

        for i, block in enumerate(mlir_blocks):
            block_name = f"block_{i+1}_lines_{block['start_line']}-{block['end_line']}"
            result = self.validate_content(block["content"], f"{python_file}:{block_name}")
            block_results[block_name] = result

        # Calculate statistics
        blocks_valid = sum(1 for r in block_results.values() if r["valid"])
        blocks_invalid = len(block_results) - blocks_valid

        total_errors = sum(len(r["errors"]) for r in block_results.values())
        total_warnings = sum(len(r["warnings"]) for r in block_results.values())

        return {
            "valid": total_errors == 0,
            "errors": total_errors,
            "warnings": total_warnings,
            "embedded_blocks": len(mlir_blocks),
            "blocks_valid": blocks_valid,
            "blocks_invalid": blocks_invalid,
            "block_results": block_results,
        }
