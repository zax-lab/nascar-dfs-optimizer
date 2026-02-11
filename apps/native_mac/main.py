"""Main entry point for NASCAR DFS Optimizer native Mac app.

Sets up the Qt application with native macOS integration,
dark mode support, standard menu bar, and system tray icon.
"""

import sys
import os
import logging
from PySide6.QtWidgets import QApplication, QMenu, QMenuBar
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt, QEvent, Signal, QTimer

logger = logging.getLogger(__name__)

from apps.native_mac.gui.main_window import MainWindow
from apps.native_mac.gui.menubar_extra import SystemTrayIcon
from apps.native_mac.persistence.session_manager import SessionManager
from apps.native_mac.persistence.database import DatabaseManager
from apps.native_mac.persistence.preset_manager import PresetManager
from apps.native_mac.dock_handler import DockIconHandler
from apps.native_mac.session_restorer import SessionRestorer
from apps.native_mac.optimization.engine import OptimizationEngine
from apps.native_mac.jobs.job_manager import JobManager
from apps.native_mac.jobs.gpu_client import GPUWorkerClient
from apps.native_mac.undo.undo_manager import UndoManager
from apps.native_mac.shortcuts.shortcut_manager import ShortcutManager
from apps.native_mac.export.backup_manager import BackupManager


class MainApplication(QApplication):
    """Custom QApplication that handles macOS file open events.

    Emits fileOpened signal when a file is double-clicked in Finder
    or dragged onto the app icon.
    """

    fileOpened = Signal(str)

    def event(self, event):
        """Handle application-level events.

        Args:
            event: The QEvent to handle.

        Returns:
            True if the event was handled, False otherwise.
        """
        if event.type() == QEvent.Type.FileOpen:
            file_path = event.file()
            if file_path and file_path.endswith(".csv"):
                self.fileOpened.emit(file_path)
                return True
        return super().event(event)


def create_application_menus(
    window: MainWindow, undo_manager: UndoManager, backup_manager: BackupManager
) -> None:
    """Create standard macOS application menus.

    Args:
        window: MainWindow instance to attach menus to.
        undo_manager: UndoManager instance for undo/redo actions.
        backup_manager: BackupManager instance for export/import actions.
    """
    menu_bar = window.menuBar()

    # File Menu
    file_menu = menu_bar.addMenu("&File")

    # Export submenu
    export_menu = file_menu.addMenu("&Export")

    # Export All Data action (Cmd+Shift+E)
    export_all_action = QAction("&All Data...", window)
    export_all_action.setShortcut("Cmd+Shift+E")
    export_all_action.setStatusTip("Export all application data to a JSON file")
    export_all_action.triggered.connect(
        lambda: _on_export_all_data(window, backup_manager)
    )
    export_menu.addAction(export_all_action)

    # Export Lineups action
    export_lineups_action = QAction("&Lineups...", window)
    export_lineups_action.setStatusTip("Export saved lineups to a JSON file")
    export_lineups_action.triggered.connect(
        lambda: _on_export_lineups(window, backup_manager)
    )
    export_menu.addAction(export_lineups_action)

    # Export Presets action
    export_presets_action = QAction("&Presets...", window)
    export_presets_action.setStatusTip("Export constraint presets to a JSON file")
    export_presets_action.triggered.connect(
        lambda: _on_export_presets(window, backup_manager)
    )
    export_menu.addAction(export_presets_action)

    file_menu.addSeparator()

    # Import submenu
    import_menu = file_menu.addMenu("&Import")

    # Import from Backup action (Cmd+Shift+I)
    import_backup_action = QAction("&From Backup...", window)
    import_backup_action.setShortcut("Cmd+Shift+I")
    import_backup_action.setStatusTip(
        "Import data from a previously exported backup file"
    )
    import_backup_action.triggered.connect(
        lambda: _on_import_backup(window, backup_manager)
    )
    import_menu.addAction(import_backup_action)

    file_menu.addSeparator()

    exit_action = QAction("E&xit", window)
    exit_action.setShortcut(QKeySequence.StandardKey.Quit)  # CMD+Q on Mac
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)

    # Edit Menu with UndoManager integration
    edit_menu = menu_bar.addMenu("&Edit")

    # Undo action - connected to UndoManager
    undo_action = undo_manager.create_undo_action(window, "&Undo")
    undo_action.setShortcut(QKeySequence.StandardKey.Undo)  # CMD+Z on Mac
    edit_menu.addAction(undo_action)

    # Redo action - connected to UndoManager
    redo_action = undo_manager.create_redo_action(window, "&Redo")
    redo_action.setShortcut(QKeySequence.StandardKey.Redo)  # CMD+Shift+Z on Mac
    edit_menu.addAction(redo_action)

    # View Menu
    view_menu = menu_bar.addMenu("&View")

    # Window Menu
    window_menu = menu_bar.addMenu("&Window")
    minimize_action = QAction("Mi&nimize", window)
    minimize_action.setShortcut("Ctrl+M")
    window_menu.addAction(minimize_action)

    # Help Menu
    help_menu = menu_bar.addMenu("&Help")
    about_action = QAction("&About", window)
    help_menu.addAction(about_action)


