"""Veto log viewer tab for debugging optimization rejections.

Provides a browsable, filterable table view of veto events logged during
optimization. Users can filter by job, rule type, severity, and driver,
perform full-text search, and export logs to JSON or CSV.

Follows Qt Model/View architecture with VetoLogTableModel and
VetoLogFilterProxyModel for efficient filtering.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableView,
    QComboBox,
    QLineEdit,
    QPushButton,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
    QMenu,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QClipboard

from ...kernel_logger import KernelVetoLogger
from ..models.veto_log_model import (
    VetoLogTableModel,
    VetoLogFilterProxyModel,
    VetoLogStatsModel,
)


class VetoLogTab(QWidget):
    """Tab for viewing and analyzing kernel veto logs.

    Displays a table of veto events with filtering controls above and
    status information below. Supports exporting filtered results to
    JSON or CSV formats.

    Attributes:
        veto_logger: KernelVetoLogger instance for data access
        table_model: Source model for veto events
        proxy_model: Filter proxy for dynamic filtering
        table_view: QTableView displaying the filtered data

    Signals:
        veto_selected: Emitted when user selects a veto row (row_data)
        export_requested: Emitted when user requests export (format, filepath)

    Example:
        veto_logger = KernelVetoLogger("veto_logs.db")
        tab = VetoLogTab(veto_logger)
        tab.load_job("job-123")  # Load vetos for a specific job
    """

    veto_selected = Signal(dict)  # Emitted when a veto row is selected
    export_requested = Signal(str, str)  # format, filepath

    def __init__(
        self,
        veto_logger: Optional[KernelVetoLogger] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize VetoLogTab.

        Args:
            veto_logger: KernelVetoLogger instance for data access
            parent: Optional parent widget
        """
        super().__init__(parent)

        self.veto_logger = veto_logger
        self.current_job_id: Optional[str] = None

        # Create models
        self.table_model = VetoLogTableModel(self)
        self.proxy_model = VetoLogFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)

        # Setup UI
        self._create_ui()
        self._setup_context_menu()

        # Update timer for refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_data)
        self._refresh_timer.setInterval(5000)  # 5 second refresh

    def _create_ui(self) -> None:
        """Create the tab UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Filter bar
        filter_layout = self._create_filter_bar()
        layout.addLayout(filter_layout)

        # Table view
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)

        # Configure header
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionsClickable(True)

        # Set initial column widths
        self.table_view.setColumnWidth(0, 80)  # Time
        self.table_view.setColumnWidth(1, 120)  # Rule
        self.table_view.setColumnWidth(2, 120)  # Driver
        self.table_view.setColumnWidth(3, 80)  # Severity
        self.table_view.setColumnWidth(4, 300)  # Reason
        self.table_view.setColumnWidth(5, 150)  # Lineup

        # Connect selection
        self.table_view.selectionModel().currentRowChanged.connect(
            self._on_selection_changed
        )

        # Double-click handler
        self.table_view.doubleClicked.connect(self._on_double_click)

        layout.addWidget(self.table_view)

        # Status bar
        status_layout = self._create_status_bar()
        layout.addLayout(status_layout)

    def _create_filter_bar(self) -> QHBoxLayout:
        """Create the filter controls bar.

        Returns:
            QHBoxLayout containing filter controls
        """
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Job selector
        layout.addWidget(QLabel("Job:"))
        self.job_combo = QComboBox()
        self.job_combo.setMinimumWidth(250)
        self.job_combo.setToolTip("Select optimization job to view veto logs")
        self.job_combo.currentTextChanged.connect(self._on_job_changed)
        layout.addWidget(self.job_combo)

        # Rule filter
        layout.addWidget(QLabel("Rule:"))
        self.rule_filter = QComboBox()
        self.rule_filter.setMinimumWidth(150)
        self.rule_filter.addItem("All Rules")
        self.rule_filter.currentTextChanged.connect(self._on_rule_filter_changed)
        layout.addWidget(self.rule_filter)

        # Severity filter
        layout.addWidget(QLabel("Severity:"))
        self.severity_filter = QComboBox()
        self.severity_filter.setMinimumWidth(100)
        self.severity_filter.addItems(["All", "Info", "Warning", "Error", "Fatal"])
        self.severity_filter.currentTextChanged.connect(
            self._on_severity_filter_changed
        )
        layout.addWidget(self.severity_filter)

        # Driver filter
        layout.addWidget(QLabel("Driver:"))
        self.driver_filter = QLineEdit()
        self.driver_filter.setPlaceholderText("Filter by driver...")
        self.driver_filter.setMaximumWidth(150)
        self.driver_filter.textChanged.connect(self._on_driver_filter_changed)
        layout.addWidget(self.driver_filter)

        # Text search
        layout.addWidget(QLabel("Search:"))
        self.text_search = QLineEdit()
        self.text_search.setPlaceholderText("Search reasons...")
        self.text_search.setMaximumWidth(200)
        self.text_search.textChanged.connect(self._on_text_search_changed)
        layout.addWidget(self.text_search)

        # Clear button
        self.clear_btn = QPushButton("Clear Filters")
        self.clear_btn.setToolTip("Clear all filters and show all veto logs")
        self.clear_btn.clicked.connect(self._clear_filters)
        layout.addWidget(self.clear_btn)

        # Export button with menu
        self.export_btn = QPushButton("Export...")
        self.export_btn.setToolTip("Export veto logs to file")
        self.export_btn.clicked.connect(self._show_export_menu)
        layout.addWidget(self.export_btn)

        layout.addStretch()
        return layout

    def _create_status_bar(self) -> QHBoxLayout:
        """Create the status information bar.

        Returns:
            QHBoxLayout containing status labels
        """
        layout = QHBoxLayout()

        self.status_total = QLabel("Total: 0")
        self.status_total.setToolTip("Total veto events for selected job")
        layout.addWidget(self.status_total)

        self.status_filtered = QLabel("Filtered: 0")
        self.status_filtered.setToolTip("Veto events matching current filters")
        layout.addWidget(self.status_filtered)

        self.status_job = QLabel("No job selected")
        self.status_job.setToolTip("Currently selected job")
        layout.addWidget(self.status_job)

        layout.addStretch()
        return layout

    def _setup_context_menu(self) -> None:
        """Setup right-click context menu for table."""
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, position) -> None:
        """Show context menu at given position."""
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)

        # Copy row action
        copy_row_action = QAction("Copy Row", self)
        copy_row_action.triggered.connect(self._copy_selected_row)
        menu.addAction(copy_row_action)

        # Copy reason action
        copy_reason_action = QAction("Copy Reason", self)
        copy_reason_action.triggered.connect(self._copy_reason)
        menu.addAction(copy_reason_action)

        # View lineup action
        view_lineup_action = QAction("View Lineup Details", self)
        view_lineup_action.triggered.connect(self._view_lineup_details)
        menu.addAction(view_lineup_action)

        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def _on_selection_changed(self, current: Any, previous: Any) -> None:
        """Handle selection change in table."""
        if current.isValid():
            source_row = self.proxy_model.mapToSource(current).row()
            row_data = self.table_model.get_row_data(source_row)
            if row_data:
                self.veto_selected.emit(row_data)

    def _on_double_click(self, index: Any) -> None:
        """Handle double-click on table row."""
        if index.isValid():
            self._view_lineup_details()

    def _copy_selected_row(self) -> None:
        """Copy selected row data to clipboard."""
        selection = self.table_view.selectionModel()
        if selection.hasSelection():
            index = selection.currentIndex()
            source_row = self.proxy_model.mapToSource(index).row()
            row_data = self.table_model.get_row_data(source_row)
            if row_data:
                text = (
                    f"{row_data.get('timestamp', '')} | "
                    f"{row_data.get('rule_name', '')} | "
                    f"{row_data.get('driver_name', '')} | "
                    f"{row_data.get('severity', '')} | "
                    f"{row_data.get('reason', '')}"
                )
                clipboard = self.clipboard()
                clipboard.setText(text)

    def _copy_reason(self) -> None:
        """Copy reason text to clipboard."""
        selection = self.table_view.selectionModel()
        if selection.hasSelection():
            index = selection.currentIndex()
            source_row = self.proxy_model.mapToSource(index).row()
            row_data = self.table_model.get_row_data(source_row)
            if row_data:
                reason = row_data.get("reason", "")
                clipboard = self.clipboard()
                clipboard.setText(reason)

    def _view_lineup_details(self) -> None:
        """Show lineup details dialog."""
        selection = self.table_view.selectionModel()
        if not selection.hasSelection():
            return

        index = selection.currentIndex()
        source_row = self.proxy_model.mapToSource(index).row()
        row_data = self.table_model.get_row_data(source_row)

        if not row_data:
            return

        # Build details message
        lines = [
            f"<b>Time:</b> {row_data.get('timestamp', 'N/A')}",
            f"<b>Rule:</b> {row_data.get('rule_name', 'N/A')}",
            f"<b>Category:</b> {row_data.get('rule_category', 'N/A') or 'N/A'}",
            f"<b>Driver:</b> {row_data.get('driver_name', 'N/A') or 'N/A'}",
            f"<b>Severity:</b> {row_data.get('severity', 'N/A')}",
            f"<b>Reason:</b> {row_data.get('reason', 'N/A')}",
        ]

        # Add constraint details if available
        constraint = row_data.get("constraint_value")
        actual = row_data.get("actual_value")
        if constraint is not None:
            lines.append(f"<b>Constraint:</b> {constraint}")
        if actual is not None:
            lines.append(f"<b>Actual Value:</b> {actual}")

        # Add lineup context
        lineup = row_data.get("lineup_context")
        if lineup:
            if isinstance(lineup, list):
                lineup_str = ", ".join(str(x) for x in lineup)
            else:
                lineup_str = str(lineup)
            lines.append(f"<b>Lineup:</b> {lineup_str}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Veto Details")
        msg.setText("<br>".join(lines))
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def clipboard(self) -> QClipboard:
        """Get application clipboard."""
        from PySide6.QtWidgets import QApplication

        return QApplication.clipboard()

    def _on_job_changed(self, text: str) -> None:
        """Handle job selection change."""
        # Extract job_id from combo text (format: "Job Name (job_id)")
        if "(" in text and text.endswith(")"):
            job_id = text[text.rfind("(") + 1 : -1]
        else:
            job_id = None

        if job_id and self.veto_logger:
            self.load_job(job_id)

    def _on_rule_filter_changed(self, text: str) -> None:
        """Handle rule filter change."""
        if text == "All Rules":
            self.proxy_model.set_rule_filter("")
        else:
            self.proxy_model.set_rule_filter(text)
        self._update_status()

    def _on_severity_filter_changed(self, text: str) -> None:
        """Handle severity filter change."""
        if text == "All":
            self.proxy_model.set_severity_filter("")
        else:
            self.proxy_model.set_severity_filter(text)
        self._update_status()

    def _on_driver_filter_changed(self, text: str) -> None:
        """Handle driver filter change."""
        self.proxy_model.set_driver_filter(text)
        self._update_status()

    def _on_text_search_changed(self, text: str) -> None:
        """Handle text search change."""
        self.proxy_model.set_text_filter(text)
        self._update_status()

    def _clear_filters(self) -> None:
        """Clear all filters."""
        self.rule_filter.setCurrentIndex(0)
        self.severity_filter.setCurrentIndex(0)
        self.driver_filter.clear()
        self.text_search.clear()
        self.proxy_model.clear_filters()
        self._update_status()

    def _show_export_menu(self) -> None:
        """Show export options menu."""
        menu = QMenu(self)

        export_json_action = QAction("Export as JSON...", self)
        export_json_action.triggered.connect(lambda: self._export("json"))
        menu.addAction(export_json_action)

        export_csv_action = QAction("Export as CSV...", self)
        export_csv_action.triggered.connect(lambda: self._export("csv"))
        menu.addAction(export_csv_action)

        menu.exec(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))

    def _export(self, format: str) -> None:
        """Export veto logs to file.

        Args:
            format: "json" or "csv"
        """
        if not self.current_job_id:
            QMessageBox.warning(self, "Export Error", "No job selected")
            return

        # Get filename from dialog
        if format == "json":
            filter_str = "JSON files (*.json)"
            default_suffix = ".json"
        else:
            filter_str = "CSV files (*.csv)"
            default_suffix = ".csv"

        default_name = f"veto_logs_{self.current_job_id}{default_suffix}"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            f"Export Veto Logs as {format.upper()}",
            default_name,
            filter_str,
        )

        if not filepath:
            return

        try:
            if self.veto_logger:
                self.veto_logger.export_vetos(self.current_job_id, format, filepath)
                self.export_requested.emit(format, filepath)
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Exported {self.proxy_model.rowCount()} veto events to {filepath}",
                )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _update_status(self) -> None:
        """Update status bar labels."""
        total = self.table_model.rowCount()
        filtered = self.proxy_model.rowCount()

        self.status_total.setText(f"Total: {total}")
        self.status_filtered.setText(f"Filtered: {filtered}")

        if self.current_job_id:
            self.status_job.setText(f"Job: {self.current_job_id[:8]}...")
        else:
            self.status_job.setText("No job selected")

    def _refresh_data(self) -> None:
        """Refresh data from database."""
        if self.current_job_id and self.veto_logger:
            self.table_model.load_for_job(self.veto_logger, self.current_job_id)
            self._update_rule_filter_options()
            self._update_status()

    def _update_rule_filter_options(self) -> None:
        """Update rule filter dropdown with distinct rules from data."""
        if not self.veto_logger or not self.current_job_id:
            return

        current_selection = self.rule_filter.currentText()

        self.rule_filter.clear()
        self.rule_filter.addItem("All Rules")

        rules = self.veto_logger.get_distinct_rules(self.current_job_id)
        for rule in rules:
            self.rule_filter.addItem(rule)

        # Restore selection if still valid
        index = self.rule_filter.findText(current_selection)
        if index >= 0:
            self.rule_filter.setCurrentIndex(index)

    def set_veto_logger(self, veto_logger: KernelVetoLogger) -> None:
        """Set the veto logger instance.

        Args:
            veto_logger: KernelVetoLogger instance
        """
        self.veto_logger = veto_logger

    def load_job(self, job_id: str) -> None:
        """Load veto logs for a specific job.

        Args:
            job_id: Job UUID to load
        """
        if not self.veto_logger:
            return

        self.current_job_id = job_id
        self.table_model.load_for_job(self.veto_logger, job_id)
        self._update_rule_filter_options()
        self._update_status()

    def add_job_to_selector(
        self, job_id: str, job_name: str, race_name: str = ""
    ) -> None:
        """Add a job to the job selector dropdown.

        Args:
            job_id: Job UUID
            job_name: Display name for job
            race_name: Optional race name
        """
        display_text = f"{job_name} ({job_id})"
        if race_name:
            display_text = f"{race_name} - {display_text}"

        # Check if already exists
        existing_index = self.job_combo.findData(job_id)
        if existing_index < 0:
            self.job_combo.addItem(display_text, job_id)

    def set_active_job(self, job_id: str) -> None:
        """Set the active job and select it in the dropdown.

        Args:
            job_id: Job UUID to activate
        """
        for i in range(self.job_combo.count()):
            if self.job_combo.itemData(i) == job_id:
                self.job_combo.setCurrentIndex(i)
                return

        # If not found, load it directly
        self.load_job(job_id)

    def refresh(self) -> None:
        """Refresh the current view."""
        self._refresh_data()

    def showEvent(self, event) -> None:
        """Handle tab being shown."""
        super().showEvent(event)
        self._refresh_timer.start()

    def hideEvent(self, event) -> None:
        """Handle tab being hidden."""
        super().hideEvent(event)
        self._refresh_timer.stop()
