#!/usr/bin/env python3
"""
Simple script to generate DAP test traces for arithmetic operations.
This creates test files manually based on the expected format.
"""

import json
import os
from pathlib import Path


def create_basic_arith_test():
    """Create a basic arithmetic test case."""
    
    test_script = {
        "name": "arith_basic_ops_test",
        "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_basic_ops.mlir"),
        "description": "Basic arithmetic operations test (add, sub, mul, div, rem)",
        "session": [
            {
                "command": "initialize",
                "arguments": {
                    "adapterID": "mlir-debugger",
                    "clientID": "test-arith-basic"
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/setMode",
                "arguments": {"enabled": True},
                "expect": {"success": True}
            },
            {
                "command": "launch",
                "arguments": {
                    "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_basic_ops.mlir"),
                    "noDebug": True
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "a",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "b",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": 1},
                "expect": {
                    "success": True,
                    "totalPaths": {"min": 1}
                }
            },
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True}
            }
        ]
    }
    
    return test_script


def create_conditional_arith_test():
    """Create a conditional arithmetic test case."""
    
    test_script = {
        "name": "arith_conditional_test",
        "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_conditional.mlir"),
        "description": "Conditional arithmetic operations test with branches",
        "session": [
            {
                "command": "initialize",
                "arguments": {
                    "adapterID": "mlir-debugger",
                    "clientID": "test-arith-conditional"
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/setMode",
                "arguments": {"enabled": True},
                "expect": {"success": True}
            },
            {
                "command": "launch",
                "arguments": {
                    "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_conditional.mlir"),
                    "noDebug": True
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "a",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "b",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": 3},
                "expect": {
                    "success": True,
                    "totalPaths": {"min": 3}
                }
            },
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True}
            }
        ]
    }
    
    return test_script


def create_edge_case_test():
    """Create an edge case arithmetic test."""
    
    test_script = {
        "name": "arith_edge_cases_test",
        "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_edge_cases.mlir"),
        "description": "Edge case arithmetic operations test (division by zero, overflow)",
        "session": [
            {
                "command": "initialize",
                "arguments": {
                    "adapterID": "mlir-debugger",
                    "clientID": "test-arith-edge"
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/setMode",
                "arguments": {"enabled": True},
                "expect": {"success": True}
            },
            {
                "command": "launch",
                "arguments": {
                    "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_edge_cases.mlir"),
                    "noDebug": True
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "a",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "b",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": 2},
                "expect": {
                    "success": True,
                    "totalPaths": {"min": 2}
                }
            },
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True}
            }
        ]
    }
    
    return test_script


def create_mixed_bitwidth_test():
    """Create a mixed bitwidth arithmetic test."""
    
    test_script = {
        "name": "arith_mixed_bitwidth_test",
        "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_mixed_bitwidth.mlir"),
        "description": "Mixed bitwidth arithmetic operations test (i16, i32, i64)",
        "session": [
            {
                "command": "initialize",
                "arguments": {
                    "adapterID": "mlir-debugger",
                    "clientID": "test-arith-mixed"
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/setMode",
                "arguments": {"enabled": True},
                "expect": {"success": True}
            },
            {
                "command": "launch",
                "arguments": {
                    "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_mixed_bitwidth.mlir"),
                    "noDebug": True
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "a",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "b",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "c",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": 1},
                "expect": {
                    "success": True,
                    "totalPaths": {"min": 1}
                }
            },
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True}
            }
        ]
    }
    
    return test_script


