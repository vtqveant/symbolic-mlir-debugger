#!/usr/bin/env python3
"""Run full workflow tests for arithmetic operations via DAP client.

This script automates the testing of arithmetic operations through
the DAP client, including parameter variation and execution path tracking.
"""

import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dap_client.core.client import DAPClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ArithmeticWorkflowTester:
    """Test arithmetic operations workflow via DAP client."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize tester."""
        self.output_dir = output_dir or "test_reports"
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.test_results = []
        self.current_test = None
        
    def create_test_mlir(self, operations: List[str], function_name: str = "test") -> str:
        """Create MLIR file with specified arithmetic operations."""
        operations_map = {
            "addi": "arith.addi %a, %b : i32",
            "subi": "arith.subi %a, %b : i32",
            "muli": "arith.muli %a, %b : i32",
            "divsi": "arith.divsi %a, %b : i32",
            "divui": "arith.divui %a, %b : i32",
            "remsi": "arith.remsi %a, %b : i32",
            "remui": "arith.remui %a, %b : i32",
            "cmpi": "arith.cmpi slt, %a, %b : i32",
            "cmpf": "arith.cmpf olt, %a, %b : f32",
            "andi": "arith.andi %a, %b : i32",
            "ori": "arith.ori %a, %b : i32",
            "xori": "arith.xori %a, %b : i32",
            "shli": "arith.shli %a, %b : i32",
            "shrui": "arith.shrui %a, %b : i32",
            "shrsi": "arith.shrsi %a, %b : i32",
        }
        
        lines = [f"// Arithmetic operations test: {', '.join(operations)}"]
        lines.append("module {")
        lines.append(f"  func.func @{function_name}(%a: i32, %b: i32) -> i32 {{")
        
        result_var = "%a"
        for i, op in enumerate(operations):
            if op in operations_map:
                var_name = f"%op{i}"
                lines.append(f"    {var_name} = {operations_map[op]}")
                result_var = var_name
        
        lines.append(f"    return {result_var} : i32")
        lines.append("  }")
        lines.append("}")
        
        return "\n".join(lines)
    
    def run_single_test(self, test_name: str, mlir_content: str, 
                       concrete_inputs: Optional[Dict] = None,
                       symbolic: bool = False,
                       max_paths: int = 5) -> Dict[str, Any]:
        """Run a single test case."""
        logger.info(f"Running test: {test_name}")
        
        # Create temporary MLIR file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
            f.write(mlir_content)
            mlir_path = f.name
        
        test_result = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "mlir_content": mlir_content,
            "concrete_inputs": concrete_inputs,
            "symbolic": symbolic,
            "success": False,
            "error": None,
            "execution_time": None,
            "paths_explored": 0,
            "breakpoints_hit": 0,
            "dap_events": [],
        }
        
        start_time = time.time()
        
        try:
            with DAPClient() as client:
                # Initialize session
                client.initialize(
                    adapter_id="mlir-debugger",
                    client_id=f"workflow-test-{test_name}"
                )
                
                # Launch with or without concrete inputs
                launch_args = {"program": mlir_path, "no_debug": False}
                if concrete_inputs:
                    launch_args.update(concrete_inputs)
                
                client.launch(**launch_args)
                
                # Set breakpoints
                source = {"path": mlir_path}
                # Count non-empty lines for breakpoints
                lines = [i+1 for i, line in enumerate(mlir_content.split('\n')) 
                        if line.strip() and '=' in line and 'arith.' in line]
                breakpoints = [{"line": line} for line in lines]
                
                result = client.set_breakpoints(
                    source=source,
                    breakpoints=breakpoints
                )
                test_result["breakpoints_set"] = len(result.get("breakpoints", []))
                
                client.configuration_done()
                
                # Continue execution
                for i in range(len(breakpoints)):
                    result = client.continue_execution(thread_id=1)
                    test_result["breakpoints_hit"] += 1
                    test_result["dap_events"].append({
                        "event": "breakpoint_hit",
                        "breakpoint": i+1,
                        "result": result
                    })
                
                # Symbolic execution if requested
                if symbolic:
                    client.symbolic_set_mode(enabled=True)
                    
                    # Explore paths
                    paths_result = client.symbolic_explore_paths(max_paths=max_paths)
                    paths = paths_result.get("paths", [])
                    test_result["paths_explored"] = len(paths)
                    test_result["paths"] = paths
                    
                    # Get constraints
                    constraints_result = client.symbolic_get_constraints()
                    test_result["constraints"] = constraints_result
                    
                    client.symbolic_set_mode(enabled=False)
                
                # Disconnect
                client.disconnect()
                
                test_result["success"] = True
                
        except Exception as e:
            test_result["error"] = str(e)
            logger.error(f"Test {test_name} failed: {e}")
            
        finally:
            # Clean up
            os.unlink(mlir_path)
            
            # Calculate execution time
            test_result["execution_time"] = time.time() - start_time
            
            # Store result
            self.test_results.append(test_result)
            
            if test_result["success"]:
                logger.info(f"Test {test_name} passed in {test_result['execution_time']:.2f}s")
            else:
                logger.error(f"Test {test_name} failed: {test_result['error']}")
            
            return test_result
    
    def run_basic_arithmetic_tests(self):
        """Run basic arithmetic operation tests."""
        logger.info("Running basic arithmetic operation tests")
        
        basic_ops = ["addi", "subi", "muli", "divsi", "remsi"]
        
        for op in basic_ops:
            mlir_content = self.create_test_mlir([op], f"test_{op}")
            test_name = f"basic_{op}"
            
            # Test with different concrete inputs
            test_cases = [
                {"a": 10, "b": 3},
                {"a": 0, "b": 5},
                {"a": -5, "b": 2},
                {"a": 100, "b": 25},
            ]
            
            for i, inputs in enumerate(test_cases):
                full_test_name = f"{test_name}_case{i+1}"
                self.run_single_test(
                    test_name=full_test_name,
                    mlir_content=mlir_content,
                    concrete_inputs=inputs
                )
    
    def run_complex_expression_tests(self):
        """Run tests with complex arithmetic expressions."""
        logger.info("Running complex arithmetic expression tests")
        
        complex_expressions = [
            ["addi", "muli", "subi"],  # (a + b) * c - d style
            ["muli", "divsi", "addi"], # a * b / c + d
            ["subi", "addi", "muli"],  # a - b + c * d
            ["addi", "addi", "addi"],  # chained additions
            ["muli", "muli", "muli"],  # chained multiplications
        ]
        
        for i, ops in enumerate(complex_expressions):
            mlir_content = self.create_test_mlir(ops, f"complex_expr_{i}")
            test_name = f"complex_expr_{i}"
            
            self.run_single_test(
                test_name=test_name,
                mlir_content=mlir_content,
                concrete_inputs={"a": 5, "b": 3}
            )
    
    def run_edge_case_tests(self):
        """Run tests with edge cases."""
        logger.info("Running edge case tests")
        
        edge_cases = [
            # Division by small numbers
            ("divsi", {"a": 10, "b": 2}),
            ("divsi", {"a": 10, "b": 1}),
            ("divsi", {"a": 0, "b": 5}),
            # Negative numbers
            ("addi", {"a": -5, "b": 3}),
            ("subi", {"a": 5, "b": -3}),
            ("muli", {"a": -5, "b": -3}),
            # Large numbers
            ("addi", {"a": 1000000, "b": 2000000}),
            ("muli", {"a": 1000, "b": 1000}),
        ]
        
        for op, inputs in edge_cases:
            mlir_content = self.create_test_mlir([op], f"edge_{op}")
            test_name = f"edge_{op}_{inputs['a']}_{inputs['b']}"
            
            self.run_single_test(
                test_name=test_name,
                mlir_content=mlir_content,
                concrete_inputs=inputs
            )
    
    def run_symbolic_tests(self):
        """Run symbolic execution tests."""
        logger.info("Running symbolic execution tests")
        
        symbolic_ops = ["cmpi", "addi", "muli", "subi"]
        
        for op in symbolic_ops:
            mlir_content = self.create_test_mlir([op], f"symbolic_{op}")
            test_name = f"symbolic_{op}"
            
            self.run_single_test(
                test_name=test_name,
                mlir_content=mlir_content,
                symbolic=True,
                max_paths=3
            )
    
    def run_concolic_tests(self):
        """Run concolic testing with parameter variation."""
        logger.info("Running concolic tests with parameter variation")
        
        # Test with branching logic
        branching_mlir = """// Concolic test with branching
module {
  func.func @concolic_branch(%a: i32, %b: i32) -> i32 {
    %cmp = arith.cmpi sgt, %a, %b : i32
    %select = arith.select %cmp, %a, %b : i32
    %result = arith.muli %select, %a : i32
    return %result : i32
  }
}
"""
        
        # Vary parameters
        parameter_sets = [
            {"a": 5, "b": 3},   # a > b
            {"a": 2, "b": 8},   # a < b
            {"a": 4, "b": 4},   # a == b
            {"a": 0, "b": 0},   # both zero
            {"a": -5, "b": 3},  # negative
        ]
        
        for i, params in enumerate(parameter_sets):
            test_name = f"concolic_branch_case{i+1}"
            
            self.run_single_test(
                test_name=test_name,
                mlir_content=branching_mlir,
                concrete_inputs=params,
                symbolic=True,
                max_paths=2
            )
    
    def generate_report(self):
        """Generate test report."""
        logger.info("Generating test report")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed_tests": sum(1 for r in self.test_results if r["success"]),
            "failed_tests": sum(1 for r in self.test_results if not r["success"]),
            "total_execution_time": sum(r["execution_time"] for r in self.test_results),
            "average_execution_time": sum(r["execution_time"] for r in self.test_results) / len(self.test_results) if self.test_results else 0,
            "test_results": self.test_results,
        }
        
        # Save JSON report
        json_path = os.path.join(self.output_dir, f"arith_workflow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate summary markdown
        md_path = os.path.join(self.output_dir, f"arith_workflow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(md_path, "w") as f:
            f.write("# Arithmetic Workflow Test Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Tests:** {report['total_tests']}\n")
            f.write(f"- **Passed:** {report['passed_tests']}\n")
            f.write(f"- **Failed:** {report['failed_tests']}\n")
            f.write(f"- **Success Rate:** {(report['passed_tests']/report['total_tests']*100):.1f}%\n")
            f.write(f"- **Total Execution Time:** {report['total_execution_time']:.2f}s\n")
            f.write(f"- **Average Time per Test:** {report['average_execution_time']:.2f}s\n\n")
            
            f.write("## Test Categories\n\n")
            
            # Group by test type
            categories = {}
            for result in self.test_results:
                test_name = result["test_name"]
                category = test_name.split("_")[0]  # basic, complex, edge, symbolic, concolic
                if category not in categories:
                    categories[category] = {"total": 0, "passed": 0}
                categories[category]["total"] += 1
                if result["success"]:
                    categories[category]["passed"] += 1
            
            for category, stats in categories.items():
                f.write(f"### {category.capitalize()} Tests\n")
                f.write(f"- Total: {stats['total']}\n")
                f.write(f"- Passed: {stats['passed']}\n")
                f.write(f"- Success Rate: {(stats['passed']/stats['total']*100):.1f}%\n\n")
            
            f.write("## Failed Tests\n\n")
            failed = [r for r in self.test_results if not r["success"]]
            if failed:
                for result in failed:
                    f.write(f"### {result['test_name']}\n")
                    f.write(f"- Error: {result['error']}\n")
                    f.write(f"- Execution Time: {result['execution_time']:.2f}s\n\n")
            else:
                f.write("All tests passed! ✅\n\n")
            
            f.write("## Detailed Results\n\n")
            f.write("| Test Name | Status | Execution Time | Breakpoints Hit | Paths Explored |\n")
            f.write("|-----------|--------|----------------|-----------------|----------------|\n")
            
            for result in self.test_results:
                status = "✅" if result["success"] else "❌"
                f.write(f"| {result['test_name']} | {status} | {result['execution_time']:.2f}s | {result.get('breakpoints_hit', 0)} | {result.get('paths_explored', 0)} |\n")
        
        logger.info(f"JSON report saved to: {json_path}")
        logger.info(f"Markdown summary saved to: {md_path}")
        
        return report
    
    def run_all_tests(self):
        """Run all test suites."""
        logger.info("Starting comprehensive arithmetic workflow testing")
        
        self.run_basic_arithmetic_tests()
        self.run_complex_expression_tests()
        self.run_edge_case_tests()
        self.run_symbolic_tests()
        self.run_concolic_tests()
        
        report = self.generate_report()
        
        # Print summary
        print(f"\n{'='*60}")
        print("ARITHMETIC WORKFLOW TESTING COMPLETE")
        print(f"{'='*60}")
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed_tests']}")
        print(f"Failed: {report['failed_tests']}")
        print(f"Success Rate: {(report['passed_tests']/report['total_tests']*100):.1f}%")
        print(f"Total Execution Time: {report['total_execution_time']:.2f}s")
        print(f"Average Time per Test: {report['average_execution_time']:.2f}s")
        
        if report['failed_tests'] > 0:
            print(f"\nFailed tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['error']}")
        
        return report['passed_tests'] == report['total_tests']


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run arithmetic workflow tests via DAP client")
    parser.add_argument("--output-dir", default="test_reports",
                       help="Directory for test reports (default: test_reports)")
    parser.add_argument("--basic", action="store_true",
                       help="Run only basic arithmetic tests")
    parser.add_argument("--complex", action="store_true",
                       help="Run only complex expression tests")
    parser.add_argument("--edge", action="store_true",
                       help="Run only edge case tests")
    parser.add_argument("--symbolic", action="store_true",
                       help="Run only symbolic execution tests")
    parser.add_argument("--concolic", action="store_true",
                       help="Run only concolic tests")
    
    args = parser.parse_args()
    
    tester = ArithmeticWorkflowTester(output_dir=args.output_dir)
    
    if args.basic:
        tester.run_basic_arithmetic_tests()
    elif args.complex:
        tester.run_complex_expression_tests()
    elif args.edge:
        tester.run_edge_case_tests()
    elif args.symbolic:
        tester.run_symbolic_tests()
    elif args.concolic:
        tester.run_concolic_tests()
    else:
        # Run all tests by default
        tester.run_all_tests()
    
    report = tester.generate_report()
    
    # Exit with appropriate code
    if report['passed_tests'] == report['total_tests']:
        print("\nAll tests passed successfully! ✅")
        return 0
    else:
        print(f"\n{report['failed_tests']} test(s) failed ❌")
        return 1


if __name__ == "__main__":
    sys.exit(main())