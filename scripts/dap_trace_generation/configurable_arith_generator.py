#!/usr/bin/env python3
"""
Configurable Arithmetic Dialect DAP Trace Generator

This script generates DAP test traces for arithmetic dialect operations
based on a configuration file. It creates individual MLIR files as test
artifacts and generates corresponding DAP traces.

Usage:
    python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml
    python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --mlir-only
    python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --traces-only
"""

import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
import subprocess
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from dap_client.generator.path_aware_generator import PathAwareGenerator
    from dap_client.generator.test_case_generator import TestCaseGenerator
    from dap_client.runner.test_runner import TestRunner

    DAP_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import DAP client modules: {e}")
    print("Some functionality may be limited.")
    PathAwareGenerator = None
    TestCaseGenerator = None
    TestRunner = None
    DAP_CLIENT_AVAILABLE = False


class ConfigurableArithGenerator:
    """Main generator class for configurable arithmetic dialect testing."""

    def __init__(self, config_path: str):
        """Initialize generator with configuration file."""
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.base_dir = Path.cwd()

        # Setup directories
        self.mlir_dir = self.base_dir / self.config["generation_settings"]["mlir_artifacts_dir"]
        self.trace_dir = self.base_dir / self.config["generation_settings"]["output_dir"]
        self.manifest_dir = self.base_dir / self.config["generation_settings"]["manifest_dir"]

        # Create directories
        self.mlir_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

        # Compute relative paths for manifest
        try:
            mlir_artifacts_dir_rel = str(self.mlir_dir.relative_to(self.base_dir))
        except ValueError:
            mlir_artifacts_dir_rel = str(self.mlir_dir)
        try:
            dap_traces_dir_rel = str(self.trace_dir.relative_to(self.base_dir))
        except ValueError:
            dap_traces_dir_rel = str(self.trace_dir)

        # Initialize manifest
        self.manifest = {
            "test_suite": "arith_comprehensive",
            "version": self.config.get("version", "1.0"),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "config_file": str(self.config_path),
            "mlir_artifacts_dir": mlir_artifacts_dir_rel,
            "dap_traces_dir": dap_traces_dir_rel,
            "tests": [],
        }

        # Statistics
        self.stats = {
            "total_operations": 0,
            "enabled_operations": 0,
            "mlir_files_generated": 0,
            "traces_generated": 0,
            "validation_passed": 0,
            "validation_failed": 0,
        }

    def load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            # Validate required fields
            required_fields = ["dialect", "operations", "generation_settings"]
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field in config: {field}")

            if config["dialect"] != "arith":
                raise ValueError(f"Expected dialect 'arith', got '{config['dialect']}'")

            return config
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)

    def generate_mlir_artifacts(self) -> None:
        """Generate individual MLIR files for each enabled operation."""
        print("Generating MLIR artifacts...")

        print(f"Total operations in config: {len(self.config['operations'])}")
        for i, op_config in enumerate(self.config["operations"]):
            enabled = op_config.get("enabled", False)
            print(f"Operation {i}: {op_config['name']} enabled={enabled}")
            if not enabled:
                continue

            op_name = op_config["name"]
            op_dir = self.mlir_dir / op_name
            op_dir.mkdir(parents=True, exist_ok=True)

            self.stats["enabled_operations"] += 1

            # Generate MLIR files based on operation type
            if op_name == "constant":
                self._generate_constant_mlir(op_config, op_dir)
            elif op_name in ["cmpi", "cmpf"]:
                self._generate_comparison_mlir(op_config, op_dir)
            elif op_name in [
                "extsi",
                "extui",
                "trunci",
                "sitofp",
                "uitofp",
                "fptosi",
                "fptoui",
            ]:
                self._generate_conversion_mlir(op_config, op_dir)
            elif op_name == "select":
                self._generate_select_mlir(op_config, op_dir)
            elif op_name == "index_cast":
                self._generate_index_cast_mlir(op_config, op_dir)
            elif op_name == "bitcast":
                self._generate_bitcast_mlir(op_config, op_dir)
            else:
                self._generate_basic_arith_mlir(op_config, op_dir)

        print(
            f"Generated {self.stats['mlir_files_generated']} MLIR files for {self.stats['enabled_operations']} operations"
        )

    def _generate_basic_arith_mlir(self, op_config: Dict[str, Any], op_dir: Path) -> None:
        """Generate MLIR for basic arithmetic operations."""
        op_name = op_config["name"]
        bitwidths = op_config.get("bitwidths", [32])

        for bitwidth in bitwidths:
            # Generate simple test case
            mlir_content = f"""// Test for {op_name} operation with i{bitwidth}
module {{
  func.func @test_{op_name}_i{bitwidth}(%a: i{bitwidth}, %b: i{bitwidth}) -> i{bitwidth} {{
    %result = arith.{op_name} %a, %b : i{bitwidth}
    return %result : i{bitwidth}
  }}
}}
"""

            filename = op_dir / f"{op_name}_basic_i{bitwidth}.mlir"
            self._write_mlir_file(filename, mlir_content)

            # Generate with constant if applicable
            if op_name in ["addi", "subi", "muli"]:
                mlir_const = f"""// Test for {op_name} with constant
module {{
  func.func @test_{op_name}_const_i{bitwidth}(%a: i{bitwidth}) -> i{bitwidth} {{
    %c5 = arith.constant 5 : i{bitwidth}
    %result = arith.{op_name} %a, %c5 : i{bitwidth}
    return %result : i{bitwidth}
  }}
}}
"""
                filename_const = op_dir / f"{op_name}_const_i{bitwidth}.mlir"
                self._write_mlir_file(filename_const, mlir_const)

    def _generate_constant_mlir(self, op_config: Dict[str, Any], op_dir: Path) -> None:
        """Generate MLIR for constant operations."""
        value_ranges = op_config.get("value_ranges", {})
        special_values = op_config.get("special_values", [])

        # Generate constants for different types
        type_values = {
            "i1": [0, 1],
            "i8": [-128, 0, 127],
            "i16": [-32768, 0, 32767],
            "i32": [-2147483648, 0, 2147483647],
            "i64": [-9223372036854775808, 0, 9223372036854775807],
            "f32": [-3.14, 0.0, 3.14],
            "f64": [-3.141592653589793, 0.0, 3.141592653589793],
        }

        for type_name, values in type_values.items():
            for i, value in enumerate(values):
                mlir_content = f"""// Constant {type_name} test
module {{
  func.func @test_constant_{type_name}_{i}() -> {type_name} {{
    %c = arith.constant {value} : {type_name}
    return %c : {type_name}
  }}
}}
"""
                filename = op_dir / f"constant_{type_name}_{i}.mlir"
                self._write_mlir_file(filename, mlir_content)

    def _generate_comparison_mlir(self, op_config: Dict[str, Any], op_dir: Path) -> None:
        """Generate MLIR for comparison operations."""
        op_name = op_config["name"]
        bitwidths = op_config.get("bitwidths", [32])
        predicates = op_config.get("predicates", ["eq", "ne"])

        for bitwidth in bitwidths:
            type_name = "i" + str(bitwidth) if op_name == "cmpi" else "f" + str(bitwidth)

            for predicate in predicates:
                mlir_content = f"""// Test for {op_name} with predicate {predicate}
module {{
  func.func @test_{op_name}_{predicate}_{type_name}(%a: {type_name}, %b: {type_name}) -> i1 {{
    %result = arith.{op_name} {predicate}, %a, %b : {type_name}
    return %result : i1
  }}
}}
"""
                filename = op_dir / f"{op_name}_{predicate}_{type_name}.mlir"
                self._write_mlir_file(filename, mlir_content)

    def _generate_conversion_mlir(self, op_config: Dict[str, Any], op_dir: Path) -> None:
        """Generate MLIR for conversion operations."""
        op_name = op_config["name"]
        source_bitwidths = op_config.get("source_bitwidths", [32])
        target_bitwidths = op_config.get("target_bitwidths", [64])

        for src_bw in source_bitwidths:
            for tgt_bw in target_bitwidths:
                if src_bw >= tgt_bw and op_name in ["extsi", "extui"]:
                    continue  # Can't extend to smaller type
                if src_bw <= tgt_bw and op_name == "trunci":
                    continue  # Can't truncate to larger type

                src_type = "i" + str(src_bw) if "i" in op_name else "f" + str(src_bw)
                tgt_type = "i" + str(tgt_bw) if "i" in op_name else "f" + str(tgt_bw)

                mlir_content = f"""// Test for {op_name} conversion
module {{
  func.func @test_{op_name}_{src_type}_to_{tgt_type}(%a: {src_type}) -> {tgt_type} {{
    %result = arith.{op_name} %a : {src_type} to {tgt_type}
    return %result : {tgt_type}
  }}
}}
"""
                filename = op_dir / f"{op_name}_{src_type}_to_{tgt_type}.mlir"
                self._write_mlir_file(filename, mlir_content)

    def _generate_select_mlir(self, op_config: Dict[str, Any], op_dir: Path) -> None:
        """Generate MLIR for select operation."""
        bitwidths = op_config.get("bitwidths", [32])

        for bitwidth in bitwidths:
            mlir_content = f"""// Test for select operation
module {{
  func.func @test_select_i{bitwidth}(%cond: i1, %true_val: i{bitwidth}, %false_val: i{bitwidth}) -> i{bitwidth} {{
    %result = arith.select %cond, %true_val, %false_val : i{bitwidth}
    return %result : i{bitwidth}
  }}
}}
"""
            filename = op_dir / f"select_i{bitwidth}.mlir"
            self._write_mlir_file(filename, mlir_content)

    def _generate_index_cast_mlir(self, op_config: Dict[str, Any], op_dir: Path) -> None:
        """Generate MLIR for index_cast operation."""
        directions = op_config.get("directions", ["index_to_int", "int_to_index"])
        int_bitwidths = op_config.get("int_bitwidths", [64])

        for direction in directions:
            for bitwidth in int_bitwidths:
                if direction == "index_to_int":
                    mlir_content = f"""// Test for index_cast from index to i{bitwidth}
module {{
  func.func @test_index_cast_to_i{bitwidth}(%idx: index) -> i{bitwidth} {{
    %result = arith.index_cast %idx : index to i{bitwidth}
    return %result : i{bitwidth}
  }}
}}
"""
                else:  # int_to_index
                    mlir_content = f"""// Test for index_cast from i{bitwidth} to index
module {{
  func.func @test_index_cast_from_i{bitwidth}(%val: i{bitwidth}) -> index {{
    %result = arith.index_cast %val : i{bitwidth} to index
    return %result : index
  }}
}}
"""
                filename = op_dir / f"index_cast_{direction}_{bitwidth}.mlir"
                self._write_mlir_file(filename, mlir_content)

    def _generate_bitcast_mlir(self, op_config: Dict[str, Any], op_dir: Path) -> None:
        """Generate MLIR for bitcast operation."""
        type_pairs = op_config.get("type_pairs", [["i32", "f32"]])

        for src_type, tgt_type in type_pairs:
            mlir_content = f"""// Test for bitcast from {src_type} to {tgt_type}
module {{
  func.func @test_bitcast_{src_type}_to_{tgt_type}(%a: {src_type}) -> {tgt_type} {{
    %result = arith.bitcast %a : {src_type} to {tgt_type}
    return %result : {tgt_type}
  }}
}}
"""
            filename = op_dir / f"bitcast_{src_type}_to_{tgt_type}.mlir"
            self._write_mlir_file(filename, mlir_content)

    def _write_mlir_file(self, filename: Path, content: str) -> None:
        """Write MLIR file and update statistics."""
        try:
            print(f"Writing MLIR file: {filename}")
            with open(filename, "w") as f:
                f.write(content)
            self.stats["mlir_files_generated"] += 1

            # Validate with MLIR LSP if enabled
            if self.config["generation_settings"].get("validate_mlir", True):
                self._validate_mlir_file(filename)

        except Exception as e:
            print(f"Error writing MLIR file {filename}: {e}")

    def _validate_mlir_file(self, filename: Path) -> bool:
        """Validate MLIR file using MLIR LSP server."""
        try:
            # Use the existing validation script
            validate_script = (
                self.base_dir / "scripts" / "mlir_validation" / "validate_mlir_precommit.py"
            )
            if validate_script.exists():
                result = subprocess.run(
                    [sys.executable, str(validate_script), str(filename)],
                    capture_output=True,
                    text=True,
                    timeout=self.config["generation_settings"].get("validation_timeout_ms", 10000)
                    / 1000,
                )
                if result.returncode == 0:
                    return True
                else:
                    print(f"MLIR validation failed for {filename}: {result.stderr}")
                    return False
            else:
                print(f"Warning: MLIR validation script not found at {validate_script}")
                return True  # Skip validation if script not found
        except subprocess.TimeoutExpired:
            print(f"MLIR validation timeout for {filename}")
            return False
        except Exception as e:
            print(f"Error during MLIR validation for {filename}: {e}")
            return False

    def generate_dap_traces(self) -> None:
        """Generate DAP traces for MLIR files."""
        print("Generating DAP traces...")

        # Walk through MLIR directory
        for mlir_file in self.mlir_dir.rglob("*.mlir"):
            if mlir_file.is_file():
                self._generate_trace_for_mlir(mlir_file)

        print(f"Generated {self.stats['traces_generated']} DAP traces")

    def _generate_trace_for_mlir(self, mlir_file: Path) -> None:
        """Generate DAP trace for a single MLIR file."""
        try:
            if PathAwareGenerator is None:
                print(
                    f"Warning: PathAwareGenerator not available, skipping trace generation for {mlir_file}"
                )
                return
            test_cases = []
            # Use existing PathAwareGenerator
            with PathAwareGenerator() as generator:
                # Generate test cases
                max_paths = self.config["generation_settings"].get("max_paths_per_op", 20)
                test_cases = generator.generate_from_program(
                    program_path=str(mlir_file),
                    max_paths=max_paths,
                    test_name=mlir_file.stem,
                )

            if not test_cases:
                print(f"No test cases generated for {mlir_file}")
                return

            # Create trace file
            relative_path = mlir_file.relative_to(self.mlir_dir)
            trace_filename = self.trace_dir / relative_path.with_suffix(".json")
            trace_filename.parent.mkdir(parents=True, exist_ok=True)

            # Convert test cases to DAP trace format
            trace_data = {
                "mlir_file": str(mlir_file.relative_to(self.base_dir)),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "test_cases": test_cases,
                "metadata": {
                    "operation": self._extract_operation_from_mlir(mlir_file),
                    "validated": False,
                    "z3_generated": True,
                },
            }

            # Write trace file
            with open(trace_filename, "w") as f:
                json.dump(trace_data, f, indent=2)

            self.stats["traces_generated"] += 1

            # Add to manifest
            self.manifest["tests"].append(
                {
                    "id": f"{relative_path.stem}",
                    "mlir_file": str(mlir_file.relative_to(self.base_dir)),
                    "dap_trace": str(trace_filename.relative_to(self.base_dir)),
                    "operation": trace_data["metadata"]["operation"],
                    "description": f"Test for {trace_data['metadata']['operation']}",
                    "validated": False,
                    "validation_timestamp": None,
                }
            )

            # Validate trace if enabled
            if self.config["generation_settings"].get("validate_traces", True):
                if self._validate_dap_trace(trace_filename, mlir_file):
                    self.stats["validation_passed"] += 1
                    # Update manifest
                    for test in self.manifest["tests"]:
                        if test["id"] == relative_path.stem:
                            test["validated"] = True
                            test["validation_timestamp"] = datetime.utcnow().isoformat() + "Z"
                            break
                else:
                    self.stats["validation_failed"] += 1

        except Exception as e:
            print(f"Error generating trace for {mlir_file}: {e}")

    def _extract_operation_from_mlir(self, mlir_file: Path) -> str:
        """Extract operation name from MLIR file content."""
        try:
            with open(mlir_file, "r") as f:
                content = f.read()

            # Look for arith. operations
            import re

            match = re.search(r"arith\.(\w+)", content)
            if match:
                return f"arith.{match.group(1)}"

            return "unknown"
        except:
            return "unknown"

    def _validate_dap_trace(self, trace_file: Path, mlir_file: Path) -> bool:
        """Validate DAP trace by actually running with DAP client."""
        try:
            # Load trace
            with open(trace_file, "r") as f:
                trace_data = json.load(f)

            test_cases = trace_data["test_cases"]
            if not test_cases:
                print(f"No test cases in trace: {trace_file}")
                return True  # empty trace considered valid

            # Use TestRunner to execute the trace
            if TestRunner is None:
                print(f"Warning: TestRunner not available, skipping validation for {trace_file}")
                return True  # skip validation
            with TestRunner() as runner:
                results = []
                for i, test_script in enumerate(test_cases):
                    try:
                        # Run single test script
                        result = runner.run_test_script(test_script, script_path=str(mlir_file))
                        # Convert success to passed for compatibility
                        result["passed"] = result.get("success", False)
                        results.append(result)
                    except Exception as e:
                        print(f"Error running test case {i} in {trace_file}: {e}")
                        results.append({"passed": False, "error": str(e)})

                # Check if all tests passed
                all_passed = all(r.get("passed", False) for r in results)

                if all_passed:
                    print(f"Trace validation passed: {trace_file}")
                else:
                    print(f"Trace validation failed: {trace_file}")
                    for i, result in enumerate(results):
                        if not result.get("passed", False):
                            print(f"  Test case {i}: {result.get('error', 'Unknown error')}")

                return all_passed

        except Exception as e:
            print(f"Error validating DAP trace {trace_file}: {e}")
            return False

    def save_manifest(self) -> None:
        """Save test suite manifest."""
        # Ensure manifest directory exists
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest_file = self.manifest_dir / "arith_test_manifest.json"

        # Add statistics to manifest
        self.manifest["statistics"] = self.stats
        self.manifest["generation_settings"] = self.config["generation_settings"]

        try:
            with open(manifest_file, "w") as f:
                json.dump(self.manifest, f, indent=2)
            print(f"Manifest saved: {manifest_file}")
        except Exception as e:
            print(f"Error saving manifest: {e}")

    def generate_documentation(self) -> None:
        """Generate documentation for the test suite."""
        if not self.config["documentation"].get("generate_coverage_report", True):
            return

        print("Generating documentation...")

        # Generate coverage report
        coverage_file = self.base_dir / self.config["documentation"]["coverage_report_path"]
        coverage_file.parent.mkdir(parents=True, exist_ok=True)

        coverage_content = self._generate_coverage_report()
        with open(coverage_file, "w") as f:
            f.write(coverage_content)

        print(f"Coverage report saved: {coverage_file}")

        # Generate artifact guide
        if self.config["documentation"].get("generate_artifact_guide", True):
            guide_file = self.base_dir / self.config["documentation"]["artifact_guide_path"]
            guide_file.parent.mkdir(parents=True, exist_ok=True)

            guide_content = self._generate_artifact_guide()
            with open(guide_file, "w") as f:
                f.write(guide_content)

            print(f"Artifact guide saved: {guide_file}")

    def _generate_coverage_report(self) -> str:
        """Generate test coverage report."""
        enabled_ops = [op["name"] for op in self.config["operations"] if op.get("enabled", False)]
        disabled_ops = [
            op["name"] for op in self.config["operations"] if not op.get("enabled", False)
        ]

        # Compute relative paths for display
        try:
            mlir_dir_rel = str(self.mlir_dir.relative_to(self.base_dir))
        except ValueError:
            mlir_dir_rel = str(self.mlir_dir)
        try:
            trace_dir_rel = str(self.trace_dir.relative_to(self.base_dir))
        except ValueError:
            trace_dir_rel = str(self.trace_dir)
        try:
            manifest_dir_rel = str(self.manifest_dir.relative_to(self.base_dir))
        except ValueError:
            manifest_dir_rel = str(self.manifest_dir)

        report = f"""# Arithmetic Dialect Test Coverage Report

## Overview
- **Generated**: {datetime.utcnow().isoformat() + "Z"}
- **Configuration**: {self.config_path.name}
- **Total Operations**: {len(self.config["operations"])}
- **Enabled Operations**: {len(enabled_ops)}
- **Disabled Operations**: {len(disabled_ops)}
- **Coverage Percentage**: {(len(enabled_ops) / len(self.config["operations"]) * 100):.1f}%

## Statistics
- MLIR Files Generated: {self.stats["mlir_files_generated"]}
- DAP Traces Generated: {self.stats["traces_generated"]}
- Validation Passed: {self.stats["validation_passed"]}
- Validation Failed: {self.stats["validation_failed"]}

## Enabled Operations
"""

        for op_name in enabled_ops:
            op_tests = [t for t in self.manifest["tests"] if t["operation"] == f"arith.{op_name}"]
            report += f"- **{op_name}**: {len(op_tests)} test(s)\n"

        report += "\n## Disabled Operations\n"
        for op_name in disabled_ops:
            report += f"- {op_name}\n"

        report += f"""
## Test Artifacts
- **MLIR Artifacts Directory**: {mlir_dir_rel}
- **DAP Traces Directory**: {trace_dir_rel}
- **Manifest File**: {manifest_dir_rel}/arith_test_manifest.json

## Validation Results
- **Total Validated**: {self.stats["validation_passed"] + self.stats["validation_failed"]}
- **Pass Rate**: {((self.stats["validation_passed"] / (self.stats["validation_passed"] + self.stats["validation_failed"])) * 100 if (self.stats["validation_passed"] + self.stats["validation_failed"]) > 0 else 0):.1f}%

## Configuration Details
```yaml
{self._get_config_summary()}
```

## Next Steps
1. Review generated test artifacts
2. Run comprehensive test suite with DAP client
3. Extend coverage to other dialects
4. Update configuration as needed
"""

        return report

    def _generate_artifact_guide(self) -> str:
        """Generate guide for using test artifacts."""
        guide = """# Test Artifact Usage Guide

## Overview
This guide explains how to use the generated MLIR artifacts and DAP traces for testing arithmetic dialect operations.

## File Structure
The generated test suite follows this structure:
- target/trace_testing/arith_ops_config.yaml - Configuration file
- target/trace_testing/test_artifacts/mlir/arith/ - Individual MLIR files organized by operation
- target/trace_testing/generated_tests/arith_comprehensive/ - DAP trace files
- target/trace_testing/manifest/arith_test_manifest.json - Test suite manifest
- target/trace_testing/docs/ - Documentation files

## Using MLIR Artifacts

### Individual Validation
```bash
# Validate a single MLIR file
python scripts/mlir_validation/validate_mlir_precommit.py target/trace_testing/test_artifacts/mlir/arith/addi/addi_basic_i32.mlir

# Validate all MLIR files
find target/trace_testing/test_artifacts/mlir/arith -name "*.mlir" -exec python scripts/mlir_validation/validate_mlir_precommit.py {} \\;
```

### Manual Testing
```python
from mlir.ir import Context, Module
import mlir.dialects.arith as arith

# Load and parse MLIR file
with open("target/trace_testing/test_artifacts/mlir/arith/addi/addi_basic_i32.mlir", "r") as f:
    mlir_code = f.read()

with Context() as ctx:
    # Register dialects
    arith.register_dialect(ctx)
    
    # Parse module
    module = Module.parse(mlir_code, ctx)
    
    # Use the module for testing
```

## Using DAP Traces

### Running Individual Traces
```python
from dap_client.runner.test_runner import TestRunner
import json

# Load trace
with open("target/trace_testing/generated_tests/arith_comprehensive/addi/addi_basic_i32.json", "r") as f:
    trace_data = json.load(f)

# Create runner and execute
runner = TestRunner()
results = runner.run_tests(trace_data['test_cases'], "target/trace_testing/test_artifacts/mlir/arith/addi/addi_basic_i32.mlir")

# Check results
for i, result in enumerate(results):
    status = "PASS" if result['passed'] else "FAIL"
    print(f"Test case {i}: {status}")
```

### Batch Execution
```bash
# Run all traces (using existing script if available)
python scripts/run_arith_workflow_tests.py --traces-dir target/trace_testing/generated_tests/arith_comprehensive
```

## Using the Manifest

### Querying Test Suite
```python
import json

# Load manifest
with open("target/trace_testing/manifest/arith_test_manifest.json", "r") as f:
    manifest_data = json.load(f)

# Get all tests for a specific operation
addi_tests = [t for t in manifest_data['tests'] if t['operation'] == 'arith.addi']

# Get validated tests
validated_tests = [t for t in manifest_data['tests'] if t['validated']]

print(f"Total tests: {len(manifest_data['tests'])}")
print(f"Validated tests: {len(validated_tests)}")
```

### Coverage Analysis
```python
# Analyze operation coverage
operations = set(t['operation'] for t in manifest_data['tests'])
print(f"Operations covered: {len(operations)}")
```

## Regenerating Tests

### Full Regeneration
```bash
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml
```

### MLIR Only
```bash
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --mlir-only
```

### Traces Only
```bash
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --traces-only
```

## Custom Configuration

### Modifying Configuration
Edit `target/trace_testing/arith_ops_config.yaml` to:
1. Enable/disable operations
2. Adjust bitwidths
3. Modify constraints
4. Change generation settings

### Adding New Operations
1. Add operation definition to configuration
2. Ensure MLIR generation method exists
3. Regenerate tests

## Troubleshooting

### Common Issues
1. **MLIR validation fails**: Check MLIR syntax, ensure proper dialect registration
2. **DAP trace execution fails**: Verify DAP client setup, check test case format
3. **Missing operations**: Ensure operation is enabled in configuration

### Debugging
```bash
# Verbose output
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --verbose

# Dry run (no file generation)
python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml --dry-run
```

## Integration with CI
Add to your CI pipeline:
```yaml
- name: Generate and Test Arithmetic Operations
  run: |
    python scripts/dap_trace_generation/configurable_arith_generator.py --config target/trace_testing/arith_ops_config.yaml
    python scripts/validate_test_suite.py --manifest target/trace_testing/manifest/arith_test_manifest.json
```

## Extending to Other Dialects
The same pattern can be applied to other MLIR dialects:
1. Create dialect documentation
2. Define configuration format
3. Implement generator script
4. Generate test artifacts

## Support
For issues or questions:
1. Check the manifest for validation status
2. Review generated documentation
3. Consult MLIR and DAP client documentation
"""

        return guide

    def _get_config_summary(self) -> str:
        """Get summary of configuration for documentation."""
        summary = {
            "dialect": self.config["dialect"],
            "version": self.config.get("version", "1.0"),
            "operations_count": len(self.config["operations"]),
            "enabled_operations_count": sum(
                1 for op in self.config["operations"] if op.get("enabled", False)
            ),
            "generation_settings": self.config["generation_settings"],
        }

        import yaml

        return yaml.dump(summary, default_flow_style=False)

    def print_statistics(self) -> None:
        """Print generation statistics."""
        print("\n" + "=" * 60)
        print("GENERATION STATISTICS")
        print("=" * 60)
        print(f"Configuration file: {self.config_path}")
        print(f"Total operations in config: {len(self.config['operations'])}")
        print(f"Enabled operations: {self.stats['enabled_operations']}")
        print(f"MLIR files generated: {self.stats['mlir_files_generated']}")
        print(f"DAP traces generated: {self.stats['traces_generated']}")
        print(f"Validation passed: {self.stats['validation_passed']}")
        print(f"Validation failed: {self.stats['validation_failed']}")

        if self.stats["validation_passed"] + self.stats["validation_failed"] > 0:
            pass_rate = (
                self.stats["validation_passed"]
                / (self.stats["validation_passed"] + self.stats["validation_failed"])
            ) * 100
            print(f"Validation pass rate: {pass_rate:.1f}%")

        print(f"Manifest file: {self.manifest_dir / 'arith_test_manifest.json'}")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Configurable Arithmetic Dialect DAP Trace Generator"
    )
    parser.add_argument("--config", required=True, help="Path to configuration YAML file")
    parser.add_argument(
        "--mlir-only",
        action="store_true",
        help="Generate only MLIR artifacts (no DAP traces)",
    )
    parser.add_argument(
        "--traces-only",
        action="store_true",
        help="Generate only DAP traces (assumes MLIR artifacts exist)",
    )
    parser.add_argument("--mlir-dir", help="Custom MLIR artifacts directory (overrides config)")
    parser.add_argument("--trace-dir", help="Custom DAP traces directory (overrides config)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no file generation)")

    args = parser.parse_args()

    # Initialize generator
    generator = ConfigurableArithGenerator(args.config)

    # Override directories if specified
    if args.mlir_dir:
        generator.mlir_dir = Path(args.mlir_dir)
    if args.trace_dir:
        generator.trace_dir = Path(args.trace_dir)

    if args.dry_run:
        print("Dry run mode - no files will be generated")
        generator.print_statistics()
        return

    # Generate based on options
    if not args.traces_only:
        generator.generate_mlir_artifacts()

    if not args.mlir_only:
        generator.generate_dap_traces()

    # Save manifest and generate documentation
    generator.save_manifest()
    generator.generate_documentation()

    # Print statistics
    generator.print_statistics()


if __name__ == "__main__":
    main()
