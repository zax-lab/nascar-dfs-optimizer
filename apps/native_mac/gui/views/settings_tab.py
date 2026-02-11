"""Settings tab for configuring application preferences.

Provides UI for:
- Session restore settings
- Optimization defaults
- Appearance preferences
- Data management actions
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QPushButton,
    QLabel,
    QMessageBox,
    QFileDialog,
    QFormLayout,
    QScrollArea,
    QFrame,
    QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from typing import Optional
from datetime import datetime
from pathlib import Path

from ...persistence.session_manager import SessionManager
from ...persistence.database import DatabaseManager
from ...jobs.gpu_client import GPUWorkerClient
from ...gui.dialogs.shortcut_config_dialog import ShortcutConfigDialog
from ...export.backup_manager import BackupManager
from ...persistence.preset_manager import PresetManager


class SettingsTab(QWidget):
    """Tab for configuring application preferences and settings.

    Provides organized sections for:
    - Session & Startup: Restore behavior on launch
    - Optimization: Default lineup count, iterations, ownership
    - Appearance: Theme, table colors
    - Data Management: Clear history, export database, reset settings

    Signals:
        settings_changed: Emitted when settings are saved
    """

    # Signal emitted when settings change (for theme updates, etc.)
    settings_changed = Signal()

    def __init__(
        self,
        session_manager: SessionManager,
        database_manager: DatabaseManager,
        backup_manager: Optional[BackupManager] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the settings tab.

        Args:
            session_manager: SessionManager for loading/saving preferences.
            database_manager: DatabaseManager for data management actions.
            backup_manager: BackupManager for export/import operations.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.session_manager = session_manager
        self.database_manager = database_manager
        self.backup_manager = backup_manager

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Create scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Container widget for scroll area
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Session & Startup group
        layout.addWidget(self._create_session_group())

        # Optimization defaults group
        layout.addWidget(self._create_optimization_group())

        # Appearance group
        layout.addWidget(self._create_appearance_group())

        # GPU Offload group
        layout.addWidget(self._create_gpu_group())

        # Live Optimization group (Split Editor)
        layout.addWidget(self._create_live_optimization_group())

        # Keyboard Shortcuts group
        layout.addWidget(self._create_shortcuts_group())

        # Data Management group
        layout.addWidget(self._create_data_management_group())

        # Backup & Export group
        layout.addWidget(self._create_backup_group())

        # Add stretch at bottom
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_session_group(self) -> QGroupBox:
        """Create Session & Startup settings group.

        Returns:
            QGroupBox with session restore settings.
        """
        group = QGroupBox("Session & Startup")
        layout = QFormLayout(group)

        # Restore previous session on launch
        self.restore_session_check = QCheckBox("Restore previous session on launch")
        self.restore_session_check.setChecked(True)
        self.restore_session_check.setToolTip(
            "Automatically restore window position, race data, and lineups on app launch"
        )
        layout.addRow(self.restore_session_check)

        # Load last race automatically
        self.load_last_race_check = QCheckBox("Load last race automatically")
        self.load_last_race_check.setChecked(True)
        self.load_last_race_check.setToolTip(
            "Automatically load the last viewed race on startup"
        )
        layout.addRow(self.load_last_race_check)

        # Remember window position and size
        self.remember_window_check = QCheckBox("Remember window position and size")
        self.remember_window_check.setChecked(True)
        self.remember_window_check.setToolTip(
            "Save and restore window geometry between sessions"
        )
        layout.addRow(self.remember_window_check)

        # Restore lineups
        self.restore_lineups_check = QCheckBox("Restore generated lineups")
        self.restore_lineups_check.setChecked(True)
        self.restore_lineups_check.setToolTip(
            "Restore previously generated lineups on startup"
        )
        layout.addRow(self.restore_lineups_check)

        # Restore active tab
        self.restore_tab_check = QCheckBox("Restore active tab")
        self.restore_tab_check.setChecked(True)
        self.restore_tab_check.setToolTip("Remember which tab was active on last quit")
        layout.addRow(self.restore_tab_check)

        return group

    def _create_optimization_group(self) -> QGroupBox:
        """Create Optimization defaults settings group.

        Returns:
            QGroupBox with optimization default settings.
        """
        group = QGroupBox("Optimization Defaults")
        layout = QFormLayout(group)

        # Default lineup count (10-150, default 20)
        self.lineup_count_spin = QSpinBox()
        self.lineup_count_spin.setRange(10, 150)
        self.lineup_count_spin.setValue(20)
        self.lineup_count_spin.setSingleStep(10)
        self.lineup_count_spin.setToolTip(
            "Default number of lineups to generate (10-150)"
        )
        layout.addRow("Default lineup count:", self.lineup_count_spin)

        # Default MCMC iterations (100-5000, default 1000)
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(100, 5000)
        self.iterations_spin.setValue(1000)
        self.iterations_spin.setSingleStep(100)
        self.iterations_spin.setToolTip(
            "Default MCMC iterations for optimization (100-5000)"
        )
        layout.addRow("Default MCMC iterations:", self.iterations_spin)

        # Default max ownership (0-100%, default 50%)
        self.max_ownership_spin = QDoubleSpinBox()
        self.max_ownership_spin.setRange(0, 100)
        self.max_ownership_spin.setValue(50)
        self.max_ownership_spin.setDecimals(1)
        self.max_ownership_spin.setSuffix("%")
        self.max_ownership_spin.setToolTip(
            "Default maximum ownership percentage for drivers"
        )
        layout.addRow("Default max ownership:", self.max_ownership_spin)

        return group

    def _create_appearance_group(self) -> QGroupBox:
        """Create Appearance settings group.

        Returns:
            QGroupBox with appearance settings.
        """
        group = QGroupBox("Appearance")
        layout = QFormLayout(group)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("System", "system")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.setToolTip(
            "Application theme (requires restart to take full effect)"
        )
        layout.addRow("Theme:", self.theme_combo)

        # Show alternating row colors
        self.alternating_rows_check = QCheckBox("Show alternating row colors in tables")
        self.alternating_rows_check.setChecked(True)
        self.alternating_rows_check.setToolTip(
            "Enable alternating row background colors for better readability"
        )
        layout.addRow(self.alternating_rows_check)

        return group

    def _create_gpu_group(self) -> QGroupBox:
        """Create GPU Offload settings group.

        Returns:
            QGroupBox with GPU worker configuration.
        """
        group = QGroupBox("GPU Offload")
        layout = QFormLayout(group)

        # Enable GPU offload checkbox
        self.gpu_enabled_check = QCheckBox("Enable GPU offload for heavy optimizations")
        self.gpu_enabled_check.setChecked(False)
        self.gpu_enabled_check.setToolTip(
            "Offload intensive optimization jobs to a remote GPU worker "
            "(Windows PC with CUDA GPU). Falls back to local CPU if unavailable."
        )
        layout.addRow(self.gpu_enabled_check)

        # GPU Worker URL
        self.gpu_url_edit = QLineEdit()
        self.gpu_url_edit.setPlaceholderText("http://192.168.1.100:8000")
        self.gpu_url_edit.setToolTip("URL of the GPU worker (Windows PC with GPU)")
        layout.addRow("GPU Worker URL:", self.gpu_url_edit)

        # API Key (password field)
        self.gpu_api_key_edit = QLineEdit()
        self.gpu_api_key_edit.setPlaceholderText("Optional API key")
        self.gpu_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gpu_api_key_edit.setToolTip(
            "API key for GPU worker authentication (optional)"
        )
        layout.addRow("API Key:", self.gpu_api_key_edit)

        # Timeout
        self.gpu_timeout_spin = QSpinBox()
        self.gpu_timeout_spin.setRange(10, 300)
        self.gpu_timeout_spin.setValue(30)
        self.gpu_timeout_spin.setSuffix(" seconds")
        self.gpu_timeout_spin.setToolTip("Connection timeout for GPU worker")
        layout.addRow("Connection Timeout:", self.gpu_timeout_spin)

        # Connection status label
        self.gpu_status_label = QLabel("Status: Not configured")
        self.gpu_status_label.setStyleSheet("color: #666;")
        layout.addRow(self.gpu_status_label)

        # Test Connection button
        test_btn_layout = QHBoxLayout()
        self.gpu_test_btn = QPushButton("Test Connection")
        self.gpu_test_btn.setToolTip("Test connection to GPU worker")
        self.gpu_test_btn.clicked.connect(self._on_test_gpu_connection)
        test_btn_layout.addWidget(self.gpu_test_btn)
        test_btn_layout.addStretch()
        layout.addRow(test_btn_layout)

        return group

    def _create_live_optimization_group(self) -> QGroupBox:
        """Create Live Optimization settings group for Split Editor.

        Returns:
            QGroupBox with live optimization configuration.
        """
        group = QGroupBox("Live Optimization (Split Editor)")
        layout = QFormLayout(group)

        # Enable live optimization
        self.live_opt_enabled_check = QCheckBox(
            "Enable live optimization on constraint changes"
        )
        self.live_opt_enabled_check.setChecked(True)
        self.live_opt_enabled_check.setToolTip(
            "Automatically run optimization when constraints change in split editor"
        )
        layout.addRow(self.live_opt_enabled_check)

        # Debounce delay
        self.debounce_spin = QSpinBox()
        self.debounce_spin.setRange(100, 2000)
        self.debounce_spin.setValue(300)
        self.debounce_spin.setSingleStep(50)
        self.debounce_spin.setSuffix(" ms")
        self.debounce_spin.setToolTip(
            "Delay before triggering optimization after constraint changes (100-2000ms). "
            "Higher values reduce CPU load during rapid adjustments."
        )
        layout.addRow("Debounce delay:", self.debounce_spin)

        # Real-time mode (no debounce)
        self.realtime_mode_check = QCheckBox("Real-time mode (no debounce)")
        self.realtime_mode_check.setChecked(False)
        self.realtime_mode_check.setToolTip(
            "Trigger optimization immediately on every constraint change. "
            "May impact performance during rapid adjustments."
        )
        layout.addRow(self.realtime_mode_check)

        return group

    def _create_shortcuts_group(self) -> QGroupBox:
        """Create Keyboard Shortcuts settings group.

        Returns:
            QGroupBox with keyboard shortcuts configuration.
        """
        group = QGroupBox("Keyboard Shortcuts")
        layout = QVBoxLayout(group)

        # Description
        desc = QLabel(
            "Customize keyboard shortcuts for all application actions. "
            "Shortcuts follow standard macOS conventions (⌘+letter)."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # Button layout
        btn_layout = QHBoxLayout()

        # Customize Shortcuts button
        self.customize_shortcuts_btn = QPushButton("Customize Shortcuts...")
        self.customize_shortcuts_btn.setToolTip(
            "Open keyboard shortcuts configuration dialog"
        )
        self.customize_shortcuts_btn.clicked.connect(self._on_customize_shortcuts)
        btn_layout.addWidget(self.customize_shortcuts_btn)

        # Reset Shortcuts button
        self.reset_shortcuts_btn = QPushButton("Reset to Defaults")
        self.reset_shortcuts_btn.setToolTip("Reset all shortcuts to factory defaults")
        self.reset_shortcuts_btn.clicked.connect(self._on_reset_shortcuts)
        btn_layout.addWidget(self.reset_shortcuts_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Shortcuts summary
        shortcuts_text = QLabel(
            "<b>Common shortcuts:</b><br>"
            "• ⌘+N - New Race<br>"
            "• ⌘+O - Open Data File<br>"
            "• ⌘+S - Save Lineups<br>"
            "• ⌘+Return - Run Optimization<br>"
            "• ⌘+Z / ⌘+Shift+Z - Undo / Redo<br>"
            "• ⌘+Tab / ⌘+Shift+Tab - Next / Previous Tab"
        )
        shortcuts_text.setWordWrap(True)
        shortcuts_text.setStyleSheet("color: #333; font-size: 12px;")
        layout.addWidget(shortcuts_text)

        return group

    def _create_data_management_group(self) -> QGroupBox:
        """Create Data Management settings group.

        Returns:
            QGroupBox with data management action buttons.
        """
        group = QGroupBox("Data Management")
        layout = QVBoxLayout(group)

        # Description label
        desc = QLabel("Manage your local data. These actions cannot be undone.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # Button layout
        button_layout = QHBoxLayout()

        # Clear Race History button
        self.clear_races_btn = QPushButton("Clear Race History")
        self.clear_races_btn.setToolTip("Delete all races from the database")
        self.clear_races_btn.clicked.connect(self._on_clear_races)
        button_layout.addWidget(self.clear_races_btn)

        # Clear Saved Lineups button
        self.clear_lineups_btn = QPushButton("Clear Saved Lineups")
        self.clear_lineups_btn.setToolTip("Delete all saved lineups from the database")
        self.clear_lineups_btn.clicked.connect(self._on_clear_lineups)
        button_layout.addWidget(self.clear_lineups_btn)

        # Export Database button
        self.export_db_btn = QPushButton("Export Database")
        self.export_db_btn.setToolTip("Backup the database to a file")
        self.export_db_btn.clicked.connect(self._on_export_database)
        button_layout.addWidget(self.export_db_btn)

        # Reset Settings button
        self.reset_settings_btn = QPushButton("Reset All Settings")
        self.reset_settings_btn.setToolTip("Restore all settings to defaults")
        self.reset_settings_btn.clicked.connect(self._on_reset_settings)
        button_layout.addWidget(self.reset_settings_btn)

        layout.addLayout(button_layout)

        return group

    def _create_backup_group(self) -> QGroupBox:
        """Create Backup & Export settings group.

        Returns:
            QGroupBox with backup and export action buttons.
        """
        group = QGroupBox("Backup & Export")
        layout = QVBoxLayout(group)

        # Description label
        desc = QLabel(
            "Export all your data for backup or transfer to another machine. "
            "Import from a previously exported backup file to restore state."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # Last backup info
        self.last_backup_label = QLabel("No backup created yet")
        self.last_backup_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.last_backup_label)

        # Button layout
        button_layout = QHBoxLayout()

        # Export All Data button
        self.export_all_btn = QPushButton("Export All Data...")
        self.export_all_btn.setToolTip("Export all application data to a JSON file")
        self.export_all_btn.clicked.connect(self._on_export_all)
        button_layout.addWidget(self.export_all_btn)

        # Export Lineups Only button
        self.export_lineups_btn = QPushButton("Export Lineups Only...")
        self.export_lineups_btn.setToolTip("Quick export of just your saved lineups")
        self.export_lineups_btn.clicked.connect(self._on_export_lineups)
        button_layout.addWidget(self.export_lineups_btn)

        # Export Presets button
        self.export_presets_btn = QPushButton("Export Presets...")
        self.export_presets_btn.setToolTip("Export constraint presets for sharing")
        self.export_presets_btn.clicked.connect(self._on_export_presets)
        button_layout.addWidget(self.export_presets_btn)

        layout.addLayout(button_layout)

        # Import button layout
        import_layout = QHBoxLayout()

        # Import Backup button
        self.import_backup_btn = QPushButton("Import Backup...")
        self.import_backup_btn.setToolTip(
            "Restore from a previously exported backup file"
        )
        self.import_backup_btn.clicked.connect(self._on_import_backup)
        import_layout.addWidget(self.import_backup_btn)

        import_layout.addStretch()
        layout.addLayout(import_layout)

        return group

    def _load_settings(self) -> None:
        """Load settings from database and update UI."""
        # Session & Startup
        self.restore_session_check.setChecked(
            self.session_manager.load_state("session_restore_enabled", True)
        )
        self.load_last_race_check.setChecked(
            self.session_manager.load_state("load_last_race_on_startup", True)
        )
        self.remember_window_check.setChecked(
            self.session_manager.load_state("restore_window_geometry", True)
        )
        self.restore_lineups_check.setChecked(
            self.session_manager.load_state("restore_lineups", True)
        )
        self.restore_tab_check.setChecked(
            self.session_manager.load_state("restore_active_tab", True)
        )

        # Optimization Defaults
        self.lineup_count_spin.setValue(
            self.session_manager.load_state("default_lineup_count", 20)
        )
        self.iterations_spin.setValue(
            self.session_manager.load_state("default_mcmc_iterations", 1000)
        )
        self.max_ownership_spin.setValue(
            self.session_manager.load_state("default_max_ownership", 50.0)
        )

        # Appearance
        theme = self.session_manager.load_state("theme", "system")
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.alternating_rows_check.setChecked(
            self.session_manager.load_state("alternating_row_colors", True)
        )

        # GPU Offload settings (not stored in DB for security)
        gpu_enabled = self.session_manager.load_state("gpu/enabled", False)
        self.gpu_enabled_check.setChecked(gpu_enabled)

        gpu_url = self.session_manager.load_state(
            "gpu/url", "http://192.168.1.100:8000"
        )
        self.gpu_url_edit.setText(gpu_url)

        # API key is session-only, not loaded from persistent storage
        self.gpu_api_key_edit.setText("")

        gpu_timeout = self.session_manager.load_state("gpu/timeout", 30)
        self.gpu_timeout_spin.setValue(gpu_timeout)

        # Live Optimization settings
        self.live_opt_enabled_check.setChecked(
            self.session_manager.load_state("live_optimization/enabled", True)
        )
        self.debounce_spin.setValue(
            self.session_manager.load_state("live_optimization/debounce_ms", 300)
        )
        self.realtime_mode_check.setChecked(
            self.session_manager.load_state("live_optimization/realtime_mode", False)
        )

        # Update status label
        if gpu_enabled:
            self.gpu_status_label.setText("Status: Enabled (test to verify)")
            self.gpu_status_label.setStyleSheet("color: blue;")
        else:
            self.gpu_status_label.setText("Status: Disabled")
            self.gpu_status_label.setStyleSheet("color: #666;")

    def save_settings(self) -> None:
        """Save current UI settings to database."""
        # Session & Startup
        self.session_manager.save_state(
            "session_restore_enabled", self.restore_session_check.isChecked()
        )
        self.session_manager.save_state(
            "load_last_race_on_startup", self.load_last_race_check.isChecked()
        )
        self.session_manager.save_state(
            "restore_window_geometry", self.remember_window_check.isChecked()
        )
        self.session_manager.save_state(
            "restore_lineups", self.restore_lineups_check.isChecked()
        )
        self.session_manager.save_state(
            "restore_active_tab", self.restore_tab_check.isChecked()
        )

        # Optimization Defaults
        self.session_manager.save_state(
            "default_lineup_count", self.lineup_count_spin.value()
        )
        self.session_manager.save_state(
            "default_mcmc_iterations", self.iterations_spin.value()
        )
        self.session_manager.save_state(
            "default_max_ownership", self.max_ownership_spin.value()
        )

        # Appearance
        self.session_manager.save_state("theme", self.theme_combo.currentData())
        self.session_manager.save_state(
            "alternating_row_colors", self.alternating_rows_check.isChecked()
        )

        # GPU Offload settings (session storage only for security)
        self.session_manager.save_state(
            "gpu/enabled", self.gpu_enabled_check.isChecked()
        )
        self.session_manager.save_state(
            "gpu/url", self.gpu_url_edit.text().strip() or "http://192.168.1.100:8000"
        )
        # API key is NOT saved to persistent storage for security
        self.session_manager.save_state("gpu/timeout", self.gpu_timeout_spin.value())

        # Live Optimization settings
        self.session_manager.save_state(
            "live_optimization/enabled", self.live_opt_enabled_check.isChecked()
        )
        self.session_manager.save_state(
            "live_optimization/debounce_ms", self.debounce_spin.value()
        )
        self.session_manager.save_state(
            "live_optimization/realtime_mode", self.realtime_mode_check.isChecked()
        )

        # Emit signal for theme changes
        self.settings_changed.emit()

    def reset_settings(self) -> None:
        """Reset all settings to defaults."""
        # Session & Startup defaults
        self.restore_session_check.setChecked(True)
        self.load_last_race_check.setChecked(True)
        self.remember_window_check.setChecked(True)
        self.restore_lineups_check.setChecked(True)
        self.restore_tab_check.setChecked(True)

        # Optimization defaults
        self.lineup_count_spin.setValue(20)
        self.iterations_spin.setValue(1000)
        self.max_ownership_spin.setValue(50.0)

        # Appearance defaults
        self.theme_combo.setCurrentIndex(0)  # System
        self.alternating_rows_check.setChecked(True)

        # GPU defaults
        self.gpu_enabled_check.setChecked(False)
        self.gpu_url_edit.setText("http://192.168.1.100:8000")
        self.gpu_api_key_edit.setText("")
        self.gpu_timeout_spin.setValue(30)
        self.gpu_status_label.setText("Status: Not configured")
        self.gpu_status_label.setStyleSheet("color: #666;")

        # Live Optimization defaults
        self.live_opt_enabled_check.setChecked(True)
        self.debounce_spin.setValue(300)
        self.realtime_mode_check.setChecked(False)

        # Clear all saved state
        self.session_manager.clear_all_state()

        # Save the defaults
        self.save_settings()

    def _on_clear_races(self) -> None:
        """Handle Clear Race History button click."""
        reply = QMessageBox.question(
            self,
            "Clear Race History",
            "Are you sure you want to delete all races?\n\n"
            "This will also delete all associated lineups. This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Clear races table (lineups will be cascade deleted)
                import sqlite3

                with self.database_manager.get_connection() as conn:
                    conn.execute("DELETE FROM races")

                QMessageBox.information(
                    self,
                    "Race History Cleared",
                    "All races have been deleted from the database.",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear race history:\n\n{str(e)}",
                )

    def _on_clear_lineups(self) -> None:
        """Handle Clear Saved Lineups button click."""
        reply = QMessageBox.question(
            self,
            "Clear Saved Lineups",
            "Are you sure you want to delete all saved lineups?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with self.database_manager.get_connection() as conn:
                    conn.execute("DELETE FROM lineups")

                QMessageBox.information(
                    self,
                    "Lineups Cleared",
                    "All saved lineups have been deleted from the database.",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear lineups:\n\n{str(e)}",
                )

    def _on_export_database(self) -> None:
        """Handle Export Database button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Database",
            f"nascar_optimizer_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            "SQLite Database (*.db);;All Files (*)",
        )

        if not file_path:
            return

        try:
            import shutil

            db_path = self.database_manager.get_database_path()
            shutil.copy2(db_path, file_path)

            QMessageBox.information(
                self,
                "Database Exported",
                f"Database successfully exported to:\n{file_path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export database:\n\n{str(e)}",
            )

    def _on_reset_settings(self) -> None:
        """Handle Reset All Settings button click."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n\n"
            "This will restore factory defaults but will not delete any race data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.reset_settings()
            QMessageBox.information(
                self,
                "Settings Reset",
                "All settings have been reset to defaults.",
            )

    def _on_test_gpu_connection(self) -> None:
        """Handle Test Connection button click for GPU worker."""
        url = self.gpu_url_edit.text().strip()
        if not url:
            url = "http://192.168.1.100:8000"  # Default

        api_key = self.gpu_api_key_edit.text().strip() or None
        timeout = self.gpu_timeout_spin.value()

        # Update UI
        self.gpu_test_btn.setEnabled(False)
        self.gpu_test_btn.setText("Testing...")
        self.gpu_status_label.setText("Status: Testing connection...")
        self.gpu_status_label.setStyleSheet("color: #666;")

        # Create temporary client and test
        try:
            client = GPUWorkerClient(base_url=url, api_key=api_key, timeout=timeout)
            is_connected = client.test_connection()

            if is_connected:
                # Try to get worker info
                info = client.get_worker_info()
                if info:
                    gpu_name = info.get("gpu_name", "Unknown GPU")
                    version = info.get("version", "Unknown")
                    self.gpu_status_label.setText(
                        f"Status: Connected - {gpu_name} (v{version})"
                    )
                    self.gpu_status_label.setStyleSheet("color: green;")
                else:
                    self.gpu_status_label.setText("Status: Connected")
                    self.gpu_status_label.setStyleSheet("color: green;")

                QMessageBox.information(
                    self,
                    "Connection Successful",
                    f"Successfully connected to GPU worker at\n{url}",
                )
            else:
                self.gpu_status_label.setText("Status: Not connected")
                self.gpu_status_label.setStyleSheet("color: red;")

                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    f"Could not connect to GPU worker at\n{url}\n\n"
                    "Please check:\n"
                    "• The GPU worker is running\n"
                    "• The URL is correct\n"
                    "• The network connection is available",
                )

        except Exception as e:
            self.gpu_status_label.setText("Status: Connection error")
            self.gpu_status_label.setStyleSheet("color: red;")

            QMessageBox.critical(
                self,
                "Connection Error",
                f"Error testing connection:\n\n{str(e)}",
            )

        finally:
            self.gpu_test_btn.setEnabled(True)
            self.gpu_test_btn.setText("Test Connection")

    def _on_customize_shortcuts(self) -> None:
        """Handle Customize Shortcuts button click."""
        from ...shortcuts.shortcut_manager import ShortcutManager

        shortcut_manager = ShortcutManager(self)
        dialog = ShortcutConfigDialog(shortcut_manager, self)
        dialog.exec()

    def _on_reset_shortcuts(self) -> None:
        """Handle Reset Shortcuts button click."""
        reply = QMessageBox.question(
            self,
            "Reset Shortcuts",
            "Are you sure you want to reset all keyboard shortcuts to factory defaults?\n\n"
            "This will discard any custom shortcuts you have set.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            from ...shortcuts.shortcut_manager import ShortcutManager

            shortcut_manager = ShortcutManager(self)
            shortcut_manager.reset_to_defaults()
            QMessageBox.information(
                self,
                "Shortcuts Reset",
                "All keyboard shortcuts have been reset to factory defaults.",
            )

    def _on_export_all(self) -> None:
        """Handle Export All Data button click."""
        if not self.backup_manager:
            QMessageBox.warning(
                self,
                "Backup Manager Not Available",
                "The backup manager is not initialized. Please restart the application.",
            )
            return

        from ...gui.dialogs.export_dialog import ExportDialog

        dialog = ExportDialog(self)
        if dialog.exec() == ExportDialog.DialogCode.Accepted:
            options = dialog.get_selected_options()
            file_path = options["file_path"]

            if not file_path:
                return

            # Show progress dialog
            progress = QMessageBox(self)
            progress.setWindowTitle("Exporting Data")
            progress.setText("Exporting data... Please wait.")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()

            # Perform export
            success, message = self.backup_manager.export_all(
                file_path, options=options["options"]
            )

            progress.close()

            if success:
                # Update last backup date
                self.session_manager.save_state(
                    "last_backup_date", datetime.now().isoformat()
                )
                self._update_last_backup_label()

                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"{message}\n\nFile saved to:\n{file_path}",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export data:\n\n{message}",
                )

    def _on_export_lineups(self) -> None:
        """Handle Export Lineups Only button click."""
        if not self.backup_manager:
            QMessageBox.warning(
                self,
                "Backup Manager Not Available",
                "The backup manager is not initialized. Please restart the application.",
            )
            return

        # Get file path
        from datetime import datetime

        default_filename = f"nascar_lineups_{datetime.now().strftime('%Y-%m-%d')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Lineups",
            str(Path.home() / "Downloads" / default_filename),
            "JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        # Show progress dialog
        progress = QMessageBox(self)
        progress.setWindowTitle("Exporting Lineups")
        progress.setText("Exporting lineups... Please wait.")
        progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
        progress.show()

        # Perform export
        success, message = self.backup_manager.export_lineups(file_path)

        progress.close()

        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"{message}\n\nFile saved to:\n{file_path}",
            )
        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export lineups:\n\n{message}",
            )

    def _on_export_presets(self) -> None:
        """Handle Export Presets button click."""
        if not self.backup_manager:
            QMessageBox.warning(
                self,
                "Backup Manager Not Available",
                "The backup manager is not initialized. Please restart the application.",
            )
            return

        # Get file path
        from datetime import datetime

        default_filename = f"nascar_presets_{datetime.now().strftime('%Y-%m-%d')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Presets",
            str(Path.home() / "Downloads" / default_filename),
            "JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        # Perform export
        success, message = self.backup_manager.export_presets(file_path)

        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"{message}\n\nFile saved to:\n{file_path}",
            )
        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export presets:\n\n{message}",
            )

    def _on_import_backup(self) -> None:
        """Handle Import Backup button click."""
        if not self.backup_manager:
            QMessageBox.warning(
                self,
                "Backup Manager Not Available",
                "The backup manager is not initialized. Please restart the application.",
            )
            return

        from ...gui.dialogs.export_dialog import ImportDialog

        dialog = ImportDialog(self, backup_manager=self.backup_manager)
        if dialog.exec() == ImportDialog.DialogCode.Accepted:
            import_options = dialog.get_import_options()
            file_path = import_options["file_path"]
            merge_strategy = import_options["merge_strategy"]

            if not file_path:
                return

            # Create automatic backup first
            auto_backup_success, auto_backup_path = (
                self.backup_manager.create_automatic_backup()
            )

            if not auto_backup_success:
                reply = QMessageBox.warning(
                    self,
                    "Automatic Backup Failed",
                    "Could not create automatic backup of current data.\n\n"
                    f"Error: {auto_backup_path}\n\n"
                    "Do you want to continue with the import anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            # Show progress dialog
            progress = QMessageBox(self)
            progress.setWindowTitle("Importing Data")
            progress.setText("Importing data... Please wait.")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()

            # Perform import
            success, message = self.backup_manager.import_backup(
                file_path, options={"merge_strategy": merge_strategy}
            )

            progress.close()

            if success:
                # Build success message
                success_msg = f"{message}\n\n"
                if auto_backup_success:
                    success_msg += f"Automatic backup created at:\n{auto_backup_path}"

                QMessageBox.information(
                    self,
                    "Import Complete",
                    success_msg,
                )

                # Refresh UI - reload races, presets, lineups
                self._refresh_ui_after_import()
            else:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    f"Failed to import data:\n\n{message}",
                )

    def _update_last_backup_label(self) -> None:
        """Update the last backup date label."""
        last_backup = self.session_manager.load_state("last_backup_date", None)
        if last_backup:
            try:
                from datetime import datetime

                backup_dt = datetime.fromisoformat(last_backup)
                formatted = backup_dt.strftime("%Y-%m-%d %H:%M")
                self.last_backup_label.setText(f"Last backup: {formatted}")
            except (ValueError, TypeError):
                self.last_backup_label.setText("Last backup: Unknown date")
        else:
            self.last_backup_label.setText("No backup created yet")

    def _refresh_ui_after_import(self) -> None:
        """Refresh UI components after import."""
        # Reload settings
        self._load_settings()

        # Emit signal to notify main window to refresh tabs
        self.settings_changed.emit()

    def showEvent(self, event) -> None:
        """Handle show event to reload settings."""
        super().showEvent(event)
        self._load_settings()
        self._update_last_backup_label()

    def hideEvent(self, event) -> None:
        """Handle hide event to save settings."""
        self.save_settings()
        super().hideEvent(event)
