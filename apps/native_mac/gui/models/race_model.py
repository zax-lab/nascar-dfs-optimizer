"""Qt Model/View models for NASCAR DFS GUI - Race History Table."""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Any, Optional
from datetime import datetime


class RaceTableModel(QAbstractTableModel):
    """Table model for displaying race history in QTableView.

    Columns: Track, Race Date, Lineups Generated, Created At (4 columns)

    This model displays historical races with lineup counts and is used
    in the \"Race Data\" tab to select historical races for analysis.
    """

    COLUMNS = ["Track", "Race Date", "Lineups Generated", "Created At"]

    def __init__(self, races: Optional[List[Any]] = None, parent=None):
        """Initialize the race history table model.

        Args:
            races: List of Race objects (from persistence.models) with attributes:
                - id: Race identifier
                - track: Track name
                - race_date: Race date (datetime or string)
                - lineups: Relationship/list of lineups (count used)
                - created_at: Creation timestamp (datetime)
        """
        super().__init__(parent)
        self._races = races or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows in the model."""
        if parent.isValid():
            return 0
        return len(self._races)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns in the model."""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for the given index and role.

        Args:
            index: Model index (row, column)
            role: Qt item data role

        Returns:
            Data appropriate for the role, or None if unsupported
        """
        if not index.isValid():
            return None

        if index.row() >= len(self._races) or index.row() < 0:
            return None

        race = self._races[index.row()]
        column = index.column()

        # DisplayRole: formatted values
        if role == Qt.DisplayRole:
            return self._get_display_data(race, column)

        # TextAlignmentRole: center-align track, right-align counts
        elif role == Qt.TextAlignmentRole:
            return self._get_text_alignment(column)

        return None

    def _get_display_data(self, race: Any, column: int) -> str:
        """Get formatted display data for a race and column."""
        if column == 0:  # Track
            # Handle both object attribute and dict access
            if hasattr(race, "track"):
                return str(race.track)
            elif isinstance(race, dict):
                return str(race.get("track", ""))
            return ""

        elif column == 1:  # Race Date
            race_date = None
            if hasattr(race, "race_date"):
                race_date = race.race_date
            elif isinstance(race, dict):
                race_date = race.get("race_date")

            return self._format_date(race_date)

        elif column == 2:  # Lineups Generated
            lineup_count = 0
            if hasattr(race, "lineups"):
                # Handle both list/relationship and count attribute
                lineups = race.lineups
                if hasattr(lineups, "__len__"):
                    lineup_count = len(lineups)
                elif hasattr(lineups, "count"):
                    lineup_count = lineups.count()
            elif isinstance(race, dict):
                lineups = race.get("lineups", [])
                lineup_count = len(lineups) if hasattr(lineups, "__len__") else 0

            return str(lineup_count)

        elif column == 3:  # Created At
            created_at = None
            if hasattr(race, "created_at"):
                created_at = race.created_at
            elif isinstance(race, dict):
                created_at = race.get("created_at")

            return self._format_datetime(created_at)

        return ""

    def _format_date(self, date_value: Any) -> str:
        """Format a date value as YYYY-MM-DD.

        Args:
            date_value: datetime, date, or string

        Returns:
            Formatted date string
        """
        if date_value is None:
            return ""

        if isinstance(date_value, datetime):
            return date_value.strftime("%Y-%m-%d")
        elif hasattr(date_value, "strftime"):  # date object
            return date_value.strftime("%Y-%m-%d")
        elif isinstance(date_value, str):
            # Try to parse and reformat
            try:
                dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                return date_value

        return str(date_value)

    def _format_datetime(self, dt_value: Any) -> str:
        """Format a datetime value as YYYY-MM-DD HH:MM.

        Args:
            dt_value: datetime or string

        Returns:
            Formatted datetime string
        """
        if dt_value is None:
            return ""

        if isinstance(dt_value, datetime):
            return dt_value.strftime("%Y-%m-%d %H:%M")
        elif hasattr(dt_value, "strftime"):  # datetime-like object
            return dt_value.strftime("%Y-%m-%d %H:%M")
        elif isinstance(dt_value, str):
            # Try to parse and reformat
            try:
                dt = datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, AttributeError):
                return dt_value

        return str(dt_value)

    def _get_text_alignment(self, column: int) -> int:
        """Get text alignment for a column.

        Returns center-alignment for Track, right-alignment for counts.
        """
        if column == 0:  # Track
            return Qt.AlignCenter | Qt.AlignVCenter
        elif column in [2]:  # Lineups Generated
            return Qt.AlignRight | Qt.AlignVCenter
        return Qt.AlignLeft | Qt.AlignVCenter

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        """Return header data for the given section and orientation."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return item flags for the given index."""
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def update_data(self, races: List[Any]) -> None:
        """Update the model with new race data.

        This method properly notifies the view of data changes using
        beginResetModel/endResetModel to trigger a full refresh.

        Args:
            races: New list of Race objects
        """
        self.beginResetModel()
        self._races = races
        self.endResetModel()

    def get_race_id(self, row: int) -> Optional[Any]:
        """Get the race ID at the specified row for loading.

        Args:
            row: Row index

        Returns:
            Race ID or None if invalid row
        """
        if 0 <= row < len(self._races):
            race = self._races[row]
            if hasattr(race, "id"):
                return race.id
            elif isinstance(race, dict):
                return race.get("id")
        return None

    def get_race(self, row: int) -> Optional[Any]:
        """Get the full race object at the specified row.

        Args:
            row: Row index

        Returns:
            Race object or None if invalid row
        """
        if 0 <= row < len(self._races):
            return self._races[row]
        return None