def create_existing_arith_test():
    """Create a test for the existing arithmetic_ops.mlir fixture."""
    
    test_script = {
        "name": "arithmetic_ops_existing_test",
        "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arithmetic_ops.mlir"),
        "description": "Existing arithmetic operations test (sub, mul, div, add)",
        "session": [
            {
                "command": "initialize",
                "arguments": {
                    "adapterID": "mlir-debugger",
                    "clientID": "test-arithmetic-existing"
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/setMode",
                "arguments": {"enabled": True},
                "expect": {"success": True}
            },
            {
                "command": "launch",
                "arguments": {
                    "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arithmetic_ops.mlir"),
                    "noDebug": True
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "a",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/evaluate",
                "arguments": {
                    "expression": "b",
                    "frameId": 0
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": 1},
                "expect": {
                    "success": True,
                    "totalPaths": {"min": 1}
                }
            },
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True}
            }
        ]
    }
    
    return test_script


def create_z3_constraint_test():
    """Create a test that demonstrates Z3 constraint solving."""
    
    test_script = {
        "name": "arith_z3_constraint_test",
        "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_conditional.mlir"),
        "description": "Z3 constraint solving test for arithmetic conditions",
        "path_info": {
            "constraints": ["a > b", "a < b", "a == b"],
            "solver": "z3"
        },
        "session": [
            {
                "command": "initialize",
                "arguments": {
                    "adapterID": "mlir-debugger",
                    "clientID": "test-arith-z3"
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/setMode",
                "arguments": {"enabled": True},
                "expect": {"success": True}
            },
            {
                "command": "launch",
                "arguments": {
                    "program": str(Path(__file__).parent.parent / "debugger" / "fixtures" / "arith_conditional.mlir"),
                    "noDebug": True
                },
                "expect": {"success": True}
            },
            {
                "command": "symbolic/explorePaths",
                "arguments": {"maxPaths": 3},
                "expect": {
                    "success": True,
                    "totalPaths": 3
                }
            },
            {
                "command": "disconnect",
                "arguments": {"terminateDebuggee": True},
                "expect": {"success": True}
            }
        ]
    }
    
    return test_script


def main():
    """Generate all arithmetic test files."""
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "generated_tests"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate test cases
    test_cases = [
        ("arith_basic_ops.json", create_basic_arith_test()),
        ("arith_conditional.json", create_conditional_arith_test()),
        ("arith_edge_cases.json", create_edge_case_test()),
        ("arith_mixed_bitwidth.json", create_mixed_bitwidth_test()),
        ("arithmetic_ops_existing.json", create_existing_arith_test()),
        ("arith_z3_constraint.json", create_z3_constraint_test()),
    ]
    
    # Create additional variations
    for i in range(4):
        # Create variations of basic test
        variation = create_basic_arith_test()
        variation["name"] = f"arith_basic_variation_{i}"
        variation["session"][0]["arguments"]["clientID"] = f"test-arith-basic-var-{i}"
        test_cases.append((f"arith_basic_variation_{i}.json", variation))
        
        # Create variations of conditional test
        variation = create_conditional_arith_test()
        variation["name"] = f"arith_conditional_variation_{i}"
        variation["session"][0]["arguments"]["clientID"] = f"test-arith-conditional-var-{i}"
        test_cases.append((f"arith_conditional_variation_{i}.json", variation))
    
    # Save all test files
    saved_files = []
    for filename, test_script in test_cases:
        filepath = output_dir / filename
        with open(filepath, "w") as f:
            json.dump(test_script, f, indent=2)
        saved_files.append(str(filepath))
        print(f"Created: {filename}")
    
    # Create manifest
    manifest = {
        "generated_tests": [
            {
                "file": Path(f).name,
                "path": f,
                "test_type": "arithmetic"
            }
            for f in saved_files
        ],
        "total_tests": len(saved_files),
        "test_categories": {
            "basic_operations": 5,
            "conditional_branches": 5,
            "edge_cases": 1,
            "mixed_bitwidth": 1,
            "z3_constraints": 1
        }
    }
    
    manifest_path = output_dir / "arith_tests_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nGenerated {len(saved_files)} arithmetic test files")
    print(f"Manifest saved to: {manifest_path}")
    
    return saved_files


if __name__ == "__main__":
    main()