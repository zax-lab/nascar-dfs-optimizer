"""Qt Model/View classes for displaying veto logs in table format.

Provides VetoLogTableModel for displaying veto events with color-coded
severity levels, and VetoLogFilterProxyModel for multi-column filtering.
Supports loading veto data from KernelVetoLogger with filtering by
rule type, severity, driver, and text search.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor


class VetoLogTableModel(QAbstractTableModel):
    """Table model for displaying veto log events.

    Displays veto events with columns for Time, Rule, Driver, Severity,
    Reason, and Lineup context. Supports color-coding by severity level
    and right-aligns numeric columns.

    Attributes:
        _data: List of veto event dictionaries
        _columns: Column definitions (key, header, tooltip)
        _severity_colors: Color mapping for severity levels

    Example:
        model = VetoLogTableModel()
        model.load_for_job(veto_logger, "job-123")
        table_view.setModel(model)
    """

    # Column definitions: (data_key, header, tooltip)
    COLUMNS = [
        ("timestamp", "Time", "When the lineup was rejected"),
        ("rule_name", "Rule", "The constraint or rule that was violated"),
        ("driver_name", "Driver", "Driver involved in violation (if applicable)"),
        (
            "severity",
            "Severity",
            "Impact level (Info=logged, Warning=edge case, Error=rejected, Fatal=critical)",
        ),
        ("reason", "Reason", "Detailed explanation of violation"),
        ("lineup_context", "Lineup", "Driver IDs in the rejected lineup"),
    ]

    # Severity color coding (background colors)
    SEVERITY_COLORS = {
        "Info": QColor(200, 255, 200),  # Light green
        "Warning": QColor(255, 255, 180),  # Light yellow
        "Error": QColor(255, 220, 180),  # Light orange
        "Fatal": QColor(255, 200, 200),  # Light red
    }

    def __init__(self, parent=None):
        """Initialize VetoLogTableModel.

        Args:
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows in model."""
        if parent.isValid():
            return 0
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns in model."""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        """Return data for given index and role."""
        if not index.isValid() or index.row() >= len(self._data):
            return None

        row_data = self._data[index.row()]
        column_key = self.COLUMNS[index.column()][0]

        if role == Qt.DisplayRole:
            value = row_data.get(column_key)

            # Format lineup context as readable string
            if column_key == "lineup_context" and value:
                if isinstance(value, list):
                    return ", ".join(str(x) for x in value)
                return str(value)

            # Format timestamps nicely
            if column_key == "timestamp" and value:
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return dt.strftime("%H:%M:%S")
                except Exception:
                    return str(value)[:19]

            return str(value) if value is not None else ""

        elif role == Qt.ToolTipRole:
            # Show full details in tooltip
            value = row_data.get(column_key)
            if column_key == "lineup_context" and value:
                if isinstance(value, list):
                    return f"Lineup drivers: {', '.join(str(x) for x in value)}"
            if column_key == "timestamp" and value:
                return f"Full timestamp: {value}"
            if column_key == "reason" and value:
                return str(value)
            return self.COLUMNS[index.column()][2]

        elif role == Qt.BackgroundRole:
            # Color-code by severity
            severity = row_data.get("severity")
            if severity in self.SEVERITY_COLORS:
                return self.SEVERITY_COLORS[severity]
            return None

        elif role == Qt.TextAlignmentRole:
            # Right-align numeric columns
            if column_key in ("constraint_value", "actual_value"):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.UserRole:
            # Return full row data for custom use
            return row_data

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ):
        """Return header data for given section."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section][1]

        elif orientation == Qt.Horizontal and role == Qt.ToolTipRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section][2]

        return super().headerData(section, orientation, role)

    def load_data(self, data: List[Dict[str, Any]]) -> None:
        """Load veto event data into model.

        Args:
            data: List of veto event dictionaries
        """
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def load_for_job(self, veto_logger, job_id: str) -> None:
        """Load veto events for a specific job.

        Args:
            veto_logger: KernelVetoLogger instance
            job_id: Job UUID to load
        """
        data = veto_logger.get_vetos_for_job(job_id)
        self.load_data(data)

    def load_for_race(self, veto_logger, race_id: str) -> None:
        """Load veto events for a specific race.

        Args:
            veto_logger: KernelVetoLogger instance
            race_id: Race identifier to load
        """
        data = veto_logger.get_vetos_for_race(race_id)
        self.load_data(data)

    def refresh(self, veto_logger) -> None:
        """Reload current data from database.

        Re-queries using the job_id from existing data if available.

        Args:
            veto_logger: KernelVetoLogger instance
        """
        if self._data:
            job_id = self._data[0].get("job_id")
            if job_id:
                self.load_for_job(veto_logger, job_id)

    def clear(self) -> None:
        """Clear all data from model."""
        self.load_data([])

    def get_row_data(self, row: int) -> Optional[Dict[str, Any]]:
        """Get full data dictionary for a row.

        Args:
            row: Row index

        Returns:
            Veto event dictionary or None if invalid row
        """
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def get_all_data(self) -> List[Dict[str, Any]]:
        """Return all data in model."""
        return self._data.copy()


class VetoLogFilterProxyModel(QSortFilterProxyModel):
    """Filter proxy model for multi-column veto log filtering.

    Extends QSortFilterProxyModel to support filtering by multiple
    criteria simultaneously: rule name, severity, driver, and text
    search across reason column.

    Attributes:
        _rule_filter: Current rule name filter (empty = all)
        _severity_filter: Current severity filter (empty = all)
        _driver_filter: Current driver filter (empty = all)
        _text_filter: Current text search filter

    Example:
        proxy_model = VetoLogFilterProxyModel()
        proxy_model.setSourceModel(source_model)
        proxy_model.set_rule_filter("salary_cap")
        proxy_model.set_severity_filter("Error")
    """

    def __init__(self, parent=None):
        """Initialize VetoLogFilterProxyModel.

        Args:
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self._rule_filter: str = ""
        self._severity_filter: str = ""
        self._driver_filter: str = ""
        self._text_filter: str = ""

        # Enable dynamic sorting/filtering
        self.setDynamicSortFilter(True)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def set_rule_filter(self, rule_name: str) -> None:
        """Set filter for rule name column.

        Args:
            rule_name: Rule name to filter by (empty = all)
        """
        self._rule_filter = rule_name.lower()
        self.invalidateFilter()

    def set_severity_filter(self, severity: str) -> None:
        """Set filter for severity column.

        Args:
            severity: Severity level to filter by (empty = all)
        """
        self._severity_filter = severity.lower()
        self.invalidateFilter()

    def set_driver_filter(self, driver: str) -> None:
        """Set filter for driver name column.

        Args:
            driver: Driver name to filter by (empty = all)
        """
        self._driver_filter = driver.lower()
        self.invalidateFilter()

    def set_text_filter(self, text: str) -> None:
        """Set text search filter (searches reason and rule).

        Args:
            text: Text to search for (empty = no filter)
        """
        self._text_filter = text.lower()
        self.invalidateFilter()

    def clear_filters(self) -> None:
        """Clear all filters."""
        self._rule_filter = ""
        self._severity_filter = ""
        self._driver_filter = ""
        self._text_filter = ""
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Determine if row should be included based on active filters.

        Args:
            source_row: Row index in source model
            source_parent: Parent index

        Returns:
            True if row matches all active filters
        """
        source_model = self.sourceModel()
        if not source_model:
            return False

        # Get row data
        row_data = source_model.get_row_data(source_row)
        if not row_data:
            return False

        # Check rule filter
        if self._rule_filter:
            rule_name = row_data.get("rule_name", "").lower()
            if self._rule_filter not in rule_name:
                return False

        # Check severity filter
        if self._severity_filter:
            severity = row_data.get("severity", "").lower()
            if self._severity_filter not in severity:
                return False

        # Check driver filter
        if self._driver_filter:
            driver = row_data.get("driver_name", "").lower()
            if self._driver_filter not in driver:
                return False

        # Check text filter (searches reason and rule)
        if self._text_filter:
            reason = row_data.get("reason", "").lower()
            rule = row_data.get("rule_name", "").lower()
            if self._text_filter not in reason and self._text_filter not in rule:
                return False

        return True

    def get_filtered_data(self) -> List[Dict[str, Any]]:
        """Get all data that passes current filters.

        Returns:
            List of veto event dictionaries matching filters
        """
        source_model = self.sourceModel()
        if not source_model:
            return []

        filtered = []
        for row in range(self.rowCount()):
            source_row = self.mapToSource(self.index(row, 0)).row()
            data = source_model.get_row_data(source_row)
            if data:
                filtered.append(data)

        return filtered


class VetoLogStatsModel:
    """Simple model for veto log statistics.

    Provides aggregated statistics about veto events for display
    in status bars or summary panels. Not a Qt model - just a
    data container with computed properties.

    Attributes:
        total_count: Total number of veto events
        by_severity: Dict mapping severity -> count
        by_rule: Dict mapping rule_name -> count
        top_rule: Rule with most vetos
        severity_percentages: Dict mapping severity -> percentage

    Example:
        stats = VetoLogStatsModel(veto_logger, "job-123")
        print(f"Total vetos: {stats.total_count}")
        print(f"Most common rule: {stats.top_rule}")
    """

    def __init__(self, veto_logger, job_id: str):
        """Initialize stats model with data from veto logger.

        Args:
            veto_logger: KernelVetoLogger instance
            job_id: Job UUID to compute stats for
        """
        summary = veto_logger.get_veto_summary(job_id)

        self.total_count: int = summary.get("total_vetos", 0)
        self.by_severity: Dict[str, int] = summary.get("by_severity", {})
        self.by_rule: Dict[str, int] = summary.get("by_rule", {})

        # Compute derived stats
        self.top_rule: Optional[str] = None
        self.top_rule_count: int = 0
        if self.by_rule:
            self.top_rule = max(self.by_rule.items(), key=lambda x: x[1])[0]
            self.top_rule_count = self.by_rule[self.top_rule]

        self.severity_percentages: Dict[str, float] = {}
        if self.total_count > 0:
            self.severity_percentages = {
                sev: (count / self.total_count * 100)
                for sev, count in self.by_severity.items()
            }

    def get_severity_count(self, severity: str) -> int:
        """Get count for a specific severity level."""
        return self.by_severity.get(severity, 0)

    def get_rule_count(self, rule_name: str) -> int:
        """Get count for a specific rule."""
        return self.by_rule.get(rule_name, 0)

    def format_summary(self) -> str:
        """Format stats as human-readable summary string."""
        if self.total_count == 0:
            return "No vetos recorded"

        parts = [f"Total: {self.total_count}"]

        # Add severity breakdown
        severity_parts = []
        for sev in ["Fatal", "Error", "Warning", "Info"]:
            count = self.by_severity.get(sev, 0)
            if count > 0:
                severity_parts.append(f"{sev}: {count}")
        if severity_parts:
            parts.append(f"({', '.join(severity_parts)})")

        return " | ".join(parts)
