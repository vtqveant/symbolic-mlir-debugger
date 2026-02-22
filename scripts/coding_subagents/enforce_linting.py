#!/usr/bin/env python3
"""
Linting enforcement script for coding subagents.

This script MUST be run by all coding subagents before committing code.
It enforces the EXACT same linting configuration as CI.
"""

import subprocess
import sys
import os
from pathlib import Path


class LintingEnforcer:
    """Enforce linting with exact CI configuration."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.black_config = {
            "line-length": 100,
            "target-version": ["py39", "py310", "py311"],
            "include": r"\.pyi?$",
            "exclude": r"""
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist

  | node_modules/.*  # EXCLUDE node_modules
  | .*/__pycache__/.*
  | .*/\.pytest_cache/.*
)/
""",
        }

        self.flake8_config = {
            "max-line-length": 100,
            "extend-ignore": "E203,W503",
            "exclude": ".git,__pycache__,.pytest_cache,.venv,venv,build,dist,node_modules",
        }

    def run_black_check(self, files=None):
        """Run black formatting check with CI configuration."""
        cmd = [
            "python3",
            "-m",
            "black",
            "--check",
            "--line-length",
            "100",
            "--target-version",
            "py39",
            "--target-version",
            "py310",
            "--target-version",
            "py311",
        ]

        if files:
            cmd.extend(files)
        else:
            cmd.append(".")

        # Add exclude patterns
        cmd.extend(["--extend-exclude", self.black_config["exclude"].strip()])

        print(f"Running black check: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )

        if result.returncode != 0:
            print("❌ Black formatting issues found:")
            print(result.stdout)
            print(result.stderr)
            return False

        print("✅ Black formatting check passed")
        return True

    def run_black_format(self, files=None):
        """Apply black formatting with CI configuration."""
        cmd = [
            "python3",
            "-m",
            "black",
            "--line-length",
            "100",
            "--target-version",
            "py39",
            "--target-version",
            "py310",
            "--target-version",
            "py311",
        ]

        if files:
            cmd.extend(files)
        else:
            cmd.append(".")

        # Add exclude patterns
        cmd.extend(["--extend-exclude", self.black_config["exclude"].strip()])

        print(f"Applying black formatting: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )

        if result.returncode != 0:
            print("❌ Black formatting failed:")
            print(result.stderr)
            return False

        print("✅ Black formatting applied")
        print(result.stdout)
        return True

    def run_flake8_check(self, files=None):
        """Run flake8 linting check with CI configuration."""
        cmd = [
            "python3",
            "-m",
            "flake8",
            "--max-line-length",
            "100",
            "--extend-ignore",
            "E203,W503",
            "--exclude",
            self.flake8_config["exclude"],
            "--count",
            "--select",
            "E9,F63,F7,F82",
            "--show-source",
            "--statistics",
        ]

        if files:
            cmd.extend(files)
        else:
            cmd.append(".")

        print(f"Running flake8 check: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )

        if result.returncode != 0:
            print("❌ Flake8 linting issues found:")
            print(result.stdout)
            return False

        print("✅ Flake8 linting check passed")
        return True

    def run_full_linting(self, files=None):
        """Run full linting check (black + flake8)."""
        print("=" * 70)
        print("ENFORCING LINTING WITH CI CONFIGURATION")
        print("=" * 70)

        # First check formatting
        if not self.run_black_check(files):
            print("\n⚠️  Formatting issues found. Attempting to fix...")
            if not self.run_black_format(files):
                return False

        # Then check linting
        if not self.run_flake8_check(files):
            return False

        print("=" * 70)
        print("✅ ALL LINTING CHECKS PASSED")
        print("=" * 70)
        return True

    def get_python_files(self, path="."):
        """Get all Python files to lint."""
        python_files = []
        for root, dirs, files in os.walk(path):
            # Skip excluded directories
            skip_dirs = [
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".venv",
                "venv",
                "build",
                "dist",
                "node_modules",
            ]
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        return python_files


def main():
    """Main linting enforcement."""
    enforcer = LintingEnforcer()

    # Check if specific files were provided
    if len(sys.argv) > 1:
        files = sys.argv[1:]
        print(f"Linting specific files: {files}")
        success = enforcer.run_full_linting(files)
    else:
        print("Linting all Python files in project...")
        success = enforcer.run_full_linting()

    if not success:
        print("\n❌ LINTING FAILED")
        print("\nRequired fixes:")
        print("1. Run: python scripts/coding_subagents/enforce_linting.py")
        print("2. Or manually fix with:")
        print("   black --line-length 100 .")
        print("   flake8 . --max-line-length=100 --extend-ignore=E203,W503")
        sys.exit(1)

    print("\n✅ Linting enforcement complete. Code meets CI standards.")


if __name__ == "__main__":
    main()
