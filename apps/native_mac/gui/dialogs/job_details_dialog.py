"""Job Details Dialog for viewing full job information.

Provides a detailed view of job configuration, results, and metadata
with re-run and export functionality.
"""

import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QGridLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont


class JobDetailsDialog(QDialog):
    """Dialog for viewing detailed job information.

    Displays:
    - Job metadata (name, ID, status, timing)
    - Execution mode (Local CPU or GPU offload)
    - Configuration (formatted JSON)
    - Results (formatted JSON or lineup table)
    - Error messages (if failed)

    Actions:
    - Re-run Job: Submit new job with same config
    - Export Results: Save results to JSON file
    """

    # Signal emitted when user requests to re-run the job
    rerun_requested = Signal(dict)  # job config

    def __init__(self, job_data: Dict[str, Any], parent: Optional[QWidget] = None):
        """Initialize the dialog.

        Args:
            job_data: Job dictionary with all fields
            parent: Optional parent widget
        """
        super().__init__(parent)

        self.job_data = job_data
        self.setWindowTitle(f"Job Details: {job_data.get('name', 'Unknown')}")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header section with job info
        layout.addWidget(self._create_header_section())

        # Tab widget for different sections
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Config tab
        self.tab_widget.addTab(self._create_config_tab(), "Configuration")

        # Results tab
        results_tab = self._create_results_tab()
        if results_tab:
            self.tab_widget.addTab(results_tab, "Results")

        # Error tab (if applicable)
        if self.job_data.get("error_message"):
            self.tab_widget.addTab(self._create_error_tab(), "Error")

        # Button bar
        layout.addLayout(self._create_button_bar())

    def _create_header_section(self) -> QGroupBox:
        """Create the header section with job metadata.

        Returns:
            QGroupBox containing job info grid
        """
        group = QGroupBox("Job Information")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        # Row 0: ID and Name
        layout.addWidget(QLabel("<b>ID:</b>"), 0, 0)
        id_label = QLabel(self.job_data.get("id", "N/A"))
        id_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(id_label, 0, 1)

        layout.addWidget(QLabel("<b>Name:</b>"), 0, 2)
        name_label = QLabel(self.job_data.get("name", "N/A"))
        layout.addWidget(name_label, 0, 3)

        # Row 1: Status with colored badge
        layout.addWidget(QLabel("<b>Status:</b>"), 1, 0)
        status = self.job_data.get("status", "unknown")
        status_label = QLabel(status.upper())
        status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: {self._get_status_color(status)};
                padding: 3px 10px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(status_label, 1, 1)

        layout.addWidget(QLabel("<b>Execution Mode:</b>"), 1, 2)
        config = self.job_data.get("config_json", {})
        execution_mode = config.get("execution_mode", "local")
        if config.get("gpu_fallback"):
            execution_mode = "local (GPU fallback)"
        mode_label = QLabel(execution_mode.replace("_", " ").title())
        layout.addWidget(mode_label, 1, 3)

        # Row 2: Timing information
        layout.addWidget(QLabel("<b>Created:</b>"), 2, 0)
        created = self._format_datetime(self.job_data.get("created_at"))
        layout.addWidget(QLabel(created), 2, 1)

        layout.addWidget(QLabel("<b>Started:</b>"), 2, 2)
        started = self._format_datetime(self.job_data.get("started_at"))
        layout.addWidget(QLabel(started), 2, 3)

        # Row 3: Completed and Duration
        layout.addWidget(QLabel("<b>Completed:</b>"), 3, 0)
        completed = self._format_datetime(self.job_data.get("completed_at"))
        layout.addWidget(QLabel(completed), 3, 1)

        layout.addWidget(QLabel("<b>Duration:</b>"), 3, 2)
        duration = self._calculate_duration()
        layout.addWidget(QLabel(duration), 3, 3)

        # Row 4: Progress
        layout.addWidget(QLabel("<b>Progress:</b>"), 4, 0)
        progress = self.job_data.get("progress_percent", 0)
        layout.addWidget(QLabel(f"{progress}%"), 4, 1)

        # Show lineup count if completed
        result = self.job_data.get("result_json", {})
        if result and isinstance(result, dict):
            lineup_count = result.get("lineup_count", 0)
            if lineup_count:
                layout.addWidget(QLabel("<b>Lineups Generated:</b>"), 4, 2)
                layout.addWidget(QLabel(str(lineup_count)), 4, 3)

        return group

    def _create_config_tab(self) -> QWidget:
        """Create the configuration tab.

        Returns:
            QWidget with formatted JSON config
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        config = self.job_data.get("config_json", {})

        # Create text edit with formatted JSON
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(
            QFont("Monaco", 11) if sys.platform == "darwin" else QFont("Consolas", 10)
        )

        # Format the JSON nicely
        try:
            formatted = json.dumps(config, indent=2, sort_keys=True)
            text_edit.setPlainText(formatted)
        except Exception:
            text_edit.setPlainText(str(config))

        layout.addWidget(text_edit)
        return widget

    def _create_results_tab(self) -> Optional[QWidget]:
        """Create the results tab.

        Returns:
            QWidget with results, or None if no results
        """
        result = self.job_data.get("result_json")
        if not result:
            return None

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # If result has lineups, show as table
        if isinstance(result, dict) and "lineups" in result:
            lineups = result.get("lineups", [])
            if lineups:
                layout.addWidget(QLabel(f"<b>Generated {len(lineups)} Lineups:</b>"))

                table = QTableWidget()
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Rank", "Total Salary", "Drivers"])
                table.horizontalHeader().setStretchLastSection(True)
                table.horizontalHeader().setSectionResizeMode(
                    QHeaderView.ResizeToContents
                )

                # Show first 50 lineups max
                display_lineups = lineups[:50]
                table.setRowCount(len(display_lineups))

                for i, lineup in enumerate(display_lineups):
                    # Rank
                    rank_item = QTableWidgetItem(str(i + 1))
                    rank_item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(i, 0, rank_item)

                    # Total salary
                    drivers = lineup.get("drivers", [])
                    total_salary = sum(d.get("salary", 0) for d in drivers)
                    salary_item = QTableWidgetItem(f"${total_salary:,}")
                    salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    table.setItem(i, 1, salary_item)

                    # Driver names
                    driver_names = [d.get("name", "Unknown") for d in drivers[:6]]
                    drivers_text = ", ".join(driver_names)
                    if len(drivers) > 6:
                        drivers_text += f" (+{len(drivers) - 6} more)"
                    table.setItem(i, 2, QTableWidgetItem(drivers_text))

                layout.addWidget(table)

                if len(lineups) > 50:
                    layout.addWidget(
                        QLabel(f"<i>Showing first 50 of {len(lineups)} lineups...</i>")
                    )
            else:
                layout.addWidget(QLabel("<i>No lineups in results</i>"))
        else:
            # Show raw JSON
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFont(
                QFont("Monaco", 11)
                if sys.platform == "darwin"
                else QFont("Consolas", 10)
            )

            try:
                formatted = json.dumps(result, indent=2, sort_keys=True)
                text_edit.setPlainText(formatted)
            except Exception:
                text_edit.setPlainText(str(result))

            layout.addWidget(text_edit)

        return widget

    def _create_error_tab(self) -> QWidget:
        """Create the error tab for failed jobs.

        Returns:
            QWidget with error message
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        error_msg = self.job_data.get("error_message", "Unknown error")

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(
            QFont("Monaco", 11) if sys.platform == "darwin" else QFont("Consolas", 10)
        )
        text_edit.setPlainText(error_msg)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #ffebee;
                color: #c62828;
                border: 1px solid #ef5350;
            }
        """)

        layout.addWidget(QLabel("<b>Error Message:</b>"))
        layout.addWidget(text_edit)

        return widget

    def _create_button_bar(self) -> QHBoxLayout:
        """Create the button bar with action buttons.

        Returns:
            QHBoxLayout with buttons
        """
        layout = QHBoxLayout()
        layout.addStretch()

        # Re-run button
        self.rerun_btn = QPushButton("Re-run Job")
        self.rerun_btn.setToolTip("Submit a new job with the same configuration")
        self.rerun_btn.clicked.connect(self._on_rerun)
        layout.addWidget(self.rerun_btn)

        # Export button
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setToolTip("Save job results to JSON file")
        self.export_btn.clicked.connect(self._on_export)

        # Only enable export if we have results
        result = self.job_data.get("result_json")
        self.export_btn.setEnabled(bool(result))
        layout.addWidget(self.export_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        return layout

    def _on_rerun(self) -> None:
        """Handle Re-run Job button click."""
        config = self.job_data.get("config_json", {})
        if not config:
            QMessageBox.warning(
                self, "Cannot Re-run", "This job has no configuration stored."
            )
            return

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Re-run Job",
            f"Re-run job '{self.job_data.get('name')}' with the same configuration?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.rerun_requested.emit(config)
            self.accept()  # Close dialog

    def _on_export(self) -> None:
        """Handle Export Results button click."""
        result = self.job_data.get("result_json")
        if not result:
            QMessageBox.warning(
                self, "No Results", "This job has no results to export."
            )
            return

        # Default filename
        job_name = self.job_data.get("name", "job").replace(" ", "_")
        default_name = f"{job_name}_results.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Job Results",
            default_name,
            "JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        try:
            export_data = {
                "job_id": self.job_data.get("id"),
                "job_name": self.job_data.get("name"),
                "status": self.job_data.get("status"),
                "created_at": self.job_data.get("created_at"),
                "completed_at": self.job_data.get("completed_at"),
                "execution_mode": self.job_data.get("config_json", {}).get(
                    "execution_mode", "local"
                ),
                "results": result,
            }

            with open(file_path, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            QMessageBox.information(
                self, "Export Complete", f"Results exported to:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Export Failed", f"Failed to export results:\n\n{str(e)}"
            )

    def _format_datetime(self, dt: Any) -> str:
        """Format datetime for display.

        Args:
            dt: Datetime string or object

        Returns:
            Formatted datetime string
        """
        if not dt:
            return "N/A"

        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                return str(dt)

        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        return str(dt)

    def _calculate_duration(self) -> str:
        """Calculate and format job duration.

        Returns:
            Formatted duration string
        """
        started = self.job_data.get("started_at")
        completed = self.job_data.get("completed_at")

        if not started:
            return "N/A"

        try:
            if isinstance(started, str):
                started = datetime.fromisoformat(started.replace("Z", "+00:00"))

            if completed:
                if isinstance(completed, str):
                    completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))
            else:
                # Still running
                if self.job_data.get("status") == "running":
                    completed = datetime.now()
                else:
                    return "N/A"

            duration_seconds = (completed - started).total_seconds()

            if duration_seconds < 60:
                return f"{int(duration_seconds)} seconds"
            elif duration_seconds < 3600:
                minutes = int(duration_seconds / 60)
                seconds = int(duration_seconds % 60)
                return f"{minutes}m {seconds}s"
            else:
                hours = int(duration_seconds / 3600)
                minutes = int((duration_seconds % 3600) / 60)
                return f"{hours}h {minutes}m"

        except (ValueError, TypeError):
            return "N/A"

    def _get_status_color(self, status: str) -> str:
        """Get hex color for status.

        Args:
            status: Job status string

        Returns:
            Hex color code
        """
        colors = {
            "queued": "#9e9e9e",  # Gray
            "running": "#2196f3",  # Blue
            "completed": "#4caf50",  # Green
            "failed": "#f44336",  # Red
            "cancelled": "#757575",  # Dark gray
        }
        return colors.get(status, "#000000")
