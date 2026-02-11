"""Session manager for saving and restoring application state.

Provides persistence for window geometry, last viewed race, and arbitrary
application state across app launches. Uses base64 encoding for binary
window geometry data.
"""

import base64
import json
from datetime import datetime
from typing import Any, Dict, Optional

from .database import DatabaseManager


class SessionManager:
    """Manages application session state persistence.

    Saves and restores:
    - Window geometry (position, size, maximized state)
    - Last viewed race
    - Arbitrary key-value application state

    Depends on DatabaseManager for storage operations.
    """

    # Key constants for app_state table
    KEY_WINDOW_GEOMETRY = "window_geometry"
    KEY_LAST_RACE = "last_race"

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize SessionManager.

        Args:
            db_manager: Optional DatabaseManager instance. If not provided,
                       creates a new one with default settings.
        """
        self.db = db_manager or DatabaseManager()

    def save_window_geometry(self, window: Any) -> None:
        """Save QMainWindow geometry to database.

        Uses Qt's saveGeometry() method to capture complete window state
        including position, size, and maximized state. Stores as base64
        encoded bytes in the app_state table.

        Args:
            window: QMainWindow or any object with saveGeometry() and
                   geometry() methods
        """
        try:
            # Get binary geometry data from Qt
            geometry_bytes = window.saveGeometry().data()

            # Get QRect for human-readable metadata
            rect = window.geometry()

            # Store both binary data and metadata
            state = {
                "geometry_b64": base64.b64encode(geometry_bytes).decode("utf-8"),
                "x": rect.x(),
                "y": rect.y(),
                "width": rect.width(),
                "height": rect.height(),
            }

            self._save_state(self.KEY_WINDOW_GEOMETRY, state)

        except AttributeError:
            # Fallback if window doesn't have Qt methods
            # Try to get basic geometry info
            try:
                rect = window.geometry()
                state = {
                    "x": rect.x(),
                    "y": rect.y(),
                    "width": rect.width(),
                    "height": rect.height(),
                }
                self._save_state(self.KEY_WINDOW_GEOMETRY, state)
            except AttributeError:
                raise ValueError(
                    "Window must have geometry() method or be a QMainWindow"
                )

    def load_window_geometry(self, window: Any) -> bool:
        """Restore QMainWindow geometry from database.

        Attempts to restore using Qt's restoreGeometry() with the binary
        data. Falls back to manual positioning if binary data not available.

        Args:
            window: QMainWindow or any object with restoreGeometry() and
                   setGeometry() methods

        Returns:
            bool: True if geometry was restored, False if no saved state
        """
        state = self._load_state(self.KEY_WINDOW_GEOMETRY)

        if not state:
            return False

        restored = False

        # Try to restore from binary geometry data (includes maximized state)
        if "geometry_b64" in state:
            try:
                geometry_bytes = base64.b64decode(state["geometry_b64"])
                # Qt's restoreGeometry expects QByteArray
                window.restoreGeometry(geometry_bytes)
                restored = True
            except (AttributeError, Exception):
                # restoreGeometry not available or failed, fall through
                pass

        # Fallback to manual geometry setting
        if not restored and all(k in state for k in ["x", "y", "width", "height"]):
            try:
                window.setGeometry(
                    state["x"], state["y"], state["width"], state["height"]
                )
                restored = True
            except AttributeError:
                pass

        return restored

    def save_last_race(
        self, race_id: int, track_name: str, race_date: Optional[str] = None
    ) -> None:
        """Save the last viewed race for session restore.

        Args:
            race_id: Database ID of the race
            track_name: Name of the track (for display)
            race_date: Optional date of the race (ISO format)
        """
        state = {
            "race_id": race_id,
            "track_name": track_name,
            "timestamp": datetime.now().isoformat(),
        }

        if race_date:
            state["race_date"] = race_date

        self._save_state(self.KEY_LAST_RACE, state)

    def load_last_race(self) -> Optional[Dict[str, Any]]:
        """Load the last viewed race information.

        Returns:
            Dictionary with race_id, track_name, and optionally race_date,
            or None if no last race saved.
        """
        return self._load_state(self.KEY_LAST_RACE)

    def save_state(self, key: str, value: Any) -> None:
        """Save arbitrary application state by key.

        Generic key-value storage for any application state that should
        persist across launches.

        Args:
            key: Unique identifier for this state
            value: Any JSON-serializable value
        """
        # Wrap non-dict values in a dict for consistent storage
        if not isinstance(value, dict):
            value = {"_value": value}

        self._save_state(key, value)

    def load_state(self, key: str, default: Any = None) -> Any:
        """Load application state by key.

        Args:
            key: Unique identifier for the state
            default: Default value if key not found

        Returns:
            The stored value, or default if not found
        """
        result = self._load_state(key)

        if result is None:
            return default

        # Unwrap single values stored in _value key
        if isinstance(result, dict) and "_value" in result and len(result) == 1:
            return result["_value"]

        return result

    def delete_state(self, key: str) -> bool:
        """Delete a state entry by key.

        Args:
            key: Key of the state to delete

        Returns:
            bool: True if deleted, False if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM app_state WHERE key = ?", (key,))
            return cursor.rowcount > 0

    def clear_all_state(self) -> None:
        """Clear all application state. Use with caution."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM app_state")

    def _save_state(self, key: str, value: Dict[str, Any]) -> None:
        """Internal method to save state to database.

        Args:
            key: State key
            value: Dictionary to store (will be JSON serialized)
        """
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO app_state (key, value) 
                   VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET 
                   value=excluded.value,
                   updated_at=CURRENT_TIMESTAMP""",
                (key, json.dumps(value)),
            )

    def _load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Internal method to load state from database.

        Args:
            key: State key to load

        Returns:
            Dictionary with stored data, or None if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,))
            row = cursor.fetchone()

            if row:
                value = row["value"]
                if isinstance(value, str):
                    return json.loads(value)
                return value

            return None

    def get_all_state_keys(self) -> list:
        """Get all state keys stored in the database.

        Returns:
            List of state keys
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT key, updated_at FROM app_state ORDER BY updated_at DESC"
            )
            return [
                {"key": row["key"], "updated_at": row["updated_at"]}
                for row in cursor.fetchall()
            ]
