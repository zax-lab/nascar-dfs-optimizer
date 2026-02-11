"""Qt Model/View models for NASCAR DFS GUI - Lineup Table."""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Dict, Any, Optional


class LineupTableModel(QAbstractTableModel):
    """Table model for displaying optimized lineups in QTableView.

    Columns: Lineup #, Driver 1-6, Total Salary, ProjPts (9 columns)

    DraftKings NASCAR requires 6 drivers per lineup.
    """

    COLUMNS = [
        "Lineup #",
        "Driver 1",
        "Driver 2",
        "Driver 3",
        "Driver 4",
        "Driver 5",
        "Driver 6",
        "Total Salary",
        "ProjPts",
    ]
    NUM_DRIVER_COLUMNS = 6  # DraftKings NASCAR requires 6 drivers

    def __init__(self, lineups: Optional[List[Dict[str, Any]]] = None, parent=None):
        """Initialize the lineup table model.

        Args:
            lineups: List of lineup dictionaries with keys:
                - id: Lineup identifier
                - drivers: List of 6 driver dicts with 'name' key
                - total_salary: Total salary used (int)
                - projected_points: Total projected points (float)
        """
        super().__init__(parent)
        self._lineups = lineups or []
        self._top_threshold = 0.0  # Cache for top 20% threshold

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows in the model."""
        if parent.isValid():
            return 0
        return len(self._lineups)

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

        if index.row() >= len(self._lineups) or index.row() < 0:
            return None

        lineup = self._lineups[index.row()]
        column = index.column()

        # DisplayRole: formatted values
        if role == Qt.DisplayRole:
            return self._get_display_data(lineup, column)

        # BackgroundRole: color-code top projected lineups
        elif role == Qt.BackgroundRole:
            return self._get_background_color(lineup, column)

        # TextAlignmentRole: right-align numeric columns
        elif role == Qt.TextAlignmentRole:
            return self._get_text_alignment(column)

        return None

    def _get_display_data(self, lineup: Dict[str, Any], column: int) -> str:
        """Get formatted display data for a lineup and column."""
        if column == 0:  # Lineup #
            lineup_id = lineup.get("id", 0)
            return f"#{lineup_id}"
        elif 1 <= column <= 6:  # Driver 1-6
            drivers = lineup.get("drivers", [])
            driver_idx = column - 1
            if driver_idx < len(drivers):
                driver = drivers[driver_idx]
                if isinstance(driver, dict):
                    return str(driver.get("name", ""))
                else:
                    return str(driver)
            return ""
        elif column == 7:  # Total Salary
            salary = lineup.get("total_salary", 0)
            return f"${salary:,}"
        elif column == 8:  # ProjPts
            points = lineup.get("projected_points", 0.0)
            return f"{points:.1f}"
        return ""

    def _get_background_color(
        self, lineup: Dict[str, Any], column: int
    ) -> Optional[Any]:
        """Get background color for top projected lineups.

        Color-codes top 20% of lineups by projected points in light green.
        """
        from PySide6.QtGui import QColor

        # Only apply color to ProjPts column
        if column != 8:
            return None

        points = lineup.get("projected_points", 0.0)

        # Check if this lineup is in the top 20%
        if self._top_threshold > 0 and points >= self._top_threshold:
            # Light green for top lineups
            return QColor(200, 255, 200)

        return None

    def _get_text_alignment(self, column: int) -> int:
        """Get text alignment for a column.

        Returns right-alignment for numeric columns (Total Salary, ProjPts).
        """
        if column in [7, 8]:  # Total Salary, ProjPts
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

    def update_data(self, lineups: List[Dict[str, Any]]) -> None:
        """Update the model with new lineup data.

        This method properly notifies the view of data changes using
        beginResetModel/endResetModel to trigger a full refresh.
        Also recalculates the top 20% threshold for color-coding.

        Args:
            lineups: New list of lineup dictionaries
        """
        self.beginResetModel()
        self._lineups = lineups
        self._calculate_top_threshold()
        self.endResetModel()

    def _calculate_top_threshold(self) -> None:
        """Calculate the threshold for top 20% lineups by projected points."""
        if not self._lineups:
            self._top_threshold = 0.0
            return

        # Sort by projected points descending
        sorted_lineups = sorted(
            self._lineups, key=lambda x: x.get("projected_points", 0.0), reverse=True
        )

        # Find the threshold for top 20%
        top_count = max(1, int(len(sorted_lineups) * 0.2))
        if top_count <= len(sorted_lineups):
            self._top_threshold = sorted_lineups[top_count - 1].get(
                "projected_points", 0.0
            )
        else:
            self._top_threshold = 0.0

    def get_lineup(self, row: int) -> Optional[Dict[str, Any]]:
        """Get the full lineup data at the specified row.

        Args:
            row: Row index

        Returns:
            Lineup dictionary or None if invalid row
        """
        if 0 <= row < len(self._lineups):
            return self._lineups[row]
        return None

    def get_lineup_summary(self, row: int) -> Optional[str]:
        """Get a text summary of the lineup for export.

        Args:
            row: Row index

        Returns:
            Formatted string with lineup details or None if invalid row
        """
        lineup = self.get_lineup(row)
        if not lineup:
            return None

        drivers = lineup.get("drivers", [])
        driver_names = []
        for driver in drivers:
            if isinstance(driver, dict):
                driver_names.append(driver.get("name", "Unknown"))
            else:
                driver_names.append(str(driver))

        return (
            f"Lineup #{lineup.get('id', 0)}: "
            f"{', '.join(driver_names)} | "
            f"Salary: ${lineup.get('total_salary', 0):,} | "
            f"Proj: {lineup.get('projected_points', 0.0):.1f} pts"
        )

    def get_all_lineups(self) -> List[Dict[str, Any]]:
        """Get all lineups in the model.

        Returns:
            List of all lineup dictionaries.
        """
        return self._lineups.copy()
