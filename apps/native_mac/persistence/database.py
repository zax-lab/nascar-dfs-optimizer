"""SQLite persistence layer for NASCAR DFS Optimizer."""

from contextlib import contextmanager
import json
import os
import sqlite3
from pathlib import Path
from typing import Generator, List, Optional, Any, Dict


class DatabaseManager:
    """Manages SQLite database connections and schema for the NASCAR DFS Optimizer.

    Provides context manager for automatic connection cleanup and schema initialization.
    Database is stored in ~/Library/Application Support/NASCAR DFS Optimizer/
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize DatabaseManager with optional custom database path.

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

        Example:
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM races")
                rows = cursor.fetchall()
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
        """Initialize database schema with all required tables.

        Creates tables if they don't exist:
        - races: Race information
        - drivers: Driver information (for historical data)
        - race_results: Historical race results
        - lineups: Saved lineup configurations
        - optimization_configs: User optimization settings
        - app_state: Application state key-value storage
        - jobs: Background job queue for optimization tasks
        """
        with self.get_connection() as conn:
            # Drivers table (for historical data)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    driver_id TEXT UNIQUE,
                    team TEXT,
                    salary INTEGER DEFAULT 8000,
                    avg_finish REAL DEFAULT 20.0
                )
            """)

            # Races table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS races (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    track TEXT NOT NULL,
                    date TEXT NOT NULL,
                    laps INTEGER,
                    status TEXT DEFAULT 'scheduled',
                    series TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Race results table (for historical data)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS race_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_id INTEGER NOT NULL,
                    driver_id INTEGER NOT NULL,
                    start_position INTEGER,
                    finish_position INTEGER,
                    laps INTEGER,
                    rating REAL,
                    FOREIGN KEY (race_id) REFERENCES races(id) ON DELETE CASCADE,
                    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE
                )
            """)

            # Lineups table with foreign key to races
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lineups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_id INTEGER NOT NULL,
                    lineup_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (race_id) REFERENCES races(id) ON DELETE CASCADE
                )
            """)

            # Optimization configs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    config_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # App state table for key-value storage
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Jobs table for background optimization tasks
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
                    config_json TEXT NOT NULL,
                    result_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    progress_percent INTEGER DEFAULT 0 CHECK(progress_percent >= 0 AND progress_percent <= 100)
                )
            """)

            # Index for efficient job queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)
            """)

            # Enable foreign key support
            conn.execute("PRAGMA foreign_keys = ON")

    def save_lineup(self, race_id: int, lineup_data: Dict[str, Any]) -> int:
        """Save a lineup to the database.

        Args:
            race_id: ID of the race this lineup is for
            lineup_data: Dictionary containing lineup configuration

        Returns:
            int: ID of the saved lineup
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO lineups (race_id, lineup_data) VALUES (?, ?)",
                (race_id, json.dumps(lineup_data)),
            )
            return cursor.lastrowid

    def load_lineups(self, race_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load lineups from the database.

        Args:
            race_id: Optional race ID to filter by. If None, returns all lineups.

        Returns:
            List of dictionaries containing lineup data with id, race_id,
            lineup_data, and created_at fields.
        """
        with self.get_connection() as conn:
            if race_id is not None:
                cursor = conn.execute(
                    "SELECT * FROM lineups WHERE race_id = ? ORDER BY created_at DESC",
                    (race_id,),
                )
            else:
                cursor = conn.execute("SELECT * FROM lineups ORDER BY created_at DESC")

            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "race_id": row["race_id"],
                    "lineup_data": json.loads(row["lineup_data"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def save_race(self, track_name: str, race_date: str) -> int:
        """Save a race to the database.

        Args:
            track_name: Name of the race track
            race_date: Date of the race (ISO format string)

        Returns:
            int: ID of the saved race
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO races (track_name, race_date) VALUES (?, ?)",
                (track_name, race_date),
            )
            return cursor.lastrowid

    def load_races(self) -> List[Dict[str, Any]]:
        """Load all races from the database.

        Returns:
            List of dictionaries containing race data.
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM races ORDER BY race_date DESC")
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "track_name": row["track_name"],
                    "race_date": row["race_date"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def save_config(self, name: str, config_data: Dict[str, Any]) -> int:
        """Save an optimization configuration.

        Args:
            name: Unique name for this configuration
            config_data: Dictionary containing configuration settings

        Returns:
            int: ID of the saved configuration
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO optimization_configs (name, config_data) 
                   VALUES (?, ?)
                   ON CONFLICT(name) DO UPDATE SET 
                   config_data=excluded.config_data,
                   created_at=CURRENT_TIMESTAMP""",
                (name, json.dumps(config_data)),
            )
            return cursor.lastrowid

    def load_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Load an optimization configuration by name.

        Args:
            name: Name of the configuration to load

        Returns:
            Dictionary containing configuration data, or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM optimization_configs WHERE name = ?", (name,)
            )
            row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "config_data": json.loads(row["config_data"]),
                    "created_at": row["created_at"],
                }
            return None

    def delete_lineup(self, lineup_id: int) -> bool:
        """Delete a lineup by ID.

        Args:
            lineup_id: ID of the lineup to delete

        Returns:
            bool: True if deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM lineups WHERE id = ?", (lineup_id,))
            return cursor.rowcount > 0

    def get_database_path(self) -> str:
        """Get the current database file path.

        Returns:
            str: Path to the database file
        """
        return str(self.db_path)

    # Job management methods

    def insert_job(self, job: Dict[str, Any]) -> str:
        """Insert a new job into the database.

        Args:
            job: Job dictionary with id, name, status, config_json, etc.

        Returns:
            str: ID of the inserted job
        """
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO jobs 
                   (id, name, status, config_json, result_json, created_at, 
                    started_at, completed_at, error_message, progress_percent)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job["id"],
                    job["name"],
                    job["status"],
                    json.dumps(job["config_json"]),
                    json.dumps(job["result_json"]) if job.get("result_json") else None,
                    job["created_at"],
                    job.get("started_at"),
                    job.get("completed_at"),
                    job.get("error_message"),
                    job.get("progress_percent", 0),
                ),
            )
            return job["id"]

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update a job with new values.

        Args:
            job_id: ID of the job to update
            updates: Dictionary of fields to update

        Returns:
            bool: True if updated, False if not found
        """
        # Build update statement dynamically
        allowed_fields = [
            "status",
            "result_json",
            "started_at",
            "completed_at",
            "error_message",
            "progress_percent",
        ]

        set_clauses = []
        values = []

        for field, value in updates.items():
            if field in allowed_fields:
                if field == "result_json" and value is not None:
                    value = json.dumps(value)
                set_clauses.append(f"{field} = ?")
                values.append(value)

        if not set_clauses:
            return False

        values.append(job_id)

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE jobs SET {', '.join(set_clauses)} WHERE id = ?",
                values,
            )
            return cursor.rowcount > 0

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID.

        Args:
            job_id: ID of the job to retrieve

        Returns:
            Dictionary containing job data, or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_job_dict(row)
            return None

    def list_jobs(
        self, status: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List jobs from the database.

        Args:
            status: Optional status filter (queued, running, completed, failed, cancelled)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip (for pagination)

        Returns:
            List of job dictionaries
        """
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute(
                    """SELECT * FROM jobs WHERE status = ? 
                       ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                    (status, limit, offset),
                )
            else:
                cursor = conn.execute(
                    """SELECT * FROM jobs 
                       ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                    (limit, offset),
                )

            rows = cursor.fetchall()
            return [self._row_to_job_dict(row) for row in rows]

    def delete_old_jobs(self, days: int = 30) -> int:
        """Delete jobs older than specified days.

        Args:
            days: Number of days to keep (delete jobs older than this)

        Returns:
            int: Number of jobs deleted
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """DELETE FROM jobs 
                   WHERE created_at < datetime('now', '-{} days')""".format(days)
            )
            return cursor.rowcount

    def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID.

        Args:
            job_id: ID of job to delete

        Returns:
            bool: True if deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0

    def get_jobs_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get jobs filtered by status.

        Args:
            status: Status to filter by (queued, running, completed, failed, cancelled)
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries with matching status
        """
        return self.list_jobs(status=status, limit=limit)

    def get_jobs_by_date_range(
        self, start_date: str, end_date: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get jobs within a date range.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries within date range
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM jobs 
                   WHERE created_at >= ? AND created_at <= ?
                   ORDER BY created_at DESC LIMIT ?""",
                (start_date, end_date, limit),
            )
            rows = cursor.fetchall()
            return [self._row_to_job_dict(row) for row in rows]

    def search_jobs(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search jobs by name or configuration content.

        Args:
            query: Search string
            limit: Maximum number of jobs to return

        Returns:
            List of matching job dictionaries
        """
        search_pattern = f"%{query}%"
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM jobs 
                   WHERE name LIKE ? OR config_json LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (search_pattern, search_pattern, limit),
            )
            rows = cursor.fetchall()
            return [self._row_to_job_dict(row) for row in rows]

    def get_job_stats(self) -> Dict[str, Any]:
        """Get statistics about jobs.

        Returns:
            Dictionary with job counts by status and totals
        """
        with self.get_connection() as conn:
            # Count by status
            cursor = conn.execute(
                """SELECT status, COUNT(*) as count 
                   FROM jobs GROUP BY status"""
            )
            status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

            # Total count
            cursor = conn.execute("SELECT COUNT(*) as total FROM jobs")
            total = cursor.fetchone()["total"]

            # Recent jobs (last 24 hours)
            cursor = conn.execute(
                """SELECT COUNT(*) as recent FROM jobs 
                   WHERE created_at >= datetime('now', '-1 day')"""
            )
            recent = cursor.fetchone()["recent"]

            return {
                "total": total,
                "recent_24h": recent,
                "by_status": status_counts,
                "queued": status_counts.get("queued", 0),
                "running": status_counts.get("running", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0),
                "cancelled": status_counts.get("cancelled", 0),
            }

    def _row_to_job_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a job dictionary.

        Args:
            row: sqlite3.Row from jobs table

        Returns:
            Dictionary with job data
        """
        config_json = row["config_json"]
        if isinstance(config_json, str):
            config_json = json.loads(config_json)

        result_json = row["result_json"]
        if isinstance(result_json, str):
            result_json = json.loads(result_json)

        return {
            "id": row["id"],
            "name": row["name"],
            "status": row["status"],
            "config_json": config_json,
            "result_json": result_json,
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "error_message": row["error_message"],
            "progress_percent": row["progress_percent"],
        }