def _on_export_all_data(window: MainWindow, backup_manager: BackupManager) -> None:
    """Handle File > Export > All Data menu action."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    from apps.native_mac.gui.dialogs.export_dialog import ExportDialog

    dialog = ExportDialog(window)
    if dialog.exec() == ExportDialog.DialogCode.Accepted:
        options = dialog.get_selected_options()
        file_path = options["file_path"]

        if not file_path:
            return

        success, message = backup_manager.export_all(
            file_path, options=options["options"]
        )

        if success:
            QMessageBox.information(
                window,
                "Export Complete",
                f"{message}\n\nFile saved to:\n{file_path}",
            )
        else:
            QMessageBox.critical(
                window,
                "Export Failed",
                f"Failed to export data:\n\n{message}",
            )


def _on_export_lineups(window: MainWindow, backup_manager: BackupManager) -> None:
    """Handle File > Export > Lineups menu action."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    from datetime import datetime
    from pathlib import Path

    default_filename = f"nascar_lineups_{datetime.now().strftime('%Y-%m-%d')}.json"
    file_path, _ = QFileDialog.getSaveFileName(
        window,
        "Export Lineups",
        str(Path.home() / "Downloads" / default_filename),
        "JSON Files (*.json);;All Files (*)",
    )

    if not file_path:
        return

    success, message = backup_manager.export_lineups(file_path)

    if success:
        QMessageBox.information(
            window,
            "Export Complete",
            f"{message}\n\nFile saved to:\n{file_path}",
        )
    else:
        QMessageBox.critical(
            window,
            "Export Failed",
            f"Failed to export lineups:\n\n{message}",
        )


