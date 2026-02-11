"""Progress dialog for MCMC optimization."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from typing import Optional


class ProgressDialog(QDialog):
    """Modal dialog showing MCMC optimization progress.

    Displays:
    - Progress bar with iteration count
    - Current best score
    - Cancel button to stop optimization

    Emits cancelled signal when user requests cancellation.
    """

    # Signal emitted when user clicks cancel
    cancelled = Signal()

    def __init__(self, max_iterations: int = 1000, parent: Optional[QWidget] = None):
        """Initialize the progress dialog.

        Args:
            max_iterations: Maximum number of iterations for progress calculation.
            parent: Parent widget.
        """
        super().__init__(parent)

        self.max_iterations = max_iterations
        self._is_cancelling = False

        self._setup_ui()
        self._setup_dialog_properties()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title label
        title_label = QLabel("Generating Lineups")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Status label
        self.status_label = QLabel("Running MCMC optimization...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Iteration 0/{}".format(self.max_iterations))
        self.progress_bar.setMinimumHeight(25)
        layout.addWidget(self.progress_bar)

        # Score label
        self.score_label = QLabel("Current best score: --")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(self.score_label)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _setup_dialog_properties(self) -> None:
        """Configure dialog window properties."""
        self.setWindowTitle("Optimization Progress")
        self.setModal(True)
        self.setMinimumSize(400, 150)
        self.setMaximumSize(500, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self._is_cancelling:
            return

        self._is_cancelling = True
        self.status_label.setText("Cancelling...")
        self.status_label.setStyleSheet("color: orange;")
        self.cancel_button.setEnabled(False)
        self.cancelled.emit()

    def update_progress(self, current: int, total: int, best_score: float) -> None:
        """Update the progress display.

        Args:
            current: Current iteration number.
            total: Total number of iterations.
            best_score: Current best score achieved.
        """
        if self._is_cancelling:
            return

        # Calculate percentage
        percentage = int((current / total) * 100) if total > 0 else 0
        percentage = min(percentage, 100)  # Cap at 100%

        # Update progress bar
        self.progress_bar.setValue(percentage)
        self.progress_bar.setFormat(f"Iteration {current}/{total}")

        # Update score label
        self.score_label.setText(f"Current best score: {best_score:.1f}")

    def set_complete(self, lineups_generated: int = 0) -> None:
        """Mark optimization as complete.

        Updates the dialog to show completion status.

        Args:
            lineups_generated: Number of lineups that were generated.
        """
        self._is_cancelling = False

        # Update progress bar to 100%
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Complete!")

        # Update status
        self.status_label.setText(f"Generated {lineups_generated} lineups")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

        # Update score label
        current_score_text = self.score_label.text()
        if "Current best score:" in current_score_text:
            score = current_score_text.replace("Current best score: ", "")
            self.score_label.setText(f"Final best score: {score}")

        # Change cancel button to close button
        self.cancel_button.setText("Close")
        self.cancel_button.setEnabled(True)
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)

    def set_error(self, error_message: str) -> None:
        """Mark optimization as failed with error.

        Args:
            error_message: Error message to display.
        """
        self._is_cancelling = False

        # Update status
        self.status_label.setText("Optimization failed")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")

        # Update score label with error
        self.score_label.setText(error_message)
        self.score_label.setStyleSheet("color: red;")

        # Change cancel button to close button
        self.cancel_button.setText("Close")
        self.cancel_button.setEnabled(True)
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)

    def closeEvent(self, event) -> None:
        """Handle dialog close event.

        Emits cancelled signal if user closes dialog via X button
        while optimization is still running.

        Args:
            event: Close event object.
        """
        if not self._is_cancelling and self.progress_bar.value() < 100:
            # User closed dialog while optimization running - treat as cancel
            self._on_cancel_clicked()
            event.ignore()  # Don't close yet, let cancellation complete
        else:
            event.accept()

    def is_cancelling(self) -> bool:
        """Check if cancellation is in progress.

        Returns:
            True if user has requested cancellation.
        """
        return self._is_cancelling
