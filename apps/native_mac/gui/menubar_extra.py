"""System tray / menubar extra for quick job status access.

Provides a system tray icon with menu showing job status,
recent jobs, and quick actions. Allows access to app features
without opening the main window.
"""

from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidget, QApplication
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont


class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon with job status menu.

    Provides:
    - Visual indicator in system tray/menubar
    - Menu showing running job count and recent jobs
    - Quick actions (Show Main Window, Preferences, Quit)
    - Notifications on job completion

    Signals:
        show_main_window_triggered: Emitted when user selects "Show Main Window"
        preferences_triggered: Emitted when user selects "Preferences"
        quit_triggered: Emitted when user selects "Quit"
    """

    # Signals for menu actions
    show_main_window_triggered = Signal()
    preferences_triggered = Signal()
    quit_triggered = Signal()

    def __init__(
        self,
        job_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the system tray icon.

        Args:
            job_manager: Optional JobManager for querying job status
            parent: Optional parent widget
        """
        super().__init__(parent)

        self.job_manager = job_manager
        self._recent_jobs: List[Dict[str, Any]] = []

        # Create icon
        self._create_icon()

        # Create menu
        self._create_menu()

        # Connect activated signal (click on tray icon)
        self.activated.connect(self._on_activated)

    def _create_icon(self) -> None:
        """Create the tray icon."""
        # Create a simple icon programmatically
        # In production, this would load an actual icon file
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(33, 150, 243))  # Blue background

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 24, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "N")
        painter.end()

        self.setIcon(QIcon(pixmap))

    def _create_menu(self) -> None:
        """Create the context menu."""
        self.menu = QMenu()

        # Header
        self.header_action = QAction("NASCAR DFS Optimizer", self)
        self.header_action.setEnabled(False)
        self.menu.addAction(self.header_action)

        self.menu.addSeparator()

        # Job status
        self.status_action = QAction("No jobs running", self)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        # Recent jobs submenu
        self.recent_menu = self.menu.addMenu("Recent Jobs")
        self._update_recent_menu()

        self.menu.addSeparator()

        # Actions
        show_action = QAction("Show Main Window", self)
        show_action.triggered.connect(self._on_show_main_window)
        self.menu.addAction(show_action)

        prefs_action = QAction("Preferences...", self)
        prefs_action.triggered.connect(self._on_preferences)
        self.menu.addAction(prefs_action)

        self.menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._on_quit)
        self.menu.addAction(quit_action)

        self.setContextMenu(self.menu)

    def _update_recent_menu(self) -> None:
        """Update the recent jobs submenu."""
        self.recent_menu.clear()

        if not self._recent_jobs:
            no_jobs_action = QAction("No recent jobs", self)
            no_jobs_action.setEnabled(False)
            self.recent_menu.addAction(no_jobs_action)
            return

        for job in self._recent_jobs[:5]:  # Show last 5
            job_name = job.get("name", "Unnamed Job")
            status = job.get("status", "unknown")
            display_text = f"{job_name} ({status})"

            action = QAction(display_text, self)
            job_id = job.get("id")
            action.triggered.connect(
                lambda checked=False, jid=job_id: self._on_recent_job_selected(jid)
            )
            self.recent_menu.addAction(action)

    def update_menu(
        self, running_count: int = 0, recent_jobs: Optional[List[Dict]] = None
    ) -> None:
        """Update the menu with current job status.

        Args:
            running_count: Number of currently running jobs
            recent_jobs: Optional list of recent job dictionaries
        """
        # Update status text
        if running_count > 0:
            self.status_action.setText(
                f"Running: {running_count} job{'s' if running_count > 1 else ''}"
            )
        else:
            self.status_action.setText("No jobs running")

        # Update recent jobs
        if recent_jobs is not None:
            self._recent_jobs = recent_jobs
            self._update_recent_menu()

    def show_notification(self, title: str, message: str) -> None:
        """Show a native notification.

        Args:
            title: Notification title
            message: Notification message
        """
        self.showMessage(
            title,
            message,
            QSystemTrayIcon.Information,
            5000,  # Show for 5 seconds
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation.

        Args:
            reason: Activation reason (click, double-click, etc.)
        """
        if reason == QSystemTrayIcon.DoubleClick:
            # Double-click: show main window
            self._on_show_main_window()
        elif reason == QSystemTrayIcon.Trigger:
            # Single click on macOS: show menu
            # On other platforms, might need to show menu explicitly
            pass

    def _on_show_main_window(self) -> None:
        """Handle Show Main Window action."""
        self.show_main_window_triggered.emit()

    def _on_preferences(self) -> None:
        """Handle Preferences action."""
        self.preferences_triggered.emit()

    def _on_quit(self) -> None:
        """Handle Quit action."""
        self.quit_triggered.emit()

    def _on_recent_job_selected(self, job_id: str) -> None:
        """Handle selection of a recent job.

        Args:
            job_id: ID of the selected job
        """
        # Show main window and potentially switch to jobs tab
        self.show_main_window_triggered.emit()


# Import Qt at module level for type hints
from PySide6.QtCore import Qt
