"""Jobs tab for viewing and managing background optimization jobs.

Provides a table view of all jobs with status badges, progress indicators,
filtering, searching, and actions for each job (view details, cancel, delete, re-run).
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QAbstractItemView,
    QHeaderView,
    QPushButton,
    QLabel,
    QMenu,
    QMessageBox,
    QDialog,
    QTextEdit,
    QDialogButtonBox,
    QToolBar,
    QLineEdit,
    QComboBox,
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, Signal
from PySide6.QtGui import QColor, QAction

from ...persistence.database import DatabaseManager
from ..dialogs.job_details_dialog import JobDetailsDialog


class JobTableModel(QAbstractTableModel):
    """Table model for displaying jobs in a QTableView.

    Columns:
    - Name: Job name
    - Status: Current status with color coding
    - Created: Creation timestamp
    - Duration: Time spent running
    - Progress: Progress percentage for running jobs
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the job table model.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._jobs: List[Dict[str, Any]] = []
        self._headers = ["Name", "Status", "Created", "Duration", "Progress"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows."""
        return len(self._jobs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns."""
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        """Return data for the given index and role."""
        if not index.isValid() or index.row() >= len(self._jobs):
            return None

        job = self._jobs[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:  # Name
                return job.get("name", "Unnamed Job")
            elif col == 1:  # Status
                return job.get("status", "unknown").capitalize()
            elif col == 2:  # Created
                created = job.get("created_at")
                if created:
                    return self._format_datetime(created)
                return ""
            elif col == 3:  # Duration
                return self._format_duration(job)
            elif col == 4:  # Progress
                progress = job.get("progress_percent", 0)
                if job.get("status") in ("running", "queued"):
                    return f"{progress}%"
                return ""

        elif role == Qt.ForegroundRole:
            if col == 1:  # Status color
                status = job.get("status", "")
                return self._get_status_color(status)

        elif role == Qt.TextAlignmentRole:
            if col == 4:  # Progress right-aligned
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.UserRole:  # Full job data
            return job

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ):
        """Return header data."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def update_data(self, jobs: List[Dict[str, Any]]) -> None:
        """Update the model with new job data.

        Args:
            jobs: List of job dictionaries
        """
        self.beginResetModel()
        self._jobs = jobs
        self.endResetModel()

    def get_job(self, row: int) -> Optional[Dict[str, Any]]:
        """Get job data for a specific row.

        Args:
            row: Row index

        Returns:
            Job dictionary or None
        """
        if 0 <= row < len(self._jobs):
            return self._jobs[row]
        return None

    def _format_datetime(self, dt: Any) -> str:
        """Format datetime for display."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                return str(dt)

        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M")
        return str(dt)

    def _format_duration(self, job: Dict[str, Any]) -> str:
        """Calculate and format job duration."""
        started = job.get("started_at")
        completed = job.get("completed_at")
        status = job.get("status", "")

        if not started:
            return "-"

        try:
            if isinstance(started, str):
                started = datetime.fromisoformat(started.replace("Z", "+00:00"))

            if completed and isinstance(completed, str):
                completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))

            if status == "running":
                completed = datetime.now()

            if completed:
                duration = (completed - started).total_seconds()
                if duration < 60:
                    return f"{int(duration)}s"
                elif duration < 3600:
                    return f"{int(duration / 60)}m {int(duration % 60)}s"
                else:
                    return f"{int(duration / 3600)}h {int((duration % 3600) / 60)}m"
        except (ValueError, TypeError):
            pass

        return "-"

    def _get_status_color(self, status: str) -> QColor:
        """Get color for status."""
        colors = {
            "queued": QColor(128, 128, 128),  # Gray
            "running": QColor(33, 150, 243),  # Blue
            "completed": QColor(76, 175, 80),  # Green
            "failed": QColor(244, 67, 54),  # Red
            "cancelled": QColor(158, 158, 158),  # Dark gray
        }
        return colors.get(status, QColor(0, 0, 0))


