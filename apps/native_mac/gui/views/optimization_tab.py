"""Optimization tab for configuring and running lineup optimization."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QPushButton,
    QComboBox,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QTableView,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from typing import List, Dict, Any, Optional

from ..widgets.constraint_panel import ConstraintPanel
from ..widgets.progress_dialog import ProgressDialog
from ...persistence.database import DatabaseManager
from ...optimization.engine import OptimizationEngine
from ..models.lineup_model import LineupTableModel


class OptimizationTab(QWidget):
    """Tab for configuring optimization parameters and running lineup generation.

    Provides:
    - Race selector to choose which race to optimize for
    - ConstraintPanel for setting salary/ownership/stacking constraints
    - Lineup count selector (10-150)
    - Iterations selector (100-5000)
    - Run Optimization button
    - Progress dialog during optimization
    - Results display in table view

    Signals:
        lineups_generated: Emitted when optimization completes with new lineups
    """

    # Signal emitted when lineups are generated: (list_of_lineups)
    lineups_generated = Signal(list)

    # Signal emitted when optimization completes (for dock bounce)
    optimization_complete = Signal()

    # Signal emitted to request notification (num_lineups)
    notify_complete = Signal(int)

    def __init__(
        self,
        database_manager: DatabaseManager,
        optimization_engine: OptimizationEngine,
        job_manager: Optional[Any] = None,
        preset_manager: Optional[Any] = None,
        undo_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the optimization tab.

        Args:
            database_manager: DatabaseManager for data persistence.
            optimization_engine: OptimizationEngine for running optimization.
            job_manager: Optional JobManager for submitting jobs to queue.
            preset_manager: Optional PresetManager for constraint presets.
            undo_manager: Optional UndoManager for undo/redo operations.
            parent: Parent widget.
        """
        super().__init__(parent)

        self.database_manager = database_manager
        self.optimization_engine = optimization_engine
        self.job_manager = job_manager
        self.preset_manager = preset_manager
        self.undo_manager = undo_manager
        self.current_race_id: Optional[int] = None
        self.current_drivers: List[Dict[str, Any]] = []
        self.current_worker: Optional[Any] = None
        self.progress_dialog: Optional[ProgressDialog] = None

        self._setup_ui()
        self._load_races()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Left panel: Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Race selector
        race_group = QGroupBox("Race Selection")
        race_layout = QFormLayout(race_group)

        self.race_combo = QComboBox()
        self.race_combo.setPlaceholderText("Select a race...")
        self.race_combo.currentIndexChanged.connect(self._on_race_changed)
        race_layout.addRow("Race:", self.race_combo)

        left_layout.addWidget(race_group)

        # Constraint panel
        self.constraint_panel = ConstraintPanel(preset_manager=self.preset_manager)
        left_layout.addWidget(self.constraint_panel)

        # Optimization settings
        settings_group = QGroupBox("Optimization Settings")
        settings_layout = QFormLayout(settings_group)

        # Lineup count selector (10-150, default 20)
        self.lineup_count_spin = QSpinBox()
        self.lineup_count_spin.setRange(10, 150)
        self.lineup_count_spin.setValue(20)
        self.lineup_count_spin.setSingleStep(10)
        settings_layout.addRow("Number of Lineups:", self.lineup_count_spin)

        # Iterations selector (100-5000, default 1000)
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(100, 5000)
        self.iterations_spin.setValue(1000)
        self.iterations_spin.setSingleStep(100)
        settings_layout.addRow("MCMC Iterations:", self.iterations_spin)

        # GPU offload checkbox
        self.gpu_checkbox = QCheckBox("Use GPU offload")
        self.gpu_checkbox.setToolTip(
            "Route job to Windows GPU worker (5-10s vs 30-60s)"
        )
        self.gpu_checkbox.stateChanged.connect(self._on_gpu_toggled)
        settings_layout.addRow(self.gpu_checkbox)

        # GPU mode status label
        self.gpu_status_label = QLabel("Local mode: Running on Mac CPU")
        self.gpu_status_label.setStyleSheet("font-size: 11px; color: #666;")
        settings_layout.addRow(self.gpu_status_label)

        left_layout.addWidget(settings_group)

        # Run button
        self.run_button = QPushButton("Run Optimization")
        self.run_button.setMinimumHeight(40)
        self.run_button.setStyleSheet(
            "QPushButton {"
            "  font-size: 14px;"
            "  font-weight: bold;"
            "  background-color: #4CAF50;"
            "  color: white;"
            "  border: none;"
            "  border-radius: 5px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #45a049;"
            "}"
            "QPushButton:disabled {"
            "  background-color: #cccccc;"
            "  color: #666666;"
            "}"
        )
        self.run_button.clicked.connect(self._on_run_optimization)
        left_layout.addWidget(self.run_button)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.status_label)

        left_layout.addStretch()
        layout.addWidget(left_panel, stretch=1)

        # Right panel: Results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        results_label = QLabel("Generated Lineups")
        results_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(results_label)

        # Results table
        self.lineup_model = LineupTableModel()
        self.results_table = QTableView()
        self.results_table.setModel(self.lineup_model)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableView.SelectRows)
        self.results_table.setSelectionMode(QTableView.SingleSelection)
        right_layout.addWidget(self.results_table)

        layout.addWidget(right_panel, stretch=2)

    def _load_races(self) -> None:
        """Load available races from database."""
        try:
            races = self.database_manager.load_races()
            self.race_combo.clear()

            for race in races:
                race_id = race.get("id")
                track_name = race.get("track_name", "Unknown")
                race_date = race.get("race_date", "")
                display_text = f"{track_name} ({race_date})"

                # Store race_id as user data
                self.race_combo.addItem(display_text, race_id)

            if races:
                self.race_combo.setCurrentIndex(0)
                self._on_race_changed(0)

        except Exception as e:
            self.status_label.setText(f"Error loading races: {e}")
            self.status_label.setStyleSheet("color: red;")

    def _on_race_changed(self, index: int) -> None:
        """Handle race selection change.

        Args:
            index: Index of selected race in combo box.
        """
        if index < 0:
            self.current_race_id = None
            self.current_drivers = []
            return

        # Get race ID from combo box user data
        self.current_race_id = self.race_combo.itemData(index)

        # Load drivers for this race from database
        # For now, we'll use the drivers from the Race Data tab
        # In a full implementation, this would load from a drivers table
        self.status_label.setText(f"Selected race: {self.race_combo.currentText()}")
        self.status_label.setStyleSheet("")

    def _on_gpu_toggled(self, state: int) -> None:
        """Handle GPU offload checkbox toggle.

        Args:
            state: Checkbox state (Qt.Checked or Qt.Unchecked)
        """
        if state == Qt.Checked.value:
            self.gpu_status_label.setText("GPU mode: Will route to Windows worker")
            self.gpu_status_label.setStyleSheet("font-size: 11px; color: #2196F3;")
        else:
            self.gpu_status_label.setText("Local mode: Running on Mac CPU")
            self.gpu_status_label.setStyleSheet("font-size: 11px; color: #666;")

    def set_drivers(self, drivers: List[Dict[str, Any]]) -> None:
        """Set the current drivers for optimization.

        This should be called from the main window when drivers are loaded.

        Args:
            drivers: List of driver dictionaries.
        """
        self.current_drivers = drivers
        self.status_label.setText(f"Loaded {len(drivers)} drivers")
        self.status_label.setStyleSheet("")

    def _on_run_optimization(self) -> None:
        """Handle Run Optimization button click."""
        # Validate: must have drivers loaded
        if not self.current_drivers:
            QMessageBox.warning(
                self,
                "No Driver Data",
                "Please import driver data first from the Race Data tab.",
            )
            return

        # Validate: must have valid constraints
        if not self.constraint_panel.is_valid():
            QMessageBox.warning(
                self,
                "Invalid Constraints",
                "Please fix the constraint validation errors before running.",
            )
            return

        # Check if job_manager is available
        if self.job_manager is None:
            # Fallback to legacy direct optimization
            self._run_optimization_legacy()
            return

        # Get race info
        race_id = self.current_race_id or 1
        race_name = (
            self.race_combo.currentText()
            if self.race_combo.currentIndex() >= 0
            else f"Race {race_id}"
        )
        track_name = race_name.split(" (")[0] if " (" in race_name else race_name

        # Build job config
        constraints = self.constraint_panel.get_constraints()
        num_lineups = self.lineup_count_spin.value()
        num_iterations = self.iterations_spin.value()
        gpu_offload = self.gpu_checkbox.isChecked()

        config = {
            "race_id": race_id,
            "race_name": race_name,
            "drivers": self.current_drivers,
            "num_lineups": num_lineups,
            "iterations": num_iterations,
            "gpu_offload": gpu_offload,
            "constraints": constraints,
        }

        # Generate job name
        job_name = f"{track_name} Optimization"

        try:
            # Submit job to queue
            job_id = self.job_manager.submit_job(config, job_name=job_name)

            # Show confirmation
            execution_mode = "GPU" if gpu_offload else "local CPU"
            QMessageBox.information(
                self,
                "Job Submitted",
                f"Job '{job_name}' submitted (ID: {job_id[:8]}...)\n"
                f"Execution mode: {execution_mode}\n\n"
                f"Check the Jobs tab for status updates.",
            )

            self.status_label.setText(f"Job submitted: {job_name}")

        except Exception as e:
            QMessageBox.critical(
                self, "Job Submission Failed", f"Failed to submit job:\n\n{str(e)}"
            )
            self.status_label.setText("Job submission failed")
            self.status_label.setStyleSheet("color: red;")

    def _run_optimization_legacy(self) -> None:
        """Run optimization using legacy direct engine (fallback)."""
        # Check if optimization already running
        if self.optimization_engine.is_running():
            QMessageBox.information(
                self,
                "Optimization Running",
                "An optimization is already in progress. Please wait for it to complete.",
            )
            return

        # Get constraints from panel
        constraints = self.constraint_panel.get_constraints()
        num_lineups = self.lineup_count_spin.value()
        num_iterations = self.iterations_spin.value()

        # Show progress dialog
        self.progress_dialog = ProgressDialog(
            max_iterations=num_iterations, parent=self
        )
        self.progress_dialog.cancelled.connect(self._on_cancel_optimization)
        self.progress_dialog.show()

        # Disable run button
        self.run_button.setEnabled(False)
        self.status_label.setText("Running optimization...")

        # Get race ID (use 1 as default if none selected)
        race_id = self.current_race_id or 1

        try:
            # Start optimization
            self.current_worker = self.optimization_engine.start_optimization(
                race_id=race_id,
                drivers=self.current_drivers,
                constraints=constraints,
                num_lineups=num_lineups,
                iterations=num_iterations,
                progress_callback=self._on_progress_update,
                finished_callback=self._on_optimization_finished,
                error_callback=self._on_optimization_error,
                cancelled_callback=self._on_optimization_cancelled,
            )
        except Exception as e:
            self._on_optimization_error(str(e))

    def _on_progress_update(self, current: int, total: int, best_score: float) -> None:
        """Handle progress updates from optimization worker.

        Args:
            current: Current iteration.
            total: Total iterations.
            best_score: Current best score.
        """
        if self.progress_dialog:
            self.progress_dialog.update_progress(current, total, best_score)

    def _on_optimization_finished(self, lineups: List[Dict[str, Any]]) -> None:
        """Handle optimization completion.

        Args:
            lineups: List of generated lineup dictionaries.
        """
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.set_complete(len(lineups))

        # Update results table
        self.lineup_model.update_data(lineups)

        # Re-enable run button
        self.run_button.setEnabled(True)
        self.status_label.setText(f"Generated {len(lineups)} lineups")

        # Emit signals
        self.lineups_generated.emit(lineups)
        self.optimization_complete.emit()
        self.notify_complete.emit(len(lineups))

        # Show success message
        QMessageBox.information(
            self,
            "Optimization Complete",
            f"Successfully generated {len(lineups)} lineups!",
        )

    def _on_optimization_error(self, error_message: str) -> None:
        """Handle optimization error.

        Args:
            error_message: Error message from the optimizer.
        """
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.set_error(error_message)

        # Re-enable run button
        self.run_button.setEnabled(True)
        self.status_label.setText("Optimization failed")
        self.status_label.setStyleSheet("color: red;")

        # Show error message
        QMessageBox.critical(
            self,
            "Optimization Error",
            f"An error occurred during optimization:\n\n{error_message}",
        )

    def _on_optimization_cancelled(self) -> None:
        """Handle optimization cancellation."""
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()

        # Re-enable run button
        self.run_button.setEnabled(True)
        self.status_label.setText("Optimization cancelled")

        QMessageBox.information(
            self, "Cancelled", "Optimization was cancelled by user."
        )

    def _on_cancel_optimization(self) -> None:
        """Handle cancel button click in progress dialog."""
        self.optimization_engine.cancel_optimization()

    def set_undo_manager(self, undo_manager: Optional[Any]) -> None:
        """Set the UndoManager for this tab.

        Called from MainWindow to wire up undo/redo functionality.

        Args:
            undo_manager: UndoManager instance for undo/redo operations.
        """
        self.undo_manager = undo_manager

        # Wire UndoManager to constraint panel if available
        if hasattr(self, "constraint_panel") and self.constraint_panel:
            self.constraint_panel.set_undo_manager(undo_manager)

    def set_focus_to_constraints(self) -> None:
        """Set focus to the constraint panel (for keyboard shortcuts)."""
        if hasattr(self, "constraint_panel") and self.constraint_panel:
            self.constraint_panel.setFocus()
