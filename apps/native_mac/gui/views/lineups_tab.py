"""Lineups tab widget for displaying and exporting generated lineups."""

from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QPushButton,
    QComboBox,
    QLabel,
    QMessageBox,
    QFileDialog,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal

from ..models.lineup_model import LineupTableModel
from ..controllers.data_controller import DataController
from ...persistence.database import DatabaseManager


class LineupsTab(QWidget):
    """Tab for displaying generated lineups with export functionality.

    Provides a table view of lineups with toolbar buttons for:
    - Exporting to DraftKings CSV format
    - Saving lineups to database
    - Loading saved lineups from database
    """

    # Signal emitted when lineups are saved to database
    lineups_saved = Signal(int)  # race_id

    def __init__(
        self,
        database_manager: DatabaseManager,
        data_controller: DataController,
        lineup_model: LineupTableModel,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the lineups tab.

        Args:
            database_manager: DatabaseManager for persistence operations.
            data_controller: DataController for export operations.
            lineup_model: LineupTableModel for displaying lineups.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.database_manager = database_manager
        self.data_controller = data_controller
        self.lineup_model = lineup_model
        self.current_race_id: Optional[int] = None

        self._create_ui()
        self._connect_signals()
        self._load_saved_races()

    def _create_ui(self) -> None:
        """Create the user interface components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top toolbar with buttons
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)

        # Export to DraftKings button (primary action)
        self.export_draftkings_btn = QPushButton("Export to DraftKings")
        self.export_draftkings_btn.setToolTip(
            "Export lineups in DraftKings upload format"
        )
        toolbar_layout.addWidget(self.export_draftkings_btn)

        # Separator
        toolbar_layout.addSpacing(20)

        # Save lineups button
        self.save_lineups_btn = QPushButton("Save Lineups")
        self.save_lineups_btn.setToolTip("Save current lineups to database")
        toolbar_layout.addWidget(self.save_lineups_btn)

        # Load saved lineups dropdown
        toolbar_layout.addWidget(QLabel("Load Saved:"))
        self.load_saved_combo = QComboBox()
        self.load_saved_combo.setMinimumWidth(200)
        self.load_saved_combo.setPlaceholderText("Select saved lineups...")
        toolbar_layout.addWidget(self.load_saved_combo)

        # Stretch to push everything to the left
        toolbar_layout.addStretch()

        layout.addLayout(toolbar_layout)

        # Main table view
        self.table_view = QTableView()
        self.table_view.setModel(self.lineup_model)
        self._configure_table()
        layout.addWidget(self.table_view)

        # Bottom status bar
        status_layout = QHBoxLayout()
        self.lineup_count_label = QLabel("No lineups")
        self.total_salary_label = QLabel("")
        status_layout.addWidget(self.lineup_count_label)
        status_layout.addStretch()
        status_layout.addWidget(self.total_salary_label)
        layout.addLayout(status_layout)

    def _configure_table(self) -> None:
        """Configure the table view appearance and behavior."""
        # Enable alternating row colors for readability
        self.table_view.setAlternatingRowColors(True)

        # Select entire rows
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)

        # Hide vertical header (row numbers)
        self.table_view.verticalHeader().setVisible(False)

        # Enable sorting
        self.table_view.setSortingEnabled(True)

        # Configure column sizing
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setMinimumSectionSize(80)

        # Set column widths
        self.table_view.setColumnWidth(0, 80)  # Lineup #
        self.table_view.setColumnWidth(1, 150)  # Driver 1
        self.table_view.setColumnWidth(2, 150)  # Driver 2
        self.table_view.setColumnWidth(3, 150)  # Driver 3
        self.table_view.setColumnWidth(4, 150)  # Driver 4
        self.table_view.setColumnWidth(5, 150)  # Driver 5
        self.table_view.setColumnWidth(6, 150)  # Driver 6
        self.table_view.setColumnWidth(7, 100)  # Total Salary
        self.table_view.setColumnWidth(8, 80)  # ProjPts

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        self.export_draftkings_btn.clicked.connect(self.on_export_draftkings)
        self.save_lineups_btn.clicked.connect(self.on_save_lineups)
        self.load_saved_combo.currentIndexChanged.connect(self.on_load_saved)

        # Update status when model changes
        self.lineup_model.modelReset.connect(self._update_status)
        self.lineup_model.dataChanged.connect(self._update_status)

    def _load_saved_races(self) -> None:
        """Load list of races with saved lineups into dropdown."""
        self.load_saved_combo.clear()
        self.load_saved_combo.addItem("Select saved lineups...", None)

        # Get all races from database
        races = self.database_manager.get_all_races()
        for race in races:
            race_id = race.get("id")
            race_name = race.get("name", f"Race {race_id}")
            # Check if this race has lineups
            lineups = self.database_manager.load_lineups(race_id)
            if lineups:
                self.load_saved_combo.addItem(race_name, race_id)

    def _update_status(self) -> None:
        """Update the status labels based on current lineups."""
        row_count = self.lineup_model.rowCount()

        if row_count == 0:
            self.lineup_count_label.setText("No lineups")
            self.total_salary_label.setText("")
        else:
            self.lineup_count_label.setText(f"{row_count} lineups")

            # Calculate average salary
            lineups = self.lineup_model.get_all_lineups()
            total_salary = sum(l.get("total_salary", 0) for l in lineups)
            avg_salary = total_salary / len(lineups) if lineups else 0
            self.total_salary_label.setText(f"Avg Salary: ${avg_salary:,.0f}")

    def on_export_draftkings(self) -> None:
        """Handle Export to DraftKings button click.

        Opens a save dialog and exports lineups in DraftKings CSV format.
        """
        if not self.lineup_model.rowCount():
            QMessageBox.warning(
                self, "No Lineups", "Generate lineups first before exporting."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Lineups for DraftKings",
            "lineups.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        # Ensure .csv extension
        if not file_path.endswith(".csv"):
            file_path += ".csv"

        lineups = self.lineup_model.get_all_lineups()

        success, error = self.data_controller.export_lineups_to_csv(
            lineups, file_path, format="draftkings"
        )

        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {len(lineups)} lineups to:\n{file_path}",
            )
        else:
            QMessageBox.critical(
                self, "Export Error", f"Failed to export lineups:\n\n{error}"
            )

    def on_save_lineups(self) -> None:
        """Handle Save Lineups button click.

        Saves current lineups to the database associated with current race.
        """
        if not self.lineup_model.rowCount():
            QMessageBox.warning(
                self, "No Lineups", "Generate lineups first before saving."
            )
            return

        if not self.current_race_id:
            QMessageBox.warning(
                self,
                "No Race Selected",
                "Please select a race in the Optimization tab first.",
            )
            return

        lineups = self.lineup_model.get_all_lineups()

        # Prepare lineup data for storage
        lineup_data = {
            "type": "generated_lineups",
            "lineups": lineups,
            "count": len(lineups),
        }

        try:
            saved_id = self.database_manager.save_lineup(
                self.current_race_id, lineup_data
            )
            self.lineups_saved.emit(self.current_race_id)
            self._load_saved_races()  # Refresh dropdown
            QMessageBox.information(
                self,
                "Lineups Saved",
                f"Successfully saved {len(lineups)} lineups to database (ID: {saved_id}).",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save lineups:\n\n{str(e)}"
            )

    def on_load_saved(self, index: int) -> None:
        """Handle Load Saved dropdown selection.

        Args:
            index: Selected index in the dropdown.
        """
        if index <= 0:  # First item is placeholder
            return

        race_id = self.load_saved_combo.currentData()
        if not race_id:
            return

        # Load lineups for this race
        lineups = self.database_manager.load_lineups(race_id)

        # Find the most recent generated_lineups entry
        for lineup in reversed(lineups):  # Most recent first
            lineup_data = lineup.get("lineup_data", {})
            if lineup_data.get("type") == "generated_lineups":
                loaded_lineups = lineup_data.get("lineups", [])
                self.lineup_model.update_data(loaded_lineups)
                self.current_race_id = race_id
                return

        QMessageBox.warning(
            self,
            "No Lineups Found",
            "No generated lineups found for the selected race.",
        )

    def set_lineups(
        self, lineups: List[Dict[str, Any]], race_id: Optional[int] = None
    ) -> None:
        """Set the lineups to display.

        Args:
            lineups: List of lineup dictionaries.
            race_id: Optional race ID to associate with these lineups.
        """
        self.lineup_model.update_data(lineups)
        self.current_race_id = race_id
        self._update_status()

    def set_race_id(self, race_id: Optional[int]) -> None:
        """Set the current race ID for saving lineups.

        Args:
            race_id: Race ID to associate with saved lineups.
        """
        self.current_race_id = race_id

    def set_undo_manager(self, undo_manager: Optional[Any]) -> None:
        """Set the UndoManager for this tab.

        Called from MainWindow to wire up undo/redo functionality.
        Enables undo/redo for lineup edits.

        Args:
            undo_manager: UndoManager instance for undo/redo operations.
        """
        self.undo_manager = undo_manager
