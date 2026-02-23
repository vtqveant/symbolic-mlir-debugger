#!/usr/bin/env python3
"""
Test script for DAP Trace Library.

Comprehensive testing of all library modules to ensure they work correctly.
"""

import sys
import tempfile
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dap_trace_library.utils.logging_utils import LoggingUtils
from dap_trace_library.utils.file_utils import FileUtils
from dap_trace_library.utils.config_utils import ConfigUtils
from dap_trace_library.config.dialect_config import (
    GeneratorConfig,
    DialectConfig,
    OperationConfig,
    DialectType,
    OperationCategory,
)
from dap_trace_library.generation.configurable_generator import ConfigurableGenerator
from dap_trace_library.validation.mlir_validator import MLIRValidator
from dap_trace_library.validation.trace_validator import TraceValidator

logger = LoggingUtils.setup_module_logging(__name__)


class LibraryTester:
    """Test DAP Trace Library functionality."""

    def __init__(self):
        """Initialize tester."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="dap_library_test_"))
        logger.info(f"Test directory: {self.test_dir}")

        # Setup logging
        log_dir = self.test_dir / "logs"
        LoggingUtils.setup_logging(level=logging.DEBUG, log_file=log_dir / "test.log", console=True)

    def test_configuration(self) -> bool:
        """Test configuration system."""
        print("=== Testing Configuration System ===")

        try:
            # Create example configuration
            config = GeneratorConfig.create_arith_example()

            # Save to file
            config_path = self.test_dir / "test_config.yaml"
            config.save_yaml(config_path)
            print(f"✅ Created example config: {config_path}")

            # Load from file
            loaded_config = GeneratorConfig.load_yaml(config_path)
            print(f"✅ Loaded config from file")

            # Validate
            validation = ConfigUtils.validate_config(loaded_config.to_dict())
            if validation["valid"]:
                print(f"✅ Configuration validation passed")
            else:
                print(f"❌ Configuration validation failed: {validation['errors']}")
                return False

            # Test configuration utilities
            config_dict = loaded_config.to_dict()
            summary = ConfigUtils.generate_config_summary(config_dict)
            print(
                f"✅ Config summary: {summary['enabled_dialects']} dialects, {summary['enabled_operations']} operations"
            )

            return True

        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_generation(self) -> bool:
        """Test generation system."""
        print("\n=== Testing Generation System ===")

        try:
            # Create minimal config for testing
            config = GeneratorConfig.create_arith_example()

            # Limit to 2 operations for quick test
            for dialect in config.dialects:
                if dialect.name == "arith":
                    for i, op in enumerate(dialect.operations):
                        op.enabled = i < 2  # Enable only first 2 operations

            # Update output directory
            config.output_settings["base_dir"] = str(self.test_dir / "generation_test")

            # Create generator
            generator = ConfigurableGenerator(config)
            print(
                f"✅ Created generator with {len(config.get_enabled_operations())} enabled operations"
            )

            # Generate
            result = generator.generate_all()
            stats = result["statistics"]

            print(f"✅ Generation complete:")
            print(f"   MLIR files: {stats['mlir_files_generated']}")
            print(f"   DAP traces: {stats['traces_generated']}")
            print(f"   Duration: {stats['duration_seconds']:.2f}s")

            # Check files were created
            mlir_dir = (
                Path(config.output_settings["base_dir"])
                / config.output_settings["mlir_artifacts_dir"]
            )
            trace_dir = (
                Path(config.output_settings["base_dir"]) / config.output_settings["dap_traces_dir"]
            )

            mlir_files = list(mlir_dir.glob("*.mlir"))
            trace_files = list(trace_dir.glob("*.json"))

            if len(mlir_files) == stats["mlir_files_generated"]:
                print(f"✅ MLIR files created: {len(mlir_files)}")
            else:
                print(
                    f"❌ MLIR file count mismatch: expected {stats['mlir_files_generated']}, found {len(mlir_files)}"
                )
                return False

            if len(trace_files) == stats["traces_generated"]:
                print(f"✅ DAP trace files created: {len(trace_files)}")
            else:
                print(
                    f"❌ DAP trace file count mismatch: expected {stats['traces_generated']}, found {len(trace_files)}"
                )
                return False

            return True

        except Exception as e:
            print(f"❌ Generation test failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_validation(self) -> bool:
        """Test validation system."""
        print("\n=== Testing Validation System ===")

        try:
            # First generate some test files
            config = GeneratorConfig.create_arith_example()
            for dialect in config.dialects:
                if dialect.name == "arith":
                    for i, op in enumerate(dialect.operations):
                        op.enabled = i < 1  # Enable only 1 operation

            config.output_settings["base_dir"] = str(self.test_dir / "validation_test")

            generator = ConfigurableGenerator(config)
            result = generator.generate_all()

            # Test MLIR validation
            mlir_dir = (
                Path(config.output_settings["base_dir"])
                / config.output_settings["mlir_artifacts_dir"]
            )
            mlir_validator = MLIRValidator()

            mlir_result = mlir_validator.validate_directory(mlir_dir, recursive=False)
            print(
                f"✅ MLIR validation: {mlir_result['files_valid']}/{mlir_result['files_validated']} files valid"
            )

            # Test trace validation
            trace_dir = (
                Path(config.output_settings["base_dir"]) / config.output_settings["dap_traces_dir"]
            )
            trace_validator = TraceValidator()

            trace_result = trace_validator.validate_directory(trace_dir, recursive=False)
            print(
                f"✅ DAP trace validation: {trace_result['files_valid']}/{trace_result['files_validated']} files valid"
            )

            # Test individual file validation
            if trace_files := list(trace_dir.glob("*.json")):
                single_result = trace_validator.validate_file(trace_files[0])
                print(
                    f"✅ Single file validation: {'VALID' if single_result['valid'] else 'INVALID'}"
                )

            return mlir_result["valid"] and trace_result["valid"]

        except Exception as e:
            print(f"❌ Validation test failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_utilities(self) -> bool:
        """Test utility modules."""
        print("\n=== Testing Utility Modules ===")

        try:
            # Test file utilities
            test_file = self.test_dir / "test_file.txt"
            test_file.write_text("Test content")

            size = FileUtils.get_file_size(test_file)
            print(f"✅ File size utility: {size} bytes")

            # Test directory creation
            test_dir = self.test_dir / "test_subdir"
            FileUtils.ensure_directory(test_dir)
            print(f"✅ Directory creation: {test_dir.exists()}")

            # Test JSON utilities
            test_data = {"test": "data", "number": 42}
            json_file = self.test_dir / "test.json"
            FileUtils.write_json(test_data, json_file)

            loaded_data = FileUtils.read_json(json_file)
            print(f"✅ JSON utilities: {loaded_data == test_data}")

            # Test config utilities
            config = ConfigUtils.create_example_config("arith")
            config_path = self.test_dir / "test_config_utils.yaml"
            ConfigUtils.save_config(config, config_path)

            loaded_config = ConfigUtils.load_config(config_path)
            print(f"✅ Config utilities: {'version' in loaded_config}")

            # Test config validation
            validation = ConfigUtils.validate_config(loaded_config)
            print(f"✅ Config validation: {validation['valid']}")

            return True

        except Exception as e:
            print(f"❌ Utilities test failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_integration(self) -> bool:
        """Test integrated workflow."""
        print("\n=== Testing Integrated Workflow ===")

        try:
            # Create comprehensive test
            config = GeneratorConfig.create_arith_example()

            # Customize for integration test
            config.output_settings["base_dir"] = str(self.test_dir / "integration_test")
            config.generation_settings["use_z3"] = True
            config.generation_settings["max_solutions_per_constraint"] = 2

            # Enable only a few operations
            for dialect in config.dialects:
                if dialect.name == "arith":
                    for i, op in enumerate(dialect.operations):
                        op.enabled = i < 3  # Enable first 3 operations

            print(f"Integration test setup:")
            print(f"  Output directory: {config.output_settings['base_dir']}")
            print(f"  Enabled operations: {len(config.get_enabled_operations())}")
            print(f"  Use Z3: {config.generation_settings['use_z3']}")

            # Run full workflow
            generator = ConfigurableGenerator(config)
            generation_result = generator.generate_all()

            print(f"✅ Generation completed:")
            print(f"   MLIR files: {generation_result['statistics']['mlir_files_generated']}")
            print(f"   DAP traces: {generation_result['statistics']['traces_generated']}")

            # Validate generated files
            mlir_dir = (
                Path(config.output_settings["base_dir"])
                / config.output_settings["mlir_artifacts_dir"]
            )
            trace_dir = (
                Path(config.output_settings["base_dir"]) / config.output_settings["dap_traces_dir"]
            )

            mlir_validator = MLIRValidator()
            trace_validator = TraceValidator()

            mlir_validation = mlir_validator.validate_directory(mlir_dir)
            trace_validation = trace_validator.validate_directory(trace_dir)

            print(f"✅ Validation results:")
            print(
                f"   MLIR: {mlir_validation['files_valid']}/{mlir_validation['files_validated']} valid"
            )
            print(
                f"   Traces: {trace_validation['files_valid']}/{trace_validation['files_validated']} valid"
            )

            # Check manifest was created
            manifest_dir = (
                Path(config.output_settings["base_dir"]) / config.output_settings["manifest_dir"]
            )
            manifest_files = list(manifest_dir.glob("*.json"))

            if manifest_files:
                print(f"✅ Manifest created: {len(manifest_files)} file(s)")

                # Load and check manifest
                manifest = FileUtils.read_json(manifest_files[0])
                if "tests" in manifest and "dialects" in manifest:
                    print(
                        f"✅ Manifest structure correct: {len(manifest['tests'])} tests, {len(manifest['dialects'])} dialects"
                    )
                else:
                    print(f"❌ Manifest structure incorrect")
                    return False
            else:
                print(f"❌ No manifest created")
                return False

            return (
                mlir_validation["valid"]
                and trace_validation["valid"]
                and generation_result["statistics"]["mlir_files_generated"] > 0
            )

        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def run_all_tests(self) -> bool:
        """Run all tests."""
        print("=" * 60)
        print("DAP Trace Library - Comprehensive Test Suite")
        print("=" * 60)

        results = []

        # Run tests
        results.append(("Configuration", self.test_configuration()))
        results.append(("Generation", self.test_generation()))
        results.append(("Validation", self.test_validation()))
        results.append(("Utilities", self.test_utilities()))
        results.append(("Integration", self.test_integration()))

        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary:")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:20} {status}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
            print(f"Test directory: {self.test_dir}")
            print("You can examine the generated files to verify functionality.")
        else:
            print("⚠️  SOME TESTS FAILED")
            print(f"Check test directory for details: {self.test_dir}")

        print("=" * 60)

        return all_passed


def main():
    """Run library tests."""
    tester = LibraryTester()

    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
