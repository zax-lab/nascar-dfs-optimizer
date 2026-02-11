"""Export dialog for configuring backup data selection.

Provides a dialog for users to select what data to export including:
- Application settings
- Constraint presets
- Saved lineups
- Race data
- Job history (optional, can be large)
- Veto logs (optional)

Also includes date range filtering and export format options.
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QDialogButtonBox,
    QSpinBox,
    QDateEdit,
    QMessageBox,
    QFrame,
    QScrollArea,
    QWidget,
    QComboBox,
)
from PySide6.QtCore import Qt, QDate


class ExportDialog(QDialog):
    """Dialog for configuring and executing data export.

    Allows users to select which data types to include in the backup,
    filter by date range, and choose export destination.

    Signals:
        None (result returned via exec() and get_selected_options())
    """

    def __init__(self, parent=None, default_filename: Optional[str] = None):
        """Initialize the export dialog.

        Args:
            parent: Parent widget
            default_filename: Default filename for the export
        """
        super().__init__(parent)

        self.setWindowTitle("Export Application Data")
        self.setMinimumSize(550, 600)

        # Generate default filename if not provided
        if default_filename is None:
            today = datetime.now().strftime("%Y-%m-%d")
            default_filename = f"nascar_optimizer_backup_{today}.json"

        self.default_filename = default_filename

        self._setup_ui()
        self._set_default_values()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header_label = QLabel(
            "<b>Export Application Data</b><br>"
            "Select what data to include in your backup file. "
            "You can export everything or select specific data types."
        )
        header_label.setWordWrap(True)
        layout.addWidget(header_label)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Container for scrollable content
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(15)

        # Data selection group
        container_layout.addWidget(self._create_data_selection_group())

        # Date range filter group
        container_layout.addWidget(self._create_date_range_group())

        # Export destination group
        container_layout.addWidget(self._create_destination_group())

        # Format options group
        container_layout.addWidget(self._create_format_group())

        # Add stretch
        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        # Rename buttons for clarity
        self.export_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.export_button.setText("Export")
        self.export_button.setDefault(True)

        layout.addWidget(self.button_box)

    def _create_data_selection_group(self) -> QGroupBox:
        """Create the data selection checkboxes group.

        Returns:
            QGroupBox with data type checkboxes
        """
        group = QGroupBox("Data to Export")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Description
        desc = QLabel("Select the data types you want to include in the export:")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Settings checkbox
        self.settings_checkbox = QCheckBox("Application Settings")
        self.settings_checkbox.setChecked(True)
        self.settings_checkbox.setToolTip(
            "Window geometry, preferences, shortcuts, and all app settings"
        )
        layout.addWidget(self.settings_checkbox)

        # Constraint presets checkbox
        self.presets_checkbox = QCheckBox("Constraint Presets")
        self.presets_checkbox.setChecked(True)
        self.presets_checkbox.setToolTip(
            "All saved constraint presets and recent preset history"
        )
        layout.addWidget(self.presets_checkbox)

        # Lineups checkbox
        self.lineups_checkbox = QCheckBox("Saved Lineups")
        self.lineups_checkbox.setChecked(True)
        self.lineups_checkbox.setToolTip(
            "All generated lineups with driver assignments"
        )
        layout.addWidget(self.lineups_checkbox)

        # Race data checkbox
        self.races_checkbox = QCheckBox("Race Data")
        self.races_checkbox.setChecked(True)
        self.races_checkbox.setToolTip("Imported driver data and race metadata")
        layout.addWidget(self.races_checkbox)

        # Separator
        layout.addSpacing(10)

        # Job history checkbox (unchecked by default - can be large)
        self.jobs_checkbox = QCheckBox("Job History")
        self.jobs_checkbox.setChecked(False)
        self.jobs_checkbox.setToolTip(
            "Optimization job configurations and results (can be large)"
        )
        layout.addWidget(self.jobs_checkbox)

        # Veto logs checkbox (unchecked by default)
        self.veto_logs_checkbox = QCheckBox("Veto Logs")
        self.veto_logs_checkbox.setChecked(False)
        self.veto_logs_checkbox.setToolTip(
            "Kernel rejection logs from optimization runs"
        )
        layout.addWidget(self.veto_logs_checkbox)

        return group

    def _create_date_range_group(self) -> QGroupBox:
        """Create the date range filter group.

        Returns:
            QGroupBox with date range controls
        """
        group = QGroupBox("Date Range Filter (Optional)")
        layout = QVBoxLayout(group)

        # Enable date filter checkbox
        self.date_filter_checkbox = QCheckBox("Only include data from the last N days")
        self.date_filter_checkbox.setChecked(False)
        self.date_filter_checkbox.stateChanged.connect(self._on_date_filter_changed)
        layout.addWidget(self.date_filter_checkbox)

        # Days spinner
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel("Number of days:"))
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setRange(1, 365)
        self.days_spinbox.setValue(30)
        self.days_spinbox.setEnabled(False)
        days_layout.addWidget(self.days_spinbox)
        days_layout.addStretch()
        layout.addLayout(days_layout)

        # Custom date range
        custom_label = QLabel("Or specify a custom date range:")
        layout.addWidget(custom_label)

        # From date
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setEnabled(False)
        from_layout.addWidget(self.from_date)
        from_layout.addStretch()
        layout.addLayout(from_layout)

        # To date
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setEnabled(False)
        to_layout.addWidget(self.to_date)
        to_layout.addStretch()
        layout.addLayout(to_layout)

        # Connect checkbox to enable/disable dates
        self.date_filter_checkbox.stateChanged.connect(self._on_custom_dates_changed)

        return group

    def _create_destination_group(self) -> QGroupBox:
        """Create the export destination group.

        Returns:
            QGroupBox with file path controls
        """
        group = QGroupBox("Export Destination")
        layout = QVBoxLayout(group)

        # Path display and browse button
        path_layout = QHBoxLayout()

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select export location...")
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # Default path hint
        default_path_hint = QLabel(
            f"Default filename: <code>{self.default_filename}</code>"
        )
        default_path_hint.setWordWrap(True)
        default_path_hint.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(default_path_hint)

        return group

    def _create_format_group(self) -> QGroupBox:
        """Create the format options group.

        Returns:
            QGroupBox with format selection
        """
        group = QGroupBox("Export Format")
        layout = QVBoxLayout(group)

        # Format combo box
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))

        self.format_combo = QComboBox()
        self.format_combo.addItem("JSON (human-readable, recommended)", "json")
        self.format_combo.addItem("Compressed JSON (smaller file)", "compressed")
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()

        layout.addLayout(format_layout)

        # Format description
        self.format_desc = QLabel(
            "JSON format is human-readable and works well with version control. "
            "Recommended for most users."
        )
        self.format_desc.setWordWrap(True)
        self.format_desc.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.format_desc)

        # Connect format change
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)

        return group

    def _set_default_values(self) -> None:
        """Set default values for date fields."""
        today = QDate.currentDate()

        # Default from date: 30 days ago
        self.from_date.setDate(today.addDays(-30))

        # Default to date: today
        self.to_date.setDate(today)

    def _on_date_filter_changed(self, state: int) -> None:
        """Handle date filter checkbox change.

        Args:
            state: Checkbox state
        """
        enabled = state == Qt.CheckState.Checked.value
        self.days_spinbox.setEnabled(enabled)

    def _on_custom_dates_changed(self, state: int) -> None:
        """Handle custom dates enable/disable.

        Args:
            state: Checkbox state
        """
        enabled = state == Qt.CheckState.Checked.value
        self.from_date.setEnabled(enabled)
        self.to_date.setEnabled(enabled)

    def _on_format_changed(self, index: int) -> None:
        """Handle format selection change.

        Args:
            index: Selected format index
        """
        format_type = self.format_combo.currentData()

        if format_type == "json":
            self.format_desc.setText(
                "JSON format is human-readable and works well with version control. "
                "Recommended for most users."
            )
        elif format_type == "compressed":
            self.format_desc.setText(
                "Compressed JSON reduces file size significantly. "
                "Best for large backups with job history."
            )

    def _on_browse(self) -> None:
        """Handle browse button click to select export location."""
        # Get default location
        default_path = str(Path.home() / "Downloads" / self.default_filename)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Backup",
            default_path,
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            self.path_edit.setText(file_path)

    def _on_accept(self) -> None:
        """Handle OK/Export button click with validation."""
        # Validate at least one checkbox is selected
        if not self._has_selection():
            QMessageBox.warning(
                self,
                "No Data Selected",
                "Please select at least one data type to export.",
            )
            return

        # Validate file path
        file_path = self.path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(
                self,
                "No Destination",
                "Please select a destination for the export file.",
            )
            return

        # Check if file already exists
        import os

        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"The file '{file_path}' already exists.\n\n"
                "Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        # Accept the dialog
        self.accept()

    def _has_selection(self) -> bool:
        """Check if at least one data type is selected.

        Returns:
            True if at least one checkbox is checked
        """
        return (
            self.settings_checkbox.isChecked()
            or self.presets_checkbox.isChecked()
            or self.lineups_checkbox.isChecked()
            or self.races_checkbox.isChecked()
            or self.jobs_checkbox.isChecked()
            or self.veto_logs_checkbox.isChecked()
        )

    def get_selected_options(self) -> Dict[str, Any]:
        """Get the selected export options.

        Returns:
            Dictionary with:
                - file_path: str (export destination)
                - options: Dict with include_* flags
                - date_range: Optional[Tuple[date, date]]
                - format: str ("json" or "compressed")
        """
        # Build options dict
        options = {
            "include_settings": self.settings_checkbox.isChecked(),
            "include_presets": self.presets_checkbox.isChecked(),
            "include_lineups": self.lineups_checkbox.isChecked(),
            "include_races": self.races_checkbox.isChecked(),
            "include_jobs": self.jobs_checkbox.isChecked(),
            "include_veto_logs": self.veto_logs_checkbox.isChecked(),
        }

        # Get date range if enabled
        date_range = None
        if self.date_filter_checkbox.isChecked():
            # Calculate date range based on days
            days = self.days_spinbox.value()
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            date_range = (start_date, end_date)

        # Get format
        format_type = self.format_combo.currentData()

        return {
            "file_path": self.path_edit.text().strip(),
            "options": options,
            "date_range": date_range,
            "format": format_type,
        }

    def get_file_path(self) -> str:
        """Get the selected file path.

        Returns:
            Path to export file (empty string if not set)
        """
        return self.path_edit.text().strip()


class ImportDialog(QDialog):
    """Dialog for importing data from a backup file.

    Provides file selection and import options including merge strategy.
    """

    def __init__(self, parent=None, backup_manager=None):
        """Initialize the import dialog.

        Args:
            parent: Parent widget
            backup_manager: BackupManager instance for validation
        """
        super().__init__(parent)

        self.backup_manager = backup_manager

        self.setWindowTitle("Import Backup")
        self.setMinimumSize(500, 400)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header = QLabel(
            "<b>Import from Backup</b><br>Select a backup file to restore your data."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # File selection group
        file_group = QGroupBox("Backup File")
        file_layout = QVBoxLayout(file_group)

        # File path and browse
        path_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select backup file...")
        self.file_path_edit.setReadOnly(True)
        path_layout.addWidget(self.file_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        path_layout.addWidget(browse_btn)

        file_layout.addLayout(path_layout)

        # File info display
        self.file_info_label = QLabel("No file selected")
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setStyleSheet("color: #666; font-size: 12px;")
        file_layout.addWidget(self.file_info_label)

        layout.addWidget(file_group)

        # Import options group
        options_group = QGroupBox("Import Options")
        options_layout = QVBoxLayout(options_group)

        # Merge strategy
        strategy_label = QLabel("When importing data that already exists:")
        options_layout.addWidget(strategy_label)

        self.merge_replace_radio = QCheckBox("Replace all existing data")
        self.merge_replace_radio.setToolTip(
            "Delete existing data and replace with backup contents"
        )
        options_layout.addWidget(self.merge_replace_radio)

        self.merge_merge_radio = QCheckBox("Merge with existing data (recommended)")
        self.merge_merge_radio.setChecked(True)
        self.merge_merge_radio.setToolTip(
            "Keep existing data and add new data from backup"
        )
        options_layout.addWidget(self.merge_merge_radio)

        self.merge_skip_radio = QCheckBox("Skip existing items")
        self.merge_skip_radio.setToolTip("Only import items that don't already exist")
        options_layout.addWidget(self.merge_skip_radio)

        # Connect radios for mutual exclusivity
        self.merge_replace_radio.stateChanged.connect(self._on_strategy_changed)
        self.merge_merge_radio.stateChanged.connect(self._on_strategy_changed)
        self.merge_skip_radio.stateChanged.connect(self._on_strategy_changed)

        options_layout.addSpacing(10)

        # Safety warning
        warning = QLabel(
            "<span style='color: #d9534f;'>⚠ Warning:</span> "
            "Importing data will modify your current database. "
            "An automatic backup will be created before importing."
        )
        warning.setWordWrap(True)
        options_layout.addWidget(warning)

        layout.addWidget(options_group)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        self.import_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.import_button.setText("Import")
        self.import_button.setEnabled(False)

        layout.addWidget(self.button_box)

        # Add stretch
        layout.addStretch()

    def _on_strategy_changed(self, state: int) -> None:
        """Handle merge strategy radio button changes for mutual exclusivity.

        Args:
            state: Checkbox state
        """
        sender = self.sender()

        if state == Qt.CheckState.Checked.value:
            # Uncheck others
            if sender == self.merge_replace_radio:
                self.merge_merge_radio.setChecked(False)
                self.merge_skip_radio.setChecked(False)
            elif sender == self.merge_merge_radio:
                self.merge_replace_radio.setChecked(False)
                self.merge_skip_radio.setChecked(False)
            elif sender == self.merge_skip_radio:
                self.merge_replace_radio.setChecked(False)
                self.merge_merge_radio.setChecked(False)

    def _on_browse(self) -> None:
        """Handle browse button click to select backup file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File",
            str(Path.home() / "Downloads"),
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            self.file_path_edit.setText(file_path)
            self._validate_file(file_path)

    def _validate_file(self, file_path: str) -> None:
        """Validate the selected backup file.

        Args:
            file_path: Path to the file to validate
        """
        if not self.backup_manager:
            self.file_info_label.setText(f"Selected: {file_path}")
            self.import_button.setEnabled(True)
            return

        is_valid, errors = self.backup_manager.validate_backup(file_path)

        if is_valid:
            # Get summary
            summary = self.backup_manager.get_backup_summary(file_path)

            if summary:
                info_parts = [
                    f"<b>Version:</b> {summary.get('version', 'unknown')}",
                    f"<b>Exported:</b> {summary.get('export_date', 'unknown')[:10]}",
                ]

                # Add counts
                counts = summary.get("counts", {})
                count_parts = []
                for key, count in counts.items():
                    if count > 0:
                        count_parts.append(f"{count} {key.replace('_', ' ')}")

                if count_parts:
                    info_parts.append(f"<b>Contains:</b> {', '.join(count_parts)}")

                self.file_info_label.setText("<br>".join(info_parts))
                self.import_button.setEnabled(True)
            else:
                self.file_info_label.setText(
                    f"Selected: {file_path}<br>Valid backup file"
                )
                self.import_button.setEnabled(True)
        else:
            self.file_info_label.setText(
                f"<span style='color: #d9534f;'>Invalid file: {', '.join(errors)}</span>"
            )
            self.import_button.setEnabled(False)

    def _on_accept(self) -> None:
        """Handle import button click with validation."""
        file_path = self.file_path_edit.text().strip()

        if not file_path:
            QMessageBox.warning(
                self,
                "No File Selected",
                "Please select a backup file to import.",
            )
            return

        # Validate again
        if self.backup_manager:
            is_valid, errors = self.backup_manager.validate_backup(file_path)
            if not is_valid:
                QMessageBox.critical(
                    self,
                    "Invalid Backup File",
                    f"The selected file cannot be imported:\n\n{', '.join(errors)}",
                )
                return

        # Confirm import
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            "This will import data from the backup file into your current database.\n\n"
            "An automatic backup of your current data will be created first.\n\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

    def get_import_options(self) -> Dict[str, Any]:
        """Get the selected import options.

        Returns:
            Dictionary with:
                - file_path: str
                - merge_strategy: str ("replace", "merge", or "skip_existing")
        """
        # Determine merge strategy
        if self.merge_replace_radio.isChecked():
            strategy = "replace"
        elif self.merge_skip_radio.isChecked():
            strategy = "skip_existing"
        else:
            strategy = "merge"

        return {
            "file_path": self.file_path_edit.text().strip(),
            "merge_strategy": strategy,
        }
