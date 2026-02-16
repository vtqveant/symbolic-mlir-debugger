#!/usr/bin/env python3
"""
Test orchestrator for automated DAP client testing.

Manages multiple test sessions, parallel execution, and result aggregation.
"""

import json
import logging
import multiprocessing
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from .test_runner import TestRunner
from ..generator import TestCaseGenerator, PathAwareGenerator

logger = logging.getLogger(__name__)


class TestOrchestrator:
    """Orchestrate multiple test sessions and result aggregation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5678,
        timeout: int = 30,
        read_timeout: int = 10,
        max_workers: Optional[int] = None,
    ):
        """Initialize test orchestrator.

        Args:
            host: DAP server host
            port: DAP server port
            timeout: Connection timeout
            read_timeout: Read timeout
            max_workers: Maximum number of parallel workers (default: CPU count)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.read_timeout = read_timeout
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.results: List[Dict[str, Any]] = []
        self.generator = TestCaseGenerator(host, port, timeout, read_timeout)
        self.path_aware_generator = PathAwareGenerator(
            host, port, timeout, read_timeout
        )

    def run_test_files(
        self,
        test_files: List[str],
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """Run multiple test files.

        Args:
            test_files: List of paths to test script JSON files
            parallel: Whether to run tests in parallel

        Returns:
            Aggregated results
        """
        logger.info(f"Running {len(test_files)} test files")

        start_time = time.time()

        if parallel and len(test_files) > 1:
            results = self._run_parallel(test_files)
        else:
            results = self._run_sequential(test_files)

        end_time = time.time()

        summary = self._aggregate_results(results)
        summary["total_duration"] = end_time - start_time
        summary["parallel"] = parallel

        self.results.extend(results)
        return summary

    def _run_sequential(self, test_files: List[str]) -> List[Dict[str, Any]]:
        """Run test files sequentially.

        Args:
            test_files: List of paths to test script JSON files

        Returns:
            List of test results
        """
        results = []
        for test_file in test_files:
            try:
                with TestRunner(
                    self.host, self.port, self.timeout, self.read_timeout
                ) as runner:
                    result = runner.run_test_file(test_file)
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to run test file {test_file}: {e}")
                results.append(
                    {
                        "name": Path(test_file).stem,
                        "program": "unknown",
                        "script_path": test_file,
                        "success": False,
                        "error": str(e),
                        "steps": [],
                    }
                )

        return results

    def _run_parallel(self, test_files: List[str]) -> List[Dict[str, Any]]:
        """Run test files in parallel.

        Args:
            test_files: List of paths to test script JSON files

        Returns:
            List of test results
        """
        results = []

        def run_single(test_file: str) -> Dict[str, Any]:
            try:
                with TestRunner(
                    self.host, self.port, self.timeout, self.read_timeout
                ) as runner:
                    return runner.run_test_file(test_file)
            except Exception as e:
                logger.error(f"Failed to run test file {test_file}: {e}")
                return {
                    "name": Path(test_file).stem,
                    "program": "unknown",
                    "script_path": test_file,
                    "success": False,
                    "error": str(e),
                    "steps": [],
                }

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(run_single, test_file): test_file
                for test_file in test_files
            }

            for future in as_completed(future_to_file):
                test_file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Unexpected error running {test_file}: {e}")
                    results.append(
                        {
                            "name": Path(test_file).stem,
                            "program": "unknown",
                            "script_path": test_file,
                            "success": False,
                            "error": str(e),
                            "steps": [],
                        }
                    )

        return results

    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate multiple test results.

        Args:
            results: List of test results

        Returns:
            Aggregated summary
        """
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.get("success", False))
        failed_tests = total_tests - passed_tests

        total_steps = sum(len(r.get("steps", [])) for r in results)
        passed_steps = sum(
            sum(1 for step in r.get("steps", []) if step.get("success", False))
            for r in results
        )
        failed_steps = total_steps - passed_steps

        # Group by test name
        test_groups: Dict[str, List[Dict[str, Any]]] = {}
        for result in results:
            name = result.get("name", "unknown")
            test_groups.setdefault(name, []).append(result)

        # Calculate durations
        durations = [r.get("duration", 0) for r in results if r.get("duration")]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "step_success_rate": passed_steps / total_steps if total_steps > 0 else 0,
            "avg_duration": avg_duration,
            "max_duration": max_duration,
            "min_duration": min_duration,
            "test_groups": {
                name: {
                    "count": len(group),
                    "passed": sum(1 for r in group if r.get("success", False)),
                    "failed": sum(1 for r in group if not r.get("success", False)),
                }
                for name, group in test_groups.items()
            },
            "results": results,
        }

    def generate_and_run(
        self,
        program_path: str,
        max_paths: int = 5,
        output_dir: str = "generated_tests",
        run_tests: bool = True,
        clean_generated: bool = False,
    ) -> Dict[str, Any]:
        """Generate test cases from program and optionally run them.

        Args:
            program_path: Path to MLIR program
            max_paths: Maximum number of paths to explore
            output_dir: Directory to save generated test scripts
            run_tests: Whether to run generated tests
            clean_generated: Whether to clean generated files after running

        Returns:
            Combined results from generation and execution
        """
        logger.info(f"Generating test cases for {program_path}")

        generation_results = {
            "program": program_path,
            "max_paths": max_paths,
            "generated_files": [],
            "generation_success": False,
        }

        try:
            # Connect generator
            with self.generator as generator:
                # Generate test scripts
                test_scripts = generator.generate_from_program(
                    program_path=program_path,
                    max_paths=max_paths,
                )

                # Save test scripts
                generated_files = generator.save_test_scripts(
                    test_scripts=test_scripts,
                    output_dir=output_dir,
                )

                generation_results["generated_files"] = generated_files
                generation_results["generation_success"] = True
                generation_results["test_script_count"] = len(test_scripts)

                logger.info(f"Generated {len(test_scripts)} test scripts")

        except Exception as e:
            logger.error(f"Failed to generate test cases: {e}")
            generation_results["generation_success"] = False
            generation_results["error"] = str(e)

        # Run generated tests if requested
        execution_results = None
        if run_tests and generation_results["generation_success"]:
            logger.info("Running generated tests")
            execution_results = self.run_test_files(
                test_files=generated_files,
                parallel=True,
            )

        # Clean up generated files if requested
        if clean_generated:
            logger.info("Cleaning up generated test files")
            for file_path in generated_files:
                try:
                    Path(file_path).unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

        # Combine results
        combined_results = {
            "generation": generation_results,
            "execution": execution_results,
        }

        return combined_results

    def run_memory_model_tests(
        self,
        program_path: str,
        output_dir: str = "memory_model_tests",
        run_tests: bool = True,
    ) -> Dict[str, Any]:
        """Generate and run memory model focused tests.

        Args:
            program_path: Path to MLIR program with memory operations
            output_dir: Directory to save generated test scripts
            run_tests: Whether to run generated tests

        Returns:
            Combined results
        """
        logger.info(f"Generating memory model tests for {program_path}")

        generation_results = {
            "program": program_path,
            "test_type": "memory_model",
            "generated_files": [],
            "generation_success": False,
        }

        try:
            # Use path-aware generator for memory model tests
            with self.path_aware_generator as generator:
                # Generate memory model tests
                test_scripts = generator.generate_memory_model_tests(
                    program_path=program_path,
                )

                # Save test scripts
                generated_files = []
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)

                for i, test_script in enumerate(test_scripts):
                    file_name = f"memory_model_test_{i}.json"
                    file_path = output_path / file_name

                    with open(file_path, "w") as f:
                        json.dump(test_script, f, indent=2)

                    generated_files.append(str(file_path))

                generation_results["generated_files"] = generated_files
                generation_results["generation_success"] = True
                generation_results["test_script_count"] = len(test_scripts)

                logger.info(f"Generated {len(test_scripts)} memory model test scripts")

        except Exception as e:
            logger.error(f"Failed to generate memory model tests: {e}")
            generation_results["generation_success"] = False
            generation_results["error"] = str(e)

        # Run generated tests if requested
        execution_results = None
        if run_tests and generation_results["generation_success"]:
            logger.info("Running memory model tests")
            execution_results = self.run_test_files(
                test_files=generated_files,
                parallel=True,
            )

        # Combine results
        combined_results = {
            "generation": generation_results,
            "execution": execution_results,
        }

        return combined_results

    def save_report(
        self, results: Dict[str, Any], output_path: str = "test_report.json"
    ) -> str:
        """Save test report to JSON file.

        Args:
            results: Test results to save
            output_path: Path to output JSON file

        Returns:
            Path to saved file
        """
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Report saved to {output_path}")
        return output_path

    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print human-readable test summary.

        Args:
            results: Test results summary
        """
        print("\n" + "=" * 60)
        print("TEST EXECUTION SUMMARY")
        print("=" * 60)

        if "total_tests" in results:
            # Execution summary
            print(f"Total Tests: {results['total_tests']}")
            print(f"Passed: {results['passed_tests']}")
            print(f"Failed: {results['failed_tests']}")
            print(f"Success Rate: {results['success_rate']:.1%}")
            print(f"Total Steps: {results['total_steps']}")
            print(f"Step Success Rate: {results['step_success_rate']:.1%}")
            print(f"Average Duration: {results['avg_duration']:.2f}s")
            print(f"Max Duration: {results['max_duration']:.2f}s")
            print(f"Min Duration: {results['min_duration']:.2f}s")

        elif "generation" in results:
            # Generation summary
            gen = results["generation"]
            print(f"Program: {gen['program']}")
            print(f"Generation Success: {gen['generation_success']}")
            if gen["generation_success"]:
                print(f"Generated Files: {len(gen['generated_files'])}")
                print(f"Test Script Count: {gen.get('test_script_count', 0)}")

            if "execution" in results and results["execution"]:
                exec_results = results["execution"]
                print(f"\nExecution Results:")
                print(f"  Total Tests: {exec_results['total_tests']}")
                print(f"  Passed: {exec_results['passed_tests']}")
                print(f"  Success Rate: {exec_results['success_rate']:.1%}")

        print("=" * 60)
