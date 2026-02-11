"""Constraint preset manager for saving and loading constraint configurations."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Any


class PresetManager:
    """Manages constraint presets with SQLite persistence and JSON storage.

    Provides save/load operations for constraint configurations with support for:
    - Global presets (available for all races)
    - Race-specific presets (filtered by race type and track)
    - Recent presets quick-access list
    - Import/export for sharing presets

    Uses SQLite JSON columns for flexible config storage with versioning support.
    """

    # Schema version for migration tracking
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None):
        """Initialize PresetManager with optional custom database path.

        Args:
            db_path: Optional custom database path. If not provided, uses default
                    macOS Application Support location.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Default to macOS Application Support directory
            self.db_path = self._get_default_db_path()

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema on first connection
        self._init_schema()

    def _get_default_db_path(self) -> Path:
        """Get the default database path in macOS Application Support.

        Returns:
            Path to the database file.
        """
        home = Path.home()
        app_support = home / "Library" / "Application Support" / "NASCAR DFS Optimizer"
        return app_support / "nascar_optimizer.db"

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections with automatic cleanup.

        Yields:
            sqlite3.Connection: Database connection with row factory set.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column name access

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Initialize database schema for preset tables."""
        with self.get_connection() as conn:
            # Constraint presets table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS constraint_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    is_global BOOLEAN DEFAULT 0,
                    race_type TEXT,
                    track_name TEXT,
                    config_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0
                )
            """)

            # Recent presets table (tracks usage for quick access)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recent_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preset_id INTEGER REFERENCES constraint_presets(id) ON DELETE CASCADE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_presets_global 
                ON constraint_presets(is_global, race_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_presets_track 
                ON constraint_presets(track_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_presets_name 
                ON constraint_presets(name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recent_presets_preset_id 
                ON recent_presets(preset_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recent_presets_applied 
                ON recent_presets(applied_at DESC)
            """)

            # Enable foreign key support
            conn.execute("PRAGMA foreign_keys = ON")

    def save_preset(
        self,
        name: str,
        config: Dict[str, Any],
        is_global: bool = False,
        race_type: Optional[str] = None,
        track_name: Optional[str] = None,
        description: str = "",
    ) -> Optional[int]:
        """Save a constraint preset to the database.

        Args:
            name: Preset name (must be unique per scope)
            config: Dictionary containing constraint configuration
            is_global: If True, preset available for all races
            race_type: Race type filter (e.g., "Cup", "Xfinity")
            track_name: Track name filter (e.g., "Daytona")
            description: Optional description of the preset

        Returns:
            int: ID of the saved preset
        """
        # Add version to config for future migrations
        config_with_version = {
            **config,
            "_version": self.SCHEMA_VERSION,
            "_saved_at": datetime.now().isoformat(),
        }

        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO constraint_presets 
                   (name, description, is_global, race_type, track_name, config_json)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                   description=excluded.description,
                   is_global=excluded.is_global,
                   race_type=excluded.race_type,
                   track_name=excluded.track_name,
                   config_json=excluded.config_json,
                   updated_at=CURRENT_TIMESTAMP""",
                (
                    name,
                    description,
                    is_global,
                    race_type,
                    track_name,
                    json.dumps(config_with_version),
                ),
            )
            return cursor.lastrowid

    def load_preset(self, preset_id: int) -> Dict[str, Any]:
        """Load a preset by ID.

        Args:
            preset_id: ID of the preset to load

        Returns:
            Dictionary containing preset data including config

        Raises:
            KeyError: If preset not found
        """
        with self.get_connection() as conn:
            row = conn.execute(
                """SELECT id, name, description, is_global, race_type, 
                          track_name, config_json, created_at, updated_at, usage_count
                   FROM constraint_presets WHERE id = ?""",
                (preset_id,),
            ).fetchone()

            if not row:
                raise KeyError(f"Preset {preset_id} not found")

            config = json.loads(row["config_json"])

            return {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "is_global": bool(row["is_global"]),
                "race_type": row["race_type"],
                "track_name": row["track_name"],
                "config": config,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "usage_count": row["usage_count"],
            }

    def delete_preset(self, preset_id: int) -> bool:
        """Delete a preset by ID.

        Args:
            preset_id: ID of the preset to delete

        Returns:
            bool: True if deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM constraint_presets WHERE id = ?", (preset_id,)
            )
            return cursor.rowcount > 0

    def get_presets_for_race(
        self, race_type: Optional[str] = None, track_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get applicable presets for a specific race.

        Returns global presets plus race-specific presets matching the
        race_type and/or track_name.

        Args:
            race_type: Type of race (e.g., "Cup", "Xfinity")
            track_name: Name of the track (e.g., "Daytona")

        Returns:
            List of preset dictionaries, sorted by is_global DESC, name ASC
        """
        with self.get_connection() as conn:
            if race_type and track_name:
                # Get global + race-specific + track-specific
                rows = conn.execute(
                    """SELECT id, name, description, is_global, race_type,
                              track_name, config_json, created_at, updated_at, usage_count
                       FROM constraint_presets 
                       WHERE is_global = 1 
                          OR (race_type = ? AND track_name IS NULL)
                          OR (race_type = ? AND track_name = ?)
                       ORDER BY is_global DESC, name ASC""",
                    (race_type, race_type, track_name),
                ).fetchall()
            elif race_type:
                # Get global + race-specific
                rows = conn.execute(
                    """SELECT id, name, description, is_global, race_type,
                              track_name, config_json, created_at, updated_at, usage_count
                       FROM constraint_presets 
                       WHERE is_global = 1 
                          OR (race_type = ? AND track_name IS NULL)
                       ORDER BY is_global DESC, name ASC""",
                    (race_type,),
                ).fetchall()
            else:
                # Get only global presets
                rows = conn.execute(
                    """SELECT id, name, description, is_global, race_type,
                              track_name, config_json, created_at, updated_at, usage_count
                       FROM constraint_presets 
                       WHERE is_global = 1
                       ORDER BY name ASC"""
                ).fetchall()

            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "is_global": bool(row["is_global"]),
                    "race_type": row["race_type"],
                    "track_name": row["track_name"],
                    "config": json.loads(row["config_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "usage_count": row["usage_count"],
                }
                for row in rows
            ]

    def get_all_presets(self) -> List[Dict[str, Any]]:
        """Get all presets in the database.

        Returns:
            List of all preset dictionaries
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT id, name, description, is_global, race_type,
                          track_name, config_json, created_at, updated_at, usage_count
                   FROM constraint_presets 
                   ORDER BY is_global DESC, name ASC"""
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "is_global": bool(row["is_global"]),
                    "race_type": row["race_type"],
                    "track_name": row["track_name"],
                    "config": json.loads(row["config_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "usage_count": row["usage_count"],
                }
                for row in rows
            ]

    def get_recent_presets(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most recently applied presets.

        Args:
            limit: Maximum number of presets to return (default 5)

        Returns:
            List of preset dictionaries with most recent first
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT p.id, p.name, p.description, p.is_global, p.race_type,
                          p.track_name, p.config_json, p.created_at, p.updated_at, 
                          p.usage_count, r.applied_at
                   FROM constraint_presets p
                   JOIN recent_presets r ON p.id = r.preset_id
                   ORDER BY r.applied_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "is_global": bool(row["is_global"]),
                    "race_type": row["race_type"],
                    "track_name": row["track_name"],
                    "config": json.loads(row["config_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "usage_count": row["usage_count"],
                    "last_applied": row["applied_at"],
                }
                for row in rows
            ]

    def record_preset_usage(self, preset_id: int) -> None:
        """Record that a preset was applied.

        Adds entry to recent_presets and increments usage_count.

        Args:
            preset_id: ID of the preset that was applied
        """
        with self.get_connection() as conn:
            # Add to recent presets
            conn.execute(
                "INSERT INTO recent_presets (preset_id) VALUES (?)", (preset_id,)
            )

            # Increment usage count
            conn.execute(
                """UPDATE constraint_presets 
                   SET usage_count = usage_count + 1 
                   WHERE id = ?""",
                (preset_id,),
            )

    def export_preset_to_json(self, preset_id: int, filepath: str) -> None:
        """Export a preset to JSON file for sharing.

        Args:
            preset_id: ID of the preset to export
            filepath: Path to save the JSON file

        Raises:
            KeyError: If preset not found
        """
        preset = self.load_preset(preset_id)

        export_data = {
            "name": preset["name"],
            "description": preset["description"],
            "is_global": preset["is_global"],
            "race_type": preset["race_type"],
            "track_name": preset["track_name"],
            "config": preset["config"],
            "exported_at": datetime.now().isoformat(),
            "export_version": self.SCHEMA_VERSION,
        }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

    def import_preset_from_json(self, filepath: str) -> Optional[int]:
        """Import a preset from JSON file.

        Args:
            filepath: Path to the JSON file to import

        Returns:
            int: ID of the imported preset

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or missing required fields
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        # Validate required fields
        if "config" not in data:
            raise ValueError("Import file missing 'config' field")
        if "name" not in data:
            raise ValueError("Import file missing 'name' field")

        # Support both old and new export formats
        config = data["config"]
        if "_version" not in config:
            config["_version"] = 1

        return self.save_preset(
            name=data["name"],
            config=config,
            is_global=data.get("is_global", False),
            race_type=data.get("race_type"),
            track_name=data.get("track_name"),
            description=data.get("description", ""),
        )

    def search_presets(self, query: str) -> List[Dict[str, Any]]:
        """Search presets by name or description.

        Args:
            query: Search string

        Returns:
            List of matching preset dictionaries
        """
        search_pattern = f"%{query}%"

        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT id, name, description, is_global, race_type,
                          track_name, config_json, created_at, updated_at, usage_count
                   FROM constraint_presets 
                   WHERE name LIKE ? OR description LIKE ?
                   ORDER BY name ASC""",
                (search_pattern, search_pattern),
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "is_global": bool(row["is_global"]),
                    "race_type": row["race_type"],
                    "track_name": row["track_name"],
                    "config": json.loads(row["config_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "usage_count": row["usage_count"],
                }
                for row in rows
            ]

    def update_preset(
        self,
        preset_id: int,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        is_global: Optional[bool] = None,
        race_type: Optional[str] = None,
        track_name: Optional[str] = None,
    ) -> bool:
        """Update an existing preset.

        Args:
            preset_id: ID of the preset to update
            name: New name (optional)
            config: New config (optional)
            description: New description (optional)
            is_global: New global flag (optional)
            race_type: New race type (optional)
            track_name: New track name (optional)

        Returns:
            bool: True if updated, False if preset not found
        """
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if is_global is not None:
            updates["is_global"] = is_global
        if race_type is not None:
            updates["race_type"] = race_type
        if track_name is not None:
            updates["track_name"] = track_name
        if config is not None:
            config_with_version = {
                **config,
                "_version": self.SCHEMA_VERSION,
                "_saved_at": datetime.now().isoformat(),
            }
            updates["config_json"] = json.dumps(config_with_version)

        if not updates:
            return False

        set_clauses = [f"{k} = ?" for k in updates.keys()]
        values = list(updates.values())
        values.append(preset_id)

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"""UPDATE constraint_presets 
                    SET {", ".join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?""",
                values,
            )
            return cursor.rowcount > 0
