"""Qt Model/View models for NASCAR DFS GUI."""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Dict, Any, Optional


class DriverTableModel(QAbstractTableModel):
    """Table model for displaying driver data in QTableView.

    Columns: Driver, Salary, ProjPts, Own%, Team
    """

    COLUMNS = ["Driver", "Salary", "ProjPts", "Own%", "Team"]

    def __init__(self, drivers: Optional[List[Dict[str, Any]]] = None, parent=None):
        """Initialize the driver table model.

        Args:
            drivers: List of driver dictionaries with keys:
                - name: Driver name
                - salary: Driver salary (int)
                - projected_points: Projected fantasy points (float)
                - ownership: Projected ownership percentage (float)
                - team: Team name
        """
        super().__init__(parent)
        self._drivers = drivers or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows in the model."""
        if parent.isValid():
            return 0
        return len(self._drivers)

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

        if index.row() >= len(self._drivers) or index.row() < 0:
            return None

        driver = self._drivers[index.row()]
        column = index.column()

        # DisplayRole: formatted values
        if role == Qt.DisplayRole:
            return self._get_display_data(driver, column)

        # BackgroundRole: color-coding for value scores
        elif role == Qt.BackgroundRole:
            return self._get_background_color(driver, column)

        # TextAlignmentRole: right-align numeric columns
        elif role == Qt.TextAlignmentRole:
            return self._get_text_alignment(column)

        return None

    def _get_display_data(self, driver: Dict[str, Any], column: int) -> str:
        """Get formatted display data for a driver and column."""
        if column == 0:  # Driver
            return str(driver.get("name", ""))
        elif column == 1:  # Salary
            salary = driver.get("salary", 0)
            return f"${salary:,}"
        elif column == 2:  # ProjPts
            points = driver.get("projected_points", 0.0)
            return f"{points:.1f}"
        elif column == 3:  # Own%
            ownership = driver.get("ownership", 0.0)
            return f"{ownership:.1f}%"
        elif column == 4:  # Team
            return str(driver.get("team", ""))
        return ""

    def _get_background_color(
        self, driver: Dict[str, Any], column: int
    ) -> Optional[Any]:
        """Get background color for value-based highlighting.

        Color-codes high-value drivers:
        - Green: >3.0 pts/$1000
        - Red: <1.5 pts/$1000
        """
        # Only apply color-coding to the ProjPts column
        if column != 2:
            return None

        salary = driver.get("salary", 0)
        points = driver.get("projected_points", 0.0)

        if salary <= 0:
            return None

        # Calculate points per $1000
        value_score = (points / salary) * 1000

        from PySide6.QtGui import QColor

        if value_score > 3.0:
            # Light green for high value
            return QColor(200, 255, 200)
        elif value_score < 1.5:
            # Light red for low value
            return QColor(255, 200, 200)

        return None

    def _get_text_alignment(self, column: int) -> int:
        """Get text alignment for a column.

        Returns right-alignment for numeric columns (Salary, ProjPts, Own%).
        """
        if column in [1, 2, 3]:  # Salary, ProjPts, Own%
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

    def update_data(self, drivers: List[Dict[str, Any]]) -> None:
        """Update the model with new driver data.

        This method properly notifies the view of data changes using
        beginResetModel/endResetModel to trigger a full refresh.

        Args:
            drivers: New list of driver dictionaries
        """
        self.beginResetModel()
        self._drivers = drivers
        self.endResetModel()

    def get_driver(self, row: int) -> Optional[Dict[str, Any]]:
        """Get the driver data at the specified row.

        Args:
            row: Row index

        Returns:
            Driver dictionary or None if invalid row
        """
        if 0 <= row < len(self._drivers):
            return self._drivers[row]
        return None
