"""Backup and export manager for comprehensive application state preservation.

Provides export/import functionality for:
- Application settings (preferences, window geometry, shortcuts)
- Constraint presets (all saved presets and recent history)
- Saved lineups (all generated lineups with driver assignments)
- Race data (imported driver data and race metadata)
- Job history (optimization job configs and results)
- Veto logs (kernel rejection logs)

Export format is JSON for human readability and version control compatibility.
"""

import json
import base64
import sqlite3
import shutil
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from PySide6.QtCore import QSettings

from ..persistence.database import DatabaseManager
from ..persistence.preset_manager import PresetManager


class BackupManager:
    """Manages comprehensive export and import of application state.

    Provides methods to export all or selective parts of the application state
    to JSON files for backup, migration, or sharing purposes.
    """

    # Export format version for compatibility checking
    EXPORT_VERSION = "1.2"
    APP_VERSION = "1.2.0"

    def __init__(
        self,
        database_manager: DatabaseManager,
        preset_manager: PresetManager,
    ):
        """Initialize BackupManager with required dependencies.

        Args:
            database_manager: DatabaseManager for querying SQLite data
            preset_manager: PresetManager for constraint preset operations
        """
        self.db_manager = database_manager
        self.preset_manager = preset_manager
        self.settings = QSettings("Zax", "NASCAR DFS Optimizer")

    def export_all(
        self, filepath: str, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Export all application state to a JSON backup file.

        Args:
            filepath: Path to save the backup file
            options: Optional dict with include_* flags to control what to export
                    Defaults include all except jobs and veto_logs

        Returns:
            Tuple of (success: bool, message: str)
        """
        options = options or {}
        default_options = {
            "include_settings": True,
            "include_presets": True,
            "include_lineups": True,
            "include_races": True,
            "include_jobs": False,
            "include_veto_logs": False,
            "date_range": None,  # Tuple of (start_date, end_date)
        }
        default_options.update(options)
        options = default_options

        try:
            backup_data = {
                "export_metadata": self._create_metadata(options),
            }

            # Export settings
            if options.get("include_settings", True):
                backup_data["settings"] = self._export_settings()

            # Export constraint presets
            if options.get("include_presets", True):
                presets_data = self._export_presets()
                backup_data["constraint_presets"] = presets_data["presets"]
                backup_data["recent_presets"] = presets_data["recent"]

            # Export races
            if options.get("include_races", True):
                backup_data["races"] = self._export_races(options.get("date_range"))

            # Export lineups
            if options.get("include_lineups", True):
                backup_data["lineups"] = self._export_lineups(options.get("date_range"))

            # Export jobs
            if options.get("include_jobs", False):
                backup_data["jobs"] = self._export_jobs(options.get("date_range"))

            # Export veto logs
            if options.get("include_veto_logs", False):
                backup_data["veto_logs"] = self._export_veto_logs(
                    options.get("date_range")
                )

            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            return True, f"Successfully exported to {filepath}"

        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def export_settings(self, filepath: str) -> Tuple[bool, str]:
        """Export only application settings to a JSON file.

        Args:
            filepath: Path to save the settings file

        Returns:
            Tuple of (success: bool, message: str)
        """
        return self.export_all(
            filepath,
            options={
                "include_settings": True,
                "include_presets": False,
                "include_lineups": False,
                "include_races": False,
                "include_jobs": False,
                "include_veto_logs": False,
            },
        )

    def export_presets(self, filepath: str) -> Tuple[bool, str]:
        """Export only constraint presets to a JSON file.

        Args:
            filepath: Path to save the presets file

        Returns:
            Tuple of (success: bool, message: str)
        """
        return self.export_all(
            filepath,
            options={
                "include_settings": False,
                "include_presets": True,
                "include_lineups": False,
                "include_races": False,
                "include_jobs": False,
                "include_veto_logs": False,
            },
        )

    def export_lineups(
        self,
        filepath: str,
        race_id: Optional[int] = None,
        date_range: Optional[Tuple[date, date]] = None,
    ) -> Tuple[bool, str]:
        """Export lineups to a JSON file, optionally filtered.

        Args:
            filepath: Path to save the lineups file
            race_id: Optional race ID to filter lineups
            date_range: Optional tuple of (start_date, end_date) to filter by date

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            lineups = self._export_lineups(date_range=date_range, race_id=race_id)

            backup_data = {
                "export_metadata": self._create_metadata(
                    {"include_lineups": True, "race_id": race_id}
                ),
                "lineups": lineups,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            count = len(lineups)
            return True, f"Successfully exported {count} lineups to {filepath}"

        except Exception as e:
            return False, f"Export failed: {str(e)}"

    def import_backup(
        self, filepath: str, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Import application state from a JSON backup file.

        Args:
            filepath: Path to the backup file to import
            options: Optional dict with import options:
                - merge_strategy: "replace" | "merge" | "skip_existing" (default: "merge")
                - target_race_id: Optional[int] - Import lineups for specific race only
                - preserve_ids: bool - Try to preserve original IDs (default: False)

        Returns:
            Tuple of (success: bool, message: str)
        """
        options = options or {}
        default_options = {
            "merge_strategy": "merge",  # replace, merge, skip_existing
            "target_race_id": None,
            "preserve_ids": False,
        }
        default_options.update(options)
        options = default_options

        try:
            # Validate the backup first
            is_valid, errors = self.validate_backup(filepath)
            if not is_valid:
                return False, f"Invalid backup file: {', '.join(errors)}"

            # Load backup data
            with open(filepath, "r", encoding="utf-8") as f:
                backup_data = json.load(f)

            imported_counts = {
                "settings": 0,
                "presets": 0,
                "races": 0,
                "lineups": 0,
                "jobs": 0,
                "veto_logs": 0,
            }

            # Import settings
            if "settings" in backup_data:
                imported_counts["settings"] = self._import_settings(
                    backup_data["settings"], options["merge_strategy"]
                )

            # Import constraint presets
            if "constraint_presets" in backup_data:
                imported_counts["presets"] = self._import_presets(
                    backup_data["constraint_presets"],
                    backup_data.get("recent_presets", []),
                    options["merge_strategy"],
                )

            # Import races
            if "races" in backup_data:
                imported_counts["races"] = self._import_races(
                    backup_data["races"],
                    options["merge_strategy"],
                    options.get("preserve_ids", False),
                )

            # Import lineups
            if "lineups" in backup_data:
                imported_counts["lineups"] = self._import_lineups(
                    backup_data["lineups"],
                    options["merge_strategy"],
                    options.get("target_race_id"),
                )

            # Import jobs
            if "jobs" in backup_data:
                imported_counts["jobs"] = self._import_jobs(
                    backup_data["jobs"],
                    options["merge_strategy"],
                )

            # Import veto logs
            if "veto_logs" in backup_data:
                imported_counts["veto_logs"] = self._import_veto_logs(
                    backup_data["veto_logs"],
                    options["merge_strategy"],
                )

            # Build summary message
            summary_parts = []
            for key, count in imported_counts.items():
                if count > 0:
                    summary_parts.append(f"{count} {key}")

            if summary_parts:
                return True, f"Successfully imported: {', '.join(summary_parts)}"
            else:
                return True, "Backup file was valid but contained no importable data"

        except Exception as e:
            return False, f"Import failed: {str(e)}"

    def validate_backup(self, filepath: str) -> Tuple[bool, List[str]]:
        """Validate a backup file format and version compatibility.

        Args:
            filepath: Path to the backup file to validate

        Returns:
            Tuple of (is_valid: bool, list_of_errors: List[str])
        """
        errors = []

        try:
            # Check file exists and is readable
            if not Path(filepath).exists():
                return False, [f"File not found: {filepath}"]

            # Try to parse JSON
            with open(filepath, "r", encoding="utf-8") as f:
                backup_data = json.load(f)

            # Check for required metadata
            if "export_metadata" not in backup_data:
                errors.append("Missing export_metadata section")
            else:
                metadata = backup_data["export_metadata"]

                # Check version compatibility
                version = metadata.get("version", "0.0")
                try:
                    major_version = int(version.split(".")[0])
                    current_major = int(self.EXPORT_VERSION.split(".")[0])

                    if major_version > current_major:
                        errors.append(
                            f"Backup version {version} is newer than "
                            f"supported version {self.EXPORT_VERSION}. "
                            f"Please update the application."
                        )
                except (ValueError, IndexError):
                    errors.append(f"Invalid version format: {version}")

                # Check export date
                if "export_date" not in metadata:
                    errors.append("Missing export_date in metadata")

            # Validate data sections if present
            if "constraint_presets" in backup_data:
                presets = backup_data["constraint_presets"]
                if not isinstance(presets, list):
                    errors.append("constraint_presets must be a list")

            if "races" in backup_data:
                races = backup_data["races"]
                if not isinstance(races, list):
                    errors.append("races must be a list")

            if "lineups" in backup_data:
                lineups = backup_data["lineups"]
                if not isinstance(lineups, list):
                    errors.append("lineups must be a list")

            if "jobs" in backup_data:
                jobs = backup_data["jobs"]
                if not isinstance(jobs, list):
                    errors.append("jobs must be a list")

            return len(errors) == 0, errors

        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON format: {str(e)}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    def _create_metadata(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Create export metadata section.

        Args:
            options: Export options dict

        Returns:
            Metadata dictionary
        """
        includes = []
        if options.get("include_settings"):
            includes.append("settings")
        if options.get("include_presets"):
            includes.append("presets")
        if options.get("include_lineups"):
            includes.append("lineups")
        if options.get("include_races"):
            includes.append("races")
        if options.get("include_jobs"):
            includes.append("jobs")
        if options.get("include_veto_logs"):
            includes.append("veto_logs")

        return {
            "version": self.EXPORT_VERSION,
            "export_date": datetime.utcnow().isoformat() + "Z",
            "app_version": self.APP_VERSION,
            "includes": includes,
        }

    def _export_settings(self) -> Dict[str, Any]:
        """Export QSettings to dictionary.

        Returns:
            Dictionary containing all settings
        """
        settings_data = {}

        # Export all keys from QSettings
        self.settings.beginGroup("")
        for key in self.settings.allKeys():
            value = self.settings.value(key)
            # Handle binary data (window geometry) via base64
            if isinstance(value, bytes):
                value = base64.b64encode(value).decode("ascii")
            settings_data[key] = value
        self.settings.endGroup()

        # Add known important settings explicitly to ensure they're captured
        known_settings = [
            "session_restore_enabled",
            "load_last_race_on_startup",
            "restore_window_geometry",
            "restore_lineups",
            "restore_active_tab",
            "default_lineup_count",
            "default_mcmc_iterations",
            "default_max_ownership",
            "theme",
            "alternating_row_colors",
            "live_optimization/enabled",
            "live_optimization/debounce_ms",
            "live_optimization/realtime_mode",
            "gpu/enabled",
            "gpu/url",
            "gpu/timeout",
        ]

        for key in known_settings:
            if key not in settings_data:
                value = self.settings.value(key)
                if value is not None:
                    settings_data[key] = value

        return settings_data

    def _export_presets(self) -> Dict[str, List]:
        """Export constraint presets and recent preset history.

        Returns:
            Dictionary with "presets" and "recent" lists
        """
        presets = []
        recent = []

        try:
            # Get all presets from PresetManager
            with self.preset_manager.get_connection() as conn:
                # Export all presets
                cursor = conn.execute(
                    """SELECT id, name, description, is_global, race_type, 
                              track_name, config_json, created_at, updated_at, usage_count
                       FROM constraint_presets ORDER BY id"""
                )

                for row in cursor.fetchall():
                    preset = {
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
                    presets.append(preset)

                # Export recent presets (just the IDs, they reference presets above)
                cursor = conn.execute(
                    """SELECT preset_id FROM recent_presets 
                       ORDER BY applied_at DESC"""
                )
                recent = [row["preset_id"] for row in cursor.fetchall()]

        except Exception as e:
            print(f"Warning: Could not export presets: {e}")

        return {"presets": presets, "recent": recent}

    def _export_races(
        self, date_range: Optional[Tuple[date, date]] = None
    ) -> List[Dict]:
        """Export races from database.

        Args:
            date_range: Optional tuple of (start_date, end_date)

        Returns:
            List of race dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                if date_range:
                    start_date, end_date = date_range
                    cursor = conn.execute(
                        """SELECT id, track_name, race_date, created_at
                           FROM races 
                           WHERE race_date >= ? AND race_date <= ?
                           ORDER BY created_at DESC""",
                        (start_date.isoformat(), end_date.isoformat()),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT id, track_name, race_date, created_at
                           FROM races ORDER BY created_at DESC"""
                    )

                races = []
                for row in cursor.fetchall():
                    race = {
                        "id": row["id"],
                        "track_name": row["track_name"],
                        "race_date": row["race_date"],
                        "created_at": row["created_at"],
                    }
                    races.append(race)

                return races

        except Exception as e:
            print(f"Warning: Could not export races: {e}")
            return []

    def _export_lineups(
        self,
        date_range: Optional[Tuple[date, date]] = None,
        race_id: Optional[int] = None,
    ) -> List[Dict]:
        """Export lineups from database.

        Args:
            date_range: Optional tuple of (start_date, end_date)
            race_id: Optional race ID to filter by

        Returns:
            List of lineup dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                query = """SELECT id, race_id, lineup_data, created_at
                          FROM lineups WHERE 1=1"""
                params = []

                if race_id is not None:
                    query += " AND race_id = ?"
                    params.append(race_id)

                if date_range:
                    query += " AND created_at >= ? AND created_at <= ?"
                    start_date, end_date = date_range
                    params.extend([start_date.isoformat(), end_date.isoformat()])

                query += " ORDER BY created_at DESC"

                cursor = conn.execute(query, params)

                lineups = []
                for row in cursor.fetchall():
                    lineup = {
                        "id": row["id"],
                        "race_id": row["race_id"],
                        "drivers": json.loads(row["lineup_data"]),
                        "created_at": row["created_at"],
                    }
                    lineups.append(lineup)

                return lineups

        except Exception as e:
            print(f"Warning: Could not export lineups: {e}")
            return []

    def _export_jobs(
        self, date_range: Optional[Tuple[date, date]] = None
    ) -> List[Dict]:
        """Export jobs from database.

        Args:
            date_range: Optional tuple of (start_date, end_date)

        Returns:
            List of job dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                if date_range:
                    start_date, end_date = date_range
                    cursor = conn.execute(
                        """SELECT id, name, status, config_json, result_json,
                                  created_at, started_at, completed_at, error_message
                           FROM jobs 
                           WHERE created_at >= ? AND created_at <= ?
                           ORDER BY created_at DESC""",
                        (start_date.isoformat(), end_date.isoformat()),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT id, name, status, config_json, result_json,
                                  created_at, started_at, completed_at, error_message
                           FROM jobs ORDER BY created_at DESC"""
                    )

                jobs = []
                for row in cursor.fetchall():
                    job = {
                        "id": row["id"],
                        "name": row["name"],
                        "status": row["status"],
                        "config": json.loads(row["config_json"])
                        if row["config_json"]
                        else None,
                        "result": json.loads(row["result_json"])
                        if row["result_json"]
                        else None,
                        "created_at": row["created_at"],
                        "started_at": row["started_at"],
                        "completed_at": row["completed_at"],
                        "error_message": row["error_message"],
                    }
                    jobs.append(job)

                return jobs

        except Exception as e:
            print(f"Warning: Could not export jobs: {e}")
            return []

    def _export_veto_logs(
        self, date_range: Optional[Tuple[date, date]] = None
    ) -> List[Dict]:
        """Export veto logs from database.

        Args:
            date_range: Optional tuple of (start_date, end_date)

        Returns:
            List of veto log dictionaries
        """
        try:
            # Veto logs are stored in a separate SQLite database
            veto_db_path = (
                Path.home()
                / "Library"
                / "Application Support"
                / "NascarOptimizer"
                / "veto_logs.db"
            )

            if not veto_db_path.exists():
                return []

            conn = sqlite3.connect(str(veto_db_path))
            conn.row_factory = sqlite3.Row

            try:
                if date_range:
                    start_date, end_date = date_range
                    cursor = conn.execute(
                        """SELECT id, timestamp, rule_name, driver, severity, 
                                  reason, lineup_context
                           FROM veto_logs 
                           WHERE timestamp >= ? AND timestamp <= ?
                           ORDER BY timestamp DESC""",
                        (start_date.isoformat(), end_date.isoformat()),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT id, timestamp, rule_name, driver, severity, 
                                  reason, lineup_context
                           FROM veto_logs ORDER BY timestamp DESC"""
                    )

                veto_logs = []
                for row in cursor.fetchall():
                    log = {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "rule_name": row["rule_name"],
                        "driver": row["driver"],
                        "severity": row["severity"],
                        "reason": row["reason"],
                        "lineup_context": row["lineup_context"],
                    }
                    veto_logs.append(log)

                return veto_logs

            finally:
                conn.close()

        except Exception as e:
            print(f"Warning: Could not export veto logs: {e}")
            return []

    def _import_settings(self, settings_data: Dict, merge_strategy: str) -> int:
        """Import settings from backup data.

        Args:
            settings_data: Dictionary of settings to import
            merge_strategy: "replace" | "merge" | "skip_existing"

        Returns:
            Number of settings imported
        """
        count = 0

        for key, value in settings_data.items():
            # Skip internal keys
            if key.startswith("_"):
                continue

            if merge_strategy == "skip_existing":
                if self.settings.value(key) is not None:
                    continue

            # Decode base64 binary data
            if isinstance(value, str) and key.endswith("_geometry"):
                try:
                    value = base64.b64decode(value)
                except Exception:
                    pass  # Keep as string if decoding fails

            self.settings.setValue(key, value)
            count += 1

        return count

    def _import_presets(
        self,
        presets: List[Dict],
        recent_preset_ids: List[int],
        merge_strategy: str,
    ) -> int:
        """Import constraint presets from backup data.

        Args:
            presets: List of preset dictionaries
            recent_preset_ids: List of recent preset IDs
            merge_strategy: "replace" | "merge" | "skip_existing"

        Returns:
            Number of presets imported
        """
        count = 0
        id_mapping = {}  # Map old IDs to new IDs

        try:
            with self.preset_manager.get_connection() as conn:
                for preset in presets:
                    old_id = preset.get("id")
                    name = preset.get("name")
                    config = preset.get("config", {})
                    is_global = preset.get("is_global", True)
                    race_type = preset.get("race_type")
                    track_name = preset.get("track_name")
                    description = preset.get("description", "")

                    # Check if preset with this name exists
                    existing = conn.execute(
                        "SELECT id FROM constraint_presets WHERE name = ?",
                        (name,),
                    ).fetchone()

                    if existing:
                        if merge_strategy == "skip_existing":
                            id_mapping[old_id] = existing["id"]
                            continue
                        elif merge_strategy == "replace":
                            # Delete existing
                            conn.execute(
                                "DELETE FROM constraint_presets WHERE id = ?",
                                (existing["id"],),
                            )

                    # Insert new preset
                    cursor = conn.execute(
                        """INSERT INTO constraint_presets 
                           (name, description, is_global, race_type, track_name, config_json)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            name,
                            description,
                            is_global,
                            race_type,
                            track_name,
                            json.dumps(config),
                        ),
                    )
                    new_id = cursor.lastrowid
                    id_mapping[old_id] = new_id
                    count += 1

                # Import recent preset history (remap IDs)
                if merge_strategy != "skip_existing":
                    for old_preset_id in recent_preset_ids:
                        new_id = id_mapping.get(old_preset_id)
                        if new_id:
                            conn.execute(
                                """INSERT INTO recent_presets (preset_id, applied_at)
                                   VALUES (?, datetime('now'))""",
                                (new_id,),
                            )

        except Exception as e:
            print(f"Warning: Could not import presets: {e}")

        return count

    def _import_races(
        self,
        races: List[Dict],
        merge_strategy: str,
        preserve_ids: bool,
    ) -> int:
        """Import races from backup data.

        Args:
            races: List of race dictionaries
            merge_strategy: "replace" | "merge" | "skip_existing"
            preserve_ids: Whether to try to preserve original IDs

        Returns:
            Number of races imported
        """
        count = 0

        try:
            with self.db_manager.get_connection() as conn:
                for race in races:
                    track_name = race.get("track_name")
                    race_date = race.get("race_date")
                    old_id = race.get("id")

                    if not track_name or not race_date:
                        continue

                    # Check if race with this track/date exists
                    existing = conn.execute(
                        """SELECT id FROM races 
                           WHERE track_name = ? AND race_date = ?""",
                        (track_name, race_date),
                    ).fetchone()

                    if existing:
                        if merge_strategy == "skip_existing":
                            continue
                        elif merge_strategy == "replace":
                            conn.execute(
                                "DELETE FROM races WHERE id = ?",
                                (existing["id"],),
                            )

                    # Insert race
                    if preserve_ids and old_id:
                        try:
                            conn.execute(
                                """INSERT INTO races (id, track_name, race_date)
                                   VALUES (?, ?, ?)""",
                                (old_id, track_name, race_date),
                            )
                        except sqlite3.IntegrityError:
                            # ID conflict, auto-generate
                            conn.execute(
                                """INSERT INTO races (track_name, race_date)
                                   VALUES (?, ?)""",
                                (track_name, race_date),
                            )
                    else:
                        conn.execute(
                            """INSERT INTO races (track_name, race_date)
                               VALUES (?, ?)""",
                            (track_name, race_date),
                        )

                    count += 1

        except Exception as e:
            print(f"Warning: Could not import races: {e}")

        return count

    def _import_lineups(
        self,
        lineups: List[Dict],
        merge_strategy: str,
        target_race_id: Optional[int] = None,
    ) -> int:
        """Import lineups from backup data.

        Args:
            lineups: List of lineup dictionaries
            merge_strategy: "replace" | "merge" | "skip_existing"
            target_race_id: Optional race ID to assign all lineups to

        Returns:
            Number of lineups imported
        """
        count = 0

        try:
            with self.db_manager.get_connection() as conn:
                # If target_race_id specified, use it for all lineups
                race_id = target_race_id

                for lineup in lineups:
                    # Get race_id from lineup data if no target specified
                    if race_id is None:
                        lineup_race_id = lineup.get("race_id")
                        if not lineup_race_id:
                            continue
                    else:
                        lineup_race_id = race_id

                    drivers = lineup.get("drivers")
                    if not drivers:
                        continue

                    # Check if this exact lineup exists for this race
                    if merge_strategy == "skip_existing":
                        existing = conn.execute(
                            """SELECT id FROM lineups 
                               WHERE race_id = ? AND lineup_data = ?""",
                            (lineup_race_id, json.dumps(drivers)),
                        ).fetchone()
                        if existing:
                            continue

                    conn.execute(
                        """INSERT INTO lineups (race_id, lineup_data)
                           VALUES (?, ?)""",
                        (lineup_race_id, json.dumps(drivers)),
                    )
                    count += 1

        except Exception as e:
            print(f"Warning: Could not import lineups: {e}")

        return count

    def _import_jobs(self, jobs: List[Dict], merge_strategy: str) -> int:
        """Import jobs from backup data.

        Args:
            jobs: List of job dictionaries
            merge_strategy: "replace" | "merge" | "skip_existing"

        Returns:
            Number of jobs imported
        """
        count = 0

        try:
            with self.db_manager.get_connection() as conn:
                for job in jobs:
                    job_id = job.get("id")
                    name = job.get("name", "Imported Job")
                    status = job.get("status", "completed")
                    config = job.get("config", {})
                    result = job.get("result")
                    created_at = job.get("created_at")
                    started_at = job.get("started_at")
                    completed_at = job.get("completed_at")
                    error_message = job.get("error_message")

                    if not job_id:
                        continue

                    # Check if job with this ID exists
                    existing = conn.execute(
                        "SELECT id FROM jobs WHERE id = ?", (job_id,)
                    ).fetchone()

                    if existing:
                        if merge_strategy == "skip_existing":
                            continue
                        elif merge_strategy == "replace":
                            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

                    conn.execute(
                        """INSERT INTO jobs 
                           (id, name, status, config_json, result_json,
                            created_at, started_at, completed_at, error_message)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            job_id,
                            name,
                            status,
                            json.dumps(config),
                            json.dumps(result) if result else None,
                            created_at or datetime.utcnow().isoformat(),
                            started_at,
                            completed_at,
                            error_message,
                        ),
                    )
                    count += 1

        except Exception as e:
            print(f"Warning: Could not import jobs: {e}")

        return count

    def _import_veto_logs(self, veto_logs: List[Dict], merge_strategy: str) -> int:
        """Import veto logs from backup data.

        Args:
            veto_logs: List of veto log dictionaries
            merge_strategy: "replace" | "merge" | "skip_existing"

        Returns:
            Number of veto logs imported
        """
        count = 0

        try:
            veto_db_path = (
                Path.home()
                / "Library"
                / "Application Support"
                / "NascarOptimizer"
                / "veto_logs.db"
            )

            # Ensure veto_logs database exists
            if not veto_db_path.parent.exists():
                veto_db_path.parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(str(veto_db_path))
            conn.row_factory = sqlite3.Row

            try:
                # Ensure table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS veto_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        rule_name TEXT NOT NULL,
                        driver TEXT,
                        severity TEXT,
                        reason TEXT,
                        lineup_context TEXT
                    )
                """)

                for log in veto_logs:
                    timestamp = log.get("timestamp")
                    rule_name = log.get("rule_name")
                    driver = log.get("driver")
                    severity = log.get("severity", "info")
                    reason = log.get("reason")
                    lineup_context = log.get("lineup_context")

                    if not rule_name:
                        continue

                    # Check for duplicate
                    if merge_strategy == "skip_existing":
                        existing = conn.execute(
                            """SELECT id FROM veto_logs 
                               WHERE timestamp = ? AND rule_name = ? AND driver = ?""",
                            (timestamp, rule_name, driver),
                        ).fetchone()
                        if existing:
                            continue

                    conn.execute(
                        """INSERT INTO veto_logs 
                           (timestamp, rule_name, driver, severity, reason, lineup_context)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            timestamp,
                            rule_name,
                            driver,
                            severity,
                            reason,
                            lineup_context,
                        ),
                    )
                    count += 1

                conn.commit()

            finally:
                conn.close()

        except Exception as e:
            print(f"Warning: Could not import veto logs: {e}")

        return count

    def create_automatic_backup(self) -> Tuple[bool, str]:
        """Create an automatic backup of current state before import.

        Creates a .bak file in the same location as the main database.

        Returns:
            Tuple of (success: bool, filepath or error message: str)
        """
        try:
            db_path = self.db_manager.get_database_path()
            backup_path = f"{db_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            shutil.copy2(db_path, backup_path)
            return True, backup_path

        except Exception as e:
            return False, f"Failed to create automatic backup: {str(e)}"

    def get_backup_summary(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Get a summary of what's contained in a backup file.

        Args:
            filepath: Path to the backup file

        Returns:
            Dictionary with summary info or None if invalid
        """
        try:
            is_valid, errors = self.validate_backup(filepath)
            if not is_valid:
                return None

            with open(filepath, "r", encoding="utf-8") as f:
                backup_data = json.load(f)

            metadata = backup_data.get("export_metadata", {})

            summary = {
                "version": metadata.get("version", "unknown"),
                "export_date": metadata.get("export_date", "unknown"),
                "app_version": metadata.get("app_version", "unknown"),
                "includes": metadata.get("includes", []),
                "counts": {},
            }

            # Count items in each section
            for section in [
                "constraint_presets",
                "races",
                "lineups",
                "jobs",
                "veto_logs",
            ]:
                if section in backup_data:
                    summary["counts"][section] = len(backup_data[section])

            # Settings is a dict, not a list
            if "settings" in backup_data:
                summary["counts"]["settings"] = len(backup_data["settings"])

            return summary

        except Exception:
            return None
