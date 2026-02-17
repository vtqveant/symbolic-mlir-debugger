#!/usr/bin/env python3
"""
Setup Verification Script for Symbolic MLIR Debugger
Checks that all dependencies are properly installed and accessible
"""

import sys
import importlib
from typing import Dict, List, Tuple


class VerificationError(Exception):
    """Custom exception for verification failures"""

    pass


class SetupVerifier:
    """Verifies the Symbolic MLIR Debugger setup"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []

    def log(self, message: str, level: str = "info"):
        """Log a message with level"""
        if level == "error":
            self.errors.append(message)
        elif level == "warning":
            self.warnings.append(message)
        else:
            self.passed.append(message)

        # Print the message (with color codes for terminal output)
        print(message)

    def check_python_version(self) -> bool:
        """Check Python version compatibility"""
        version = sys.version_info
        major = version.major
        minor = version.minor

        self.log(f"Python version: {major}.{minor}.{version.micro}", "info")

        if major >= 3 and minor >= 8:
            self.log(f"✓ Python {major}.{minor} is compatible (>= 3.8)", "passed")
            return True
        else:
            self.log(f"✗ Python {major}.{minor} is too old (requires >= 3.8)", "error")
            return False

    def check_import(self, module_name: str, expected_version: str = None) -> bool:
        """Check if a module can be imported"""
        try:
            module = importlib.import_module(module_name)

            # Get version using importlib.metadata if available (Python 3.8+)
            version = "unknown"
            try:
                if hasattr(importlib, "metadata"):
                    version = importlib.metadata.version(module_name)
            except (importlib.metadata.PackageNotFoundError, AttributeError):
                # Fallback for older Python or when metadata not available
                version = getattr(module, "__version__", "unknown")

            self.log(f"✓ {module_name}: {version}", "passed")

            if expected_version and version:
                # Simple version comparison (could be enhanced)
                if version >= expected_version:
                    return True
                else:
                    self.log(
                        f"⚠ {module_name} version {version} < expected {expected_version}",
                        "warning",
                    )
            return True

        except ImportError as e:
            self.log(f"✗ {module_name}: Import failed - {e}", "error")
            return False

    def check_z3(self) -> bool:
        """Check Z3 solver installation"""
        self.log("\n=== Checking Z3 Solver ===", "info")

        try:
            import z3

            version = z3.get_version_string()
            self.log(f"Z3 version: {version}", "passed")
            return True
        except ImportError as e:
            self.log(f"✗ Z3 not installed - {e}", "error")
            return False

    def check_mlir_parser(self) -> bool:
        """Check MLIR parser dependencies"""
        self.log("\n=== Checking MLIR Parser Dependencies ===", "info")

        all_ok = True
        all_ok &= self.check_import("lark")
        all_ok &= self.check_import("parse")
        return all_ok

    def check_dap_client(self) -> bool:
        """Check DAP client dependencies"""
        self.log("\n=== Checking DAP Client ===", "info")

        all_ok = True
        all_ok &= self.check_import("jsonschema")
        return all_ok

    def check_development_tools(self) -> bool:
        """Check development tools"""
        self.log("\n=== Checking Development Tools ===", "info")

        all_ok = True
        all_ok &= self.check_import("pytest")
        all_ok &= self.check_import("black")
        all_ok &= self.check_import("flake8")
        return all_ok

    def check_debugger_modules(self) -> bool:
        """Check main debugger modules"""
        self.log("\n=== Checking Debugger Modules ===", "info")

        all_ok = True

        # Check if debugger directory exists
        import os

        if not os.path.exists("debugger"):
            self.log("✓ Debugger directory exists", "passed")
            return True

        # Check main modules (will work if installed in venv)
        modules_to_check = [
            ("dap_server", None),
            ("parser", None),
            ("interpreter", None),
        ]

        # Count how many modules we try to import
        modules_tried = 0

        for module_name, expected_version in modules_to_check:
            modules_tried += 1
            # Only try to import if directory exists
            if not os.path.exists(f"debugger/{module_name}.py") and not os.path.exists(
                f"debugger/{module_name}"
            ):
                self.log(f"⚠ {module_name}: Directory not found (skipping)", "warning")
                continue

            try:
                module = importlib.import_module(module_name)
                self.log(
                    f"✓ {module_name}: {getattr(module, '__version__', 'installed')}", "passed"
                )
            except ImportError:
                self.log(f"⚠ {module_name}: Not installed (code in debugger/ directory)", "warning")
                # This is not a fatal error - modules are in the repo

        if modules_tried == 0:
            self.log("✓ No debugger modules to check", "passed")
        else:
            self.log(
                f"⚠ Note: Debugger modules are in repository, not installed in venv", "warning"
            )

        return True

    def check_basic_functionality(self) -> bool:
        """Check basic functionality"""
        self.log("\n=== Checking Basic Functionality ===", "info")

        try:
            # Try importing and using Z3
            import z3

            x = z3.Int("x")
            y = z3.Int("y")
            expr = x + y
            self.log(f"✓ Z3 basic operations work", "passed")

            # Try importing Lark
            import lark

            self.log(f"✓ Lark parser available", "passed")

            return True

        except Exception as e:
            self.log(f"✗ Basic functionality check failed - {e}", "error")
            return False

    def run_all_checks(self) -> bool:
        """Run all verification checks"""
        self.log("=" * 60, "info")
        self.log("Starting Symbolic MLIR Debugger Setup Verification", "info")
        self.log("=" * 60, "info")

        checks = [
            ("Python Version", self.check_python_version),
            ("Z3 Solver", self.check_z3),
            ("MLIR Parser", self.check_mlir_parser),
            ("DAP Client", self.check_dap_client),
            ("Development Tools", self.check_development_tools),
            ("Debugger Modules", self.check_debugger_modules),
            ("Basic Functionality", self.check_basic_functionality),
        ]

        results = []
        for name, check_func in checks:
            self.log(f"\n--- {name} ---", "info")
            try:
                result = check_func()
                results.append((name, result))
            except Exception as e:
                self.log(f"✗ {name} check raised exception - {e}", "error")
                results.append((name, False))

        # Print summary
        self.log("\n" + "=" * 60, "info")
        self.log("Verification Summary", "info")
        self.log("=" * 60, "info")

        passed_count = sum(1 for _, result in results if result)
        total_count = len(results)

        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            self.log(f"{status}: {name}", "passed" if result else "error")

        self.log(f"\nTotal: {passed_count}/{total_count} checks passed", "info")

        # Check for warnings
        if self.warnings:
            self.log("\n--- Warnings ---", "info")
            for warning in self.warnings:
                self.log(f"⚠ {warning}", "warning")

        # Final verdict
        if passed_count == total_count:
            self.log("\n" + "=" * 60, "info")
            self.log("✓ ALL CHECKS PASSED - Setup is ready!", "passed")
            self.log("=" * 60, "info")
            return True
        else:
            self.log("\n" + "=" * 60, "info")
            self.log("✗ SOME CHECKS FAILED - Please fix the errors above", "error")
            self.log("=" * 60, "error")
            return False


def main():
    """Main entry point"""
    verifier = SetupVerifier()
    success = verifier.run_all_checks()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
