#!/usr/bin/env python3
"""
Visualization module for DAP Trace Library.

Creates charts and visualizations from execution results, validation results,
and generation statistics. Supports multiple output formats.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import asdict

logger = logging.getLogger(__name__)

# Try to import matplotlib, but handle missing dependency gracefully
try:
    import matplotlib.pyplot as plt
    import matplotlib
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
    
    # Use non-interactive backend for server environments
    matplotlib.use('Agg')
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available. Visualization features will be limited.")


class VisualizationGenerator:
    """Generate visualizations from DAP Trace Library results."""
    
    def __init__(self, output_dir: Union[str, Path] = None):
        """Initialize visualization generator.
        
        Args:
            output_dir: Directory to save visualizations (default: current directory)
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Style configuration
        if MATPLOTLIB_AVAILABLE:
            plt.style.use('seaborn-v0_8-darkgrid')
            self.colors = plt.cm.Set3(np.linspace(0, 1, 12))
        else:
            # Default colors when matplotlib is not available
            self.colors = [
                (0.55, 0.71, 0.0, 1.0),   # Green
                (1.0, 0.5, 0.0, 1.0),     # Orange
                (0.0, 0.63, 0.91, 1.0),   # Blue
                (0.91, 0.0, 0.04, 1.0),   # Red
                (0.58, 0.0, 0.83, 1.0),   # Purple
                (0.0, 0.82, 0.8, 1.0),    # Cyan
                (0.98, 0.75, 0.0, 1.0),   # Yellow
                (0.0, 0.42, 0.24, 1.0),   # Dark Green
                (0.64, 0.0, 0.0, 1.0),    # Dark Red
                (0.0, 0.0, 0.46, 1.0),    # Dark Blue
                (0.45, 0.31, 0.59, 1.0),  # Purple Gray
                (0.5, 0.5, 0.5, 1.0)      # Gray
            ]
    
    def create_execution_summary_chart(self, execution_metrics: Dict[str, Any],
                                      filename: str = "execution_summary.png") -> Path:
        """Create a summary chart of execution metrics.
        
        Args:
            execution_metrics: Execution metrics dictionary
            filename: Output filename
            
        Returns:
            Path to the generated chart, or None if matplotlib not available
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping chart generation.")
            return None
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Pie chart for trace outcomes
        trace_labels = ['Successful', 'Failed', 'Timeout']
        trace_sizes = [
            execution_metrics.get('successful_traces', 0),
            execution_metrics.get('failed_traces', 0),
            execution_metrics.get('timeout_traces', 0)
        ]
        
        # Filter out zero values
        filtered_labels = []
        filtered_sizes = []
        filtered_colors = []
        for label, size, color in zip(trace_labels, trace_sizes, self.colors[:3]):
            if size > 0:
                filtered_labels.append(f"{label}\n({size})")
                filtered_sizes.append(size)
                filtered_colors.append(color)
        
        if filtered_sizes:
            axes[0].pie(filtered_sizes, labels=filtered_labels, colors=filtered_colors,
                       autopct='%1.1f%%', startangle=90)
            axes[0].set_title('Trace Execution Outcomes')
        else:
            axes[0].text(0.5, 0.5, 'No execution data', ha='center', va='center')
            axes[0].set_title('Trace Execution Outcomes')
        
        # Bar chart for duration statistics
        duration_labels = ['Total', 'Average', 'Min', 'Max']
        duration_values = [
            execution_metrics.get('total_duration', 0),
            execution_metrics.get('avg_duration', 0),
            execution_metrics.get('min_duration', 0),
            execution_metrics.get('max_duration', 0)
        ]
        
        bars = axes[1].bar(duration_labels, duration_values, color=self.colors[3:7])
        axes[1].set_title('Duration Statistics (seconds)')
        axes[1].set_ylabel('Seconds')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                axes[1].text(bar.get_x() + bar.get_width()/2., height,
                            f'{height:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created execution summary chart: {output_path}")
        return output_path
    
    def create_validation_summary_chart(self, validation_metrics: Dict[str, Any],
                                       filename: str = "validation_summary.png") -> Path:
        """Create a summary chart of validation metrics.
        
        Args:
            validation_metrics: Validation metrics dictionary
            filename: Output filename
            
        Returns:
            Path to the generated chart, or None if matplotlib not available
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping chart generation.")
            return None
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Bar chart for file validation results
        file_labels = ['Total', 'Validated', 'Valid', 'Invalid']
        file_values = [
            validation_metrics.get('total_files', 0),
            validation_metrics.get('validated_files', 0),
            validation_metrics.get('valid_files', 0),
            validation_metrics.get('invalid_files', 0)
        ]
        
        bars = axes[0].bar(file_labels, file_values, color=self.colors[:4])
        axes[0].set_title('File Validation Results')
        axes[0].set_ylabel('Number of Files')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            axes[0].text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
        
        # Pie chart for validation success rate
        if validation_metrics.get('validated_files', 0) > 0:
            valid_pct = (validation_metrics.get('valid_files', 0) / 
                        validation_metrics.get('validated_files', 0) * 100)
            invalid_pct = 100 - valid_pct
            
            sizes = [valid_pct, invalid_pct]
            labels = [f'Valid\n{valid_pct:.1f}%', f'Invalid\n{invalid_pct:.1f}%']
            colors = [self.colors[4], self.colors[5]]
            
            axes[1].pie(sizes, labels=labels, colors=colors, autopct='', startangle=90)
            axes[1].set_title('Validation Success Rate')
        else:
            axes[1].text(0.5, 0.5, 'No validation data', ha='center', va='center')
            axes[1].set_title('Validation Success Rate')
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created validation summary chart: {output_path}")
        return output_path
    
    def create_generation_summary_chart(self, generation_metrics: Dict[str, Any],
                                       filename: str = "generation_summary.png") -> Path:
        """Create a summary chart of generation metrics.
        
        Args:
            generation_metrics: Generation metrics dictionary
            filename: Output filename
            
        Returns:
            Path to the generated chart, or None if matplotlib not available
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping chart generation.")
            return None
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Bar chart for generation statistics
        gen_labels = ['MLIR Files', 'Traces', 'Operations']
        gen_values = [
            generation_metrics.get('mlir_files_generated', 0),
            generation_metrics.get('traces_generated', 0),
            generation_metrics.get('total_operations', 0)
        ]
        
        bars = axes[0].bar(gen_labels, gen_values, color=self.colors[6:9])
        axes[0].set_title('Generation Statistics')
        axes[0].set_ylabel('Count')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            axes[0].text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
        
        # Dialects used (if available)
        dialects = generation_metrics.get('dialects_used', [])
        if dialects:
            dialect_counts = {}
            for dialect in dialects:
                dialect_counts[dialect] = dialect_counts.get(dialect, 0) + 1
            
            dialect_names = list(dialect_counts.keys())
            dialect_values = list(dialect_counts.values())
            
            bars = axes[1].bar(dialect_names, dialect_values, color=self.colors[9:])
            axes[1].set_title('Dialects Used')
            axes[1].set_ylabel('Count')
            axes[1].tick_params(axis='x', rotation=45)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                axes[1].text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(height)}', ha='center', va='bottom')
        else:
            axes[1].text(0.5, 0.5, 'No dialect data', ha='center', va='center')
            axes[1].set_title('Dialects Used')
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created generation summary chart: {output_path}")
        return output_path
    
    def create_timeline_chart(self, execution_results: List[Dict[str, Any]],
                             filename: str = "execution_timeline.png") -> Path:
        """Create a timeline chart of execution events.
        
        Args:
            execution_results: List of execution result dictionaries
            filename: Output filename
            
        Returns:
            Path to the generated chart, or None if matplotlib not available
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping chart generation.")
            return None
        
        if not execution_results:
            logger.warning("No execution results for timeline chart")
            return None
        
        # Extract timeline data
        timelines = []
        labels = []
        colors = []
        
        for i, result in enumerate(execution_results[:20]):  # Limit to first 20 for clarity
            if 'start_time' in result and 'end_time' in result:
                try:
                    start = datetime.fromisoformat(result['start_time'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(result['end_time'].replace('Z', '+00:00'))
                    duration = (end - start).total_seconds()
                    
                    if duration > 0:
                        timelines.append((start, duration))
                        labels.append(f"Trace {i+1}")
                        colors.append(self.colors[i % len(self.colors)])
                except (ValueError, TypeError):
                    continue
        
        if not timelines:
            logger.warning("No valid timeline data found")
            return None
        
        # Create timeline chart
        fig, ax = plt.subplots(figsize=(12, max(4, len(timelines) * 0.3)))
        
        for i, (start, duration) in enumerate(timelines):
            ax.barh(i, duration, left=start, height=0.6, color=colors[i])
        
        ax.set_yticks(range(len(timelines)))
        ax.set_yticklabels(labels)
        ax.set_xlabel('Time')
        ax.set_title('Execution Timeline')
        
        # Format x-axis as time
        ax.xaxis_date()
        fig.autofmt_xdate()
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created timeline chart: {output_path}")
        return output_path
    
    def create_error_distribution_chart(self, validation_metrics: Dict[str, Any],
                                       filename: str = "error_distribution.png") -> Path:
        """Create a chart showing error distribution.
        
        Args:
            validation_metrics: Validation metrics dictionary
            filename: Output filename
            
        Returns:
            Path to the generated chart, or None if matplotlib not available
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping chart generation.")
            return None
        
        errors = validation_metrics.get('validation_errors', [])
        if not errors:
            logger.warning("No errors for distribution chart")
            return None
        
        # Categorize errors
        error_categories = {}
        for error in errors:
            # Simple categorization based on error content
            if 'syntax' in error.lower():
                category = 'Syntax Errors'
            elif 'semantic' in error.lower():
                category = 'Semantic Errors'
            elif 'type' in error.lower():
                category = 'Type Errors'
            elif 'format' in error.lower():
                category = 'Format Errors'
            else:
                category = 'Other Errors'
            
            error_categories[category] = error_categories.get(category, 0) + 1
        
        # Create chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        categories = list(error_categories.keys())
        counts = list(error_categories.values())
        
        bars = ax.bar(categories, counts, color=self.colors[:len(categories)])
        ax.set_title('Error Distribution')
        ax.set_ylabel('Number of Errors')
        ax.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created error distribution chart: {output_path}")
        return output_path
    
    def create_comprehensive_dashboard(self, execution_metrics: Dict[str, Any],
                                      validation_metrics: Dict[str, Any],
                                      generation_metrics: Dict[str, Any],
                                      filename: str = "comprehensive_dashboard.png") -> Path:
        """Create a comprehensive dashboard with multiple charts.
        
        Args:
            execution_metrics: Execution metrics dictionary
            validation_metrics: Validation metrics dictionary
            generation_metrics: Generation metrics dictionary
            filename: Output filename
            
        Returns:
            Path to the generated dashboard, or None if matplotlib not available
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available. Skipping chart generation.")
            return None
        
        fig = plt.figure(figsize=(16, 12))
        
        # Create subplots grid
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Execution outcomes (top left)
        ax1 = fig.add_subplot(gs[0, 0])
        if execution_metrics:
            trace_labels = ['Successful', 'Failed', 'Timeout']
            trace_sizes = [
                execution_metrics.get('successful_traces', 0),
                execution_metrics.get('failed_traces', 0),
                execution_metrics.get('timeout_traces', 0)
            ]
            
            filtered_labels = []
            filtered_sizes = []
            for label, size in zip(trace_labels, trace_sizes):
                if size > 0:
                    filtered_labels.append(f"{label}\n({size})")
                    filtered_sizes.append(size)
            
            if filtered_sizes:
                ax1.pie(filtered_sizes, labels=filtered_labels, autopct='%1.1f%%')
            ax1.set_title('Execution Outcomes')
        
        # 2. Validation results (top middle)
        ax2 = fig.add_subplot(gs[0, 1])
        if validation_metrics:
            file_labels = ['Valid', 'Invalid']
            file_values = [
                validation_metrics.get('valid_files', 0),
                validation_metrics.get('invalid_files', 0)
            ]
            
            if sum(file_values) > 0:
                ax2.bar(file_labels, file_values, color=['green', 'red'])
                ax2.set_title('Validation Results')
                ax2.set_ylabel('Files')
        
        # 3. Generation statistics (top right)
        ax3 = fig.add_subplot(gs[0, 2])
        if generation_metrics:
            gen_labels = ['MLIR Files', 'Traces']
            gen_values = [
                generation_metrics.get('mlir_files_generated', 0),
                generation_metrics.get('traces_generated', 0)
            ]
            
            ax3.bar(gen_labels, gen_values)
            ax3.set_title('Generation Statistics')
            ax3.set_ylabel('Count')
        
        # 4. Duration statistics (middle row, full width)
        ax4 = fig.add_subplot(gs[1, :])
        if execution_metrics:
            duration_labels = ['Total', 'Average', 'Min', 'Max']
            duration_values = [
                execution_metrics.get('total_duration', 0),
                execution_metrics.get('avg_duration', 0),
                execution_metrics.get('min_duration', 0),
                execution_metrics.get('max_duration', 0)
            ]
            
            bars = ax4.bar(duration_labels, duration_values)
            ax4.set_title('Duration Statistics (seconds)')
            ax4.set_ylabel('Seconds')
        
        # 5. Dialects used (bottom left)
        ax5 = fig.add_subplot(gs[2, 0])
        if generation_metrics:
            dialects = generation_metrics.get('dialects_used', [])
            if dialects:
                dialect_counts = {}
                for dialect in dialects:
                    dialect_counts[dialect] = dialect_counts.get(dialect, 0) + 1
                
                dialect_names = list(dialect_counts.keys())
                dialect_values = list(dialect_counts.values())
                
                ax5.bar(dialect_names, dialect_values)
                ax5.set_title('Dialects Used')
                ax5.set_ylabel('Count')
                ax5.tick_params(axis='x', rotation=45)
        
        # 6. Operation categories (bottom middle)
        ax6 = fig.add_subplot(gs[2, 1])
        if generation_metrics:
            categories = generation_metrics.get('operation_categories', {})
            if categories:
                cat_names = list(categories.keys())
                cat_values = list(categories.values())
                
                ax6.bar(cat_names, cat_values)
                ax6.set_title('Operation Categories')
                ax6.set_ylabel('Count')
                ax6.tick_params(axis='x', rotation=45)
        
        # 7. Summary metrics (bottom right)
        ax7 = fig.add_subplot(gs[2, 2])
        ax7.axis('off')
        
        summary_text = "DAP Trace Library Dashboard\n\n"
        
