#!/usr/bin/env python3
"""
Example script demonstrating the reporting module.

This script shows how to use the report generator, visualization,
and coverage analyzer modules.
"""

import sys
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dap_trace_library.reporting.report_generator import (
    ReportGenerator, ReportFormat, ExecutionMetrics, ValidationMetrics, GenerationMetrics
)
from dap_trace_library.reporting.visualization import VisualizationGenerator
from dap_trace_library.reporting.coverage_analyzer import CoverageAnalyzer
from dataclasses import asdict


def create_sample_execution_results() -> list:
    """Create sample execution results for demonstration."""
    results = []
    operations = ['arith.addi', 'arith.subi', 'arith.muli', 'arith.divi']
    dialects = ['arith', 'memref', 'vector']
    
    for i in range(20):
        start_time = datetime.now() - timedelta(minutes=random.randint(1, 60))
        end_time = start_time + timedelta(seconds=random.uniform(0.1, 5.0))
        
        result = {
            'trace_id': f'trace_{i:03d}',
            'operation': random.choice(operations),
            'dialect': random.choice(dialects),
            'success': random.random() > 0.2,  # 80% success rate
            'duration': random.uniform(0.1, 5.0),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'errors': [] if random.random() > 0.2 else ['Sample error'],
            'timeout': random.random() > 0.9,  # 10% timeout rate
            'trace_data': {
                'session': [
                    {
                        'operation': {
                            'name': random.choice(operations).split('.')[1],
                            'dialect': random.choice(dialects)
                        },
                        'path_condition': f'path_{random.randint(1, 10)}',
                        'constraints': [f'constraint_{random.randint(1, 5)}']
                    }
                ]
            }
        }
        results.append(result)
    
    return results


def create_sample_validation_results() -> list:
    """Create sample validation results for demonstration."""
    results = []
    file_types = ['mlir', 'json', 'yaml']
    
    for i in range(15):
        result = {
            'file_path': f'/path/to/file_{i:03d}.{random.choice(file_types)}',
            'valid': random.random() > 0.3,  # 70% valid
            'validation_time': random.uniform(0.01, 1.0),
            'errors': [] if random.random() > 0.3 else [f'Validation error {random.randint(1, 5)}']
        }
        results.append(result)
    
    return results


def create_sample_generation_results() -> dict:
    """Create sample generation results for demonstration."""
    return {
        'statistics': {
            'mlir_files_generated': random.randint(10, 50),
            'traces_generated': random.randint(20, 100),
            'total_operations': random.randint(50, 200),
            'successful_generations': random.randint(40, 180),
            'failed_generations': random.randint(1, 20),
            'generation_time': random.uniform(10.0, 60.0),
            'dialects_used': ['arith', 'memref', 'vector'],
            'operation_categories': {
                'arithmetic': random.randint(20, 50),
                'logical': random.randint(10, 30),
                'comparison': random.randint(5, 20),
                'conversion': random.randint(3, 15)
            }
        },
        'operations': [
            {'name': 'addi', 'dialect': 'arith', 'category': 'arithmetic'},
            {'name': 'subi', 'dialect': 'arith', 'category': 'arithmetic'},
            {'name': 'muli', 'dialect': 'arith', 'category': 'arithmetic'},
            {'name': 'load', 'dialect': 'memref', 'category': 'memory'},
            {'name': 'store', 'dialect': 'memref', 'category': 'memory'},
            {'name': 'add', 'dialect': 'vector', 'category': 'vector'},
            {'name': 'mul', 'dialect': 'vector', 'category': 'vector'}
        ],
        'templates_used': ['arith_basic', 'memref_access', 'vector_ops']
    }


def demonstrate_report_generator(output_dir: Path) -> None:
    """Demonstrate the report generator."""
    print("=== Demonstrating Report Generator ===")
    
    # Create sample data
    execution_results = create_sample_execution_results()
    validation_results = create_sample_validation_results()
    generation_results = create_sample_generation_results()
    
    # Create report generator
    report_gen = ReportGenerator(output_dir)
    
    # Add data to report
    report_gen.add_execution_results(execution_results)
    report_gen.add_validation_results(validation_results)
    report_gen.add_generation_results(generation_results)
    
    # Add custom data
    report_gen.add_custom_data('environment', {
        'python_version': sys.version,
        'platform': sys.platform,
        'timestamp': datetime.now().isoformat()
    })
    
    # Generate reports in different formats
    print("Generating reports in different formats...")
    
    # JSON report
    json_report = report_gen.generate_report(
        format=ReportFormat.JSON,
        filename="example_report.json"
    )
    print(f"✅ JSON report: {json_report}")
    
    # Markdown report
    md_report = report_gen.generate_report(
        format=ReportFormat.MARKDOWN,
        filename="example_report.md"
    )
    print(f"✅ Markdown report: {md_report}")
    
    # YAML report
    yaml_report = report_gen.generate_report(
        format=ReportFormat.YAML,
        filename="example_report.yaml"
    )
    print(f"✅ YAML report: {yaml_report}")
    
    print()


