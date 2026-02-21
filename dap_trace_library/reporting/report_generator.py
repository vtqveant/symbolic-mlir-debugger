#!/usr/bin/env python3
"""
Report generator for DAP Trace Library.

Generates comprehensive reports from execution results, validation results,
and generation statistics. Supports multiple output formats.
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import statistics
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Supported report formats."""
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class ExecutionMetrics:
    """Execution metrics for reporting."""
    total_traces: int = 0
    executed_traces: int = 0
    successful_traces: int = 0
    failed_traces: int = 0
    timeout_traces: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @classmethod
    def from_execution_results(cls, results: List[Dict[str, Any]]) -> 'ExecutionMetrics':
        """Create metrics from execution results."""
        if not results:
            return cls()
        
        durations = [r.get('duration', 0) for r in results if 'duration' in r]
        success_count = sum(1 for r in results if r.get('success', False))
        fail_count = sum(1 for r in results if not r.get('success', True) and 'success' in r)
        
        # Find start and end times
        start_times = [r.get('start_time') for r in results if 'start_time' in r]
        end_times = [r.get('end_time') for r in results if 'end_time' in r]
        
        start_time = min(start_times) if start_times else None
        end_time = max(end_times) if end_times else None
        
        return cls(
            total_traces=len(results),
            executed_traces=len([r for r in results if 'success' in r]),
            successful_traces=success_count,
            failed_traces=fail_count,
            timeout_traces=len([r for r in results if r.get('timeout', False)]),
            total_duration=sum(durations) if durations else 0.0,
            avg_duration=statistics.mean(durations) if durations else 0.0,
            min_duration=min(durations) if durations else 0.0,
            max_duration=max(durations) if durations else 0.0,
            start_time=start_time,
            end_time=end_time
        )


@dataclass
class ValidationMetrics:
    """Validation metrics for reporting."""
    total_files: int = 0
    validated_files: int = 0
    valid_files: int = 0
    invalid_files: int = 0
    validation_errors: List[str] = None
    avg_validation_time: float = 0.0
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
    
    @classmethod
    def from_validation_results(cls, results: List[Dict[str, Any]]) -> 'ValidationMetrics':
        """Create metrics from validation results."""
        if not results:
            return cls()
        
        valid_count = sum(1 for r in results if r.get('valid', False))
        errors = []
        for r in results:
            if 'errors' in r:
                errors.extend(r['errors'])
        
        validation_times = [r.get('validation_time', 0) for r in results if 'validation_time' in r]
        avg_time = statistics.mean(validation_times) if validation_times else 0.0
        
        return cls(
            total_files=len(results),
            validated_files=len(results),
            valid_files=valid_count,
            invalid_files=len(results) - valid_count,
            validation_errors=errors,
            avg_validation_time=avg_time
        )


@dataclass
class GenerationMetrics:
    """Generation metrics for reporting."""
    mlir_files_generated: int = 0
    traces_generated: int = 0
    total_operations: int = 0
    successful_generations: int = 0
    failed_generations: int = 0
    generation_time: float = 0.0
    dialects_used: List[str] = None
    operation_categories: Dict[str, int] = None
    
    def __post_init__(self):
        if self.dialects_used is None:
            self.dialects_used = []
        if self.operation_categories is None:
            self.operation_categories = {}
    
    @classmethod
    def from_generation_results(cls, results: Dict[str, Any]) -> 'GenerationMetrics':
        """Create metrics from generation results."""
        stats = results.get('statistics', {})
        return cls(
            mlir_files_generated=stats.get('mlir_files_generated', 0),
            traces_generated=stats.get('traces_generated', 0),
            total_operations=stats.get('total_operations', 0),
            successful_generations=stats.get('successful_generations', 0),
            failed_generations=stats.get('failed_generations', 0),
            generation_time=stats.get('generation_time', 0.0),
            dialects_used=stats.get('dialects_used', []),
            operation_categories=stats.get('operation_categories', {})
        )


