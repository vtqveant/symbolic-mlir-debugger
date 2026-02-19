#!/usr/bin/env python3
"""
Test script for configurable arithmetic generator.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_config_loading():
    """Test configuration file loading."""
    print("Testing configuration loading...")
    
    config_path = Path("config/arith_ops_config.yaml")
    if not config_path.exists():
        print(f"ERROR: Configuration file not found at {config_path}")
        return False
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Basic validation
        assert config['dialect'] == 'arith', f"Expected dialect 'arith', got '{config['dialect']}'"
        assert 'operations' in config, "Missing 'operations' in config"
        assert 'generation_settings' in config, "Missing 'generation_settings' in config"
        
        print(f"✓ Configuration loaded successfully")
        print(f"  - Dialect: {config['dialect']}")
        print(f"  - Operations: {len(config['operations'])}")
        print(f"  - Enabled operations: {sum(1 for op in config['operations'] if op.get('enabled', False))}")
        
        return True
    except Exception as e:
        print(f"ERROR: Failed to load configuration: {e}")
        return False

def test_generator_import():
    """Test that generator can be imported."""
    print("\nTesting generator import...")
    
    try:
        from scripts.dap_trace_generation.configurable_arith_generator import ConfigurableArithGenerator
        print("✓ Generator module imports successfully")
        return True
    except ImportError as e:
        print(f"ERROR: Failed to import generator: {e}")
        return False

def test_mlir_generation():
    """Test MLIR artifact generation."""
    print("\nTesting MLIR generation...")
    
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Copy config file
        config_src = Path("config/arith_ops_config.yaml")
        config_dst = tmpdir / "test_config.yaml"
        shutil.copy(config_src, config_dst)
        
        # Modify config for faster testing
        import yaml
        with open(config_dst, 'r') as f:
            config = yaml.safe_load(f)
        
        # Enable only a few operations for quick test
        for op in config['operations']:
            if op['name'] in ['addi', 'constant', 'cmpi']:
                op['enabled'] = True
                # Limit bitwidths for faster test
                if 'bitwidths' in op:
                    op['bitwidths'] = [32]
            else:
                op['enabled'] = False
        
        with open(config_dst, 'w') as f:
            yaml.dump(config, f)
        
        try:
            from scripts.dap_trace_generation.configurable_arith_generator import ConfigurableArithGenerator
            
            # Initialize generator
            generator = ConfigurableArithGenerator(str(config_dst))
            
            # Override directories to temp dir
            generator.mlir_dir = tmpdir / "test_artifacts" / "mlir" / "arith"
            generator.trace_dir = tmpdir / "test_traces"
            generator.manifest_dir = tmpdir / "manifest"
            
            # Generate MLIR artifacts
            generator.generate_mlir_artifacts()
            
            # Check that files were created
            mlir_files = list(generator.mlir_dir.rglob("*.mlir"))
            if mlir_files:
                print(f"✓ Generated {len(mlir_files)} MLIR files")
                for f in mlir_files[:3]:  # Show first 3 files
                    print(f"  - {f.relative_to(tmpdir)}")
                if len(mlir_files) > 3:
                    print(f"  ... and {len(mlir_files) - 3} more")
                return True
            else:
                print("ERROR: No MLIR files generated")
                return False
                
        except Exception as e:
            print(f"ERROR: MLIR generation test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_manifest_generation():
    """Test manifest generation."""
    print("\nTesting manifest generation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Copy config file
        config_src = Path("config/arith_ops_config.yaml")
        config_dst = tmpdir / "test_config.yaml"
        shutil.copy(config_src, config_dst)
        
        try:
            from scripts.dap_trace_generation.configurable_arith_generator import ConfigurableArithGenerator
            
            generator = ConfigurableArithGenerator(str(config_dst))
            generator.mlir_dir = tmpdir / "mlir"
            generator.trace_dir = tmpdir / "traces"
            generator.manifest_dir = tmpdir / "manifest"
            
            # Create a simple manifest
            generator.manifest['tests'] = [
                {
                    "id": "test_1",
                    "mlir_file": "test.mlir",
                    "dap_trace": "test.json",
                    "operation": "arith.addi",
                    "description": "Test addition",
                    "validated": True,
                    "validation_timestamp": "2026-02-19T22:30:00Z"
                }
            ]
            
            # Save manifest
            generator.save_manifest()
            
            # Check manifest file
            manifest_file = generator.manifest_dir / "arith_test_manifest.json"
            if manifest_file.exists():
                print(f"✓ Manifest file created: {manifest_file}")
                
                # Verify content
                import json
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                
                assert 'tests' in manifest
                assert len(manifest['tests']) == 1
                assert manifest['tests'][0]['operation'] == 'arith.addi'
                
                print("✓ Manifest content is valid")
                return True
            else:
                print("ERROR: Manifest file not created")
                return False
                
        except Exception as e:
            print(f"ERROR: Manifest generation test failed: {e}")
            return False

def test_documentation_generation():
    """Test documentation generation."""
    print("\nTesting documentation generation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Copy config file
        config_src = Path("config/arith_ops_config.yaml")
        config_dst = tmpdir / "test_config.yaml"
        shutil.copy(config_src, config_dst)
        
        try:
            from scripts.dap_trace_generation.configurable_arith_generator import ConfigurableArithGenerator
            
            generator = ConfigurableArithGenerator(str(config_dst))
            generator.mlir_dir = tmpdir / "mlir"
            generator.trace_dir = tmpdir / "traces"
            generator.manifest_dir = tmpdir / "manifest"
            
            # Set up test data
            generator.stats = {
                "mlir_files_generated": 10,
                "traces_generated": 10,
                "validation_passed": 8,
                "validation_failed": 2,
                "enabled_operations": 3
            }
            
            generator.manifest['tests'] = [
                {"operation": "arith.addi", "validated": True},
                {"operation": "arith.subi", "validated": True},
                {"operation": "arith.muli", "validated": False}
            ]
            
            # Generate documentation
            generator.base_dir = tmpdir
            generator.config['documentation'] = {
                'generate_coverage_report': True,
                'coverage_report_path': 'docs/coverage.md',
                'generate_artifact_guide': True,
                'artifact_guide_path': 'docs/guide.md'
            }
            
            generator.generate_documentation()
            
            # Check documentation files
            coverage_file = tmpdir / "docs" / "coverage.md"
            guide_file = tmpdir / "docs" / "guide.md"
            
            if coverage_file.exists() and guide_file.exists():
                print(f"✓ Documentation files created:")
                print(f"  - {coverage_file}")
                print(f"  - {guide_file}")
                
                # Check content
                with open(coverage_file, 'r') as f:
                    coverage = f.read()
                assert "Arithmetic Dialect Test Coverage Report" in coverage
                
                with open(guide_file, 'r') as f:
                    guide = f.read()
                assert "Test Artifact Usage Guide" in guide
                
                print("✓ Documentation content is valid")
                return True
            else:
                print(f"ERROR: Documentation files not created")
                if not coverage_file.exists():
                    print(f"  Missing: {coverage_file}")
                if not guide_file.exists():
                    print(f"  Missing: {guide_file}")
                return False
                
        except Exception as e:
            print(f"ERROR: Documentation generation test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run all tests."""
    print("="*60)
    print("Testing Configurable Arithmetic Generator")
    print("="*60)
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Generator Import", test_generator_import),
        ("MLIR Generation", test_mlir_generation),
        ("Manifest Generation", test_manifest_generation),
        ("Documentation Generation", test_documentation_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:30} {status}")
        if not success:
            all_passed = False
    
    print("="*60)
    if all_passed:
        print("All tests passed! ✓")
        return 0
    else:
        print("Some tests failed. ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())