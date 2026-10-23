#!/usr/bin/env python3
"""
DAP trace execution module.

This module executes DAP traces and collects results, replacing
functionality from trace_testing scripts.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TraceExecutor:
    """Execute DAP traces and collect results."""

    def __init__(self, debugger_path: str = None, timeout: int = 30):
        """Initialize trace executor.

        Args:
            debugger_path: Path to MLIR debugger executable
            timeout: Execution timeout in seconds
        """
        self.debugger_path = debugger_path
        self.timeout = timeout

        # Results storage
        self.results = []
        self.statistics = {
            "total_traces": 0,
            "executed_traces": 0,
            "successful_traces": 0,
            "failed_traces": 0,
            "timeout_traces": 0,
            "total_duration": 0.0,
            "start_time": None,
            "end_time": None,
        }

    def execute_trace(
        self, trace_data: Dict[str, Any], trace_name: str = "unknown"
    ) -> Dict[str, Any]:
        """Execute one DAP trace through the supported DAP client stack.

        The trace library must not invent a second execution path. A trace is
        a sequence of DAP commands; ``dap_client.runner.test_runner.TestRunner``
        owns command dispatch, session lifecycle, and expectation checks.
        """
        start_time = time.time()
        trace_name = trace_data.get("name", trace_name)

        # Import lazily so a missing/broken client installation is reported as
        # a normal execution failure instead of an import-time crash.
        try:
            from dap_client.runner.test_runner import TestRunner
        except Exception as exc:  # noqa: BLE001 - reported in the result
            return self._failure_result(
                trace_name,
                start_time,
                f"dap_client is unavailable: {exc}",
            )

        runner = TestRunner(debugger_path=self.debugger_path, timeout=self.timeout)
        try:
            if not runner.connect():
                return self._failure_result(
                    trace_name,
                    start_time,
                    "could not connect to the DAP server",
                )
            result = runner.run_test_script(trace_data, script_path=trace_name)
        except Exception as exc:  # noqa: BLE001 - reported in the result
            return self._failure_result(trace_name, start_time, str(exc), returncode=1)
        finally:
            try:
                runner.disconnect()
            except Exception:  # noqa: BLE001 - cleanup must not mask results
                logger.debug("Failed to disconnect DAP client", exc_info=True)

        execution_time = time.time() - start_time
        steps = result.get("steps", []) or []
        step_errors = [step.get("error") for step in steps if step.get("error")]
        success = bool(result.get("success", False))
        execution_result = {
            "trace_name": trace_name,
            "success": success,
            "expected_success": True,
            "returncode": 0 if success else 1,
            "execution_time": result.get("duration", execution_time),
            "stdout": "",
            "stderr": "\n".join(step_errors),
            "command": "dap_client.runner.test_runner.TestRunner",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "steps": steps,
            "errors_detected": bool(step_errors),
            "error_messages": step_errors,
        }
        if not success and not step_errors:
            execution_result["error_messages"] = [result.get("error", "trace failed")]
        return execution_result

    def _failure_result(
        self, trace_name: str, start_time: float, message: str, returncode: int = -1
    ) -> Dict[str, Any]:
        """Build the legacy result shape for an execution failure."""
        return {
            "trace_name": trace_name,
            "success": False,
            "expected_success": True,
            "returncode": returncode,
            "execution_time": time.time() - start_time,
            "stdout": "",
            "stderr": message,
            "command": "dap_client.runner.test_runner.TestRunner",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exception": message,
            "errors_detected": True,
            "error_messages": [message],
        }

    def execute_file(self, trace_file: Union[str, Path]) -> Dict[str, Any]:
        """Execute a DAP trace from file.

        Args:
            trace_file: Path to trace file

        Returns:
            Execution results dictionary
        """
        trace_file = Path(trace_file)

        if not trace_file.exists():
            return {
                "success": False,
                "error": f"Trace file not found: {trace_file}",
                "trace_name": str(trace_file),
            }

        # Load trace data
        try:
            with open(trace_file, "r") as f:
                trace_data = json.load(f)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load trace file: {e}",
                "trace_file": str(trace_file),
            }

        trace_name = trace_data.get("name", trace_file.stem)

        return self.execute_trace(trace_data, trace_name)

    def execute_directory(
        self, directory: Union[str, Path], recursive: bool = True
    ) -> Dict[str, Any]:
        """Execute all DAP traces in a directory.

        Args:
            directory: Directory path
            recursive: Whether to search recursively

        Returns:
            Execution results with statistics
        """
        directory = Path(directory)

        if not directory.exists():
            return {
                "success": False,
                "error": f"Directory not found: {directory}",
                "statistics": self.statistics,
            }

        # Find trace files
        pattern = "**/*.json" if recursive else "*.json"
        trace_files = list(directory.glob(pattern))

        logger.info(f"Found {len(trace_files)} trace files in {directory}")

        # Initialize statistics
        self.statistics = {
            "total_traces": len(trace_files),
            "executed_traces": 0,
            "successful_traces": 0,
            "failed_traces": 0,
            "timeout_traces": 0,
            "total_duration": 0.0,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
        }

        self.results = []

        # Execute each trace
        for trace_file in trace_files:
            # Skip non-trace JSON files
            try:
                with open(trace_file, "r") as f:
                    content = f.read(100)
                    if '"session"' not in content and '"command"' not in content:
                        continue
            except:
                continue

            result = self.execute_file(trace_file)
            self.results.append(result)

            # Update statistics
            self.statistics["executed_traces"] += 1
            self.statistics["total_duration"] += result.get("execution_time", 0)

            if result.get("success", False):
                self.statistics["successful_traces"] += 1
            else:
                self.statistics["failed_traces"] += 1

            if result.get("timeout", False):
                self.statistics["timeout_traces"] += 1

            # Log progress
            if self.statistics["executed_traces"] % 10 == 0:
                logger.info(
                    f"Progress: {self.statistics['executed_traces']}/{self.statistics['total_traces']} traces executed"
                )

        # Finalize statistics
        self.statistics["end_time"] = datetime.now(timezone.utc).isoformat()

        # Calculate success rate
        if self.statistics["executed_traces"] > 0:
            self.statistics["success_rate"] = (
                self.statistics["successful_traces"] / self.statistics["executed_traces"] * 100
            )
            self.statistics["average_duration"] = (
                self.statistics["total_duration"] / self.statistics["executed_traces"]
            )
        else:
            self.statistics["success_rate"] = 0.0
            self.statistics["average_duration"] = 0.0

        return {
            "success": self.statistics["success_rate"] > 0,
            "statistics": self.statistics,
            "results": self.results,
            "directory": str(directory),
        }

    def execute_with_validation(
        self, trace_data: Dict[str, Any], validator: Any = None
    ) -> Dict[str, Any]:
        """Execute trace with pre-execution validation.

        Args:
            trace_data: DAP trace dictionary
            validator: Optional trace validator

        Returns:
            Combined validation and execution results
        """
        from ..validation.trace_validator import TraceValidator

        if validator is None:
            validator = TraceValidator()

        # Validate trace first
        validation_result = validator.validate_trace(trace_data)

        if not validation_result["valid"]:
            return {
                "success": False,
                "validation_passed": False,
                "validation_errors": validation_result["errors"],
                "validation_warnings": validation_result["warnings"],
                "execution_result": None,
            }

        # Execute trace
        trace_name = trace_data.get("name", "validated_trace")
        execution_result = self.execute_trace(trace_data, trace_name)

        return {
            "success": execution_result["success"],
            "validation_passed": True,
            "validation_errors": validation_result["errors"],
            "validation_warnings": validation_result["warnings"],
            "execution_result": execution_result,
        }

    def generate_report(self, results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate execution report.

        Args:
            results: Optional list of execution results

        Returns:
            Report dictionary
        """
        if results is None:
            results = self.results

        # Calculate detailed statistics
        total_traces = len(results)
        successful_traces = sum(1 for r in results if r.get("success", False))
        failed_traces = total_traces - successful_traces
        timeout_traces = sum(1 for r in results if r.get("timeout", False))

        execution_times = [r.get("execution_time", 0) for r in results]
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        min_time = min(execution_times) if execution_times else 0

        # Group by trace name pattern
        trace_groups = {}
        for result in results:
            trace_name = result.get("trace_name", "unknown")
            # Extract base name (without suffixes)
            base_name = trace_name.split("_")[0] if "_" in trace_name else trace_name

            if base_name not in trace_groups:
                trace_groups[base_name] = {
                    "count": 0,
                    "successful": 0,
                    "failed": 0,
                    "timeouts": 0,
                    "avg_time": 0.0,
                }

            group = trace_groups[base_name]
            group["count"] += 1
            if result.get("success", False):
                group["successful"] += 1
            else:
                group["failed"] += 1
            if result.get("timeout", False):
                group["timeouts"] += 1

        # Calculate group statistics
        for group_name, group_data in trace_groups.items():
            if group_data["count"] > 0:
                group_data["success_rate"] = group_data["successful"] / group_data["count"] * 100

        # Find common errors
        error_messages = []
        for result in results:
            if not result.get("success", False):
                stderr = result.get("stderr", "")
                if stderr:
                    # Extract first error line
                    for line in stderr.split("\n"):
                        if "error" in line.lower() or "exception" in line.lower():
                            error_messages.append(line.strip())
                            break

        # Count error frequencies
        from collections import Counter

        error_counts = Counter(error_messages)
        common_errors = error_counts.most_common(10)

        # Create report
        report = {
            "summary": {
                "total_traces": total_traces,
                "successful_traces": successful_traces,
                "failed_traces": failed_traces,
                "timeout_traces": timeout_traces,
                "success_rate": (successful_traces / total_traces * 100) if total_traces > 0 else 0,
                "execution_time": {
                    "total": sum(execution_times),
                    "average": avg_time,
                    "maximum": max_time,
                    "minimum": min_time,
                },
            },
            "trace_groups": trace_groups,
            "common_errors": common_errors,
            "execution_details": results,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        return report

    def save_report(self, report: Dict[str, Any], output_dir: Union[str, Path]) -> Path:
        """Save execution report to file.

        Args:
            report: Report dictionary
            output_dir: Output directory

        Returns:
            Path to saved report
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        json_path = (
            output_dir / f"execution_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2)

        # Also save as Markdown for readability
        md_path = output_dir / f"execution_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        self._save_markdown_report(report, md_path)

        logger.info(f"Saved execution reports: {json_path}, {md_path}")
        return json_path

    def _save_markdown_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Save report as Markdown.

        Args:
            report: Report dictionary
            output_path: Output file path
        """
        summary = report["summary"]
        trace_groups = report["trace_groups"]
        common_errors = report["common_errors"]

        with open(output_path, "w") as f:
            f.write("# DAP Trace Execution Report\n\n")
            f.write(f"**Generated**: {report['generated_at']}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- **Total traces executed**: {summary['total_traces']}\n")
            f.write(f"- **Successful traces**: {summary['successful_traces']}\n")
            f.write(f"- **Failed traces**: {summary['failed_traces']}\n")
            f.write(f"- **Timeout traces**: {summary['timeout_traces']}\n")
            f.write(f"- **Success rate**: {summary['success_rate']:.1f}%\n")
            f.write(f"- **Total execution time**: {summary['execution_time']['total']:.2f}s\n")
            f.write(f"- **Average execution time**: {summary['execution_time']['average']:.2f}s\n")
            f.write(f"- **Maximum execution time**: {summary['execution_time']['maximum']:.2f}s\n")
            f.write(
                f"- **Minimum execution time**: {summary['execution_time']['minimum']:.2f}s\n\n"
            )

            f.write("## Trace Groups\n\n")
            f.write("| Group | Count | Successful | Failed | Timeouts | Success Rate |\n")
            f.write("|-------|-------|------------|--------|----------|--------------|\n")

            for group_name, group_data in trace_groups.items():
                f.write(
                    f"| {group_name} | {group_data['count']} | {group_data['successful']} | "
                    f"{group_data['failed']} | {group_data.get('timeouts', 0)} | "
                    f"{group_data.get('success_rate', 0):.1f}% |\n"
                )

            f.write("\n## Common Errors\n\n")
            if common_errors:
                f.write("| Error Message | Count |\n")
                f.write("|---------------|-------|\n")
                for error_msg, count in common_errors:
                    f.write(f"| {error_msg[:100]}... | {count} |\n")
            else:
                f.write("No common errors found.\n")

            f.write("\n## Detailed Results\n\n")
            f.write("For detailed JSON results, see the accompanying JSON file.\n")
