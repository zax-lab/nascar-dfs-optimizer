"""Dock icon handler for macOS integration.

Provides dock icon bounce notifications, dock badge for job count,
and dock menu with recent races and quick actions.
"""

from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import QApplication, QMenu
from PySide6.QtCore import QObject, Signal


class DockIconHandler(QObject):
    """Handle dock icon interactions and notifications.

    Provides:
    - Dock icon bounce for user attention
    - Dock badge showing running/queued job count
    - Dock menu with recent races and quick actions
    - Signals for menu action handling

    Signals:
        race_selected: Emitted when a recent race is selected from dock menu
        new_race_triggered: Emitted when "New Race..." is selected
        generate_lineups_triggered: Emitted when "Generate Lineups" is selected
        preferences_triggered: Emitted when "Preferences..." is selected
    """

    # Signals for dock menu actions
    race_selected = Signal(int)  # race_id
    new_race_triggered = Signal()
    generate_lineups_triggered = Signal()
    preferences_triggered = Signal()

    def __init__(self, app: QApplication, parent: Optional[QObject] = None):
        """Initialize the dock icon handler.

        Args:
            app: QApplication instance
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.app = app
        self._recent_races: List[Dict[str, Any]] = []
        self._current_badge_count: int = 0

    def bounce(self, critical: bool = False) -> None:
        """Request user attention via dock bounce.

        Args:
            critical: If True, dock icon bounces until app is activated.
                     If False, single bounce notification.
        """
        try:
            # Use NSApp via PyObjC for native dock bounce
            import AppKit

            ns_app = AppKit.NSApp()
            if critical:
                ns_app.requestUserAttention_(AppKit.NSCriticalRequest)
            else:
                ns_app.requestUserAttention_(AppKit.NSInformationalRequest)
        except ImportError:
            # PyObjC not available, use Qt fallback
            # QApplication.alert() provides basic attention notification
            self.app.alert(self.app.activeWindow(), 0)

    def set_badge_count(self, count: int) -> None:
        """Set the dock badge to show job count.

        Args:
            count: Number to display on dock badge (0 to clear)
        """
        self._current_badge_count = count

        try:
            # Use NSApp via PyObjC for native dock badge
            import AppKit

            ns_app = AppKit.NSApp()
            dock_tile = ns_app.dockTile()

            if count > 0:
                dock_tile.setBadgeLabel_(str(count))
            else:
                dock_tile.setBadgeLabel_(None)
        except ImportError:
            # PyObjC not available, can't set badge
            pass

    def set_badge_progress(self, percent: int) -> None:
        """Set dock badge to show progress percentage.

        This is an alternative to count - shows progress as percentage.

        Args:
            percent: Progress percentage (0-100, 0 to clear)
        """
        try:
            import AppKit

            ns_app = AppKit.NSApp()
            dock_tile = ns_app.dockTile()

            if percent > 0 and percent < 100:
                dock_tile.setBadgeLabel_(f"{percent}%")
            elif percent >= 100:
                dock_tile.setBadgeLabel_("✓")
            else:
                dock_tile.setBadgeLabel_(None)
        except ImportError:
            pass

    def clear_badge(self) -> None:
        """Clear the dock badge."""
        self.set_badge_count(0)

    def set_recent_races(self, recent_races: List[Dict[str, Any]]) -> None:
        """Update the list of recent races for the dock menu.

        Args:
            recent_races: List of race dictionaries with 'id' and 'track_name' keys
        """
        self._recent_races = recent_races[:5]  # Keep only 5 most recent
        self._update_dock_menu()

    def create_dock_menu(
        self, recent_races: Optional[List[Dict[str, Any]]] = None
    ) -> QMenu:
        """Create dock menu with recent races and actions.

        Args:
            recent_races: Optional list of recent races. If None, uses cached races.

        Returns:
            QMenu configured for dock display
        """
        if recent_races is not None:
            self._recent_races = recent_races[:5]

        menu = QMenu()

        # Recent races section
        if self._recent_races:
            menu.addSection("Recent Races")
            for race in self._recent_races:
                track_name = race.get("track_name", "Unknown Track")
                race_id = race.get("id")
                action = menu.addAction(track_name)
                # Use default argument to capture race_id correctly
                action.triggered.connect(
                    lambda checked=False, rid=race_id: self._on_race_selected(rid)
                )
            menu.addSeparator()

        # Quick actions
        menu.addAction("New Race...", self._on_new_race)
        menu.addAction("Generate Lineups", self._on_generate_lineups)
        menu.addSeparator()
        menu.addAction("Preferences...", self._on_preferences)

        return menu

    def _update_dock_menu(self) -> None:
        """Update the application's dock menu."""
        menu = self.create_dock_menu()
        self.app.setDockMenu(menu)

    def _on_race_selected(self, race_id: int) -> None:
        """Handle race selection from dock menu.

        Args:
            race_id: ID of the selected race
        """
        self.race_selected.emit(race_id)

    def _on_new_race(self) -> None:
        """Handle New Race action from dock menu."""
        self.new_race_triggered.emit()

    def _on_generate_lineups(self) -> None:
        """Handle Generate Lineups action from dock menu."""
        self.generate_lineups_triggered.emit()

    def _on_preferences(self) -> None:
        """Handle Preferences action from dock menu."""
        self.preferences_triggered.emit()