class JobDetailsDialog(QDialog):
    """Dialog for viewing job details."""

    def __init__(self, job: Dict[str, Any], parent: Optional[QWidget] = None):
        """Initialize the dialog.

        Args:
            job: Job dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(f"Job Details: {job.get('name', 'Unknown')}")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # Job info
        info_text = self._format_job_info(job)
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        layout.addWidget(info_label)

        # Config
        layout.addWidget(QLabel("Configuration:"))
        config_edit = QTextEdit()
        config_edit.setReadOnly(True)
        import json

        config = job.get("config_json", {})
        config_edit.setPlainText(json.dumps(config, indent=2))
        config_edit.setMaximumHeight(150)
        layout.addWidget(config_edit)

        # Results or error
        result_json = job.get("result_json")
        error_message = job.get("error_message")

        if result_json:
            layout.addWidget(QLabel("Results:"))
            result_edit = QTextEdit()
            result_edit.setReadOnly(True)
            result_edit.setPlainText(json.dumps(result_json, indent=2))
            result_edit.setMaximumHeight(150)
            layout.addWidget(result_edit)

        if error_message:
            layout.addWidget(QLabel("Error:"))
            error_edit = QTextEdit()
            error_edit.setReadOnly(True)
            error_edit.setPlainText(error_message)
            error_edit.setStyleSheet("color: red;")
            error_edit.setMaximumHeight(100)
            layout.addWidget(error_edit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _format_job_info(self, job: Dict[str, Any]) -> str:
        """Format job info as text."""
        lines = [
            f"ID: {job.get('id', 'N/A')}",
            f"Name: {job.get('name', 'N/A')}",
            f"Status: {job.get('status', 'N/A').upper()}",
            f"Created: {job.get('created_at', 'N/A')}",
            f"Started: {job.get('started_at', 'N/A')}",
            f"Completed: {job.get('completed_at', 'N/A')}",
            f"Progress: {job.get('progress_percent', 0)}%",
        ]
        return "\n".join(lines)


class JobsTab(QWidget):
    """Tab for viewing and managing background jobs.

    Provides:
    - Table view of all jobs with status badges
    - Auto-refresh for running jobs
    - Context menu with actions (View Details, Cancel, Delete, Re-run, Export)
    - Toolbar with Refresh, Filter, Search, and Export History
    - Search and filter capabilities
    - Stats display at bottom
    """

    # Signal emitted when user requests to re-run a job
    rerun_job_requested = Signal(dict)  # job config

    def __init__(
        self,
        database_manager: DatabaseManager,
        job_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the jobs tab.

        Args:
            database_manager: DatabaseManager for job persistence
            job_manager: Optional JobManager for job operations (cancel, etc.)
            parent: Parent widget
        """
        super().__init__(parent)

        self.database_manager = database_manager
        self.job_manager = job_manager
        self._current_filter = "all"
        self._search_query = ""

        self._setup_ui()
        self._setup_timer()
        self._refresh_jobs()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Toolbar
        toolbar = QToolBar()
        layout.addWidget(toolbar)

        # Refresh button
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh_jobs)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # View Details button (requires selection)
        self.view_details_action = QAction("View Details", self)
        self.view_details_action.triggered.connect(self._on_view_selected)
        self.view_details_action.setEnabled(False)
        toolbar.addAction(self.view_details_action)

        # Re-run button (requires selection)
        self.rerun_action = QAction("Re-run", self)
        self.rerun_action.triggered.connect(self._on_rerun_selected)
        self.rerun_action.setEnabled(False)
        toolbar.addAction(self.rerun_action)

        toolbar.addSeparator()

        # Filter dropdown
        toolbar.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All", "all")
        self.filter_combo.addItem("Running", "running")
        self.filter_combo.addItem("Completed", "completed")
        self.filter_combo.addItem("Failed", "failed")
        self.filter_combo.addItem("Queued", "queued")
        self.filter_combo.addItem("Cancelled", "cancelled")
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_combo)

        toolbar.addSeparator()

        # Search field
        toolbar.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search job names...")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_edit)

        toolbar.addSeparator()

        # Export button
        export_action = QAction("Export History", self)
        export_action.triggered.connect(self._export_history)
        toolbar.addAction(export_action)

        # Jobs table
        self.table_view = QTableView()
        self.table_model = JobTableModel(self)
        self.table_view.setModel(self.table_model)

        # Configure table
        self.table_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        self.table_view.doubleClicked.connect(self._on_double_click)
        self.table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

        layout.addWidget(self.table_view)

        # Stats label at bottom
        self.stats_label = QLabel("No jobs")
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.stats_label)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def _setup_timer(self) -> None:
        """Set up auto-refresh timer for running jobs."""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_jobs)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds

    def _refresh_jobs(self) -> None:
        """Refresh the jobs list from database with current filter/search."""
        try:
            # Apply filter
            if self._search_query:
                jobs = self.database_manager.search_jobs(self._search_query, limit=100)
            elif self._current_filter != "all":
                jobs = self.database_manager.get_jobs_by_status(
                    self._current_filter, limit=100
                )
            else:
                jobs = self.database_manager.list_jobs(limit=100)

            self.table_model.update_data(jobs)

            # Get stats
            stats = self.database_manager.get_job_stats()

            # Update status label
            running = sum(1 for j in jobs if j.get("status") == "running")
            queued = sum(1 for j in jobs if j.get("status") == "queued")
            completed = sum(1 for j in jobs if j.get("status") == "completed")
            failed = sum(1 for j in jobs if j.get("status") == "failed")

            status_parts = []
            if running:
                status_parts.append(f"{running} running")
            if queued:
                status_parts.append(f"{queued} queued")
            if completed:
                status_parts.append(f"{completed} completed")
            if failed:
                status_parts.append(f"{failed} failed")

            if status_parts:
                self.status_label.setText(
                    f"Showing {len(jobs)} jobs ({', '.join(status_parts)})"
                )
            else:
                self.status_label.setText(f"Showing {len(jobs)} jobs")

            # Update stats label
            stats_text = (
                f"Total: {stats['total']} jobs | "
                f"Completed: {stats['completed']} | "
                f"Failed: {stats['failed']} | "
                f"Running: {stats['running']} | "
                f"24h: {stats['recent_24h']}"
            )
            self.stats_label.setText(stats_text)

        except Exception as e:
            self.status_label.setText(f"Error loading jobs: {e}")

    def _on_filter_changed(self, index: int) -> None:
        """Handle filter dropdown change.

        Args:
            index: Selected index
        """
        self._current_filter = self.filter_combo.currentData()
        self._refresh_jobs()

    def _on_search_changed(self, text: str) -> None:
        """Handle search text change.

        Args:
            text: Search query
        """
        self._search_query = text.strip()
        self._refresh_jobs()

    def _on_selection_changed(self) -> None:
        """Handle table selection change - enable/disable action buttons."""
        has_selection = len(self.table_view.selectionModel().selectedRows()) > 0
        self.view_details_action.setEnabled(has_selection)
        self.rerun_action.setEnabled(has_selection)

    def _on_view_selected(self) -> None:
        """View details for selected job."""
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return

        job = self.table_model.get_job(selected[0].row())
        if job:
            self._view_job_details(job)

    def _on_rerun_selected(self) -> None:
        """Re-run selected job."""
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return

        job = self.table_model.get_job(selected[0].row())
        if job:
            self._rerun_job(job)

    def _show_context_menu(self, position) -> None:
        """Show context menu for job actions.

        Args:
            position: Position where menu was requested
        """
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return

        job = self.table_model.get_job(index.row())
        if not job:
            return

        menu = QMenu(self)

        # View Details
        view_action = menu.addAction("View Details")
        view_action.triggered.connect(lambda: self._view_job_details(job))

        menu.addSeparator()

        # Cancel (only for queued/running)
        status = job.get("status", "")
        if status in ("queued", "running"):
            cancel_action = menu.addAction("Cancel Job")
            cancel_action.triggered.connect(lambda: self._cancel_job(job))

        # Delete
        delete_action = menu.addAction("Delete Job")
        delete_action.triggered.connect(lambda: self._delete_job(job))

        menu.addSeparator()

        # Re-run
        rerun_action = menu.addAction("Re-run Job")
        rerun_action.triggered.connect(lambda: self._rerun_job(job))

        # Export (only if has results)
        if job.get("result_json"):
            export_action = menu.addAction("Export Job")
            export_action.triggered.connect(lambda: self._export_job(job))

        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def _on_double_click(self, index: QModelIndex) -> None:
        """Handle double-click on job row.

        Args:
            index: Index of clicked item
        """
        job = self.table_model.get_job(index.row())
        if job:
            self._view_job_details(job)

    def _view_job_details(self, job: Dict[str, Any]) -> None:
        """Show job details dialog.

        Args:
            job: Job dictionary
        """
        dialog = JobDetailsDialog(job, self)
        dialog.rerun_requested.connect(self.rerun_job_requested.emit)
        dialog.exec()

    def _cancel_job(self, job: Dict[str, Any]) -> None:
        """Cancel a job.

        Args:
            job: Job dictionary
        """
        job_id = job.get("id")
        if not job_id:
            return

        if self.job_manager:
            success = self.job_manager.cancel_job(job_id)
            if success:
                QMessageBox.information(
                    self,
                    "Cancel Job",
                    f"Job '{job.get('name')}' cancellation requested.",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Cancel Job",
                    f"Could not cancel job '{job.get('name')}'.\n"
                    "It may have already completed or been cancelled.",
                )
        else:
            QMessageBox.information(
                self,
                "Cancel Job",
                f"Cancel job '{job.get('name')}' (ID: {job_id})\n\n"
                "Note: Cancellation requires JobManager integration.",
            )

    def _delete_job(self, job: Dict[str, Any]) -> None:
        """Delete a job from history.

        Args:
            job: Job dictionary
        """
        job_id = job.get("id")
        if not job_id:
            return

        reply = QMessageBox.question(
            self,
            "Delete Job",
            f"Delete job '{job.get('name')}' from history?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.database_manager.delete_job(job_id)
            if success:
                QMessageBox.information(
                    self, "Delete Job", f"Job '{job.get('name')}' deleted successfully."
                )
            else:
                QMessageBox.warning(
                    self, "Delete Job", f"Job '{job.get('name')}' not found."
                )
            self._refresh_jobs()

    def _export_job(self, job: Dict[str, Any]) -> None:
        """Export a single job to JSON file.

        Args:
            job: Job dictionary
        """
        import json
        from PySide6.QtWidgets import QFileDialog

        result = job.get("result_json")
        if not result:
            QMessageBox.warning(
                self, "No Results", "This job has no results to export."
            )
            return

        # Default filename
        job_name = job.get("name", "job").replace(" ", "_")
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
                "job_id": job.get("id"),
                "job_name": job.get("name"),
                "status": job.get("status"),
                "created_at": job.get("created_at"),
                "completed_at": job.get("completed_at"),
                "execution_mode": job.get("config_json", {}).get(
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

    def _rerun_job(self, job: Dict[str, Any]) -> None:
        """Re-run a job with the same configuration.

        Args:
            job: Job dictionary
        """
        config = job.get("config_json", {})
        if not config:
            QMessageBox.warning(
                self, "Cannot Re-run", "This job has no configuration stored."
            )
            return

        reply = QMessageBox.question(
            self,
            "Re-run Job",
            f"Re-run job '{job.get('name')}' with the same configuration?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Add re-run suffix to job name for tracking
            config = config.copy()
            original_name = job.get("name", "Job")
            if not original_name.endswith(" (re-run)"):
                config["_rerun_of"] = job.get("id")
                config["_rerun_name"] = f"{original_name} (re-run)"
            self.rerun_job_requested.emit(config)

    def _clear_completed(self) -> None:
        """Clear completed jobs from history."""
        reply = QMessageBox.question(
            self,
            "Clear Completed Jobs",
            "Clear all completed, failed, and cancelled jobs from history?\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Get jobs to delete
                completed = self.database_manager.get_jobs_by_status(
                    "completed", limit=1000
                )
                failed = self.database_manager.get_jobs_by_status("failed", limit=1000)
                cancelled = self.database_manager.get_jobs_by_status(
                    "cancelled", limit=1000
                )

                deleted_count = 0
                for job in completed + failed + cancelled:
                    if self.database_manager.delete_job(job["id"]):
                        deleted_count += 1

                QMessageBox.information(
                    self,
                    "Clear Completed",
                    f"Deleted {deleted_count} jobs from history.",
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to clear jobs:\n\n{str(e)}"
                )
            self._refresh_jobs()

    def _export_history(self) -> None:
        """Export job history to file."""
        from PySide6.QtWidgets import QFileDialog
        import json

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Job History",
            "jobs_history.json",
            "JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        try:
            jobs = self.database_manager.list_jobs(limit=1000)
            with open(file_path, "w") as f:
                json.dump(jobs, f, indent=2, default=str)

            QMessageBox.information(
                self, "Export Complete", f"Exported {len(jobs)} jobs to {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export jobs: {e}")

    def add_job(self, job: Dict[str, Any]) -> None:
        """Add a new job to the view.

        Args:
            job: Job dictionary
        """
        self._refresh_jobs()

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update status of a job in the view.

        Args:
            job_id: Job ID to update
            status: New status
        """
        self._refresh_jobs()
