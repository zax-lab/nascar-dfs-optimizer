"""Live preview widget for displaying optimization results.

Shows lineup table with status updates during live optimization.
Similar to LineupsTab but optimized for compact display in split view.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableView,
    QProgressBar,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from typing import List, Dict, Any, Optional

from ..models.lineup_model import LineupTableModel


class LivePreview(QWidget):
    """Widget for displaying live optimization results in split view.

    Provides:
    - Compact lineup table showing top lineups
    - Status label with optimization state
    - Progress indicator
    - Auto-update when optimization completes

    Designed to be embedded in split-pane layout with minimal footprint
    while still providing useful lineup information.
    """

    # Signal emitted when user selects a lineup
    lineup_selected = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the live preview widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header with title and status
        header = QHBoxLayout()

        title = QLabel("Live Preview")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(title)

        header.addStretch()

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 12px; color: #666;")
        header.addWidget(self.status_label)

        layout.addLayout(header)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #cccccc;")
        layout.addWidget(line)

        # Lineup table
        self.lineup_model = LineupTableModel()
        self.lineup_table = QTableView()
        self.lineup_table.setModel(self.lineup_model)
        self.lineup_table.setAlternatingRowColors(True)
        self.lineup_table.setSelectionBehavior(QTableView.SelectRows)
        self.lineup_table.setSelectionMode(QTableView.SingleSelection)
        self.lineup_table.setSortingEnabled(True)

        # Compact table styling
        self.lineup_table.verticalHeader().setVisible(False)
        self.lineup_table.setStyleSheet("""
            QTableView {
                font-size: 11px;
            }
            QTableView::item {
                padding: 2px 5px;
            }
            QHeaderView::section {
                font-size: 11px;
                padding: 3px 5px;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.lineup_table)

        # Footer with stats
        footer = QHBoxLayout()

        self.stats_label = QLabel("No lineups generated")
        self.stats_label.setStyleSheet("font-size: 11px; color: #666;")
        footer.addWidget(self.stats_label)

        footer.addStretch()

        # Top 20% indicator
        self.top_indicator = QLabel("Top 20% highlighted in green")
        self.top_indicator.setStyleSheet(
            "font-size: 10px; color: #4CAF50; font-style: italic;"
        )
        footer.addWidget(self.top_indicator)

        layout.addLayout(footer)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_lineups(self, lineups: List[Dict[str, Any]]) -> None:
        """Update the lineup table with new results.

        Args:
            lineups: List of generated lineup dictionaries.
        """
        self.lineup_model.update_data(lineups)

        # Update stats
        if lineups:
            avg_points = sum(l.get("total_points", 0) for l in lineups) / len(lineups)
            best_score = max(l.get("total_points", 0) for l in lineups)
            self.stats_label.setText(
                f"{len(lineups)} lineups | Best: {best_score:.1f} pts | Avg: {avg_points:.1f} pts"
            )
        else:
            self.stats_label.setText("No lineups generated")

        # Auto-resize columns to content
        self.lineup_table.resizeColumnsToContents()

    def set_status(self, status: str, detail: str = "") -> None:
        """Set the status display.

        Args:
            status: Main status text (e.g., "Optimizing...", "Ready").
            detail: Optional detail text shown in parentheses.
        """
        if detail:
            self.status_label.setText(f"{status} ({detail})")
        else:
            self.status_label.setText(status)

        # Update color based on status
        if status.lower() in ["optimizing...", "waiting..."]:
            self.status_label.setStyleSheet(
                "font-size: 12px; color: #ff9800; font-weight: bold;"
            )
        elif status.lower() in ["ready", "lineups ready"]:
            self.status_label.setStyleSheet(
                "font-size: 12px; color: #4CAF50; font-weight: bold;"
            )
        elif "failed" in status.lower() or "error" in status.lower():
            self.status_label.setStyleSheet(
                "font-size: 12px; color: #f44336; font-weight: bold;"
            )
        else:
            self.status_label.setStyleSheet("font-size: 12px; color: #666;")

    def set_progress(self, percent: int, message: str = "") -> None:
        """Set the progress bar value.

        Args:
            percent: Progress percentage (0-100).
            message: Optional progress message.
        """
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(percent)

        if message:
            self.progress_bar.setFormat(f"{message}: %p%")
        else:
            self.progress_bar.setFormat("%p%")

        if percent >= 100:
            self.progress_bar.setVisible(False)

    def clear(self) -> None:
        """Clear the lineup table and reset status."""
        self.lineup_model.update_data([])
        self.set_status("Ready")
        self.stats_label.setText("No lineups generated")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)

    def show_placeholder(self, message: str) -> None:
        """Show a placeholder message when no data is available.

        Args:
            message: Placeholder message to display.
        """
        self.clear()
        self.set_status(message)