def _on_export_presets(window: MainWindow, backup_manager: BackupManager) -> None:
    """Handle File > Export > Presets menu action."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    from datetime import datetime
    from pathlib import Path

    default_filename = f"nascar_presets_{datetime.now().strftime('%Y-%m-%d')}.json"
    file_path, _ = QFileDialog.getSaveFileName(
        window,
        "Export Presets",
        str(Path.home() / "Downloads" / default_filename),
        "JSON Files (*.json);;All Files (*)",
    )

    if not file_path:
        return

    success, message = backup_manager.export_presets(file_path)

    if success:
        QMessageBox.information(
            window,
            "Export Complete",
            f"{message}\n\nFile saved to:\n{file_path}",
        )
    else:
        QMessageBox.critical(
            window,
            "Export Failed",
            f"Failed to export presets:\n\n{message}",
        )


def _on_import_backup(window: MainWindow, backup_manager: BackupManager) -> None:
    """Handle File > Import > From Backup menu action."""
    from PySide6.QtWidgets import QMessageBox
    from apps.native_mac.gui.dialogs.export_dialog import ImportDialog

    dialog = ImportDialog(window, backup_manager=backup_manager)
    if dialog.exec() == ImportDialog.DialogCode.Accepted:
        import_options = dialog.get_import_options()
        file_path = import_options["file_path"]
        merge_strategy = import_options["merge_strategy"]

        if not file_path:
            return

        # Create automatic backup first
        auto_backup_success, auto_backup_path = backup_manager.create_automatic_backup()

        if not auto_backup_success:
            reply = QMessageBox.warning(
                window,
                "Automatic Backup Failed",
                "Could not create automatic backup of current data.\n\n"
                f"Error: {auto_backup_path}\n\n"
                "Do you want to continue with the import anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Perform import
        success, message = backup_manager.import_backup(
            file_path, options={"merge_strategy": merge_strategy}
        )

        if success:
            # Build success message
            success_msg = f"{message}\n\n"
            if auto_backup_success:
                success_msg += f"Automatic backup created at:\n{auto_backup_path}"

            QMessageBox.information(
                window,
                "Import Complete",
                success_msg,
            )
        else:
            QMessageBox.critical(
                window,
                "Import Failed",
                f"Failed to import data:\n\n{message}",
            )


def main():
    """Main application entry point."""
    app = MainApplication(sys.argv)

    # Set organization info for settings persistence
    app.setOrganizationName("Zax")
    app.setApplicationName("NASCAR DFS Optimizer")

    # Create session manager for persistence
    session_manager = SessionManager()

    # Create database manager
    database_manager = DatabaseManager()

    # Create preset manager for constraint presets
    preset_manager = PresetManager()

    # Create optimization engine for session restoration
    optimization_engine = OptimizationEngine(database_manager)

    # Initialize GPU client if enabled
    gpu_client = None
    try:
        gpu_enabled = session_manager.load_state("gpu/enabled", False)
        if gpu_enabled:
            gpu_url = session_manager.load_state("gpu/url", "http://192.168.1.100:8000")
            gpu_timeout = session_manager.load_state("gpu/timeout", 30)
            # API key is not loaded from persistent storage for security
            gpu_client = GPUWorkerClient(base_url=gpu_url, timeout=gpu_timeout)
            logger.info(f"GPU client initialized: {gpu_url}")
    except Exception as e:
        logger.warning(f"Failed to initialize GPU client: {e}")
        gpu_client = None

    # Create JobManager for background job execution
    job_manager = JobManager(database_manager, gpu_client=gpu_client)

    # Create UndoManager for undo/redo functionality
    undo_manager = UndoManager()

    # Create ShortcutManager for keyboard shortcuts
    shortcut_manager = ShortcutManager()

    # Create BackupManager for export/import functionality
    backup_manager = BackupManager(database_manager, preset_manager)

    # Create and show main window with all managers
    window = MainWindow(
        session_manager=session_manager,
        db_manager=database_manager,
        preset_manager=preset_manager,
        shortcut_manager=shortcut_manager,
        backup_manager=backup_manager,
    )
    create_application_menus(window, undo_manager, backup_manager)

    # Wire JobManager to window and tabs
    window.set_job_manager(job_manager)
    logger.info("JobManager wired to MainWindow and tabs")

    # Wire UndoManager to window and tabs
    window.set_undo_manager(undo_manager)
    logger.info("UndoManager wired to MainWindow and tabs")

    # Wire PresetManager to window
    window.set_preset_manager(preset_manager)
    logger.info("PresetManager wired to MainWindow")

    # Connect PresetsTab to ConstraintPanel for preset loading
    if hasattr(window, "presets_tab") and window.presets_tab:
        if hasattr(window, "constraint_panel") and window.constraint_panel:
            window.presets_tab.preset_loaded.connect(
                window.constraint_panel.set_constraints
            )
            logger.info("PresetsTab connected to ConstraintPanel")

    # Connect JobsTab re-run signal to JobManager
    if hasattr(window, "jobs_tab") and window.jobs_tab:
        window.jobs_tab.rerun_job_requested.connect(
            lambda config: job_manager.submit_job(
                config, job_name=config.get("_rerun_name", "Re-run Job")
            )
        )
        logger.info("JobsTab re-run signal connected to JobManager")

    # Connect file open signal for CSV file association
    app.fileOpened.connect(window.on_file_opened)

    # Set up dock icon handler
    dock_handler = DockIconHandler(app)
    dock_handler.race_selected.connect(window._on_dock_race_selected)
    dock_handler.new_race_triggered.connect(window._on_dock_new_race)
    dock_handler.generate_lineups_triggered.connect(window._on_dock_generate_lineups)
    dock_handler.preferences_triggered.connect(window._on_dock_preferences)
    window.set_dock_handler(dock_handler)

    # Set up system tray icon (skip in CI/test mode)
    tray_icon = None
    if not os.environ.get("CI") and not os.environ.get("TEST_MODE"):
        tray_icon = SystemTrayIcon(job_manager=job_manager)

        # Connect tray icon signals
        tray_icon.show_main_window_triggered.connect(window.show)
        tray_icon.show_main_window_triggered.connect(window.raise_)
        tray_icon.preferences_triggered.connect(window._on_dock_preferences)
        tray_icon.quit_triggered.connect(app.quit)

        # Show tray icon
        tray_icon.show()

    # Connect JobManager signals to update dock badge and tray icon
    def update_job_status():
        """Update dock badge and tray icon with current job status."""
        running_count = job_manager.get_running_jobs_count()
        queued_count = job_manager.get_queued_jobs_count()
        total_active = running_count + queued_count

        # Update dock badge
        dock_handler.set_badge_count(total_active)

        # Update tray icon menu
        if tray_icon:
            recent_jobs = job_manager.get_recent_jobs(limit=5)
            tray_icon.update_menu(running_count=running_count, recent_jobs=recent_jobs)

    # Connect job signals
    job_manager.job_started.connect(lambda jid: update_job_status())
    job_manager.job_completed.connect(lambda jid, lineups: update_job_status())
    job_manager.job_failed.connect(lambda jid, error: update_job_status())
    job_manager.job_cancelled.connect(lambda jid: update_job_status())

    # Show notification on job completion
    def on_job_completed(job_id: str, lineups: list):
        """Handle job completion with notification."""
        job = job_manager.get_job(job_id)
        if job:
            job_name = job.get("name", "Optimization")
            lineup_count = len(lineups) if lineups else 0

            if tray_icon:
                tray_icon.show_notification(
                    "Optimization Complete",
                    f"Job '{job_name}' finished with {lineup_count} lineups",
                )

            # Also bounce dock
            dock_handler.bounce(critical=False)

    job_manager.job_completed.connect(on_job_completed)

    # Set up periodic updates for job status
    status_timer = QTimer(app)
    status_timer.timeout.connect(update_job_status)
    status_timer.start(2000)  # Update every 2 seconds

    # Restore previous session
    restorer = SessionRestorer(session_manager, database_manager, optimization_engine)
    restorer.set_main_window(window)
    restorer.restore_session()

    window.show()

    # Run application
    exit_code = app.exec()

    # Cleanup
    job_manager.shutdown(wait=True)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
