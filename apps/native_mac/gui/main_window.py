"""Main window for NASCAR DFS Optimizer GUI.

Provides tabbed interface with Race Data, Optimization, Lineups, and Settings tabs.
Integrates with SessionManager for window geometry persistence.
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableView,
    QAbstractItemView,
    QFileDialog,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence
from typing import Optional, Dict, Any
from pathlib import Path

# QAbstractItemView selection constants
SelectionMode = QAbstractItemView.SelectionMode
SelectionBehavior = QAbstractItemView.SelectionBehavior

from ..persistence.database import DatabaseManager
from ..persistence.session_manager import SessionManager
from ..optimization.engine import OptimizationEngine
from ..notification_manager import NotificationManager
from ..shortcuts.shortcut_manager import ShortcutManager
from .controllers.data_controller import DataController
from .models.driver_model import DriverTableModel
from .models.lineup_model import LineupTableModel
from .views.driver_table import DriverTableView
from .views.optimization_tab import OptimizationTab
from .views.lineups_tab import LineupsTab
from .views.jobs_tab import JobsTab
from .views.settings_tab import SettingsTab
from .views.veto_log_tab import VetoLogTab
from .views.presets_tab import PresetsTab
from .views.split_editor_tab import SplitEditorTab
from .widgets.about_dialog import AboutDialog
from ..kernel_logger import KernelVetoLogger


class MainWindow(QMainWindow):
    """Main application window with tabbed interface.

    Provides four main tabs:
    - Race Data: Driver table with projections and salaries
    - Optimization: Lineup optimization interface (placeholder)
    - Lineups: Saved lineups viewer (placeholder)
    - Settings: Application settings (placeholder)

    Integrates with SessionManager for window geometry persistence.
    """

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        preset_manager: Optional[Any] = None,
        shortcut_manager: Optional[ShortcutManager] = None,
        db_manager: Optional[DatabaseManager] = None,
        backup_manager: Optional[Any] = None,
    ):
        """Initialize the main window.

        Args:
            session_manager: SessionManager instance for persistence.
                           If None, creates a new one.
            preset_manager: PresetManager instance for constraint presets.
            shortcut_manager: ShortcutManager instance for keyboard shortcuts.
            db_manager: DatabaseManager instance for data operations.
                       If None, creates a new one.
            backup_manager: BackupManager instance for export/import operations.
        """
        super().__init__()

        self.session_manager = session_manager or SessionManager()
        self.db_manager = db_manager or DatabaseManager()
        self.shortcut_manager = shortcut_manager or ShortcutManager(self)
        self.backup_manager = backup_manager

        # Create data controller
        self.data_controller = DataController(self.db_manager)

        # Create optimization engine
        self.optimization_engine = OptimizationEngine(self.db_manager)

        # Create notification manager
        self.notification_manager = NotificationManager(self)
        self.notification_manager.notification_clicked.connect(
            self._on_notification_clicked
        )

        # Track current race ID for session persistence
        self.current_race_id: Optional[int] = None

        # JobManager reference (set after creation in main.py)
        self.job_manager: Optional[Any] = None

        # PresetManager reference (set via setter after creation in main.py)
        self.preset_manager: Optional[Any] = None

        # Reference to constraint panel for preset loading
        self.constraint_panel: Optional[Any] = None

        # Set window properties
        self.setWindowTitle("NASCAR DFS Optimizer")
        self.setMinimumSize(QSize(1200, 800))

        # Create central tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Create tabs
        self._create_tabs()

        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Setup menu bar
        self._create_menu_bar()

        # Setup status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Restore window geometry
        self._restore_geometry()

    def _create_tabs(self) -> None:
        """Create all application tabs."""
        # Race Data tab
        race_data_tab = self._create_race_data_tab()
        self.tab_widget.addTab(race_data_tab, "Race Data")

        # Optimization tab (will be recreated with job_manager after it's available)
        optimization_tab = self._create_optimization_tab()
        self.tab_widget.addTab(optimization_tab, "Optimization")

        # Split Editor tab (split-view with live preview)
        self.split_editor_tab = self._create_split_editor_tab()
        self.tab_widget.addTab(self.split_editor_tab, "Split Editor")

        # Presets tab (preset_manager will be set via setter after creation)
        self.presets_tab = PresetsTab(preset_manager=self.preset_manager)
        self.tab_widget.addTab(self.presets_tab, "Presets")

        # Lineups tab
        lineups_tab = self._create_lineups_tab()
        self.tab_widget.addTab(lineups_tab, "Lineups")

        # Jobs tab (job_manager will be set after JobManager is created)
        self.jobs_tab = JobsTab(database_manager=self.db_manager, job_manager=None)
        self.tab_widget.addTab(self.jobs_tab, "Jobs")

        # Veto Logs tab
        self.veto_logger = KernelVetoLogger(
            db_path=str(
                Path.home()
                / "Library"
                / "Application Support"
                / "NascarOptimizer"
                / "veto_logs.db"
            ),
            batch_mode=True,
        )
        self.veto_log_tab = VetoLogTab(veto_logger=self.veto_logger)
        self.tab_widget.addTab(self.veto_log_tab, "Veto Logs")

        # Settings tab
        settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(settings_tab, "Settings")

    def _create_race_data_tab(self) -> QWidget:
        """Create the Race Data tab with driver table.

        Returns:
            QWidget containing the race data interface.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create sample driver data for testing
        sample_drivers = [
            {
                "name": "Kyle Larson",
                "salary": 12500,
                "projected_points": 52.3,
                "ownership": 25.5,
                "team": "Hendrick Motorsports",
            },
            {
                "name": "Max Verstappen",
                "salary": 12000,
                "projected_points": 48.7,
                "ownership": 22.1,
                "team": "Red Bull Racing",
            },
            {
                "name": "William Byron",
                "salary": 10500,
                "projected_points": 45.2,
                "ownership": 18.3,
                "team": "Hendrick Motorsports",
            },
            {
                "name": "Christopher Bell",
                "salary": 9800,
                "projected_points": 42.8,
                "ownership": 15.7,
                "team": "Joe Gibbs Racing",
            },
            {
                "name": "Tyler Reddick",
                "salary": 9200,
                "projected_points": 40.1,
                "ownership": 12.5,
                "team": "23XI Racing",
            },
            {
                "name": "Ryan Blaney",
                "salary": 10100,
                "projected_points": 38.9,
                "ownership": 14.2,
                "team": "Team Penske",
            },
            {
                "name": "Denny Hamlin",
                "salary": 9900,
                "projected_points": 37.5,
                "ownership": 13.8,
                "team": "Joe Gibbs Racing",
            },
            {
                "name": "Joey Logano",
                "salary": 9400,
                "projected_points": 36.2,
                "ownership": 11.9,
                "team": "Team Penske",
            },
            {
                "name": "Chase Elliott",
                "salary": 10800,
                "projected_points": 35.8,
                "ownership": 16.4,
                "team": "Hendrick Motorsports",
            },
            {
                "name": "Alex Bowman",
                "salary": 8500,
                "projected_points": 34.1,
                "ownership": 9.2,
                "team": "Hendrick Motorsports",
            },
        ]

        # Create model first
        self.driver_model = DriverTableModel(sample_drivers)

        # Create table view for drivers with DriverTableView
        self.driver_table = DriverTableView(self.data_controller, self.driver_model)

        # Connect data_loaded signal to status bar
        self.driver_table.data_loaded.connect(self._on_drivers_loaded)

        # Add table to layout
        layout.addWidget(self.driver_table)

        return tab

    def _create_optimization_tab(self) -> QWidget:
        """Create the Optimization tab.

        Returns:
            QWidget containing the optimization interface.
        """
        self.optimization_tab = OptimizationTab(
            database_manager=self.db_manager,
            optimization_engine=self.optimization_engine,
        )

        # Connect lineups_generated signal to update lineup model
        self.optimization_tab.lineups_generated.connect(self._on_lineups_generated)

        # Connect optimization_complete signal for dock bounce
        self.optimization_tab.optimization_complete.connect(
            lambda: self.trigger_dock_bounce(critical=True)
        )

        # Connect notify_complete signal for macOS notification
        self.optimization_tab.notify_complete.connect(self.notify_optimization_complete)

        return self.optimization_tab

    def _create_split_editor_tab(self) -> QWidget:
        """Create the Split Editor tab with live preview.

        Returns:
            QWidget containing the split editor interface.
        """
        self.split_editor_tab = SplitEditorTab(
            database_manager=self.db_manager,
            optimization_engine=self.optimization_engine,
            preset_manager=self.preset_manager,
        )

        # Connect signals for split editor
        self.split_editor_tab.lineups_generated.connect(self._on_lineups_generated)
        self.split_editor_tab.optimization_complete.connect(
            lambda: self.trigger_dock_bounce(critical=True)
        )
        self.split_editor_tab.notify_complete.connect(self.notify_optimization_complete)

        return self.split_editor_tab

    def _create_lineups_tab(self) -> QWidget:
        """Create the Lineups tab.

        Returns:
            QWidget containing the lineups interface with export functionality.
        """
        # Create lineup model for the table
        self.lineup_model = LineupTableModel()

        # Create the lineups tab
        self.lineups_tab = LineupsTab(
            database_manager=self.db_manager,
            data_controller=self.data_controller,
            lineup_model=self.lineup_model,
        )

        return self.lineups_tab

    def _create_settings_tab(self) -> QWidget:
        """Create the Settings tab.

        Returns:
            QWidget containing the settings interface.
        """
        self.settings_tab = SettingsTab(
            session_manager=self.session_manager,
            database_manager=self.db_manager,
            backup_manager=self.backup_manager,
        )

        # Connect settings changed signal for theme updates
        self.settings_tab.settings_changed.connect(self._on_settings_changed)

        return self.settings_tab

    def _create_menu_bar(self) -> None:
        """Create the application menu bar with ShortcutManager integration."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # New Race action (Cmd+N)
        new_action = self.shortcut_manager.create_action(
            "new_race", "New Race", self._on_new_race, parent=self
        )
        new_action.setStatusTip("Create a new race")
        file_menu.addAction(new_action)

        # Open Data File action (Cmd+O)
        open_action = self.shortcut_manager.create_action(
            "open_data", "Open Data File...", self._open_file, parent=self
        )
        open_action.setStatusTip("Open driver data CSV file")
        file_menu.addAction(open_action)

        # Save Lineups action (Cmd+S)
        save_action = self.shortcut_manager.create_action(
            "save_lineups", "Save Lineups", self._on_save_lineups, parent=self
        )
        save_action.setStatusTip("Save current lineups")
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # Export CSV action (Ctrl+E)
        export_action = self.shortcut_manager.create_action(
            "export_csv", "Export to DraftKings...", self._on_export_csv, parent=self
        )
        export_action.setStatusTip("Export lineups to DraftKings CSV format")
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        # Quit action (Cmd+Q)
        quit_action = self.shortcut_manager.create_action(
            "quit", "Quit", self.close, parent=self
        )
        quit_action.setStatusTip("Quit the application")
        quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        # Undo action (Cmd+Z)
        undo_action = self.shortcut_manager.create_action(
            "undo", "Undo", self._on_undo, parent=self
        )
        undo_action.setStatusTip("Undo last action")
        edit_menu.addAction(undo_action)

        # Redo action (Cmd+Shift+Z)
        redo_action = self.shortcut_manager.create_action(
            "redo", "Redo", self._on_redo, parent=self
        )
        redo_action.setStatusTip("Redo last undone action")
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        # Preferences action (Cmd+,)
        prefs_action = self.shortcut_manager.create_action(
            "preferences", "Preferences", self._on_preferences, parent=self
        )
        prefs_action.setStatusTip("Open preferences")
        prefs_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        edit_menu.addAction(prefs_action)

        # Optimization menu
        optimize_menu = menubar.addMenu("&Optimize")

        # Run Optimization action (Cmd+Return)
        run_opt_action = self.shortcut_manager.create_action(
            "optimize", "Run Optimization", self._on_run_optimization, parent=self
        )
        run_opt_action.setStatusTip("Run lineup optimization")
        optimize_menu.addAction(run_opt_action)

        # Cancel action (Cmd+.)
        cancel_action = self.shortcut_manager.create_action(
            "cancel", "Cancel", self._on_cancel, parent=self
        )
        cancel_action.setStatusTip("Cancel current operation")
        optimize_menu.addAction(cancel_action)

        optimize_menu.addSeparator()

        # Apply Preset action (Ctrl+P)
        apply_preset_action = self.shortcut_manager.create_action(
            "apply_preset",
            "Apply Constraint Preset",
            self._on_apply_preset,
            parent=self,
        )
        apply_preset_action.setStatusTip("Apply a saved constraint preset")
        optimize_menu.addAction(apply_preset_action)

        # Save Preset action (Ctrl+Shift+P)
        save_preset_action = self.shortcut_manager.create_action(
            "save_preset", "Save Constraint Preset", self._on_save_preset, parent=self
        )
        save_preset_action.setStatusTip("Save current constraints as preset")
        optimize_menu.addAction(save_preset_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        # Toggle Split action (Ctrl+\)
        toggle_split_action = self.shortcut_manager.create_action(
            "toggle_split", "Toggle Split View", self._on_toggle_split, parent=self
        )
        toggle_split_action.setStatusTip("Toggle split-pane layout")
        view_menu.addAction(toggle_split_action)

        view_menu.addSeparator()

        # Focus actions
        focus_constraints_action = self.shortcut_manager.create_action(
            "focus_constraints",
            "Focus Constraints Panel",
            self._on_focus_constraints,
            parent=self,
        )
        focus_constraints_action.setStatusTip("Focus the constraints panel (Ctrl+1)")
        view_menu.addAction(focus_constraints_action)

        focus_preview_action = self.shortcut_manager.create_action(
            "focus_preview", "Focus Preview Panel", self._on_focus_preview, parent=self
        )
        focus_preview_action.setStatusTip("Focus the preview panel (Ctrl+2)")
        view_menu.addAction(focus_preview_action)

        focus_logs_action = self.shortcut_manager.create_action(
            "focus_logs", "Focus Log Panel", self._on_focus_logs, parent=self
        )
        focus_logs_action.setStatusTip("Focus the log panel (Ctrl+3)")
        view_menu.addAction(focus_logs_action)

        view_menu.addSeparator()

        # Customize Shortcuts action
        customize_shortcuts_action = self.shortcut_manager.create_action(
            "customize_shortcuts",
            "Customize Keyboard Shortcuts...",
            self._on_customize_shortcuts,
            parent=self,
        )
        customize_shortcuts_action.setStatusTip("Customize keyboard shortcuts")
        view_menu.addAction(customize_shortcuts_action)

        # Navigate menu
        navigate_menu = menubar.addMenu("&Navigate")

        # Next Tab action (Ctrl+Tab)
        next_tab_action = self.shortcut_manager.create_action(
            "next_tab", "Next Tab", self._on_next_tab, parent=self
        )
        next_tab_action.setStatusTip("Switch to next tab")
        navigate_menu.addAction(next_tab_action)

        # Previous Tab action (Ctrl+Shift+Tab)
        prev_tab_action = self.shortcut_manager.create_action(
            "prev_tab", "Previous Tab", self._on_prev_tab, parent=self
        )
        prev_tab_action.setStatusTip("Switch to previous tab")
        navigate_menu.addAction(prev_tab_action)

        navigate_menu.addSeparator()

        # Show Jobs action (Ctrl+J)
        show_jobs_action = self.shortcut_manager.create_action(
            "show_jobs", "Show Jobs Tab", self._on_show_jobs, parent=self
        )
        show_jobs_action.setStatusTip("Switch to Jobs tab")
        navigate_menu.addAction(show_jobs_action)

        # Show Lineups action (Ctrl+L)
        show_lineups_action = self.shortcut_manager.create_action(
            "show_lineups", "Show Lineups Tab", self._on_show_lineups, parent=self
        )
        show_lineups_action.setStatusTip("Switch to Lineups tab")
        navigate_menu.addAction(show_lineups_action)

        # Find action (Cmd+F)
        find_action = self.shortcut_manager.create_action(
            "find", "Find", self._on_find, parent=self
        )
        find_action.setStatusTip("Find in current view")
        navigate_menu.addAction(find_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        # About action
        about_action = QAction("About NASCAR DFS Optimizer", self)
        about_action.setMenuRole(QAction.MenuRole.AboutRole)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _open_file(self) -> None:
        """Handle File > Open Data File menu action.

        Opens a native macOS file dialog to select a CSV file,
        then imports the driver data and updates the table view.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Driver Data CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        self.status_bar.showMessage(f"Loading {file_path}...", 0)
        success = self.driver_table.load_drivers_from_csv(file_path)

        if success:
            self.status_bar.showMessage(f"Loaded {file_path}", 3000)
        else:
            self.status_bar.showMessage("Import failed", 3000)

    def _on_new_race(self) -> None:
        """Handle File > New Race menu action (Cmd+N)."""
        self.tab_widget.setCurrentIndex(0)
        self._open_file()

    def _on_save_lineups(self) -> None:
        """Handle File > Save Lineups menu action (Cmd+S)."""
        if hasattr(self, "lineups_tab"):
            self.lineups_tab._on_save_lineups()

    def _on_export_csv(self) -> None:
        """Handle File > Export to DraftKings menu action (Ctrl+E)."""
        self.tab_widget.setCurrentIndex(2)
        if hasattr(self, "lineups_tab"):
            self.lineups_tab._on_export_csv()

    def _on_undo(self) -> None:
        """Handle Edit > Undo menu action (Cmd+Z)."""
        if self.undo_manager:
            self.undo_manager.undo()
        else:
            self.status_bar.showMessage("Undo not yet implemented", 2000)

    def _on_redo(self) -> None:
        """Handle Edit > Redo menu action (Cmd+Shift+Z)."""
        if self.undo_manager:
            self.undo_manager.redo()
        else:
            self.status_bar.showMessage("Redo not yet implemented", 2000)

    def _on_preferences(self) -> None:
        """Handle Edit > Preferences menu action (Cmd+,)."""
        self.tab_widget.setCurrentIndex(5)  # Settings tab

    def _on_run_optimization(self) -> None:
        """Handle Optimize > Run Optimization menu action (Cmd+Return)."""
        self.tab_widget.setCurrentIndex(1)
        if hasattr(self, "optimization_tab"):
            self.optimization_tab._on_run_optimization()

    def _on_cancel(self) -> None:
        """Handle Optimize > Cancel menu action (Cmd+.)."""
        self.status_bar.showMessage("Cancel not yet implemented", 2000)

    def _on_apply_preset(self) -> None:
        """Handle Optimize > Apply Constraint Preset menu action (Ctrl+P)."""
        self.status_bar.showMessage("Apply preset not yet implemented", 2000)

    def _on_save_preset(self) -> None:
        """Handle Optimize > Save Constraint Preset menu action (Ctrl+Shift+P)."""
        self.status_bar.showMessage("Save preset not yet implemented", 2000)

    def _on_toggle_split(self) -> None:
        """Handle View > Toggle Split View menu action (Ctrl+\\)."""
        # Switch to Split Editor tab and toggle split view
        if hasattr(self, "split_editor_tab") and self.split_editor_tab:
            self.tab_widget.setCurrentWidget(self.split_editor_tab)
            self.split_editor_tab.toggle_split_view()
        else:
            self.status_bar.showMessage("Split Editor not available", 2000)

    def _on_focus_constraints(self) -> None:
        """Handle View > Focus Constraints Panel menu action (Ctrl+1)."""
        # Check if we're on split editor tab
        if self.tab_widget.currentWidget() == self.split_editor_tab:
            self.split_editor_tab.focus_constraints()
        else:
            self.tab_widget.setCurrentIndex(1)
            if hasattr(self, "optimization_tab"):
                self.optimization_tab.set_focus_to_constraints()

    def _on_focus_preview(self) -> None:
        """Handle View > Focus Preview Panel menu action (Ctrl+2)."""
        # Check if we're on split editor tab
        if (
            hasattr(self, "split_editor_tab")
            and self.tab_widget.currentWidget() == self.split_editor_tab
        ):
            self.split_editor_tab.focus_preview()
        else:
            self.tab_widget.setCurrentIndex(2)

    def _on_focus_logs(self) -> None:
        """Handle View > Focus Log Panel menu action (Ctrl+3)."""
        # Check if we're on split editor tab
        if (
            hasattr(self, "split_editor_tab")
            and self.tab_widget.currentWidget() == self.split_editor_tab
        ):
            self.split_editor_tab.focus_logs()
        else:
            self.tab_widget.setCurrentIndex(4)

    def _on_customize_shortcuts(self) -> None:
        """Handle View > Customize Keyboard Shortcuts menu action."""
        from .dialogs.shortcut_config_dialog import ShortcutConfigDialog

        dialog = ShortcutConfigDialog(self.shortcut_manager, self)
        dialog.exec()

    def _on_next_tab(self) -> None:
        """Handle Navigate > Next Tab menu action (Ctrl+Tab)."""
        current = self.tab_widget.currentIndex()
        next_index = (current + 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(next_index)

    def _on_prev_tab(self) -> None:
        """Handle Navigate > Previous Tab menu action (Ctrl+Shift+Tab)."""
        current = self.tab_widget.currentIndex()
        prev_index = (current - 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(prev_index)

    def _on_show_jobs(self) -> None:
        """Handle Navigate > Show Jobs Tab menu action (Ctrl+J)."""
        self.tab_widget.setCurrentIndex(3)

    def _on_show_lineups(self) -> None:
        """Handle Navigate > Show Lineups Tab menu action (Ctrl+L)."""
        self.tab_widget.setCurrentIndex(2)

    def _on_find(self) -> None:
        """Handle Navigate > Find menu action (Cmd+F)."""
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0 and hasattr(self, "driver_table"):
            self.driver_table.setFocus()
        self.status_bar.showMessage("Find: Type to search", 3000)

    def _on_drivers_loaded(self, count: int) -> None:
        """Handle data_loaded signal from DriverTableView.

        Args:
            count: Number of drivers loaded.
        """
        self.status_bar.showMessage(f"Loaded {count} drivers", 3000)

        # Pass drivers to optimization tab
        if hasattr(self, "optimization_tab") and self.driver_model:
            drivers = self.driver_model._drivers
            self.optimization_tab.set_drivers(drivers)

        # Pass drivers to split editor tab
        if (
            hasattr(self, "split_editor_tab")
            and self.split_editor_tab
            and self.driver_model
        ):
            self.split_editor_tab.set_drivers(self.driver_model._drivers)

    def _on_lineups_generated(self, lineups: list) -> None:
        """Handle lineups_generated signal from OptimizationTab.

        Args:
            lineups: List of generated lineup dictionaries.
        """
        self.status_bar.showMessage(f"Generated {len(lineups)} lineups", 3000)

        # Get current race_id from optimization tab and update main window
        race_id = getattr(self.optimization_tab, "current_race_id", None)
        if race_id:
            self.current_race_id = race_id

        # Pass lineups to the lineups tab
        if hasattr(self, "lineups_tab"):
            self.lineups_tab.set_lineups(lineups, race_id)

        # Switch to Lineups tab to show results
        lineups_tab_index = (
            3  # Lineups tab is now index 3 (after Race Data, Optimization, Presets)
        )
        self.tab_widget.setCurrentIndex(lineups_tab_index)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change event.

        Updates window title to reflect current tab.

        Args:
            index: Index of the newly selected tab.
        """
        tab_name = self.tab_widget.tabText(index)
        self.setWindowTitle(f"NASCAR DFS Optimizer - {tab_name}")

    def on_file_opened(self, file_path: str) -> None:
        """Handle file open event from macOS file association.

        Called when user double-clicks a CSV file associated with the app
        or drags a CSV file onto the app icon.

        Args:
            file_path: Path to the CSV file that was opened.
        """
        # Switch to Race Data tab (index 0)
        self.tab_widget.setCurrentIndex(0)

        # Load the CSV file
        self.status_bar.showMessage(f"Opening {file_path}...", 0)
        success = self.driver_table.load_drivers_from_csv(file_path)

        if success:
            self.status_bar.showMessage(f"Opened {file_path}", 3000)
        else:
            self.status_bar.showMessage("Failed to open file", 3000)

    def _restore_geometry(self) -> None:
        """Restore window geometry from session manager."""
        try:
            self.session_manager.load_window_geometry(self)
        except Exception:
            # If restoration fails, use default geometry
            pass

    def _show_about_dialog(self) -> None:
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def set_dock_handler(self, dock_handler) -> None:
        """Set the dock icon handler for bounce and menu integration.

        Args:
            dock_handler: DockIconHandler instance
        """
        self._dock_handler = dock_handler

    def trigger_dock_bounce(self, critical: bool = False) -> None:
        """Trigger dock icon bounce for user attention.

        Args:
            critical: If True, dock bounces until activated
        """
        if hasattr(self, "_dock_handler") and self._dock_handler:
            self._dock_handler.bounce(critical)

    def update_dock_menu(self, recent_races: list) -> None:
        """Update dock menu with recent races.

        Args:
            recent_races: List of race dictionaries with 'id' and 'track_name'
        """
        if hasattr(self, "_dock_handler") and self._dock_handler:
            self._dock_handler.set_recent_races(recent_races)

    def _on_dock_race_selected(self, race_id: int) -> None:
        """Handle race selection from dock menu.

        Args:
            race_id: ID of the selected race
        """
        # Switch to Race Data tab and load the race
        self.tab_widget.setCurrentIndex(0)
        self.status_bar.showMessage(f"Loading race {race_id}...", 3000)

    def _on_dock_new_race(self) -> None:
        """Handle New Race action from dock menu."""
        # Switch to Race Data tab and trigger file open
        self.tab_widget.setCurrentIndex(0)
        self._open_file()

    def _on_dock_generate_lineups(self) -> None:
        """Handle Generate Lineups action from dock menu."""
        # Switch to Optimization tab
        self.tab_widget.setCurrentIndex(1)
        # Trigger optimization if drivers are loaded
        if hasattr(self, "optimization_tab"):
            self.optimization_tab._on_run_optimization()

    def _on_dock_preferences(self) -> None:
        """Handle Preferences action from dock menu."""
        # Switch to Settings tab
        self.tab_widget.setCurrentIndex(4)

    def _on_notification_clicked(self, identifier: str) -> None:
        """Handle notification click from macOS notification center.

        Args:
            identifier: The action identifier from the notification
        """
        if identifier == "view_lineups":
            # Switch to Lineups tab
            self.tab_widget.setCurrentIndex(2)
            self.status_bar.showMessage("Showing lineups from notification", 3000)

    def notify_optimization_complete(self, num_lineups: int) -> None:
        """Send notification when optimization completes.

        Args:
            num_lineups: Number of lineups generated
        """
        if hasattr(self, "notification_manager"):
            self.notification_manager.notify_optimization_complete(num_lineups)

    def _on_settings_changed(self) -> None:
        """Handle settings changes from SettingsTab.

        Applies settings that can take effect immediately.
        """
        # Apply alternating row colors setting to tables
        if hasattr(self, "driver_table"):
            alternating = self.session_manager.load_state(
                "alternating_row_colors", True
            )
            self.driver_table.setAlternatingRowColors(alternating)

        if hasattr(self, "lineups_tab") and hasattr(self.lineups_tab, "table_view"):
            alternating = self.session_manager.load_state(
                "alternating_row_colors", True
            )
            self.lineups_tab.table_view.setAlternatingRowColors(alternating)

        # Theme changes require restart - could show a message here
        # For now, theme is applied on next launch

    def get_current_race_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current race.

        Returns:
            Dictionary with race info or None if no current race.
        """
        if not self.current_race_id:
            return None

        try:
            races = self.db_manager.load_races()
            for race in races:
                if race.get("id") == self.current_race_id:
                    return race
        except Exception:
            pass

        return None

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Saves session state before closing:
        - Window geometry
        - Last viewed race
        - Active tab index

        Args:
            event: Close event object.
        """
        try:
            # Save window geometry
            self.session_manager.save_window_geometry(self)

            # Save last viewed race
            if self.current_race_id:
                race_info = self.get_current_race_info()
                if race_info:
                    self.session_manager.save_last_race(
                        race_id=self.current_race_id,
                        track_name=race_info.get("track_name", "Unknown"),
                        race_date=race_info.get("race_date", ""),
                    )

            # Save active tab
            self.session_manager.save_state(
                "active_tab", self.tab_widget.currentIndex()
            )
        except Exception:
            # If saving fails, still allow close
            pass

        event.accept()

    def set_job_manager(self, job_manager: Optional[Any]) -> None:
        """Set the JobManager and wire it to all tabs.

        Called from main.py after JobManager is created.

        Args:
            job_manager: JobManager instance for job queue operations.
        """
        self.job_manager = job_manager

        # Wire JobsTab
        if hasattr(self, "jobs_tab") and self.jobs_tab:
            self.jobs_tab.job_manager = job_manager

        # Recreate OptimizationTab with job_manager
        if hasattr(self, "optimization_tab") and self.optimization_tab:
            # Get current tab index
            current_index = self.tab_widget.currentIndex()

            # Remove old optimization tab
            opt_index = self.tab_widget.indexOf(self.optimization_tab)
            if opt_index >= 0:
                self.tab_widget.removeTab(opt_index)

            # Create new optimization tab with job_manager and preset_manager
            self.optimization_tab = OptimizationTab(
                database_manager=self.db_manager,
                optimization_engine=self.optimization_engine,
                job_manager=job_manager,
                preset_manager=self.preset_manager,
            )

            # Reconnect signals
            self.optimization_tab.lineups_generated.connect(self._on_lineups_generated)
            self.optimization_tab.optimization_complete.connect(
                lambda: self.trigger_dock_bounce(critical=True)
            )
            self.optimization_tab.notify_complete.connect(
                self.notify_optimization_complete
            )

            # Insert at the original position (index 1)
            self.tab_widget.insertTab(1, self.optimization_tab, "Optimization")

            # Restore current tab if it was the optimization tab
            if current_index == opt_index:
                self.tab_widget.setCurrentIndex(1)

        # Wire SplitEditorTab with job manager
        if hasattr(self, "split_editor_tab") and self.split_editor_tab:
            self.split_editor_tab.set_job_manager(job_manager)

        # Wire VetoLogTab to job completion
        if job_manager and hasattr(self, "veto_log_tab"):
            job_manager.job_completed.connect(self._on_job_completed_for_veto_logs)

    def _on_job_completed_for_veto_logs(self, job_id: str, lineups: list) -> None:
        """Handle job completion to add job to veto log selector.

        Args:
            job_id: Completed job ID
            lineups: Generated lineups (unused)
        """
        if hasattr(self, "veto_log_tab") and self.veto_log_tab:
            # Get job details
            if self.job_manager:
                job = self.job_manager.get_job(job_id)
                if job:
                    job_name = job.get("name", f"Job {job_id[:8]}")
                    config = job.get("config_json", {})
                    race_id = config.get("race_id", "Unknown")

                    # Add to job selector
                    self.veto_log_tab.add_job_to_selector(
                        job_id=job_id,
                        job_name=job_name,
                        race_name=str(race_id),
                    )

                    # Auto-select this job
                    self.veto_log_tab.set_active_job(job_id)

    def set_preset_manager(self, preset_manager: Optional[Any]) -> None:
        """Set the PresetManager and wire it to all tabs.

        Called from main.py after PresetManager is created.

        Args:
            preset_manager: PresetManager instance for preset operations.
        """
        self.preset_manager = preset_manager

        # Wire PresetsTab
        if hasattr(self, "presets_tab") and self.presets_tab:
            self.presets_tab.preset_manager = preset_manager
            # Refresh presets with the new manager
            self.presets_tab._refresh_presets()
            self.presets_tab._refresh_recent_presets()

        # Wire ConstraintPanel in OptimizationTab
        if (
            hasattr(self, "optimization_tab")
            and self.optimization_tab
            and hasattr(self.optimization_tab, "constraint_panel")
        ):
            self.optimization_tab.constraint_panel.preset_manager = preset_manager
            self.optimization_tab.constraint_panel._load_presets()
            # Store reference for preset loading from PresetsTab
            self.constraint_panel = self.optimization_tab.constraint_panel

        # Wire SplitEditorTab with preset manager
        if hasattr(self, "split_editor_tab") and self.split_editor_tab:
            self.split_editor_tab.preset_manager = preset_manager
            self.split_editor_tab._load_presets()

    def set_undo_manager(self, undo_manager: Optional[Any]) -> None:
        """Set the UndoManager and wire it to all tabs.

        Args:
            undo_manager: UndoManager instance for undo/redo actions.
        """
        self.undo_manager = undo_manager

        # Wire undo manager to tabs that support undo/redo
        if hasattr(self, "optimization_tab") and self.optimization_tab:
            self.optimization_tab.undo_manager = undo_manager

        if hasattr(self, "lineups_tab") and self.lineups_tab:
            self.lineups_tab.undo_manager = undo_manager
