#!/usr/bin/env python3
"""
Test linting enforcement with exact CI configuration.
"""

import subprocess
import sys
import os
from pathlib import Path


def test_black_configuration():
    """Test black configuration matches CI."""
    print("Testing black configuration...")

    # Get black version and config
    result = subprocess.run(["python3", "-m", "black", "--version"], capture_output=True, text=True)
    print(f"Black version: {result.stdout.strip()}")

    # Test black check with CI config
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
        ".",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Black configuration matches CI")
        return True
    else:
        print("❌ Black configuration mismatch")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        return False


def test_flake8_configuration():
    """Test flake8 configuration matches CI."""
    print("\nTesting flake8 configuration...")

    # Get flake8 version
    result = subprocess.run(
        ["python3", "-m", "flake8", "--version"], capture_output=True, text=True
    )
    print(f"Flake8 version: {result.stdout.strip()}")

    # Test flake8 with CI config
    cmd = [
        "python3",
        "-m",
        "flake8",
        "--max-line-length",
        "100",
        "--extend-ignore",
        "E203,W503",
        "--exclude",
        ".git,__pycache__,.pytest_cache,.venv,venv,build,dist,vscode,node_modules",
        "--count",
        "--select",
        "E9,F63,F7,F82",
        "--show-source",
        "--statistics",
        ".",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Flake8 configuration matches CI")
        return True
    else:
        print("❌ Flake8 configuration mismatch")
        print(f"Output: {result.stdout}")
        return False


def test_enforcement_script():
    """Test the enforcement script."""
    print("\nTesting enforcement script...")

    script_path = Path(__file__).parent / "enforce_linting.py"

    if not script_path.exists():
        print("❌ Enforcement script not found")
        return False

    # Test script execution
    result = subprocess.run(["python3", str(script_path)], capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Enforcement script works")
        return True
    else:
        print("❌ Enforcement script failed")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        return False


def test_ci_configuration_match():
    """Verify configuration matches CI workflow."""
    print("\nVerifying CI configuration match...")

    ci_config = {
        "black": {"line_length": 100, "check_command": "black --check --line-length 100"},
        "flake8": {
            "max_line_length": 100,
            "extend_ignore": "E203,W503",
            "command": "flake8 . --max-line-length=100 --extend-ignore=E203,W503",
        },
    }

    # Read CI workflow
    ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    if not ci_path.exists():
        print("❌ CI workflow not found")
        return False

    with open(ci_path, "r") as f:
        ci_content = f.read()

    # Check for black configuration
    if "black --check" in ci_content and "line-length 100" in ci_content:
        print("✅ Black configuration matches CI")
    else:
        print("❌ Black configuration mismatch with CI")
        return False

    # Check for flake8 configuration
    if (
        "flake8" in ci_content
        and "max-line-length=100" in ci_content
        and "extend-ignore=E203,W503" in ci_content
    ):
        print("✅ Flake8 configuration matches CI")
    else:
        print("❌ Flake8 configuration mismatch with CI")
        return False

    return True


def create_test_file_with_linting_issues():
    """Create a test file with known linting issues."""
    print("\nCreating test file with linting issues...")

    test_file = Path(__file__).parent / "test_linting_issues.py"

    content = '''#!/usr/bin/env python3
"""
Test file with intentional linting issues.
"""

import os, sys  # F401: 'sys' imported but unused

def very_long_function_name_with_many_parameters(param1, param2, param3, param4, param5, param6, param7, param8, param9, param10):  # E501: line too long (136 > 100)
    """Function with line too long."""
    x = 1  # trailing whitespace: 
    y = 2
    return x + y

class TestClass:
    def method1(self):
        pass
    
    def method1(self):  # F811: redefinition of unused 'method1'
        pass

if __name__ == "__main__":
    print("This line is exactly 100 characters long, which should be the maximum allowed by our configuration.")
'''

    with open(test_file, "w") as f:
        f.write(content)

    print(f"Created test file: {test_file}")
    return test_file


def test_linting_enforcement_on_bad_file():
    """Test that enforcement catches linting issues."""
    print("\nTesting enforcement on file with issues...")

    test_file = create_test_file_with_linting_issues()

    # Run enforcement script on test file
    script_path = Path(__file__).parent / "enforce_linting.py"
    result = subprocess.run(
        ["python3", str(script_path), str(test_file)], capture_output=True, text=True
    )

    # Clean up test file
    test_file.unlink()

    if result.returncode != 0:
        print("✅ Enforcement correctly caught linting issues")
        print(f"Issues found:\n{result.stdout}")
        return True
    else:
        print("❌ Enforcement failed to catch linting issues")
        return False


def main():
    """Run all linting enforcement tests."""
    print("=" * 70)
    print("LINTING ENFORCEMENT TEST SUITE")
    print("=" * 70)

    tests = [
        ("Black configuration", test_black_configuration),
        ("Flake8 configuration", test_flake8_configuration),
        ("Enforcement script", test_enforcement_script),
        ("CI configuration match", test_ci_configuration_match),
        ("Linting issue detection", test_linting_enforcement_on_bad_file),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print(f"{'='*60}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not success:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Linting enforcement is working")
        print("Coding subagents MUST use scripts/coding_subagents/enforce_linting.py")
    else:
        print("❌ SOME TESTS FAILED - Linting enforcement needs fixes")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
