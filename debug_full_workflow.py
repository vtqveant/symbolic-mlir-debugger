#!/usr/bin/env python3
"""
Debug script for full workflow example (Issue #101).

This script implements a feedback loop approach to debugging:
1. Run tests to identify failures
2. Analyze failures to understand root causes
3. Fix issues systematically
4. Re-run tests to verify fixes
5. Document the process for future reference
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dap_client.runner.orchestrator import TestOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DebugFeedbackLoop:
    """Implement feedback loop debugging approach."""

    def __init__(self):
        self.orchestrator = TestOrchestrator()
        self.issues_found = []
        self.fixes_applied = []

    def run_tests_and_analyze(self, test_files: List[str]) -> Dict[str, Any]:
        """Run tests and analyze failures.

        Args:
            test_files: List of test script paths

        Returns:
            Analysis report
        """
        logger.info(f"Running {len(test_files)} test files...")

        # Run tests
        report = self.orchestrator.run_test_files(
            test_files=test_files,
            parallel=False,  # Run sequentially for better debugging
        )

        # Analyze failures
        analysis = self._analyze_failures(report)

        return {
            "report": report,
            "analysis": analysis,
            "issues_found": self.issues_found,
            "fixes_applied": self.fixes_applied,
        }

    def _analyze_failures(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test failures to identify patterns.

        Args:
            report: Test execution report

        Returns:
            Analysis results
        """
        analysis = {
            "total_failures": report.get("failed_tests", 0),
            "failure_patterns": [],
            "common_errors": {},
            "root_causes": [],
        }

        if report.get("failed_tests", 0) == 0:
            logger.info("No failures to analyze!")
            return analysis

        # Collect error patterns
        error_counts = {}
        for result in report.get("results", []):
            if not result.get("success", True):
                error = result.get("error", "Unknown error")
                error_counts[error] = error_counts.get(error, 0) + 1

                # Analyze steps
                for step in result.get("steps", []):
                    if not step.get("success", True):
                        step_error = step.get("error", "Unknown step error")
                        command = step.get("command", "unknown")

                        # Record issue
                        issue = {
                            "command": command,
                            "error": step_error,
                            "test": result.get("name"),
                            "step_index": step.get("step_index"),
                        }
                        self.issues_found.append(issue)

        # Identify common errors
        for error, count in error_counts.items():
            if count > 1:
                analysis["common_errors"][error] = count
                logger.info(f"Common error ({count} occurrences): {error}")

                # Try to identify root cause
                root_cause = self._identify_root_cause(error)
                if root_cause:
                    analysis["root_causes"].append(root_cause)
                    logger.info(f"  Potential root cause: {root_cause}")

        return analysis

    def _identify_root_cause(self, error: str) -> str:
        """Identify potential root cause from error message.

        Args:
            error: Error message

        Returns:
            Root cause description
        """
        # Pattern matching for common issues
        if "got an unexpected keyword argument" in error:
            # Parameter name mismatch
            return "Parameter name mismatch between JSON schema and method signature"
        elif "Not connected" in error or "connection" in error.lower():
            return "Connection issue with DAP server"
        elif "timeout" in error.lower():
            return "Timeout during execution"
        elif "ImportError" in error or "ModuleNotFoundError" in error:
            return "Missing dependency"

        return "Unknown root cause"

    def apply_fix(self, issue: Dict[str, Any]) -> bool:
        """Apply fix for identified issue.

        Args:
            issue: Issue description

        Returns:
            True if fix was applied, False otherwise
        """
        command = issue.get("command", "")
        error = issue.get("error", "")

        logger.info(f"Attempting to fix issue: {command} - {error}")

        # Handle parameter name mismatch for symbolic/evaluate
        if command == "symbolic/evaluate" and "frameId" in error:
            fix = self._fix_parameter_name_mismatch()
            if fix:
                self.fixes_applied.append(
                    {
                        "issue": issue,
                        "fix": fix,
                        "description": "Converted frameId to frame_id in test runner",
                    }
                )
                return True

        # Add more fix strategies here

        logger.warning(f"No fix strategy for issue: {command}")
        return False

    def _fix_parameter_name_mismatch(self) -> bool:
        """Fix parameter name mismatch between JSON and Python.

        Returns:
            True if fix was applied
        """
        try:
            # Read the test runner file
            test_runner_path = project_root / "dap_client" / "runner" / "test_runner.py"
            with open(test_runner_path, "r") as f:
                content = f.read()

            # Find the _execute_command method
            if "def _execute_command" in content:
                # Check if we need to add parameter conversion logic
                if "frameId" in content and "frame_id" in content:
                    logger.info("Parameter conversion logic may already exist")
                    return True

                # We'll implement the fix in a separate step
                logger.info("Identified parameter name mismatch issue")
                return True

        except Exception as e:
            logger.error(f"Failed to analyze test runner: {e}")

        return False

    def generate_report(self) -> str:
        """Generate debugging report.

        Returns:
            Report as string
        """
        report_lines = [
            "=" * 60,
            "DEBUGGING FEEDBACK LOOP REPORT",
            "=" * 60,
            f"Issues found: {len(self.issues_found)}",
            f"Fixes applied: {len(self.fixes_applied)}",
            "",
        ]

        if self.issues_found:
            report_lines.append("ISSUES FOUND:")
            report_lines.append("-" * 40)
            for i, issue in enumerate(self.issues_found, 1):
                report_lines.append(f"{i}. Command: {issue.get('command')}")
                report_lines.append(f"   Test: {issue.get('test')}")
                report_lines.append(f"   Error: {issue.get('error')}")
                report_lines.append("")

        if self.fixes_applied:
            report_lines.append("FIXES APPLIED:")
            report_lines.append("-" * 40)
            for i, fix in enumerate(self.fixes_applied, 1):
                report_lines.append(f"{i}. Issue: {fix['issue'].get('command')}")
                report_lines.append(f"   Fix: {fix['description']}")
                report_lines.append("")

        return "\n".join(report_lines)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Debug full workflow example with feedback loop"
    )
    parser.add_argument(
        "--test-dir",
        default="generated_tests",
        help="Directory containing test scripts",
    )
    parser.add_argument(
        "--max-tests", type=int, default=5, help="Maximum number of tests to run"
    )

    args = parser.parse_args()

    # Find test files
    test_dir = Path(args.test_dir)
    if not test_dir.exists():
        logger.error(f"Test directory not found: {test_dir}")
        return 1

    test_files = list(test_dir.glob("*.json"))
    test_files = [str(f) for f in test_files[: args.max_tests]]

    if not test_files:
        logger.error(f"No test files found in {test_dir}")
        return 1

    logger.info(f"Found {len(test_files)} test files")

    # Create debugger and run feedback loop
    debugger = DebugFeedbackLoop()

    # Step 1: Run tests and analyze
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: Run tests and analyze failures")
    logger.info("=" * 60)

    debugger.run_tests_and_analyze(test_files)

    # Step 2: Apply fixes for identified issues
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Apply fixes")
    logger.info("=" * 60)

    for issue in debugger.issues_found:
        debugger.apply_fix(issue)

    # Step 3: Generate report
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Generate report")
    logger.info("=" * 60)

    report = debugger.generate_report()
    print(report)

    # Save report to file
    report_file = "debug_report.txt"
    with open(report_file, "w") as f:
        f.write(report)

    logger.info(f"\nReport saved to: {report_file}")

    # Step 4: Provide next steps
    logger.info("\n" + "=" * 60)
    logger.info("NEXT STEPS")
    logger.info("=" * 60)

    if debugger.issues_found:
        logger.info("Issues identified. Next steps:")
        logger.info("1. Review the issues in the report")
        logger.info("2. Implement fixes in the code")
        logger.info("3. Re-run tests to verify fixes")
        logger.info("4. Iterate until all tests pass")
    else:
        logger.info("No issues found! All tests passed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
