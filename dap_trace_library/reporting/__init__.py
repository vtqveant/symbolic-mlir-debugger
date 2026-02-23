"""
Reporting module for DAP Trace Library.

This module provides comprehensive reporting, visualization, and coverage analysis
for DAP trace generation, validation, and execution results.
"""

from .report_generator import (
    ReportGenerator,
    ReportFormat,
    ExecutionMetrics,
    ValidationMetrics,
    GenerationMetrics,
)

from .visualization import VisualizationGenerator
from .coverage_analyzer import CoverageAnalyzer, CoverageType, CoverageMetric, OperationCoverage

__all__ = [
    # Report generator
    "ReportGenerator",
    "ReportFormat",
    "ExecutionMetrics",
    "ValidationMetrics",
    "GenerationMetrics",
    # Visualization
    "VisualizationGenerator",
    # Coverage analysis
    "CoverageAnalyzer",
    "CoverageType",
    "CoverageMetric",
    "OperationCoverage",
]

__version__ = "1.0.0"