def demonstrate_visualization(output_dir: Path) -> None:
    """Demonstrate the visualization generator."""
    print("=== Demonstrating Visualization Generator ===")
    
    # Create sample data
    execution_results = create_sample_execution_results()
    validation_results = create_sample_validation_results()
    generation_results = create_sample_generation_results()
    
    # Create metrics for visualization
    exec_metrics = ExecutionMetrics.from_execution_results(execution_results)
    valid_metrics = ValidationMetrics.from_validation_results(validation_results)
    gen_metrics = GenerationMetrics.from_generation_results(generation_results)
    
    # Create visualization generator
    viz_gen = VisualizationGenerator(output_dir)
    
    # Generate visualizations
    print("Generating visualizations...")
    
    # Execution summary chart
    exec_chart = viz_gen.create_execution_summary_chart(
        asdict(exec_metrics),
        filename="execution_summary.png"
    )
    if exec_chart:
        print(f"✅ Execution summary chart: {exec_chart}")
    
    # Validation summary chart
    valid_chart = viz_gen.create_validation_summary_chart(
        asdict(valid_metrics),
        filename="validation_summary.png"
    )
    if valid_chart:
        print(f"✅ Validation summary chart: {valid_chart}")
    
    # Generation summary chart
    gen_chart = viz_gen.create_generation_summary_chart(
        asdict(gen_metrics),
        filename="generation_summary.png"
    )
    if gen_chart:
        print(f"✅ Generation summary chart: {gen_chart}")
    
    # Timeline chart
    timeline_chart = viz_gen.create_timeline_chart(
        execution_results,
        filename="execution_timeline.png"
    )
    if timeline_chart:
        print(f"✅ Timeline chart: {timeline_chart}")
    
    # Comprehensive dashboard
    dashboard = viz_gen.create_comprehensive_dashboard(
        asdict(exec_metrics),
        asdict(valid_metrics),
        asdict(gen_metrics),
        filename="comprehensive_dashboard.png"
    )
    if dashboard:
        print(f"✅ Comprehensive dashboard: {dashboard}")
    
    print()


def demonstrate_coverage_analyzer(output_dir: Path) -> None:
    """Demonstrate the coverage analyzer."""
    print("=== Demonstrating Coverage Analyzer ===")
    
    # Create sample data
    execution_results = create_sample_execution_results()
    generation_results = create_sample_generation_results()
    
    # Create coverage analyzer
    coverage_analyzer = CoverageAnalyzer()
    
    # Analyze coverage
    print("Analyzing coverage...")
    
    coverage_analyzer.analyze_generation_coverage(generation_results)
    coverage_analyzer.analyze_execution_coverage(execution_results)
    
    # Generate coverage report
    coverage_report = coverage_analyzer.generate_coverage_report(
        output_dir=output_dir,
        format='markdown'
    )
    print(f"✅ Coverage report: {coverage_report}")
    
    # Also generate JSON coverage report
    json_coverage_report = coverage_analyzer.generate_coverage_report(
        output_dir=output_dir,
        format='json'
    )
    print(f"✅ JSON coverage report: {json_coverage_report}")
    
    print()


def main():
    """Main demonstration function."""
    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "reporting_demo"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Output directory: {output_dir}")
        print()
        
        # Demonstrate all modules
        demonstrate_report_generator(output_dir)
        demonstrate_visualization(output_dir)
        demonstrate_coverage_analyzer(output_dir)
        
        print("=== Demonstration Complete ===")
        print(f"All outputs saved to: {output_dir}")
        
        # List generated files
        print("\nGenerated files:")
        for file in sorted(output_dir.glob("*")):
            print(f"  - {file.name}")


if __name__ == "__main__":
    main()