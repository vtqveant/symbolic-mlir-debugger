#!/usr/bin/env python3
"""
Coverage analyzer for DAP Trace Library.

Analyzes test coverage from execution results and generation statistics.
Provides insights into which operations, dialects, and paths are covered.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class CoverageType(Enum):
    """Types of coverage analysis."""

    OPERATION = "operation"
    DIALECT = "dialect"
    PATH = "path"
    CONSTRAINT = "constraint"
    TEMPLATE = "template"


@dataclass
class CoverageMetric:
    """Coverage metric for a specific type."""

    coverage_type: CoverageType
    total_items: int = 0
    covered_items: int = 0
    coverage_percentage: float = 0.0
    uncovered_items: List[str] = field(default_factory=list)

    def calculate_coverage(self) -> None:
        """Calculate coverage percentage."""
        if self.total_items > 0:
            self.coverage_percentage = (self.covered_items / self.total_items) * 100
        else:
            self.coverage_percentage = 0.0


@dataclass
class OperationCoverage:
    """Coverage information for a specific operation."""

    operation_name: str
    dialect: str
    total_test_cases: int = 0
    executed_test_cases: int = 0
    successful_test_cases: int = 0
    failed_test_cases: int = 0
    coverage_percentage: float = 0.0
    test_case_details: List[Dict[str, Any]] = field(default_factory=list)

    def update_coverage(self) -> None:
        """Update coverage percentage."""
        if self.total_test_cases > 0:
            self.coverage_percentage = (self.executed_test_cases / self.total_test_cases) * 100


class CoverageAnalyzer:
    """Analyze test coverage from DAP Trace Library results."""

    def __init__(self):
        """Initialize coverage analyzer."""
        self.operation_coverage: Dict[str, OperationCoverage] = {}
        self.dialect_coverage: Dict[str, CoverageMetric] = {}
        self.path_coverage: Dict[str, CoverageMetric] = {}
        self.constraint_coverage: Dict[str, CoverageMetric] = {}
        self.template_coverage: Dict[str, CoverageMetric] = {}

        # Track covered items
        self.covered_operations: Set[str] = set()
        self.covered_dialects: Set[str] = set()
        self.covered_paths: Set[str] = set()
        self.covered_constraints: Set[str] = set()
        self.covered_templates: Set[str] = set()

    def analyze_generation_coverage(self, generation_results: Dict[str, Any]) -> None:
        """Analyze coverage from generation results.

        Args:
            generation_results: Generation results dictionary
        """
        # Extract operation information
        operations = generation_results.get("operations", [])
        for op in operations:
            op_name = op.get("name", "unknown")
            dialect = op.get("dialect", "unknown")
            key = f"{dialect}.{op_name}"

            if key not in self.operation_coverage:
                self.operation_coverage[key] = OperationCoverage(
                    operation_name=op_name, dialect=dialect
                )

            # Update dialect coverage
            if dialect not in self.dialect_coverage:
                self.dialect_coverage[dialect] = CoverageMetric(coverage_type=CoverageType.DIALECT)
            self.dialect_coverage[dialect].total_items += 1

        # Extract template information
        templates = generation_results.get("templates_used", [])
        for template in templates:
            if template not in self.template_coverage:
                self.template_coverage[template] = CoverageMetric(
                    coverage_type=CoverageType.TEMPLATE
                )
            self.template_coverage[template].total_items += 1

    def analyze_execution_coverage(self, execution_results: List[Dict[str, Any]]) -> None:
        """Analyze coverage from execution results.

        Args:
            execution_results: List of execution result dictionaries
        """
        for result in execution_results:
            # Extract operation information from trace
            trace_data = result.get("trace_data", {})
            session = trace_data.get("session", [])

            for item in session:
                # Look for operation information
                if "operation" in item:
                    op_info = item["operation"]
                    op_name = op_info.get("name", "unknown")
                    dialect = op_info.get("dialect", "unknown")
                    key = f"{dialect}.{op_name}"

                    # Mark operation as covered
                    self.covered_operations.add(key)

                    # Update operation coverage
                    if key in self.operation_coverage:
                        self.operation_coverage[key].executed_test_cases += 1
                        if result.get("success", False):
                            self.operation_coverage[key].successful_test_cases += 1
                        else:
                            self.operation_coverage[key].failed_test_cases += 1

                        # Add test case details
                        self.operation_coverage[key].test_case_details.append(
                            {
                                "trace_id": result.get("trace_id", "unknown"),
                                "success": result.get("success", False),
                                "duration": result.get("duration", 0),
                                "errors": result.get("errors", []),
                            }
                        )

                    # Mark dialect as covered
                    self.covered_dialects.add(dialect)

                # Look for path information
                if "path_condition" in item:
                    path_id = item.get("path_id", "unknown")
                    self.covered_paths.add(path_id)

                # Look for constraint information
                if "constraints" in item:
                    constraints = item["constraints"]
                    for constraint in constraints:
                        self.covered_constraints.add(str(constraint))

    def calculate_coverage_metrics(self) -> Dict[str, Any]:
        """Calculate all coverage metrics.

        Returns:
            Dictionary with all coverage metrics
        """
        # Calculate operation coverage
        for op_coverage in self.operation_coverage.values():
            op_coverage.update_coverage()

        # Calculate dialect coverage
        for dialect, metric in self.dialect_coverage.items():
            metric.covered_items = 1 if dialect in self.covered_dialects else 0
            metric.calculate_coverage()
            if metric.covered_items == 0:
                metric.uncovered_items.append(dialect)

        # Calculate path coverage
        total_paths = len(self.path_coverage)
        covered_paths = len(self.covered_paths)
        path_coverage_metric = CoverageMetric(
            coverage_type=CoverageType.PATH, total_items=total_paths, covered_items=covered_paths
        )
        path_coverage_metric.calculate_coverage()

        # Calculate constraint coverage
        total_constraints = len(self.constraint_coverage)
        covered_constraints = len(self.covered_constraints)
        constraint_coverage_metric = CoverageMetric(
            coverage_type=CoverageType.CONSTRAINT,
            total_items=total_constraints,
            covered_items=covered_constraints,
        )
        constraint_coverage_metric.calculate_coverage()

        # Calculate template coverage
        for template, metric in self.template_coverage.items():
            metric.covered_items = 1 if template in self.covered_templates else 0
            metric.calculate_coverage()
            if metric.covered_items == 0:
                metric.uncovered_items.append(template)

        # Calculate overall coverage
        total_operations = len(self.operation_coverage)
        covered_operations = len(self.covered_operations)
        overall_coverage = CoverageMetric(
            coverage_type=CoverageType.OPERATION,
            total_items=total_operations,
            covered_items=covered_operations,
        )
        overall_coverage.calculate_coverage()

        # Identify uncovered operations
        for op_key in self.operation_coverage:
            if op_key not in self.covered_operations:
                overall_coverage.uncovered_items.append(op_key)

        return {
            "overall_coverage": overall_coverage,
            "dialect_coverage": self.dialect_coverage,
            "path_coverage": path_coverage_metric,
            "constraint_coverage": constraint_coverage_metric,
            "template_coverage": self.template_coverage,
            "operation_details": self.operation_coverage,
        }

    def generate_coverage_report(
        self, output_dir: Union[str, Path] = None, format: str = "markdown"
    ) -> Path:
        """Generate a coverage report.

        Args:
            output_dir: Directory to save the report
            format: Report format ('markdown', 'json', 'html')

        Returns:
            Path to the generated report
        """
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path.cwd()
        output_path.mkdir(parents=True, exist_ok=True)

        # Calculate metrics
        coverage_metrics = self.calculate_coverage_metrics()

        # Generate report based on format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            filename = f"coverage_report_{timestamp}.json"
            report_path = output_path / filename
            self._generate_json_report(coverage_metrics, report_path)
        elif format == "html":
            filename = f"coverage_report_{timestamp}.html"
            report_path = output_path / filename
            self._generate_html_report(coverage_metrics, report_path)
        else:  # Default to markdown
            filename = f"coverage_report_{timestamp}.md"
            report_path = output_path / filename
            self._generate_markdown_report(coverage_metrics, report_path)

        logger.info(f"Generated coverage report: {report_path}")
        return report_path

    def _generate_json_report(self, metrics: Dict[str, Any], output_path: Path) -> None:
        """Generate JSON coverage report."""
        # Convert dataclasses to dictionaries
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_coverage": asdict(metrics["overall_coverage"]),
            "dialect_coverage": {
                dialect: asdict(metric) for dialect, metric in metrics["dialect_coverage"].items()
            },
            "path_coverage": asdict(metrics["path_coverage"]),
            "constraint_coverage": asdict(metrics["constraint_coverage"]),
            "template_coverage": {
                template: asdict(metric)
                for template, metric in metrics["template_coverage"].items()
            },
            "operation_details": {
                op_key: asdict(op_coverage)
                for op_key, op_coverage in metrics["operation_details"].items()
            },
        }

        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2, default=str)

    def _generate_markdown_report(self, metrics: Dict[str, Any], output_path: Path) -> None:
        """Generate Markdown coverage report."""
        overall = metrics["overall_coverage"]

        lines = [
            "# DAP Trace Library Coverage Report",
            f"**Generated**: {datetime.now().isoformat()}",
            "",
            "## Overall Coverage",
            "",
            f"- **Total Operations**: {overall.total_items}",
            f"- **Covered Operations**: {overall.covered_items}",
            f"- **Coverage Percentage**: {overall.coverage_percentage:.1f}%",
            "",
        ]

        # Add coverage by dialect
        lines.append("## Coverage by Dialect")
        lines.append("")
        lines.append("| Dialect | Coverage | Covered/Total |")
        lines.append("|---------|----------|---------------|")

        for dialect, metric in metrics["dialect_coverage"].items():
            lines.append(
                f"| {dialect} | {metric.coverage_percentage:.1f}% | "
                f"{metric.covered_items}/{metric.total_items} |"
            )

        # Add operation details
        lines.append("")
        lines.append("## Operation Details")
        lines.append("")
        lines.append("| Operation | Dialect | Coverage | Test Cases | Success Rate |")
        lines.append("|-----------|---------|----------|------------|--------------|")

        for op_key, op_coverage in metrics["operation_details"].items():
            if op_coverage.total_test_cases > 0:
                success_rate = (
                    (op_coverage.successful_test_cases / op_coverage.executed_test_cases * 100)
                    if op_coverage.executed_test_cases > 0
                    else 0
                )
                lines.append(
                    f"| {op_coverage.operation_name} | {op_coverage.dialect} | "
                    f"{op_coverage.coverage_percentage:.1f}% | "
                    f"{op_coverage.executed_test_cases}/{op_coverage.total_test_cases} | "
                    f"{success_rate:.1f}% |"
                )

        # Add uncovered operations
        if overall.uncovered_items:
            lines.append("")
            lines.append("## Uncovered Operations")
            lines.append("")
            for op_key in overall.uncovered_items[:20]:  # Show first 20
                lines.append(f"- {op_key}")
            if len(overall.uncovered_items) > 20:
                lines.append(f"- ... and {len(overall.uncovered_items) - 20} more operations")

        # Add recommendations
        lines.append("")
        lines.append("## Recommendations")
        lines.append("")

        if overall.coverage_percentage < 50:
            lines.append("1. **Priority**: Focus on increasing overall coverage")
            lines.append("2. **Action**: Test uncovered operations from the list above")
            lines.append("3. **Goal**: Achieve at least 50% coverage")
        elif overall.coverage_percentage < 75:
            lines.append("1. **Priority**: Improve coverage of partially tested operations")
            lines.append("2. **Action**: Add more test cases for low-coverage operations")
            lines.append("3. **Goal**: Achieve at least 75% coverage")
        elif overall.coverage_percentage < 90:
            lines.append("1. **Priority**: Address edge cases and error conditions")
            lines.append("2. **Action**: Test boundary conditions and error paths")
            lines.append("3. **Goal**: Achieve at least 90% coverage")
        else:
            lines.append("1. **Priority**: Maintain high coverage")
            lines.append("2. **Action**: Add tests for any new operations")
            lines.append("3. **Goal**: Maintain >90% coverage")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

    def _generate_html_report(self, metrics: Dict[str, Any], output_path: Path) -> None:
        """Generate HTML coverage report."""
        overall = metrics["overall_coverage"]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DAP Trace Library Coverage Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #555; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .coverage-high {{ color: green; font-weight: bold; }}
                .coverage-medium {{ color: orange; font-weight: bold; }}
                .coverage-low {{ color: red; font-weight: bold; }}
                .summary {{ background-color: #e8f4f8; padding: 20px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>DAP Trace Library Coverage Report</h1>
            <p><strong>Generated</strong>: {datetime.now().isoformat()}</p>
            
            <div class="summary">
                <h2>Overall Coverage</h2>
                <p><strong>Total Operations</strong>: {overall.total_items}</p>
                <p><strong>Covered Operations</strong>: {overall.covered_items}</p>
                <p><strong>Coverage Percentage</strong>: 
                    <span class="{self._get_coverage_class(overall.coverage_percentage)}">
                        {overall.coverage_percentage:.1f}%
                    </span>
                </p>
            </div>
        """

        # Add coverage by dialect
        html += """
            <h2>Coverage by Dialect</h2>
            <table>
                <tr>
                    <th>Dialect</th>
                    <th>Coverage</th>
                    <th>Covered/Total</th>
                </tr>
        """

        for dialect, metric in metrics["dialect_coverage"].items():
            html += f"""
                <tr>
                    <td>{dialect}</td>
                    <td>
                        <span class="{self._get_coverage_class(metric.coverage_percentage)}">
                            {metric.coverage_percentage:.1f}%
                        </span>
                    </td>
                    <td>{metric.covered_items}/{metric.total_items}</td>
                </tr>
            """

        html += """
            </table>
            
            <h2>Operation Details</h2>
            <table>
                <tr>
                    <th>Operation</th>
                    <th>Dialect</th>
                    <th>Coverage</th>
                    <th>Test Cases</th>
                    <th>Success Rate</th>
                </tr>
        """

        for op_key, op_coverage in metrics["operation_details"].items():
            if op_coverage.total_test_cases > 0:
                success_rate = (
                    (op_coverage.successful_test_cases / op_coverage.executed_test_cases * 100)
                    if op_coverage.executed_test_cases > 0
                    else 0
                )
                html += f"""
                <tr>
                    <td>{op_coverage.operation_name}</td>
                    <td>{op_coverage.dialect}</td>
                    <td>
                        <span class="{self._get_coverage_class(op_coverage.coverage_percentage)}">
                            {op_coverage.coverage_percentage:.1f}%
                        </span>
                    </td>
                    <td>{op_coverage.executed_test_cases}/{op_coverage.total_test_cases}</td>
                    <td>{success_rate:.1f}%</td>
                </tr>
                """

        html += """
            </table>
        """

        # Add uncovered operations if any
        if overall.uncovered_items:
            html += """
            <h2>Uncovered Operations</h2>
            <ul>
            """

            for op_key in overall.uncovered_items[:20]:
                html += f"<li>{op_key}</li>"

            if len(overall.uncovered_items) > 20:
                html += f"<li>... and {len(overall.uncovered_items) - 20} more operations</li>"

            html += "</ul>"

        # Close HTML
        html += """
        </body>
        </html>
        """

        with open(output_path, "w") as f:
            f.write(html)

    def _get_coverage_class(self, percentage: float) -> str:
        """Get CSS class for coverage percentage.

        Args:
            percentage: Coverage percentage

        Returns:
            CSS class name
        """
        if percentage >= 80:
            return "coverage-high"
        elif percentage >= 50:
            return "coverage-medium"
        else:
            return "coverage-low"
