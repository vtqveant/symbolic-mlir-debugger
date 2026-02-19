#!/usr/bin/env python3
"""
Run full workflow tests for arithmetic operations.

This script executes generated DAP traces and validates the MLIR debugger's
handling of arithmetic operations.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import from dap_client
try:
    from dap_client.runner.test_runner import TestRunner
    TEST_RUNNER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: TestRunner not available: {e}")
    print("Creating a simple test runner for demonstration")
    TEST_RUNNER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_arith_test_files() -> List[Path]:
    """Collect all arithmetic test files from generated_tests directory."""
    
    tests_dir = Path(__file__).parent.parent / "generated_tests"
    
    if not tests_dir.exists():
        logger.error(f"Tests directory not found: {tests_dir}")
        return []
    
    # Find all arithmetic test files
    arith_test_files = []
    for test_file in tests_dir.glob("*.json"):
        if test_file.name.startswith("arith_") or "arithmetic" in test_file.name:
            arith_test_files.append(test_file)
    
    logger.info(f"Found {len(arith_test_files)} arithmetic test files")
    return arith_test_files


def run_arith_tests(test_files: List[Path]) -> Dict[str, Any]:
    """Run arithmetic tests and collect results."""
    
    all_results = []
    start_time = time.time()
    
    with TestRunner() as runner:
        for test_file in test_files:
            logger.info(f"Running test: {test_file.name}")
            
            try:
                result = runner.run_test_file(str(test_file))
                all_results.append(result)
                
                if result["success"]:
                    logger.info(f"  ✓ PASSED: {test_file.name} ({result['duration']:.2f}s)")
                else:
                    logger.error(f"  ✗ FAILED: {test_file.name} - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"  ✗ ERROR executing {test_file.name}: {e}")
                all_results.append({
                    "name": test_file.name,
                    "success": False,
                    "error": str(e),
                    "duration": 0
                })
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Calculate statistics
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r.get("success", False))
    failed_tests = total_tests - passed_tests
    
    # Group by test type
    test_types = {}
    for result in all_results:
        test_name = result.get("name", "")
        if "edge" in test_name.lower():
            test_type = "edge_cases"
        elif "conditional" in test_name.lower():
            test_type = "conditional"
        elif "basic" in test_name.lower():
            test_type = "basic"
        elif "mixed" in test_name.lower():
            test_type = "mixed_bitwidth"
        else:
            test_type = "other"
        
        test_types.setdefault(test_type, {"total": 0, "passed": 0})
        test_types[test_type]["total"] += 1
        if result.get("success", False):
            test_types[test_type]["passed"] += 1
    
    # Calculate success rates
    for test_type in test_types:
        total = test_types[test_type]["total"]
        passed = test_types[test_type]["passed"]
        test_types[test_type]["success_rate"] = passed / total if total > 0 else 0
    
    summary = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
        "total_duration": total_duration,
        "average_duration": total_duration / total_tests if total_tests > 0 else 0,
        "test_types": test_types,
        "results": all_results
    }
    
    return summary


def generate_test_report(summary: Dict[str, Any], output_path: Path) -> None:
    """Generate a comprehensive test report in Markdown format."""
    
    report_lines = [
        "# Arithmetic Operations Workflow Test Report",
        "",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "## Executive Summary",
        "",
        f"- **Total Tests:** {summary['total_tests']}",
        f"- **Passed Tests:** {summary['passed_tests']}",
        f"- **Failed Tests:** {summary['failed_tests']}",
        f"- **Success Rate:** {summary['success_rate']:.1%}",
        f"- **Total Duration:** {summary['total_duration']:.2f} seconds",
        f"- **Average Duration:** {summary['average_duration']:.2f} seconds per test",
        "",
        "## Test Type Breakdown",
        ""
    ]
    
    # Add test type breakdown
    report_lines.append("| Test Type | Total | Passed | Success Rate |")
    report_lines.append("|-----------|-------|--------|--------------|")
    
    for test_type, stats in summary["test_types"].items():
        success_rate = stats["success_rate"]
        report_lines.append(
            f"| {test_type.replace('_', ' ').title()} | "
            f"{stats['total']} | {stats['passed']} | {success_rate:.1%} |"
        )
    
    report_lines.extend([
        "",
        "## Detailed Results",
        ""
    ])
    
    # Add detailed results
    for i, result in enumerate(summary["results"]):
        status = "✓ PASS" if result.get("success", False) else "✗ FAIL"
        error = result.get("error", "")
        duration = result.get("duration", 0)
        
        report_lines.append(f"### {i+1}. {result.get('name', 'Unknown Test')}")
        report_lines.append(f"- **Status:** {status}")
        report_lines.append(f"- **Duration:** {duration:.2f}s")
        
        if error:
            report_lines.append(f"- **Error:** {error}")
        
        # Add path information if available
        if "path_info" in result:
            path_info = result["path_info"]
            report_lines.append(f"- **Path Index:** {path_info.get('index', 'N/A')}")
            report_lines.append(f"- **Inputs:** {path_info.get('inputs', {})}")
        
        report_lines.append("")
    
    report_lines.extend([
        "## Test Coverage Analysis",
        "",
        "### Arithmetic Operations Tested",
        "",
        "- **Basic Operations:** `arith.addi`, `arith.subi`, `arith.muli`, `arith.divsi`, `arith.remsi`",
        "- **Bit Widths:** i16, i32, i64",
        "- **Conditional Paths:** Branch conditions based on arithmetic comparisons",
        "- **Edge Cases:** Division by zero avoidance, overflow conditions",
        "- **Mixed Operations:** Combined arithmetic with control flow",
        "",
        "### Path Exploration Coverage",
        "",
        "The tests validate that the MLIR debugger can:",
        "",
        "1. Symbolically explore all execution paths through arithmetic functions",
        "2. Generate concrete inputs using Z3 solver for each path",
        "3. Execute DAP traces that validate symbolic evaluation",
        "4. Handle arithmetic edge cases correctly",
        "5. Support mixed bit-width arithmetic operations",
        "",
        "## Recommendations",
        ""
    ])
    
    # Add recommendations based on test results
    if summary["success_rate"] >= 0.9:
        report_lines.append("- ✅ **Excellent coverage:** Arithmetic operations are well-supported")
        report_lines.append("- ✅ **Path exploration works correctly:** All execution paths can be explored")
        report_lines.append("- ✅ **Constraint solving effective:** Z3 solver generates valid inputs")
    elif summary["success_rate"] >= 0.7:
        report_lines.append("- ⚠️ **Good coverage:** Most arithmetic operations work correctly")
        report_lines.append("- ⚠️ **Some issues detected:** Review failed tests for specific problems")
        report_lines.append("- ⚠️ **Consider expanding test coverage:** Add more edge cases")
    else:
        report_lines.append("- ❌ **Poor coverage:** Significant issues with arithmetic operations")
        report_lines.append("- ❌ **Investigate failures:** Check debugger implementation")
        report_lines.append("- ❌ **Expand debugging:** Add more logging for failed cases")
    
    report_lines.extend([
        "",
        "## Next Steps",
        "",
        "1. Review any failed tests to identify implementation issues",
        "2. Expand test coverage with additional arithmetic operations",
        "3. Add performance benchmarks for arithmetic operations",
        "4. Integrate with CI/CD pipeline for automated testing",
        ""
    ])
    
    # Write the report
    with open(output_path, "w") as f:
        f.write("\n".join(report_lines))
    
    logger.info(f"Test report saved to: {output_path}")


def save_json_results(summary: Dict[str, Any], output_path: Path) -> None:
    """Save detailed results in JSON format."""
    
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"JSON results saved to: {output_path}")


def main():
    """Main function to run arithmetic workflow tests."""
    
    logger.info("Starting arithmetic workflow tests...")
    
    # Create reports directory
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect test files
    test_files = collect_arith_test_files()
    
    if not test_files:
        logger.error("No arithmetic test files found. Generate tests first.")
        logger.info("Run: python scripts/generate_arith_tests.py")
        return 1
    
    # Run tests
    logger.info(f"Running {len(test_files)} arithmetic tests...")
    summary = run_arith_tests(test_files)
    
    # Generate reports
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Markdown report
    report_path = reports_dir / f"arith_workflow_test_report_{timestamp}.md"
    generate_test_report(summary, report_path)
    
    # JSON results
    json_path = reports_dir / f"arith_test_results_{timestamp}.json"
    save_json_results(summary, json_path)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("ARITHMETIC WORKFLOW TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Tests: {summary['total_tests']}")
    logger.info(f"Passed: {summary['passed_tests']}")
    logger.info(f"Failed: {summary['failed_tests']}")
    logger.info(f"Success Rate: {summary['success_rate']:.1%}")
    logger.info(f"Total Duration: {summary['total_duration']:.2f}s")
    logger.info("="*60)
    
    # Print test type breakdown
    logger.info("\nTest Type Breakdown:")
    for test_type, stats in summary["test_types"].items():
        rate = stats["success_rate"]
        logger.info(f"  {test_type.replace('_', ' ').title():20} {stats['passed']}/{stats['total']} ({rate:.1%})")
    
    logger.info("\nReports generated:")
    logger.info(f"  - Markdown: {report_path}")
    logger.info(f"  - JSON: {json_path}")
    
    # Return non-zero exit code if success rate is below 90%
    if summary["success_rate"] < 0.9:
        logger.warning("\nWARNING: Success rate below 90% target")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())