"""
Export Service for AAA Admin Monitoring

This service provides comprehensive export capabilities for dashboard data,
including CSV exports, PDF reports, and scheduled report generation.

Sprint 2.3 Features:
- CSV data export
- PDF report generation
- Professional report templates
- Scheduled report delivery
- Multi-format export support
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from app.utils.saved_questions_db import DB_FILE
from app.services.dashboard_service import DashboardService
from app.services.learning_analytics import LearningAnalyticsService
from app.services.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)

# Try to import reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available - PDF export will be disabled")


@dataclass
class ExportRequest:
    """Export request configuration."""

    export_type: str  # 'csv', 'pdf', 'json'
    # ['health', 'performance', 'learning', 'benchmarks']
    data_types: List[str]
    time_period: int  # days
    format_options: Dict[str, Any]
    recipient_email: Optional[str] = None
    schedule: Optional[str] = None  # 'daily', 'weekly', 'monthly'


@dataclass
class ExportResult:
    """Export operation result."""

    export_id: str
    export_type: str
    file_path: Optional[str]
    file_content: Optional[bytes]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    metadata: Dict[str, Any]


class ExportService:
    """Service for data export and report generation."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the export service.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self.dashboard_service = DashboardService(db_path)
        self.analytics_service = LearningAnalyticsService(db_path)
        self.benchmark_service = BenchmarkService(db_path)

        # Create export directory
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)

    def export_data(self, request: ExportRequest) -> ExportResult:
        """Export data based on the request configuration.

        Args:
            request: Export request configuration

        Returns:
            Export result with file path or content
        """
        export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            logger.info(f"Starting export: {export_id}, type: {request.export_type}")

            # Collect data based on request
            data = self._collect_export_data(request)

            # Generate export based on type
            if request.export_type == "csv":
                result = self._export_csv(export_id, data, request)
            elif request.export_type == "pdf":
                result = self._export_pdf(export_id, data, request)
            elif request.export_type == "json":
                result = self._export_json(export_id, data, request)
            else:
                raise ValueError(f"Unsupported export type: {request.export_type}")

            logger.info(f"Export completed successfully: {export_id}")
            return result

        except Exception as e:
            logger.error(f"Export failed: {export_id}, error: {e}")
            return ExportResult(
                export_id=export_id,
                export_type=request.export_type,
                file_path=None,
                file_content=None,
                success=False,
                error_message=str(e),
                created_at=datetime.now(),
                metadata={},
            )

    def _collect_export_data(self, request: ExportRequest) -> Dict[str, Any]:
        """Collect data for export based on request."""
        data = {}

        try:
            if "health" in request.data_types:
                data["health"] = {
                    "current_status": self.dashboard_service.get_health_status(),
                    "timestamp": datetime.now().isoformat(),
                }

            if "performance" in request.data_types:
                # Get performance metrics from dashboard
                data["performance"] = {
                    "current_metrics": self.dashboard_service._get_current_metrics(),
                    "system_info": self.dashboard_service._get_system_info(),
                    "timestamp": datetime.now().isoformat(),
                }

            if "learning" in request.data_types:
                data["learning"] = {
                    "pattern_effectiveness": self.analytics_service.get_pattern_effectiveness(
                        request.time_period
                    ),
                    "correction_analysis": self.analytics_service.get_correction_analysis(
                        request.time_period
                    ),
                    "learning_progress": self.analytics_service.get_learning_progress(
                        request.time_period
                    ),
                    "user_feedback": self.analytics_service.get_user_feedback_analytics(
                        request.time_period
                    ),
                    "timestamp": datetime.now().isoformat(),
                }

            if "benchmarks" in request.data_types:
                benchmark_history = self.benchmark_service.get_benchmark_history(
                    request.time_period
                )
                data["benchmarks"] = {
                    "recent_suites": benchmark_history,
                    "summary": self._summarize_benchmarks(benchmark_history),
                    "timestamp": datetime.now().isoformat(),
                }

            return data

        except Exception as e:
            logger.error(f"Error collecting export data: {e}")
            raise

    def _summarize_benchmarks(self, benchmark_history: List) -> Dict[str, Any]:
        """Summarize benchmark history for export."""
        if not benchmark_history:
            return {}

        try:
            total_suites = len(benchmark_history)
            avg_score = (
                sum(suite.performance_score for suite in benchmark_history)
                / total_suites
            )
            avg_duration = (
                sum(suite.avg_duration_ms for suite in benchmark_history) / total_suites
            )

            return {
                "total_suites": total_suites,
                "avg_performance_score": avg_score,
                "avg_duration_ms": avg_duration,
                "latest_score": (
                    benchmark_history[0].performance_score if benchmark_history else 0
                ),
                "trend": (
                    "improving"
                    if len(benchmark_history) > 1
                    and benchmark_history[0].performance_score
                    > benchmark_history[-1].performance_score
                    else "stable"
                ),
            }

        except Exception as e:
            logger.error(f"Error summarizing benchmarks: {e}")
            return {}

    def _export_csv(
        self, export_id: str, data: Dict[str, Any], request: ExportRequest
    ) -> ExportResult:
        """Export data as CSV format."""
        try:
            file_path = self.export_dir / f"{export_id}.csv"

            with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Write header
                writer.writerow(["Export ID", export_id])
                writer.writerow(["Generated", datetime.now().isoformat()])
                writer.writerow(["Time Period (days)", request.time_period])
                writer.writerow([])  # Empty row

                # Export each data type
                for data_type, data_content in data.items():
                    writer.writerow([f"=== {data_type.upper()} DATA ==="])

                    if data_type == "health":
                        self._write_health_csv(writer, data_content)
                    elif data_type == "performance":
                        self._write_performance_csv(writer, data_content)
                    elif data_type == "learning":
                        self._write_learning_csv(writer, data_content)
                    elif data_type == "benchmarks":
                        self._write_benchmarks_csv(writer, data_content)

                    writer.writerow([])  # Empty row between sections

            return ExportResult(
                export_id=export_id,
                export_type="csv",
                file_path=str(file_path),
                file_content=None,
                success=True,
                error_message=None,
                created_at=datetime.now(),
                metadata={"file_size": file_path.stat().st_size},
            )

        except Exception as e:
            logger.error(f"CSV export error: {e}")
            raise

    def _write_health_csv(self, writer, health_data):
        """Write health data to CSV."""
        writer.writerow(["Component", "Status", "Details"])

        health_status = health_data["current_status"]
        for component, details in health_status.components.items():
            writer.writerow([component, details.get("status", "unknown"), str(details)])

        writer.writerow([])
        writer.writerow(["Overall Status", health_status.overall_status])
        writer.writerow(["Last Updated", health_status.last_updated])

    def _write_performance_csv(self, writer, performance_data):
        """Write performance data to CSV."""
        writer.writerow(["Metric", "Value", "Unit"])

        current_metrics = performance_data["current_metrics"]
        for metric, value in current_metrics.items():
            writer.writerow([metric, value, ""])

    def _write_learning_csv(self, writer, learning_data):
        """Write learning data to CSV."""
        # Pattern effectiveness
        writer.writerow(["=== PATTERN EFFECTIVENESS ==="])
        writer.writerow(
            ["Pattern ID", "Type", "Success Rate", "Total Applications", "Trend"]
        )

        for pattern in learning_data["pattern_effectiveness"]:
            writer.writerow(
                [
                    pattern.pattern_id,
                    pattern.pattern_type,
                    f"{pattern.success_rate:.2%}",
                    pattern.total_applications,
                    pattern.trend,
                ]
            )

        writer.writerow([])

        # Correction analysis
        writer.writerow(["=== CORRECTION ANALYSIS ==="])
        correction_analysis = learning_data["correction_analysis"]
        writer.writerow(["Total Corrections", correction_analysis.total_corrections])
        writer.writerow(
            ["Successful Corrections", correction_analysis.successful_corrections]
        )
        writer.writerow(["Success Rate", f"{correction_analysis.success_rate:.2%}"])
        writer.writerow(
            [
                "Avg Time to Success (min)",
                f"{correction_analysis.avg_time_to_success:.1f}",
            ]
        )

    def _write_benchmarks_csv(self, writer, benchmark_data):
        """Write benchmark data to CSV."""
        writer.writerow(
            [
                "Suite ID",
                "Started At",
                "Performance Score",
                "Total Tests",
                "Success Rate",
            ]
        )

        for suite in benchmark_data["recent_suites"]:
            success_rate = (
                suite.successful_tests / suite.total_tests
                if suite.total_tests > 0
                else 0
            )
            writer.writerow(
                [
                    suite.suite_id,
                    suite.started_at.isoformat(),
                    f"{suite.performance_score:.1f}",
                    suite.total_tests,
                    f"{success_rate:.2%}",
                ]
            )

    def _export_pdf(
        self, export_id: str, data: Dict[str, Any], request: ExportRequest
    ) -> ExportResult:
        """Export data as PDF report."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF export")

        try:
            file_path = self.export_dir / f"{export_id}.pdf"

            # Create PDF document
            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18,
            )

            # Build story (content)
            story = []
            styles = getSampleStyleSheet()

            # Title page
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # Center
            )

            story.append(Paragraph("AAA System Monitoring Report", title_style))
            story.append(Spacer(1, 20))

            # Report metadata
            story.append(Paragraph(f"<b>Report ID:</b> {export_id}", styles["Normal"]))
            story.append(
                Paragraph(
                    f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Time Period:</b> {request.time_period} days", styles["Normal"]
                )
            )
            story.append(Spacer(1, 30))

            # Add sections for each data type
            for data_type, data_content in data.items():
                if data_type == "health":
                    self._add_health_pdf_section(story, data_content, styles)
                elif data_type == "performance":
                    self._add_performance_pdf_section(story, data_content, styles)
                elif data_type == "learning":
                    self._add_learning_pdf_section(story, data_content, styles)
                elif data_type == "benchmarks":
                    self._add_benchmarks_pdf_section(story, data_content, styles)

                story.append(PageBreak())

            # Build PDF
            doc.build(story)

            return ExportResult(
                export_id=export_id,
                export_type="pdf",
                file_path=str(file_path),
                file_content=None,
                success=True,
                error_message=None,
                created_at=datetime.now(),
                metadata={"file_size": file_path.stat().st_size},
            )

        except Exception as e:
            logger.error(f"PDF export error: {e}")
            raise

    def _add_health_pdf_section(self, story, health_data, styles):
        """Add health section to PDF."""
        story.append(Paragraph("System Health Status", styles["Heading1"]))
        story.append(Spacer(1, 12))

        health_status = health_data["current_status"]

        # Overall status
        status_color = (
            colors.green if health_status.overall_status == "healthy" else colors.red
        )
        story.append(
            Paragraph(
                f"<b>Overall Status:</b> <font color='{status_color}'>{health_status.overall_status.upper()}</font>",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 12))

        # Component status table
        component_data = [["Component", "Status", "Details"]]
        for component, details in health_status.components.items():
            status = details.get("status", "unknown")
            component_data.append(
                [component.title(), status, str(details.get("icon", ""))]
            )

        component_table = Table(component_data)
        component_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(component_table)
        story.append(Spacer(1, 20))

        # Recommendations
        if health_status.recommendations:
            story.append(Paragraph("Recommendations:", styles["Heading2"]))
            for rec in health_status.recommendations:
                story.append(Paragraph(f"• {rec}", styles["Normal"]))
            story.append(Spacer(1, 12))

    def _add_performance_pdf_section(self, story, performance_data, styles):
        """Add performance section to PDF."""
        story.append(Paragraph("Performance Metrics", styles["Heading1"]))
        story.append(Spacer(1, 12))

        # Current metrics table
        metrics_data = [["Metric", "Value"]]
        current_metrics = performance_data["current_metrics"]

        for metric, value in current_metrics.items():
            if isinstance(value, float):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            metrics_data.append([metric.replace("_", " ").title(), formatted_value])

        metrics_table = Table(metrics_data)
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(metrics_table)

    def _add_learning_pdf_section(self, story, learning_data, styles):
        """Add learning analytics section to PDF."""
        story.append(Paragraph("Learning System Analytics", styles["Heading1"]))
        story.append(Spacer(1, 12))

        # Learning progress summary
        progress = learning_data["learning_progress"]
        story.append(
            Paragraph(
                f"<b>Overall Learning Rate:</b> {progress.overall_learning_rate:.1%}",
                styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"<b>Patterns Learned:</b> {progress.patterns_learned}",
                styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"<b>Learning Velocity:</b> {progress.learning_velocity:.1f} patterns/day",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 12))

        # Top patterns table
        story.append(Paragraph("Top Performing Patterns", styles["Heading2"]))
        pattern_data = [["Pattern ID", "Type", "Success Rate", "Applications"]]

        top_patterns = sorted(
            learning_data["pattern_effectiveness"],
            key=lambda p: p.success_rate,
            reverse=True,
        )[:10]

        for pattern in top_patterns:
            pattern_data.append(
                [
                    (
                        pattern.pattern_id[:20] + "..."
                        if len(pattern.pattern_id) > 20
                        else pattern.pattern_id
                    ),
                    pattern.pattern_type,
                    f"{pattern.success_rate:.1%}",
                    str(pattern.total_applications),
                ]
            )

        pattern_table = Table(pattern_data)
        pattern_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(pattern_table)

    def _add_benchmarks_pdf_section(self, story, benchmark_data, styles):
        """Add benchmarks section to PDF."""
        story.append(Paragraph("Performance Benchmarks", styles["Heading1"]))
        story.append(Spacer(1, 12))

        # Summary
        summary = benchmark_data["summary"]
        if summary:
            story.append(
                Paragraph(
                    f"<b>Total Benchmark Suites:</b> {summary['total_suites']}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Average Performance Score:</b> {summary['avg_performance_score']:.1f}/100",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Average Duration:</b> {summary['avg_duration_ms']:.1f}ms",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 12))

        # Recent benchmarks table
        story.append(Paragraph("Recent Benchmark Results", styles["Heading2"]))
        benchmark_data_table = [["Suite ID", "Date", "Score", "Tests", "Success Rate"]]

        for suite in benchmark_data["recent_suites"][:10]:  # Last 10 suites
            success_rate = (
                suite.successful_tests / suite.total_tests
                if suite.total_tests > 0
                else 0
            )
            benchmark_data_table.append(
                [
                    (
                        suite.suite_id[:20] + "..."
                        if len(suite.suite_id) > 20
                        else suite.suite_id
                    ),
                    suite.started_at.strftime("%Y-%m-%d"),
                    f"{suite.performance_score:.1f}",
                    str(suite.total_tests),
                    f"{success_rate:.1%}",
                ]
            )

        benchmark_table = Table(benchmark_data_table)
        benchmark_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(benchmark_table)

    def _export_json(
        self, export_id: str, data: Dict[str, Any], request: ExportRequest
    ) -> ExportResult:
        """Export data as JSON format."""
        try:
            file_path = self.export_dir / f"{export_id}.json"

            # Convert data to JSON-serializable format
            json_data = {
                "export_id": export_id,
                "generated_at": datetime.now().isoformat(),
                "time_period_days": request.time_period,
                "data_types": request.data_types,
                "data": self._serialize_for_json(data),
            }

            with open(file_path, "w", encoding="utf-8") as jsonfile:
                json.dump(json_data, jsonfile, indent=2, default=str)

            return ExportResult(
                export_id=export_id,
                export_type="json",
                file_path=str(file_path),
                file_content=None,
                success=True,
                error_message=None,
                created_at=datetime.now(),
                metadata={"file_size": file_path.stat().st_size},
            )

        except Exception as e:
            logger.error(f"JSON export error: {e}")
            raise

    def _serialize_for_json(self, data: Any) -> Any:
        """Convert data to JSON-serializable format."""
        if hasattr(data, "__dict__"):
            # Convert dataclass or object to dict
            return {k: self._serialize_for_json(v) for k, v in data.__dict__.items()}
        elif isinstance(data, dict):
            return {k: self._serialize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_json(item) for item in data]
        elif isinstance(data, (datetime,)):
            return data.isoformat()
        else:
            return data

    def get_export_templates(self) -> List[Dict[str, Any]]:
        """Get available export templates."""
        return [
            {
                "id": "executive_summary",
                "name": "Executive Summary",
                "description": "High-level overview for executives",
                "data_types": ["health", "performance"],
                "format": "pdf",
                "time_period": 7,
            },
            {
                "id": "technical_report",
                "name": "Technical Report",
                "description": "Detailed technical analysis",
                "data_types": ["health", "performance", "learning", "benchmarks"],
                "format": "pdf",
                "time_period": 30,
            },
            {
                "id": "learning_analytics",
                "name": "Learning Analytics Report",
                "description": "Focus on learning system performance",
                "data_types": ["learning"],
                "format": "pdf",
                "time_period": 30,
            },
            {
                "id": "performance_data",
                "name": "Performance Data Export",
                "description": "Raw performance data for analysis",
                "data_types": ["performance", "benchmarks"],
                "format": "csv",
                "time_period": 90,
            },
            {
                "id": "complete_export",
                "name": "Complete System Export",
                "description": "All available data in JSON format",
                "data_types": ["health", "performance", "learning", "benchmarks"],
                "format": "json",
                "time_period": 30,
            },
        ]
