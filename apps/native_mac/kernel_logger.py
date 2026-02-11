"""Kernel veto logger for capturing and storing optimization rejection events.

Provides KernelVetoLogger class that logs veto events during optimization,
storing them in SQLite for post-hoc analysis. Veto logs capture why lineups
were rejected by the kernel validation system, enabling users to debug
constraint violations and tune their optimization settings.
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class VetoSeverity(Enum):
    """Severity levels for veto events."""

    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"
    FATAL = "Fatal"


class RuleCategory(Enum):
    """Categories of veto rules."""

    CONSTRAINT = "constraint"
    DK_RULE = "dk_rule"
    STACKING = "stacking"
    VETO = "veto"


class KernelVetoLogger:
    """Logs and retrieves kernel veto events for optimization debugging.

    Captures veto events during optimization (lineup rejections) and stores
    them in SQLite for post-hoc analysis. Supports filtering by job, race,
    rule type, and severity. Provides export capabilities to JSON and CSV.

    Performance optimized by batching writes during optimization and
    flushing to database on job completion to avoid DB writes in hot loop.

    Attributes:
        db_path: Path to SQLite database file
        batch_mode: Whether to batch writes (True during optimization)
        _batch_buffer: In-memory buffer for batch writes
        _connection: SQLite connection (lazily initialized)

    Example:
        veto_logger = KernelVetoLogger("veto_logs.db")

        # During optimization, log vetos
        veto_logger.log_veto(
            job_id="job-123",
            race_id="daytona-500",
            rule_name="salary_cap",
            severity="Error",
            reason="Lineup costs $52,000, exceeds $50,000 cap",
            constraint_value=50000,
            actual_value=52000
        )

        # Retrieve vetos for analysis
        vetos = veto_logger.get_vetos_for_job("job-123")
        veto_logger.export_vetos("job-123", "json", "vetos.json")
    """

    def __init__(self, db_path: str, batch_mode: bool = True):
        """Initialize KernelVetoLogger.

        Args:
            db_path: Path to SQLite database file
            batch_mode: If True, buffer writes until flush() is called
        """
        self.db_path = db_path
        self.batch_mode = batch_mode
        self._batch_buffer: List[Dict[str, Any]] = []
        self._connection: Optional[sqlite3.Connection] = None

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        logger.info(
            f"KernelVetoLogger initialized: {db_path} (batch_mode={batch_mode})"
        )

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def _init_database(self) -> None:
        """Create veto_logs table if not exists."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS veto_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                race_id TEXT,
                timestamp TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                rule_category TEXT,
                driver_id TEXT,
                driver_name TEXT,
                severity TEXT NOT NULL,
                reason TEXT NOT NULL,
                lineup_context TEXT,  -- JSON array
                constraint_value REAL,
                actual_value REAL,
                additional_data TEXT,  -- JSON for extensibility
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for common queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_veto_logs_job_id 
            ON veto_logs(job_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_veto_logs_race_id 
            ON veto_logs(race_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_veto_logs_rule_name 
            ON veto_logs(rule_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_veto_logs_severity 
            ON veto_logs(severity)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_veto_logs_timestamp 
            ON veto_logs(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_veto_logs_driver_id 
            ON veto_logs(driver_id)
        """)

        conn.commit()

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def log_veto(
        self,
        job_id: str,
        race_id: str,
        rule_name: str,
        severity: str,
        reason: str,
        rule_category: Optional[str] = None,
        driver_id: Optional[str] = None,
        driver_name: Optional[str] = None,
        lineup_context: Optional[List[Any]] = None,
        constraint_value: Optional[float] = None,
        actual_value: Optional[float] = None,
        **kwargs,
    ) -> None:
        """Log a single veto event.

        In batch_mode, the veto is buffered in memory until flush() is called.
        Otherwise, it's written immediately to the database.

        Args:
            job_id: UUID of optimization job
            race_id: Race identifier
            rule_name: Name of rule that triggered veto (e.g., "salary_cap")
            severity: One of "Info", "Warning", "Error", "Fatal"
            reason: Human-readable explanation of violation
            rule_category: Optional category ("constraint", "dk_rule", "stacking", "veto")
            driver_id: Optional driver identifier (if driver-specific)
            driver_name: Optional driver name for display
            lineup_context: Optional list of driver IDs in rejected lineup
            constraint_value: The constraint that was violated
            actual_value: The actual value that caused violation
            **kwargs: Additional data stored as JSON
        """
        veto_event = {
            "job_id": job_id,
            "race_id": race_id,
            "timestamp": datetime.now().isoformat(),
            "rule_name": rule_name,
            "rule_category": rule_category,
            "driver_id": driver_id,
            "driver_name": driver_name,
            "severity": severity,
            "reason": reason,
            "lineup_context": json.dumps(lineup_context) if lineup_context else None,
            "constraint_value": constraint_value,
            "actual_value": actual_value,
            "additional_data": json.dumps(kwargs) if kwargs else None,
        }

        if self.batch_mode:
            self._batch_buffer.append(veto_event)
        else:
            self._write_veto_to_db(veto_event)

    def _write_veto_to_db(self, veto_event: Dict[str, Any]) -> None:
        """Write a single veto event to database."""
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO veto_logs (
                    job_id, race_id, timestamp, rule_name, rule_category,
                    driver_id, driver_name, severity, reason, lineup_context,
                    constraint_value, actual_value, additional_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    veto_event["job_id"],
                    veto_event["race_id"],
                    veto_event["timestamp"],
                    veto_event["rule_name"],
                    veto_event["rule_category"],
                    veto_event["driver_id"],
                    veto_event["driver_name"],
                    veto_event["severity"],
                    veto_event["reason"],
                    veto_event["lineup_context"],
                    veto_event["constraint_value"],
                    veto_event["actual_value"],
                    veto_event["additional_data"],
                ),
            )

    def flush(self) -> int:
        """Flush batched veto events to database.

        Returns:
            Number of veto events written to database
        """
        if not self._batch_buffer:
            return 0

        count = len(self._batch_buffer)

        with self._transaction() as conn:
            for veto_event in self._batch_buffer:
                conn.execute(
                    """
                    INSERT INTO veto_logs (
                        job_id, race_id, timestamp, rule_name, rule_category,
                        driver_id, driver_name, severity, reason, lineup_context,
                        constraint_value, actual_value, additional_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        veto_event["job_id"],
                        veto_event["race_id"],
                        veto_event["timestamp"],
                        veto_event["rule_name"],
                        veto_event["rule_category"],
                        veto_event["driver_id"],
                        veto_event["driver_name"],
                        veto_event["severity"],
                        veto_event["reason"],
                        veto_event["lineup_context"],
                        veto_event["constraint_value"],
                        veto_event["actual_value"],
                        veto_event["additional_data"],
                    ),
                )

        self._batch_buffer.clear()
        logger.info(f"Flushed {count} veto events to database")
        return count

    def start_batch(self) -> None:
        """Enable batch mode (buffer writes)."""
        self.batch_mode = True
        logger.debug("Batch mode enabled")

    def end_batch(self) -> int:
        """Disable batch mode and flush pending events.

        Returns:
            Number of events flushed
        """
        self.batch_mode = False
        return self.flush()

    def get_vetos_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all veto events for a specific job.

        Args:
            job_id: Job UUID to query

        Returns:
            List of veto event dictionaries
        """
        # Include batched events if querying current job
        batched = [v for v in self._batch_buffer if v["job_id"] == job_id]

        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT * FROM veto_logs WHERE job_id = ? ORDER BY timestamp", (job_id,)
            )
            rows = cursor.fetchall()

        result = [self._row_to_dict(row) for row in rows]
        result.extend(batched)
        return result

    def get_vetos_for_race(self, race_id: str) -> List[Dict[str, Any]]:
        """Get all veto events for a specific race.

        Args:
            race_id: Race identifier to query

        Returns:
            List of veto event dictionaries
        """
        batched = [v for v in self._batch_buffer if v["race_id"] == race_id]

        with self._transaction() as conn:
            cursor = conn.execute(
                "SELECT * FROM veto_logs WHERE race_id = ? ORDER BY timestamp",
                (race_id,),
            )
            rows = cursor.fetchall()

        result = [self._row_to_dict(row) for row in rows]
        result.extend(batched)
        return result

    def get_vetos_by_rule(
        self, rule_name: str, job_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get veto events filtered by rule name.

        Args:
            rule_name: Rule name to filter by
            job_id: Optional job ID to further filter

        Returns:
            List of veto event dictionaries
        """
        batched = [
            v
            for v in self._batch_buffer
            if v["rule_name"] == rule_name and (job_id is None or v["job_id"] == job_id)
        ]

        with self._transaction() as conn:
            if job_id:
                cursor = conn.execute(
                    """SELECT * FROM veto_logs 
                       WHERE rule_name = ? AND job_id = ? 
                       ORDER BY timestamp""",
                    (rule_name, job_id),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM veto_logs WHERE rule_name = ? ORDER BY timestamp",
                    (rule_name,),
                )
            rows = cursor.fetchall()

        result = [self._row_to_dict(row) for row in rows]
        result.extend(batched)
        return result

    def get_vetos_by_severity(
        self, severity: str, job_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get veto events filtered by severity.

        Args:
            severity: Severity level ("Info", "Warning", "Error", "Fatal")
            job_id: Optional job ID to further filter

        Returns:
            List of veto event dictionaries
        """
        batched = [
            v
            for v in self._batch_buffer
            if v["severity"] == severity and (job_id is None or v["job_id"] == job_id)
        ]

        with self._transaction() as conn:
            if job_id:
                cursor = conn.execute(
                    """SELECT * FROM veto_logs 
                       WHERE severity = ? AND job_id = ? 
                       ORDER BY timestamp""",
                    (severity, job_id),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM veto_logs WHERE severity = ? ORDER BY timestamp",
                    (severity,),
                )
            rows = cursor.fetchall()

        result = [self._row_to_dict(row) for row in rows]
        result.extend(batched)
        return result

    def get_veto_summary(self, job_id: str) -> Dict[str, Any]:
        """Get summary statistics for a job's veto events.

        Args:
            job_id: Job UUID to summarize

        Returns:
            Dictionary with veto counts by severity and rule
        """
        with self._transaction() as conn:
            # Count by severity
            cursor = conn.execute(
                """SELECT severity, COUNT(*) as count 
                   FROM veto_logs 
                   WHERE job_id = ? 
                   GROUP BY severity""",
                (job_id,),
            )
            severity_counts = {
                row["severity"]: row["count"] for row in cursor.fetchall()
            }

            # Count by rule
            cursor = conn.execute(
                """SELECT rule_name, COUNT(*) as count 
                   FROM veto_logs 
                   WHERE job_id = ? 
                   GROUP BY rule_name 
                   ORDER BY count DESC""",
                (job_id,),
            )
            rule_counts = {row["rule_name"]: row["count"] for row in cursor.fetchall()}

            # Total count
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM veto_logs WHERE job_id = ?", (job_id,)
            )
            total = cursor.fetchone()["count"]

        # Add batched counts
        for v in self._batch_buffer:
            if v["job_id"] == job_id:
                total += 1
                severity_counts[v["severity"]] = (
                    severity_counts.get(v["severity"], 0) + 1
                )
                rule_counts[v["rule_name"]] = rule_counts.get(v["rule_name"], 0) + 1

        return {
            "job_id": job_id,
            "total_vetos": total,
            "by_severity": severity_counts,
            "by_rule": rule_counts,
        }

    def get_distinct_rules(self, job_id: Optional[str] = None) -> List[str]:
        """Get list of distinct rule names.

        Args:
            job_id: Optional job ID to filter by

        Returns:
            List of unique rule names
        """
        batched_rules = set()
        if job_id:
            batched_rules = {
                v["rule_name"] for v in self._batch_buffer if v["job_id"] == job_id
            }
        else:
            batched_rules = {v["rule_name"] for v in self._batch_buffer}

        with self._transaction() as conn:
            if job_id:
                cursor = conn.execute(
                    "SELECT DISTINCT rule_name FROM veto_logs WHERE job_id = ? ORDER BY rule_name",
                    (job_id,),
                )
            else:
                cursor = conn.execute(
                    "SELECT DISTINCT rule_name FROM veto_logs ORDER BY rule_name"
                )
            rules = [row["rule_name"] for row in cursor.fetchall()]

        rules.extend(batched_rules - set(rules))
        return sorted(rules)

    def get_distinct_drivers(self, job_id: Optional[str] = None) -> List[str]:
        """Get list of distinct driver names.

        Args:
            job_id: Optional job ID to filter by

        Returns:
            List of unique driver names
        """
        batched_drivers = set()
        if job_id:
            batched_drivers = {
                v["driver_name"]
                for v in self._batch_buffer
                if v["job_id"] == job_id and v["driver_name"]
            }
        else:
            batched_drivers = {
                v["driver_name"] for v in self._batch_buffer if v["driver_name"]
            }

        with self._transaction() as conn:
            if job_id:
                cursor = conn.execute(
                    """SELECT DISTINCT driver_name FROM veto_logs 
                       WHERE job_id = ? AND driver_name IS NOT NULL 
                       ORDER BY driver_name""",
                    (job_id,),
                )
            else:
                cursor = conn.execute(
                    """SELECT DISTINCT driver_name FROM veto_logs 
                       WHERE driver_name IS NOT NULL 
                       ORDER BY driver_name"""
                )
            drivers = [row["driver_name"] for row in cursor.fetchall()]

        drivers.extend(batched_drivers - set(drivers))
        return sorted([d for d in drivers if d])

    def clear_old_vetos(self, days: int = 30) -> int:
        """Delete veto events older than specified days.

        Args:
            days: Age threshold for deletion (default: 30 days)

        Returns:
            Number of records deleted
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM veto_logs WHERE timestamp < ?", (cutoff_date,)
            )
            deleted = cursor.rowcount

        logger.info(f"Cleared {deleted} old veto records (older than {days} days)")
        return deleted

    def clear_vetos_for_job(self, job_id: str) -> int:
        """Delete all veto events for a specific job.

        Args:
            job_id: Job UUID to clear

        Returns:
            Number of records deleted
        """
        # Clear from batch buffer
        self._batch_buffer = [v for v in self._batch_buffer if v["job_id"] != job_id]

        with self._transaction() as conn:
            cursor = conn.execute("DELETE FROM veto_logs WHERE job_id = ?", (job_id,))
            deleted = cursor.rowcount

        logger.info(f"Cleared {deleted} veto records for job {job_id}")
        return deleted

    def export_vetos(
        self, job_id: str, format: str, filepath: str, include_headers: bool = True
    ) -> None:
        """Export veto events to file.

        Args:
            job_id: Job UUID to export
            format: "json" or "csv"
            filepath: Output file path
            include_headers: For CSV, include header row

        Raises:
            ValueError: If format is not "json" or "csv"
        """
        vetos = self.get_vetos_for_job(job_id)

        if format.lower() == "json":
            self._export_json(vetos, filepath)
        elif format.lower() == "csv":
            self._export_csv(vetos, filepath, include_headers)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")

        logger.info(f"Exported {len(vetos)} vetos to {filepath} ({format})")

    def _export_json(self, vetos: List[Dict[str, Any]], filepath: str) -> None:
        """Export veto events to JSON file."""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "count": len(vetos),
            "vetos": vetos,
        }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

    def _export_csv(
        self, vetos: List[Dict[str, Any]], filepath: str, include_headers: bool
    ) -> None:
        """Export veto events to CSV file."""
        import csv

        if not vetos:
            # Write empty file with headers
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                if include_headers:
                    writer.writerow(
                        [
                            "timestamp",
                            "rule_name",
                            "driver_name",
                            "severity",
                            "reason",
                            "lineup_context",
                            "constraint_value",
                            "actual_value",
                        ]
                    )
            return

        fieldnames = [
            "timestamp",
            "rule_name",
            "rule_category",
            "driver_name",
            "severity",
            "reason",
            "lineup_context",
            "constraint_value",
            "actual_value",
        ]

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if include_headers:
                writer.writeheader()
            for veto in vetos:
                row = {k: veto.get(k, "") for k in fieldnames}
                writer.writerow(row)

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary."""
        result = dict(row)

        # Parse JSON fields
        if result.get("lineup_context"):
            try:
                result["lineup_context"] = json.loads(result["lineup_context"])
            except json.JSONDecodeError:
                pass

        if result.get("additional_data"):
            try:
                result["additional_data"] = json.loads(result["additional_data"])
            except json.JSONDecodeError:
                pass

        return result

    def close(self) -> None:
        """Close database connection and flush any pending events."""
        self.flush()
        if self._connection:
            self._connection.close()
            self._connection = None
        logger.info("KernelVetoLogger closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
