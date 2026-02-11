"""Session restorer for restoring application state on launch.

Orchestrates the restoration of window geometry, last viewed race,
and generated lineups when the application launches.
"""

from typing import Optional, List, Dict, Any

from apps.native_mac.persistence.session_manager import SessionManager
from apps.native_mac.persistence.database import DatabaseManager
from apps.native_mac.optimization.engine import OptimizationEngine


class SessionRestorer:
    """Restores previous application session on app launch.

    Coordinates restoration of:
    - Window geometry (position, size, maximized state)
    - Last viewed race data and drivers
    - Generated lineups for the last race
    - Active tab selection

    Respects user preferences for session restore behavior.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        database_manager: DatabaseManager,
        optimization_engine: Optional[OptimizationEngine] = None,
    ):
        """Initialize the session restorer.

        Args:
            session_manager: SessionManager for loading saved state.
            database_manager: DatabaseManager for loading race/lineup data.
            optimization_engine: Optional OptimizationEngine for loading results.
        """
        self.session_manager = session_manager
        self.database_manager = database_manager
        self.optimization_engine = optimization_engine
        self.main_window: Optional[Any] = None

    def set_main_window(self, main_window: Any) -> None:
        """Set the main window reference for UI restoration.

        Must be called before restore_session() if UI restoration is needed.

        Args:
            main_window: MainWindow instance.
        """
        self.main_window = main_window

    def restore_session(self) -> bool:
        """Restore previous session on app launch.

        Checks user preferences and restores:
        - Window geometry (if enabled)
        - Last viewed race (if enabled)
        - Generated lineups (if enabled)
        - Active tab (if enabled)

        Returns:
            bool: True if any restoration was performed, False otherwise.
        """
        if not self._is_restore_enabled():
            return False

        restored = False

        # Restore window geometry if enabled
        if self._is_window_geometry_enabled() and self.main_window:
            try:
                self.session_manager.load_window_geometry(self.main_window)
                restored = True
            except Exception:
                # Window geometry restoration failed, continue
                pass

        # Restore last viewed race if enabled
        if self._is_load_last_race_enabled():
            last_race = self._load_last_race()
            if last_race:
                self._restore_race(last_race)
                restored = True

                # Restore generated lineups for last race
                if self._is_restore_lineups_enabled():
                    lineups = self._load_lineups_for_race(last_race["id"])
                    if lineups:
                        self._restore_lineups(lineups)

        # Restore active tab if enabled
        if self._is_restore_tab_enabled() and self.main_window:
            active_tab = self.session_manager.load_state("active_tab", 0)
            try:
                self.main_window.tab_widget.setCurrentIndex(active_tab)
                restored = True
            except Exception:
                # Tab restoration failed, continue
                pass

        return restored

    def _is_restore_enabled(self) -> bool:
        """Check if session restore is enabled in settings.

        Returns:
            bool: True if session restore is enabled (default: True).
        """
        return self.session_manager.load_state("session_restore_enabled", True)

    def _is_window_geometry_enabled(self) -> bool:
        """Check if window geometry restore is enabled.

        Returns:
            bool: True if window geometry restore is enabled (default: True).
        """
        return self.session_manager.load_state("restore_window_geometry", True)

    def _is_load_last_race_enabled(self) -> bool:
        """Check if loading last race is enabled.

        Returns:
            bool: True if loading last race is enabled (default: True).
        """
        return self.session_manager.load_state("load_last_race_on_startup", True)

    def _is_restore_lineups_enabled(self) -> bool:
        """Check if lineup restoration is enabled.

        Returns:
            bool: True if lineup restoration is enabled (default: True).
        """
        return self.session_manager.load_state("restore_lineups", True)

    def _is_restore_tab_enabled(self) -> bool:
        """Check if tab restoration is enabled.

        Returns:
            bool: True if tab restoration is enabled (default: True).
        """
        return self.session_manager.load_state("restore_active_tab", True)

    def _load_last_race(self) -> Optional[Dict[str, Any]]:
        """Load the last viewed race information.

        Returns:
            Dictionary with race info or None if no last race.
        """
        race_info = self.session_manager.load_last_race()
        if not race_info:
            return None

        # Verify the race still exists in database
        race_id = race_info.get("race_id")
        if not race_id:
            return None

        # Load race details from database
        try:
            races = self.database_manager.load_races()
            for race in races:
                if race.get("id") == race_id:
                    return {
                        "id": race_id,
                        "track_name": race.get("track_name", "Unknown"),
                        "race_date": race.get("race_date", ""),
                    }
        except Exception:
            pass

        return None

    def _restore_race(self, race_info: Dict[str, Any]) -> bool:
        """Restore the last viewed race in the UI.

        Args:
            race_info: Dictionary with race id, track_name, race_date.

        Returns:
            bool: True if restoration succeeded.
        """
        if not self.main_window:
            return False

        race_id = race_info.get("id")
        if not race_id:
            return False

        try:
            # Update the race selector in optimization tab
            if hasattr(self.main_window, "optimization_tab"):
                opt_tab = self.main_window.optimization_tab
                if hasattr(opt_tab, "race_combo"):
                    # Find and select the race in the combo box
                    combo = opt_tab.race_combo
                    for i in range(combo.count()):
                        if combo.itemData(i) == race_id:
                            combo.setCurrentIndex(i)
                            break

            # Try to load drivers for this race
            if hasattr(self.main_window, "driver_table"):
                self.main_window.driver_table.load_drivers_from_db(race_id)

            # Store current race ID in main window
            if hasattr(self.main_window, "current_race_id"):
                self.main_window.current_race_id = race_id

            return True
        except Exception:
            return False

    def _load_lineups_for_race(self, race_id: int) -> Optional[List[Dict[str, Any]]]:
        """Load generated lineups for a race.

        Args:
            race_id: ID of the race to load lineups for.

        Returns:
            List of lineup dictionaries or None if no lineups.
        """
        if not self.optimization_engine:
            return None

        try:
            lineups = self.optimization_engine.load_results(race_id)
            return lineups if lineups else None
        except Exception:
            return None

    def _restore_lineups(self, lineups: List[Dict[str, Any]]) -> bool:
        """Restore generated lineups in the UI.

        Args:
            lineups: List of lineup dictionaries.

        Returns:
            bool: True if restoration succeeded.
        """
        if not self.main_window or not lineups:
            return False

        try:
            # Update lineup model in lineups tab
            if hasattr(self.main_window, "lineups_tab"):
                lineups_tab = self.main_window.lineups_tab
                if hasattr(lineups_tab, "set_lineups"):
                    race_id = getattr(self.main_window, "current_race_id", None)
                    lineups_tab.set_lineups(lineups, race_id)

            # Also update results table in optimization tab
            if hasattr(self.main_window, "optimization_tab"):
                opt_tab = self.main_window.optimization_tab
                if hasattr(opt_tab, "lineup_model"):
                    opt_tab.lineup_model.update_data(lineups)

            return True
        except Exception:
            return False
