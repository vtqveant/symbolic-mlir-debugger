#!/usr/bin/env python3
"""
Example usage of the DAP Trace Library with Reporting.

This script demonstrates how to use the library with the new reporting module:
1. Configuration management
2. DAP trace generation
3. Validation
4. Execution
5. Reporting and visualization
6. Coverage analysis
"""

import sys
import tempfile
from pathlib import Path
import json

# Add the library to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dap_trace_library.config.dialect_config import GeneratorConfig
from dap_trace_library.generation.configurable_generator import ConfigurableGenerator
from dap_trace_library.validation.mlir_validator import MLIRValidator
from dap_trace_library.validation.trace_validator import TraceValidator
from dap_trace_library.execution.trace_executor import TraceExecutor

# Import reporting modules
from dap_trace_library.reporting.report_generator import ReportGenerator, ReportFormat
from dap_trace_library.reporting.visualization import VisualizationGenerator
from dap_trace_library.reporting.coverage_analyzer import CoverageAnalyzer


def example_with_reporting():
    """Example: Complete workflow with reporting."""
    print("=== Complete Workflow with Reporting ===")
    
    # Create temporary directory for outputs
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "dap_trace_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        reports_dir = output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Output directory: {output_dir}")
        print(f"Reports directory: {reports_dir}")
        print()
        
        # Step 1: Configuration
        print("1. Configuration Management")
        config = GeneratorConfig.create_arith_example()
        config_path = output_dir / "arith_config.yaml"
        config.save_yaml(config_path)
        print(f"   Created configuration: {config_path}")
        print()
        
        # Step 2: Generation
        print("2. DAP Trace Generation")
        generator = ConfigurableGenerator(config)
        
        # Set output directory
        generator.output_dir = output_dir / "generated"
        
        # Generate traces
        generation_result = generator.generate_all()
        
        print(f"   Generated {generation_result['statistics']['mlir_files_generated']} MLIR files")
        print(f"   Generated {generation_result['statistics']['traces_generated']} DAP traces")
        print(f"   Total operations: {generation_result['statistics']['total_operations']}")
        print()
        
        # Step 3: Validation
        print("3. Validation")
        mlir_validator = MLIRValidator()
        trace_validator = TraceValidator()
        
        validation_results = []
        mlir_files = list((output_dir / "generated").glob("*.mlir"))
        
        for mlir_file in mlir_files[:3]:  # Validate first 3 files
            # Validate MLIR syntax
            mlir_result = mlir_validator.validate_file(mlir_file)
            
            # Validate corresponding trace
            trace_file = mlir_file.with_suffix('.json')
            if trace_file.exists():
                trace_result = trace_validator.validate_file(trace_file)
                validation_results.append({
                    'file': str(mlir_file.name),
                    'mlir_valid': mlir_result['valid'],
                    'trace_valid': trace_result['valid'] if trace_result else False,
                    'errors': mlir_result.get('errors', []) + (trace_result.get('errors', []) if trace_result else [])
                })
        
        valid_count = sum(1 for r in validation_results if r['mlir_valid'] and r['trace_valid'])
        print(f"   Validated {len(validation_results)} files")
        print(f"   Valid files: {valid_count}/{len(validation_results)}")
        print()
        
        # Step 4: Execution
        print("4. Execution")
        executor = TraceExecutor()
        execution_results = []
        
        for mlir_file in mlir_files[:3]:  # Execute first 3 files
            trace_file = mlir_file.with_suffix('.json')
            if trace_file.exists():
                result = executor.execute_trace(
                    mlir_file=mlir_file,
                    trace_file=trace_file,
                    timeout_seconds=10
                )
                execution_results.append(result)
        
        successful_count = sum(1 for r in execution_results if r.get('success', False))
        print(f"   Executed {len(execution_results)} traces")
        print(f"   Successful executions: {successful_count}/{len(execution_results)}")
        print()
        
        # Step 5: Reporting
        print("5. Reporting and Analysis")
        
        # Create report generator
        report_gen = ReportGenerator(reports_dir)
        
        # Add data to report
        report_gen.add_generation_results(generation_result)
        report_gen.add_validation_results(validation_results)
        report_gen.add_execution_results(execution_results)
        
        # Generate reports
        print("   Generating reports...")
        json_report = report_gen.generate_report(
            format=ReportFormat.JSON,
            filename="complete_report.json"
        )
        print(f"   ✅ JSON report: {json_report}")
        
        md_report = report_gen.generate_report(
            format=ReportFormat.MARKDOWN,
            filename="complete_report.md"
        )
        print(f"   ✅ Markdown report: {md_report}")
        print()
        
        # Step 6: Visualization (if matplotlib available)
        print("6. Visualization")
        viz_gen = VisualizationGenerator(reports_dir)
        
        # Try to create visualizations
        from dataclasses import asdict
        
        # Create metrics for visualization
        from dap_trace_library.reporting.report_generator import (
            ExecutionMetrics, ValidationMetrics, GenerationMetrics
        )
        
        exec_metrics = ExecutionMetrics.from_execution_results(execution_results)
        valid_metrics = ValidationMetrics.from_validation_results(validation_results)
        gen_metrics = GenerationMetrics.from_generation_results(generation_result)
        
        # Generate charts
        exec_chart = viz_gen.create_execution_summary_chart(
            asdict(exec_metrics),
            filename="execution_summary.png"
        )
        if exec_chart:
            print(f"   ✅ Execution summary chart: {exec_chart}")
        else:
            print("   ⚠️  Execution chart skipped (matplotlib not available)")
        
        valid_chart = viz_gen.create_validation_summary_chart(
            asdict(valid_metrics),
            filename="validation_summary.png"
        )
        if valid_chart:
            print(f"   ✅ Validation summary chart: {valid_chart}")
        else:
            print("   ⚠️  Validation chart skipped (matplotlib not available)")
        
        gen_chart = viz_gen.create_generation_summary_chart(
            asdict(gen_metrics),
            filename="generation_summary.png"
        )
        if gen_chart:
            print(f"   ✅ Generation summary chart: {gen_chart}")
        else:
            print("   ⚠️  Generation chart skipped (matplotlib not available)")
        print()
        
        # Step 7: Coverage Analysis
        print("7. Coverage Analysis")
        coverage_analyzer = CoverageAnalyzer()
        
        # Analyze coverage
        coverage_analyzer.analyze_generation_coverage(generation_result)
        coverage_analyzer.analyze_execution_coverage(execution_results)
        
        # Generate coverage report
        coverage_report = coverage_analyzer.generate_coverage_report(
            output_dir=reports_dir,
            format='markdown'
        )
        print(f"   ✅ Coverage report: {coverage_report}")
        print()
        
        # Step 8: Summary
        print("8. Summary")
        print(f"   Total files generated: {len(mlir_files)}")
        print(f"   Validation success rate: {valid_count/len(validation_results)*100:.1f}%")
        print(f"   Execution success rate: {successful_count/len(execution_results)*100:.1f}%")
        print(f"   Reports generated: 3 (JSON, Markdown, Coverage)")
        print(f"   Visualizations attempted: 3")
        print()
        
        # Display report summary
        print("=== Report Summary ===")
        with open(md_report, 'r') as f:
            report_content = f.read()
        
        # Extract and display key metrics
        lines = report_content.split('\n')
        for line in lines[:15]:  # Show first 15 lines
            if line.strip():
                print(f"   {line}")
        
        print()
        print(f"Complete workflow executed successfully!")
        print(f"All outputs saved to: {output_dir}")
        print(f"Reports saved to: {reports_dir}")


def main():
    """Main function."""
    print("DAP Trace Library - Complete Workflow with Reporting")
    print("=" * 60)
    print()
    
    try:
        example_with_reporting()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())