class ReportGenerator:
    """Generate comprehensive reports from DAP Trace Library results."""
    
    def __init__(self, output_dir: Union[str, Path] = None):
        """Initialize report generator.
        
        Args:
            output_dir: Directory to save reports (default: current directory)
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Report data storage
        self.execution_metrics: Optional[ExecutionMetrics] = None
        self.validation_metrics: Optional[ValidationMetrics] = None
        self.generation_metrics: Optional[GenerationMetrics] = None
        self.additional_data: Dict[str, Any] = {}
    
    def add_execution_results(self, results: List[Dict[str, Any]]) -> None:
        """Add execution results for reporting.
        
        Args:
            results: List of execution result dictionaries
        """
        self.execution_metrics = ExecutionMetrics.from_execution_results(results)
    
    def add_validation_results(self, results: List[Dict[str, Any]]) -> None:
        """Add validation results for reporting.
        
        Args:
            results: List of validation result dictionaries
        """
        self.validation_metrics = ValidationMetrics.from_validation_results(results)
    
    def add_generation_results(self, results: Dict[str, Any]) -> None:
        """Add generation results for reporting.
        
        Args:
            results: Generation results dictionary
        """
        self.generation_metrics = GenerationMetrics.from_generation_results(results)
    
    def add_custom_data(self, key: str, data: Any) -> None:
        """Add custom data to the report.
        
        Args:
            key: Key for the custom data
            data: Custom data (must be JSON serializable)
        """
        self.additional_data[key] = data
    
    def generate_report(self, format: ReportFormat = ReportFormat.MARKDOWN,
                       filename: str = None) -> Path:
        """Generate and save a report.
        
        Args:
            format: Report format (JSON, YAML, Markdown, HTML)
            filename: Output filename (default: report_{timestamp}.{format})
            
        Returns:
            Path to the generated report file
        """
        # Prepare report data
        report_data = self._prepare_report_data()
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.{format.value}"
        
        output_path = self.output_dir / filename
        
        # Generate report based on format
        if format == ReportFormat.JSON:
            self._generate_json_report(report_data, output_path)
        elif format == ReportFormat.YAML:
            self._generate_yaml_report(report_data, output_path)
        elif format == ReportFormat.MARKDOWN:
            self._generate_markdown_report(report_data, output_path)
        elif format == ReportFormat.HTML:
            self._generate_html_report(report_data, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Generated report: {output_path}")
        return output_path
    
    def _prepare_report_data(self) -> Dict[str, Any]:
        """Prepare report data from all metrics."""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "report_version": "1.0",
            "summary": self._generate_summary()
        }
        
        # Add metrics if available
        if self.execution_metrics:
            report_data["execution_metrics"] = asdict(self.execution_metrics)
        
        if self.validation_metrics:
            report_data["validation_metrics"] = asdict(self.validation_metrics)
        
        if self.generation_metrics:
            report_data["generation_metrics"] = asdict(self.generation_metrics)
        
        # Add custom data
        if self.additional_data:
            report_data["custom_data"] = self.additional_data
        
        return report_data
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of all metrics."""
        summary = {
            "total_execution_time": 0.0,
            "total_files_processed": 0,
            "success_rate": 0.0,
            "overall_status": "UNKNOWN"
        }
        
        # Calculate totals
        if self.execution_metrics:
            summary["total_execution_time"] = self.execution_metrics.total_duration
            if self.execution_metrics.executed_traces > 0:
                summary["execution_success_rate"] = (
                    self.execution_metrics.successful_traces / 
                    self.execution_metrics.executed_traces * 100
                )
        
        if self.validation_metrics:
            summary["total_files_processed"] += self.validation_metrics.total_files
            if self.validation_metrics.validated_files > 0:
                summary["validation_success_rate"] = (
                    self.validation_metrics.valid_files / 
                    self.validation_metrics.validated_files * 100
                )
        
        if self.generation_metrics:
            summary["mlir_files_generated"] = self.generation_metrics.mlir_files_generated
            summary["traces_generated"] = self.generation_metrics.traces_generated
        
        # Determine overall status
        success_rates = []
        if 'execution_success_rate' in summary:
            success_rates.append(summary['execution_success_rate'])
        if 'validation_success_rate' in summary:
            success_rates.append(summary['validation_success_rate'])
        
        if success_rates:
            avg_success_rate = statistics.mean(success_rates)
            if avg_success_rate >= 90:
                summary["overall_status"] = "EXCELLENT"
            elif avg_success_rate >= 75:
                summary["overall_status"] = "GOOD"
            elif avg_success_rate >= 50:
                summary["overall_status"] = "FAIR"
            else:
                summary["overall_status"] = "POOR"
            summary["overall_success_rate"] = avg_success_rate
        
        return summary
    
    def _generate_json_report(self, data: Dict[str, Any], output_path: Path) -> None:
        """Generate JSON report."""
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _generate_yaml_report(self, data: Dict[str, Any], output_path: Path) -> None:
        """Generate YAML report."""
        with open(output_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def _generate_markdown_report(self, data: Dict[str, Any], output_path: Path) -> None:
        """Generate Markdown report."""
        markdown_content = self._format_markdown(data)
        with open(output_path, 'w') as f:
            f.write(markdown_content)
    
    def _generate_html_report(self, data: Dict[str, Any], output_path: Path) -> None:
        """Generate HTML report."""
        html_content = self._format_html(data)
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def _format_markdown(self, data: Dict[str, Any]) -> str:
        """Format data as Markdown."""
        lines = [
            "# DAP Trace Library Report",
            f"**Generated**: {data['timestamp']}",
            f"**Report Version**: {data['report_version']}",
            "",
            "## Summary",
            ""
        ]
        
        summary = data['summary']
        lines.append(f"- **Overall Status**: {summary['overall_status']}")
        if 'overall_success_rate' in summary:
            lines.append(f"- **Overall Success Rate**: {summary['overall_success_rate']:.1f}%")
        lines.append(f"- **Total Execution Time**: {summary['total_execution_time']:.2f}s")
        lines.append(f"- **Total Files Processed**: {summary['total_files_processed']}")
        
        if 'execution_success_rate' in summary:
            lines.append(f"- **Execution Success Rate**: {summary['execution_success_rate']:.1f}%")
        if 'validation_success_rate' in summary:
            lines.append(f"- **Validation Success Rate**: {summary['validation_success_rate']:.1f}%")
        
        if 'mlir_files_generated' in summary:
            lines.append(f"- **MLIR Files Generated**: {summary['mlir_files_generated']}")
        if 'traces_generated' in summary:
            lines.append(f"- **Traces Generated**: {summary['traces_generated']}")
        
        # Add detailed metrics sections
        if 'execution_metrics' in data:
            lines.extend(self._format_execution_metrics_markdown(data['execution_metrics']))
        
        if 'validation_metrics' in data:
            lines.extend(self._format_validation_metrics_markdown(data['validation_metrics']))
        
        if 'generation_metrics' in data:
            lines.extend(self._format_generation_metrics_markdown(data['generation_metrics']))
        
        return '\n'.join(lines)
    
    def _format_execution_metrics_markdown(self, metrics: Dict[str, Any]) -> List[str]:
        """Format execution metrics as Markdown."""
        if not metrics:
            return []
        
        lines = [
            "",
            "## Execution Metrics",
            "",
            f"- **Total Traces**: {metrics.get('total_traces', 0)}",
            f"- **Executed Traces**: {metrics.get('executed_traces', 0)}",
            f"- **Successful Traces**: {metrics.get('successful_traces', 0)}",
            f"- **Failed Traces**: {metrics.get('failed_traces', 0)}",
            f"- **Timeout Traces**: {metrics.get('timeout_traces', 0)}",
            f"- **Total Duration**: {metrics.get('total_duration', 0.0):.2f}s",
            f"- **Average Duration**: {metrics.get('avg_duration', 0.0):.3f}s",
            f"- **Min Duration**: {metrics.get('min_duration', 0.0):.3f}s",
            f"- **Max Duration**: {metrics.get('max_duration', 0.0):.3f}s",
        ]
        
        start_time = metrics.get('start_time')
        if start_time:
            lines.append(f"- **Start Time**: {start_time}")
        end_time = metrics.get('end_time')
        if end_time:
            lines.append(f"- **End Time**: {end_time}")
        
        return lines
    
    def _format_validation_metrics_markdown(self, metrics: Dict[str, Any]) -> List[str]:
        """Format validation metrics as Markdown."""
        if not metrics:
            return []
        
        lines = [
            "",
            "## Validation Metrics",
            "",
            f"- **Total Files**: {metrics.get('total_files', 0)}",
            f"- **Validated Files**: {metrics.get('validated_files', 0)}",
            f"- **Valid Files**: {metrics.get('valid_files', 0)}",
            f"- **Invalid Files**: {metrics.get('invalid_files', 0)}",
            f"- **Average Validation Time**: {metrics.get('avg_validation_time', 0.0):.3f}s",
        ]
        
        validation_errors = metrics.get('validation_errors', [])
        if validation_errors:
            lines.append("")
            lines.append("### Validation Errors")
            for error in validation_errors[:10]:  # Show first 10 errors
                lines.append(f"- {error}")
            if len(validation_errors) > 10:
                lines.append(f"- ... and {len(validation_errors) - 10} more errors")
        
        return lines
    
    def _format_generation_metrics_markdown(self, metrics: Dict[str, Any]) -> List[str]:
        """Format generation metrics as Markdown."""
        if not metrics:
            return []
        
        lines = [
            "",
            "## Generation Metrics",
            "",
            f"- **MLIR Files Generated**: {metrics.get('mlir_files_generated', 0)}",
            f"- **Traces Generated**: {metrics.get('traces_generated', 0)}",
            f"- **Total Operations**: {metrics.get('total_operations', 0)}",
            f"- **Successful Generations**: {metrics.get('successful_generations', 0)}",
            f"- **Failed Generations**: {metrics.get('failed_generations', 0)}",
            f"- **Generation Time**: {metrics.get('generation_time', 0.0):.2f}s",
        ]
        
        dialects_used = metrics.get('dialects_used', [])
        if dialects_used:
            lines.append(f"- **Dialects Used**: {', '.join(dialects_used)}")
        
        return lines