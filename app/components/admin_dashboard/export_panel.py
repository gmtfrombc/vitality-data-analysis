"""
Export Panel Component for Admin Dashboard

Provides user interface for data export and report generation.

Sprint 2.3 Features:
- Export template selection
- Custom export configuration
- Report generation interface
- Download management
"""

import panel as pn
import asyncio
import io
import os
from typing import Optional
import logging

from app.services.export_service import ExportService, ExportRequest, ExportResult

logger = logging.getLogger(__name__)

pn.extension("bokeh")


class ExportPanel:
    """Panel for data export and report generation."""

    def __init__(self, export_service: Optional[ExportService] = None):
        """Initialize the export panel.

        Args:
            export_service: Optional export service (for testing)
        """
        self.export_service = export_service or ExportService()

        # Track active downloads
        self.active_downloads = []

        # Create UI components
        self._create_components()

    def _create_components(self):
        """Create all UI components."""
        # Template selector
        templates = self.export_service.get_export_templates()
        template_options = {t["name"]: t["id"] for t in templates}

        self.template_selector = pn.widgets.Select(
            name="Report Template",
            value=list(template_options.values())[0],
            options=template_options,
            width=300,
        )

        # Template description
        self.template_description = pn.pane.HTML(
            self._get_template_description(list(template_options.values())[0]),
            width=300,
            height=60,
        )

        # Custom configuration
        self.data_type_selector = pn.widgets.CheckBoxGroup(
            name="Data Types",
            value=["health", "performance"],
            options=["health", "performance", "learning", "benchmarks"],
            inline=False,
        )

        self.format_selector = pn.widgets.RadioButtonGroup(
            name="Export Format",
            value="pdf",
            options=["csv", "pdf", "json"],
            button_type="primary",
        )

        self.time_period_slider = pn.widgets.IntSlider(
            name="Time Period (days)", value=30, start=7, end=90, step=7, width=300
        )

        # Export buttons
        self.export_button = pn.widgets.Button(
            name="Generate Report", button_type="primary", width=150
        )

        self.template_export_button = pn.widgets.Button(
            name="Use Template", button_type="success", width=150
        )

        # Benchmark button
        self.benchmark_button = pn.widgets.Button(
            name="Run Benchmark", button_type="light", width=150
        )

        # Cleanup button
        self.cleanup_button = pn.widgets.Button(
            name="Clear All Downloads", button_type="danger", width=150
        )

        # Status and results
        self.status_text = pn.pane.HTML("<p>Ready to generate reports</p>", width=600)

        self.download_container = pn.Column(width=600)

        # Bind events
        self.template_selector.param.watch(self._on_template_change, "value")
        self.export_button.on_click(self._on_custom_export)
        self.template_export_button.on_click(self._on_template_export)
        self.benchmark_button.on_click(self._on_run_benchmark)
        self.cleanup_button.on_click(self._on_cleanup_downloads)

    def _get_template_description(self, template_id: str) -> str:
        """Get description for a template."""
        templates = self.export_service.get_export_templates()
        template = next((t for t in templates if t["id"] == template_id), None)
        if template:
            return f"<p><small>{template['description']}</small></p>"
        return "<p><small>Template description not available</small></p>"

    def _on_template_change(self, event):
        """Handle template selection change."""
        try:
            templates = self.export_service.get_export_templates()
            selected_template = next(t for t in templates if t["id"] == event.new)

            # Update form with template values
            self.data_type_selector.value = selected_template["data_types"]
            self.format_selector.value = selected_template["format"]
            self.time_period_slider.value = selected_template["time_period"]

            # Update description
            self.template_description.object = self._get_template_description(event.new)

        except Exception as e:
            logger.error(f"Error updating template: {e}")

    def _on_custom_export(self, event):
        """Handle custom export button click."""
        try:
            self.status_text.object = "<p>🔄 Generating custom report...</p>"

            # Create export request
            request = ExportRequest(
                export_type=self.format_selector.value,
                data_types=self.data_type_selector.value,
                time_period=self.time_period_slider.value,
                format_options={},
            )

            # Run export in background
            asyncio.create_task(self._run_export(request, "Custom Report"))

        except Exception as e:
            logger.error(f"Error starting custom export: {e}")
            self.status_text.object = f"<p>❌ Error: {str(e)}</p>"

    def _on_template_export(self, event):
        """Handle template export button click."""
        try:
            self.status_text.object = "<p>🔄 Generating template report...</p>"

            # Get selected template
            templates = self.export_service.get_export_templates()
            selected_template = next(
                t for t in templates if t["id"] == self.template_selector.value
            )

            # Create export request from template
            request = ExportRequest(
                export_type=selected_template["format"],
                data_types=selected_template["data_types"],
                time_period=selected_template["time_period"],
                format_options={},
            )

            # Run export in background
            asyncio.create_task(self._run_export(request, selected_template["name"]))

        except Exception as e:
            logger.error(f"Error starting template export: {e}")
            self.status_text.object = f"<p>❌ Error: {str(e)}</p>"

    def _on_run_benchmark(self, event):
        """Handle benchmark button click."""
        try:
            self.status_text.object = "<p>🔄 Running performance benchmark...</p>"

            # Run benchmark in background
            asyncio.create_task(self._run_benchmark())

        except Exception as e:
            logger.error(f"Error starting benchmark: {e}")
            self.status_text.object = f"<p>❌ Error: {str(e)}</p>"

    async def _run_export(self, request: ExportRequest, report_name: str):
        """Run export operation asynchronously."""
        try:
            # Run export
            result = self.export_service.export_data(request)

            if result.success:
                self.status_text.object = (
                    f"<p>✅ {report_name} generated successfully!</p>"
                )

                # Add download link
                download_link = self._create_download_link(result, report_name)
                self.download_container.append(download_link)

                # Keep only last 5 downloads
                if len(self.download_container) > 5:
                    self.download_container.pop(0)

            else:
                self.status_text.object = (
                    f"<p>❌ Export failed: {result.error_message}</p>"
                )

        except Exception as e:
            logger.error(f"Error running export: {e}")
            self.status_text.object = f"<p>❌ Export error: {str(e)}</p>"

    async def _run_benchmark(self):
        """Run benchmark operation asynchronously."""
        try:
            # Import benchmark service here to avoid circular imports
            from app.services.benchmark_service import BenchmarkService

            benchmark_service = BenchmarkService()

            # Run benchmark suite
            suite = await benchmark_service.run_benchmark_suite("dashboard_initiated")

            self.status_text.object = f"""
            <p>✅ Benchmark completed!</p>
            <p><strong>Performance Score:</strong> {suite.performance_score:.1f}/100</p>
            <p><strong>Tests:</strong> {suite.successful_tests}/{suite.total_tests} passed</p>
            <p><strong>Average Duration:</strong> {suite.avg_duration_ms:.1f}ms</p>
            """

            # Add benchmark results as a "download"
            benchmark_summary = self._create_benchmark_summary(suite)
            self.download_container.append(benchmark_summary)

            # Keep only last 5 items
            if len(self.download_container) > 5:
                self.download_container.pop(0)

        except Exception as e:
            logger.error(f"Error running benchmark: {e}")
            self.status_text.object = f"<p>❌ Benchmark error: {str(e)}</p>"

    def _create_download_link(
        self, result: ExportResult, report_name: str
    ) -> pn.Column:
        """Create download widget for export result."""
        try:
            file_size_mb = result.metadata.get("file_size", 0) / (1024 * 1024)

            # Read file content for download
            file_content = None
            if result.file_path and os.path.exists(result.file_path):
                with open(result.file_path, "rb") as f:
                    file_content = f.read()

            # Create download widget
            download_widget = pn.widgets.FileDownload(
                label=f"📥 Download {report_name}",
                button_type="success",
                filename=(
                    os.path.basename(result.file_path)
                    if result.file_path
                    else f"{report_name}.{result.export_type}"
                ),
                file=io.BytesIO(file_content) if file_content else None,
                disabled=file_content is None,
                width=200,
            )

            # Create info panel
            info_html = f"""
            <div style="background: #f0f8ff; padding: 10px; border-radius: 5px; margin: 5px 0;">
                <h4 style="margin: 0 0 5px 0;">📄 {report_name}</h4>
                <p style="margin: 0; color: #666;">
                    Format: {result.export_type.upper()} | 
                    Size: {file_size_mb:.2f} MB | 
                    Generated: {result.created_at.strftime('%Y-%m-%d %H:%M')}
                </p>
                <p style="margin: 5px 0 0 0; color: #999; font-size: 12px;">
                    Export ID: {result.export_id}
                </p>
            </div>
            """

            info_panel = pn.pane.HTML(info_html, width=380)

            # Create delete button
            delete_button = pn.widgets.Button(
                name="🗑️ Delete", button_type="danger", width=80, height=30
            )

            # Store reference to container for deletion
            container = pn.Column(
                pn.Row(
                    info_panel,
                    pn.Column(download_widget, delete_button, width=200),
                    width=580,
                ),
                width=580,
            )

            # Bind delete button
            def delete_export(event):
                try:
                    # Remove file if it exists
                    if result.file_path and os.path.exists(result.file_path):
                        os.remove(result.file_path)

                    # Remove from UI
                    if container in self.download_container:
                        self.download_container.remove(container)

                    self.status_text.object = f"<p>✅ Deleted export: {report_name}</p>"
                except Exception as e:
                    logger.error(f"Error deleting export: {e}")
                    self.status_text.object = (
                        f"<p>❌ Error deleting export: {str(e)}</p>"
                    )

            delete_button.on_click(delete_export)

            return container

        except Exception as e:
            logger.error(f"Error creating download link: {e}")
            return pn.pane.HTML(
                f"<p>❌ Error creating download for {report_name}: {str(e)}</p>"
            )

    def _create_benchmark_summary(self, suite) -> pn.pane.HTML:
        """Create benchmark summary display."""
        try:
            # Get top recommendations
            top_recommendations = suite.recommendations[:3]
            rec_html = ""
            for rec in top_recommendations:
                rec_html += f"<li>{rec}</li>"

            summary_html = f"""
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0; border-left: 4px solid #007bff;">
                <h4 style="margin: 0 0 5px 0;">⚡ Benchmark Results</h4>
                <p style="margin: 0; color: #666;">
                    Suite: {suite.suite_id} | 
                    Score: {suite.performance_score:.1f}/100 | 
                    Duration: {suite.avg_duration_ms:.1f}ms
                </p>
                <p style="margin: 5px 0 0 0;"><strong>Top Recommendations:</strong></p>
                <ul style="margin: 5px 0 0 20px; padding: 0;">
                    {rec_html}
                </ul>
            </div>
            """

            return pn.pane.HTML(summary_html, width=580)

        except Exception as e:
            logger.error(f"Error creating benchmark summary: {e}")
            return pn.pane.HTML("<p>Error creating benchmark summary</p>")

    def _on_cleanup_downloads(self, event):
        """Handle cleanup button click."""
        try:
            self.status_text.object = "<p>🔄 Cleaning up downloads...</p>"

            # Clear all downloads from UI
            self.download_container.clear()

            # Also clean up old export files from disk
            import glob

            export_dir = self.export_service.export_dir
            export_files = (
                glob.glob(str(export_dir / "export_*.csv"))
                + glob.glob(str(export_dir / "export_*.pdf"))
                + glob.glob(str(export_dir / "export_*.json"))
            )

            deleted_count = 0
            for file_path in export_files:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Could not delete file {file_path}: {e}")

            self.status_text.object = (
                f"<p>✅ Cleared {deleted_count} export files from disk and UI!</p>"
            )

        except Exception as e:
            logger.error(f"Error cleaning up downloads: {e}")
            self.status_text.object = f"<p>❌ Error: {str(e)}</p>"

    def get_panel(self):
        """Get the complete export panel."""
        return pn.Column(
            pn.pane.HTML("<h2>📊 Export & Reports</h2>"),
            # Template section
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<h3>📋 Quick Templates</h3>"),
                    self.template_selector,
                    self.template_description,
                    self.template_export_button,
                    width=350,
                ),
                pn.Spacer(width=50),
                pn.Column(
                    pn.pane.HTML("<h3>⚙️ Custom Export</h3>"),
                    self.data_type_selector,
                    self.format_selector,
                    self.time_period_slider,
                    self.export_button,
                    width=350,
                ),
            ),
            pn.pane.HTML("<hr style='margin: 20px 0;'>"),
            # Benchmark section
            pn.Row(
                pn.Column(
                    pn.pane.HTML("<h3>⚡ Performance Testing</h3>"),
                    pn.pane.HTML(
                        "<p>Run comprehensive system benchmarks to assess performance.</p>"
                    ),
                    self.benchmark_button,
                    width=350,
                ),
                pn.Spacer(width=50),
                pn.Column(
                    pn.pane.HTML("<h3>📈 Quick Stats</h3>"),
                    pn.pane.HTML(
                        """
                    <p><strong>Available Templates:</strong> 5</p>
                    <p><strong>Export Formats:</strong> CSV, PDF, JSON</p>
                    <p><strong>Data Types:</strong> Health, Performance, Learning, Benchmarks</p>
                    """
                    ),
                    width=350,
                ),
            ),
            pn.pane.HTML("<hr style='margin: 20px 0;'>"),
            # Status and downloads
            pn.pane.HTML("<h3>📥 Export Status & Downloads</h3>"),
            self.status_text,
            self.download_container,
            pn.Row(
                self.cleanup_button,
            ),
            width=800,
        )
