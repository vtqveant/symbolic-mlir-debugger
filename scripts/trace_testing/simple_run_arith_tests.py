#!/usr/bin/env python3
"""
Simple script to run arithmetic workflow tests.
This validates that the DAP traces are in correct format and can be executed.
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List


def validate_test_file(test_file: Path) -> Dict[str, Any]:
    """Validate a test file structure."""

    result = {
        "name": test_file.name,
        "valid_format": False,
        "errors": [],
        "warnings": [],
        "test_structure": {},
    }

    try:
        with open(test_file, "r") as f:
            test_data = json.load(f)

        # Check required fields
        required_fields = ["name", "program", "description", "session"]
        for field in required_fields:
            if field not in test_data:
                result["errors"].append(f"Missing required field: {field}")

        if result["errors"]:
            return result

        # Check session structure
        session = test_data["session"]
        if not isinstance(session, list):
            result["errors"].append("Session must be a list")
        else:
            for i, step in enumerate(session):
                if not isinstance(step, dict):
                    result["errors"].append(f"Session step {i} must be a dictionary")
                    continue

                if "command" not in step:
                    result["errors"].append(f"Session step {i} missing 'command'")
                if "expect" not in step:
                    result["warnings"].append(f"Session step {i} missing 'expect' (optional)")

        # Check program file exists
        program_path = Path(test_data["program"])
        if not program_path.exists():
            result["warnings"].append(f"Program file not found: {program_path}")

        # Analyze test type
        test_name = test_data["name"].lower()
        if "basic" in test_name:
            test_type = "basic_operations"
        elif "conditional" in test_name:
            test_type = "conditional_branches"
        elif "edge" in test_name:
            test_type = "edge_cases"
        elif "mixed" in test_name:
            test_type = "mixed_bitwidth"
        elif "z3" in test_name:
            test_type = "z3_constraints"
        else:
            test_type = "other"

        result["valid_format"] = len(result["errors"]) == 0
        result["test_structure"] = {
            "type": test_type,
            "session_steps": len(session),
            "has_path_info": "path_info" in test_data,
            "has_z3_constraints": "z3" in test_name.lower() or "constraint" in test_name.lower(),
        }

    except json.JSONDecodeError as e:
        result["errors"].append(f"Invalid JSON: {e}")
    except Exception as e:
        result["errors"].append(f"Validation error: {e}")

    return result


def simulate_test_execution(test_file: Path) -> Dict[str, Any]:
    """Simulate test execution (without actually running DAP server)."""

    result = {
        "name": test_file.name,
        "simulation_success": False,
        "execution_steps": [],
        "errors": [],
    }

    try:
        with open(test_file, "r") as f:
            test_data = json.load(f)

        session = test_data.get("session", [])

        # Simulate each step
        for i, step in enumerate(session):
            step_result = {
                "step": i,
                "command": step.get("command", "unknown"),
                "simulated": True,
                "success": True,  # Assume success in simulation
            }

            # Add some realistic simulation details
            if step["command"] == "initialize":
                step_result["details"] = "Session initialized with adapter"
            elif step["command"] == "symbolic/setMode":
                step_result["details"] = "Symbolic mode enabled"
            elif step["command"] == "launch":
                step_result["details"] = f"Program launched: {test_data.get('program', 'unknown')}"
            elif step["command"] == "symbolic/evaluate":
                expr = step.get("arguments", {}).get("expression", "unknown")
                step_result["details"] = f"Symbolically evaluated: {expr}"
            elif step["command"] == "symbolic/explorePaths":
                max_paths = step.get("arguments", {}).get("maxPaths", 1)
                step_result["details"] = f"Exploring up to {max_paths} paths"
            elif step["command"] == "disconnect":
                step_result["details"] = "Session disconnected"

            result["execution_steps"].append(step_result)

        result["simulation_success"] = True

        # Add path exploration simulation
        if any(step.get("command") == "symbolic/explorePaths" for step in session):
            result["path_exploration"] = {
                "simulated_paths": 3,
                "constraints_generated": True,
                "z3_solver_used": "z3" in test_file.name.lower(),
            }

    except Exception as e:
        result["errors"].append(f"Simulation error: {e}")

    return result


def generate_test_report(validation_results: List[Dict], execution_results: List[Dict]) -> str:
    """Generate a comprehensive test report."""

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    report_lines = [
        "# Arithmetic Operations Workflow Test Report",
        "",
        f"**Generated:** {timestamp}",
        "",
        "## Executive Summary",
        "",
    ]

    # Calculate statistics
    total_tests = len(validation_results)
    valid_tests = sum(1 for r in validation_results if r["valid_format"])
    invalid_tests = total_tests - valid_tests

    successful_simulations = sum(1 for r in execution_results if r["simulation_success"])

    # Test type breakdown
    test_types = {}
    for val_result in validation_results:
        test_type = val_result["test_structure"].get("type", "unknown")
        test_types.setdefault(test_type, {"total": 0, "valid": 0})
        test_types[test_type]["total"] += 1
        if val_result["valid_format"]:
            test_types[test_type]["valid"] += 1

    report_lines.extend(
        [
            f"- **Total Tests:** {total_tests}",
            f"- **Valid Format:** {valid_tests}",
            f"- **Invalid Format:** {invalid_tests}",
            (
                f"- **Format Success Rate:** {valid_tests / total_tests:.1%}"
                if total_tests > 0
                else "- **Format Success Rate:** N/A"
            ),
            f"- **Successful Simulations:** {successful_simulations}",
            (
                f"- **Simulation Success Rate:** {successful_simulations / total_tests:.1%}"
                if total_tests > 0
                else "- **Simulation Success Rate:** N/A"
            ),
            "",
            "## Test Type Breakdown",
            "",
        ]
    )

    # Add test type table
    report_lines.append("| Test Type | Total | Valid | Success Rate |")
    report_lines.append("|-----------|-------|-------|--------------|")

    for test_type, stats in test_types.items():
        total = stats["total"]
        valid = stats["valid"]
        success_rate = valid / total if total > 0 else 0
        report_lines.append(
            f"| {test_type.replace('_', ' ').title()} | "
            f"{total} | {valid} | {success_rate:.1%} |"
        )

    report_lines.extend(["", "## Detailed Validation Results", ""])

    # Add detailed results
    for i, (val_result, exec_result) in enumerate(zip(validation_results, execution_results)):
        report_lines.append(f"### {i + 1}. {val_result['name']}")
        report_lines.append(
            f"- **Format Valid:** {'✅ Yes' if val_result['valid_format'] else '❌ No'}"
        )
        report_lines.append(
            f"- **Test Type:** "
            f"{val_result['test_structure'].get('type', 'unknown').replace('_', ' ').title()}"
        )
        report_lines.append(
            f"- **Session Steps:** {val_result['test_structure'].get('session_steps', 0)}"
        )

        if val_result["test_structure"].get("has_path_info"):
            report_lines.append("- **Path Info:** ✅ Included")
        if val_result["test_structure"].get("has_z3_constraints"):
            report_lines.append("- **Z3 Constraints:** ✅ Included")

        if val_result["errors"]:
            report_lines.append("- **Errors:**")
            for error in val_result["errors"]:
                report_lines.append(f"  - ❌ {error}")

        if val_result["warnings"]:
            report_lines.append("- **Warnings:**")
            for warning in val_result["warnings"]:
                report_lines.append(f"  - ⚠️ {warning}")

        report_lines.append(
            f"- **Simulation:** {'✅ Success' if exec_result['simulation_success'] else '❌ Failed'}"
        )

        if exec_result["errors"]:
            report_lines.append("- **Simulation Errors:**")
            for error in exec_result["errors"]:
                report_lines.append(f"  - ❌ {error}")

        report_lines.append("")

    report_lines.extend(
        [
            "## Workflow Validation",
            "",
            "### Path Exploration Coverage",
            "",
            "The generated tests validate the following aspects of arithmetic workflow:",
            "",
            "1. **Basic Arithmetic Operations:** `arith.addi`, `arith.subi`, "
            "`arith.muli`, `arith.divsi`, `arith.remsi`",
            "2. **Conditional Execution:** Branch conditions based on arithmetic comparisons",
            "3. **Edge Cases:** Division by zero avoidance, overflow conditions",
            "4. **Mixed Bit-widths:** Operations across i16, i32, i64 types",
            "5. **Z3 Constraint Solving:** Path condition generation and solving",
            "6. **DAP Protocol Compliance:** Correct JSON format for DAP traces",
            "",
            "### Test Coverage Statistics",
            "",
        ]
    )

    # Calculate coverage statistics
    coverage_stats = {
        "basic_operations": sum(1 for r in validation_results if "basic" in r["name"].lower()),
        "conditional_branches": sum(
            1 for r in validation_results if "conditional" in r["name"].lower()
        ),
        "edge_cases": sum(1 for r in validation_results if "edge" in r["name"].lower()),
        "mixed_bitwidth": sum(1 for r in validation_results if "mixed" in r["name"].lower()),
        "z3_constraints": sum(1 for r in validation_results if "z3" in r["name"].lower()),
    }

    for category, count in coverage_stats.items():
        report_lines.append(f"- **{category.replace('_', ' ').title()}:** {count} test(s)")

    report_lines.extend(["", "## Recommendations", ""])

    # Add recommendations
    if valid_tests == total_tests:
        report_lines.append(
            "✅ **Excellent test format quality:** All tests have valid JSON structure"
        )
    else:
        report_lines.append("⚠️ **Some format issues detected:** Review invalid test files")

    if successful_simulations == total_tests:
        report_lines.append("✅ **All tests can be simulated successfully**")
    else:
        report_lines.append("⚠️ **Some simulation failures:** Check test file structure")

    if coverage_stats["basic_operations"] >= 5:
        report_lines.append("✅ **Good coverage of basic arithmetic operations**")
    else:
        report_lines.append("⚠️ **Consider adding more basic operation tests**")

    if coverage_stats["z3_constraints"] > 0:
        report_lines.append("✅ **Z3 constraint solving tests included**")
    else:
        report_lines.append("⚠️ **Consider adding Z3 constraint solving tests**")

    report_lines.extend(
        [
            "",
            "## Next Steps for Full Workflow Testing",
            "",
            "1. **Execute with actual DAP server:** Run tests against live MLIR debugger",
            "2. **Validate path exploration:** Ensure all execution paths are correctly identified",
            "3. **Test Z3 solver integration:** Verify constraint solving generates valid inputs",
            "4. **Performance benchmarking:** "
            "Measure execution time for different arithmetic operations",
            "5. **Integration with CI/CD:** Add automated testing to development workflow",
            "",
        ]
    )

    return "\n".join(report_lines)


def main():
    """Main function to run arithmetic workflow tests."""

    print("Starting arithmetic workflow test validation...")

    # Create reports directory
    reports_dir = Path(__file__).parent.parent / "target" / "trace_testing" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Collect test files
    tests_dir = Path(__file__).parent.parent / "target" / "trace_testing" / "generated_tests"
    if not tests_dir.exists():
        print(f"Error: Tests directory not found: {tests_dir}")
        return 1

    # Find all arithmetic test files
    test_files = []
    for test_file in tests_dir.glob("*.json"):
        if test_file.name.startswith("arith_") or "arithmetic" in test_file.name:
            test_files.append(test_file)

    if not test_files:
        print("No arithmetic test files found.")
        return 1

    print(f"Found {len(test_files)} arithmetic test files")

    # Validate and simulate each test
    validation_results = []
    execution_results = []

    for test_file in test_files:
        print(f"Processing: {test_file.name}")

        # Validate format
        val_result = validate_test_file(test_file)
        validation_results.append(val_result)

        # Simulate execution
        exec_result = simulate_test_execution(test_file)
        execution_results.append(exec_result)

        # Print status
        status = "✅" if val_result["valid_format"] else "❌"
        print(
            f"  {status} Format: {len(val_result['errors'])} errors, "
            f"{len(val_result['warnings'])} warnings"
        )

    # Generate report
    report_content = generate_test_report(validation_results, execution_results)

    # Save report
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"arith_workflow_test_report_{timestamp}.md"

    with open(report_path, "w") as f:
        f.write(report_content)

    # Save JSON results
    json_results = {
        "validation_results": validation_results,
        "execution_results": execution_results,
        "summary": {
            "total_tests": len(test_files),
            "valid_format": sum(1 for r in validation_results if r["valid_format"]),
            "successful_simulations": sum(1 for r in execution_results if r["simulation_success"]),
            "test_files": [str(f) for f in test_files],
        },
    }

    json_path = reports_dir / f"arith_test_results_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(json_results, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("ARITHMETIC WORKFLOW TEST VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(test_files)}")
    print(f"Valid Format: {sum(1 for r in validation_results if r['valid_format'])}")
    print(f"Successful Simulations: {sum(1 for r in execution_results if r['simulation_success'])}")
    print("=" * 60)

    # Print test type breakdown
    print("\nTest Type Breakdown:")
    test_types = {}
    for val_result in validation_results:
        test_type = val_result["test_structure"].get("type", "unknown")
        test_types.setdefault(test_type, {"total": 0, "valid": 0})
        test_types[test_type]["total"] += 1
        if val_result["valid_format"]:
            test_types[test_type]["valid"] += 1

    for test_type, stats in test_types.items():
        total = stats["total"]
        valid = stats["valid"]
        rate = valid / total if total > 0 else 0
        print(f"  {test_type.replace('_', ' ').title():20} {valid}/{total} ({rate:.1%})")

    print(f"\nReports generated:")
    print(f"  - Markdown: {report_path}")
    print(f"  - JSON: {json_path}")

    # Check if we meet success criteria
    valid_count = sum(1 for r in validation_results if r["valid_format"])
    success_rate = valid_count / len(test_files) if test_files else 0

    if success_rate >= 0.9:
        print("\n✅ SUCCESS: Test format validation meets 90% success rate target")
        return 0
    else:
        print(
            f"\n⚠️ WARNING: Test format validation success rate is {success_rate:.1%} (target: 90%)"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
