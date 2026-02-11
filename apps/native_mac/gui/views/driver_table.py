"""Driver table view widget with import integration."""

from typing import Optional, List

from PySide6.QtWidgets import QTableView, QMessageBox, QAbstractItemView
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from ..controllers.data_controller import DataController
from ..models.driver_model import DriverTableModel


class DriverTableView(QTableView):
    """Table view widget for displaying and importing driver data.

    Integrates with DataController for CSV import operations and provides
    visual feedback through signals and user-friendly error dialogs.
    Supports drag-and-drop of CSV files.
    """

    # Signal emitted when data is successfully loaded, passing the count
    data_loaded = Signal(int)

    def __init__(
        self, data_controller: DataController, model: DriverTableModel, parent=None
    ):
        """Initialize the driver table view.

        Args:
            data_controller: DataController instance for import operations.
            model: DriverTableModel instance for data display.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.data_controller = data_controller
        self.model = model

        # Set the model
        self.setModel(self.model)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Configure table appearance
        self._configure_table()

    def _configure_table(self) -> None:
        """Configure table display settings."""
        # Enable alternating row colors for readability
        self.setAlternatingRowColors(True)

        # Select entire rows
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

        # Hide vertical header (row numbers)
        self.verticalHeader().setVisible(False)

        # Enable sorting
        self.setSortingEnabled(True)

        # Configure column sizing
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setMinimumSectionSize(80)

        # Set column widths (name wider, numeric columns narrower)
        self.setColumnWidth(0, 200)  # Driver name
        self.setColumnWidth(1, 100)  # Salary
        self.setColumnWidth(2, 100)  # ProjPts
        self.setColumnWidth(3, 100)  # Own%
        self.setColumnWidth(4, 200)  # Team

    def load_drivers_from_csv(self, file_path: str) -> bool:
        """Load driver data from a CSV file.

        Uses DataController to import the CSV and updates the model
        on success. Shows error dialog on failure.

        Args:
            file_path: Path to the CSV file to import.

        Returns:
            bool: True if import succeeded, False otherwise.
        """
        success, error, drivers = self.data_controller.import_driver_csv(file_path)

        if not success:
            QMessageBox.critical(
                self, "Import Error", f"Failed to import CSV file:\n\n{error}"
            )
        return False

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event for drag-and-drop.

        Accepts drag events that contain file URLs with .csv extension.

        Args:
            event: The drag enter event.
        """
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            # Check if any URL is a CSV file
            for url in urls:
                if url.isLocalFile() and url.toLocalFile().endswith(".csv"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event for drag-and-drop.

        Imports the dropped CSV file(s).

        Args:
            event: The drop event.
        """
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            csv_files = [
                url.toLocalFile()
                for url in urls
                if url.isLocalFile() and url.toLocalFile().endswith(".csv")
            ]

            if csv_files:
                # Import the first CSV file
                # (Could be extended to import multiple)
                self.load_drivers_from_csv(csv_files[0])
                event.acceptProposedAction()
                return

        event.ignore()

        # Update the model with imported data
        self.model.update_data(drivers)

        # Emit signal with count
        self.data_loaded.emit(len(drivers))

        return True

    def load_drivers_from_db(self, race_id: int) -> bool:
        """Load driver data from the database for a specific race.

        Args:
            race_id: ID of the race to load drivers for.

        Returns:
            bool: True if load succeeded, False otherwise.
        """
        # Load lineups for the race
        lineups = self.data_controller.db_manager.load_lineups(race_id)

        # Find the most recent imported_drivers entry
        for lineup in lineups:
            lineup_data = lineup.get("lineup_data", {})
            if lineup_data.get("type") == "imported_drivers":
                drivers = lineup_data.get("drivers", [])
                self.model.update_data(drivers)
                self.data_loaded.emit(len(drivers))
                return True

        return False
