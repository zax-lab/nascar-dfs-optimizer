"""Split editor tab with draggable panes and debounced live optimization.

Provides iTerm/VSCode-style split-view layout with:
- Left pane: ConstraintPanel for editing constraints
- Right pane: Vertical splitter with LivePreview (top) and veto log (bottom)
- State persistence for splitter positions
- Debounced optimization trigger on constraint changes
"""

import logging

from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QFrame,
    QMenu,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer, QSettings, QByteArray
from typing import Dict, Any, List, Optional

from ..widgets.constraint_panel import ConstraintPanel
from ..widgets.live_preview import LivePreview
from ...persistence.database import DatabaseManager
from ...persistence.preset_manager import PresetManager
from ...optimization.engine import OptimizationEngine

logger = logging.getLogger(__name__)


class SplitEditorTab(QWidget):
    """Split-view editor tab with constraint panel and live preview.

    Layout structure:
    - Main horizontal QSplitter (left/right panes)
    - Left pane: ConstraintPanel with race selector and preset dropdown
    - Right pane: QSplitter (vertical) containing:
        - Top: LivePreview widget (lineup results table)
        - Bottom: Collapsible veto log viewer placeholder

    Features:
    - Draggable splitters with state persistence via QSettings
    - Debounced optimization trigger on constraint changes
    - Real-time vs debounced mode toggle
    - Navigation shortcuts for pane focus

    Signals:
        lineups_generated: Emitted when optimization completes (list_of_lineups)
        optimization_complete: Emitted when optimization finishes (for dock bounce)
        notify_complete: Emitted to request notification (num_lineups)
    """

    # Signal emitted when lineups are generated
    lineups_generated = Signal(list)

    # Signal emitted when optimization completes
    optimization_complete = Signal()

    # Signal emitted to request notification
    notify_complete = Signal(int)

    def __init__(
        self,
        database_manager: DatabaseManager,
        optimization_engine: OptimizationEngine,
        job_manager: Optional[Any] = None,
        preset_manager: Optional[PresetManager] = None,
        undo_manager: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the split editor tab.

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
        self.pending_job_id: Optional[str] = None

        # Debounce settings
        self.debounce_ms = 300
        self.real_time_mode = False
        self.live_optimization_enabled = True

        # Settings for persistence
        self.settings = QSettings("AxiomaticDFS", "NascarOptimizer")

        # Create debounce timer
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)

        # Create save state timer (debounced save)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_splitter_state)

        self._setup_ui()
        self._restore_splitter_state()
        self._load_races()

    def _setup_ui(self) -> None:
        """Set up the user interface with split-pane layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create main horizontal splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setChildrenCollapsible(True)

        # Left pane container
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        # Race selector at top of left pane
        race_header = QHBoxLayout()
        race_label = QLabel("Race:")
        race_label.setStyleSheet("font-weight: bold;")
        race_header.addWidget(race_label)

        self.race_combo = QComboBox()
        self.race_combo.setPlaceholderText("Select a race...")
        self.race_combo.currentIndexChanged.connect(self._on_race_changed)
        race_header.addWidget(self.race_combo, stretch=1)

        left_layout.addLayout(race_header)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #cccccc;")
        left_layout.addWidget(line)

        # Preset selector (if preset manager available)
        if self.preset_manager:
            preset_header = QHBoxLayout()
            preset_label = QLabel("Preset:")
            preset_label.setStyleSheet("font-weight: bold;")
            preset_header.addWidget(preset_label)

            self.preset_combo = QComboBox()
            self.preset_combo.setPlaceholderText("Quick apply preset...")
            self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
            preset_header.addWidget(self.preset_combo, stretch=1)

            self.refresh_presets_btn = QPushButton("↻")
            self.refresh_presets_btn.setMaximumWidth(30)
            self.refresh_presets_btn.setToolTip("Refresh presets")
            self.refresh_presets_btn.clicked.connect(self._load_presets)
            preset_header.addWidget(self.refresh_presets_btn)

            left_layout.addLayout(preset_header)

            # Quick-apply recent presets buttons
            self.recent_presets_layout = QHBoxLayout()
            self.recent_presets_layout.setSpacing(5)
            left_layout.addLayout(self.recent_presets_layout)

            self._load_presets()

        # Constraint panel
        self.constraint_panel = ConstraintPanel(preset_manager=self.preset_manager)
        self.constraint_panel.constraints_changed.connect(self._on_constraints_changed)
        left_layout.addWidget(self.constraint_panel)

        # Live optimization settings
        settings_group = QHBoxLayout()
        settings_group.setSpacing(15)

        self.live_opt_check = QPushButton("⚡ Live")
        self.live_opt_check.setCheckable(True)
        self.live_opt_check.setChecked(True)
        self.live_opt_check.setToolTip("Toggle live optimization on constraint changes")
        self.live_opt_check.toggled.connect(self._on_live_toggle)
        settings_group.addWidget(self.live_opt_check)

        self.realtime_check = QPushButton("Real-time")
        self.realtime_check.setCheckable(True)
        self.realtime_check.setChecked(False)
        self.realtime_check.setToolTip(
            "Real-time mode (no debounce) - triggers immediately"
        )
        self.realtime_check.toggled.connect(self._on_realtime_toggle)
        settings_group.addWidget(self.realtime_check)

        self.debounce_label = QLabel(f"Debounce: {self.debounce_ms}ms")
        self.debounce_label.setStyleSheet("font-size: 11px; color: #666;")
        settings_group.addWidget(self.debounce_label)

        settings_group.addStretch()
        left_layout.addLayout(settings_group)

        # Add left container to main splitter
        self.main_splitter.addWidget(left_container)

        # Right pane: Vertical splitter
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setHandleWidth(8)
        self.right_splitter.setChildrenCollapsible(True)

        # Top: Live preview
        self.live_preview = LivePreview()
        self.live_preview.setMinimumHeight(200)
        self.right_splitter.addWidget(self.live_preview)

        # Bottom: Veto log placeholder (collapsible)
        self.veto_log_container = QWidget()
        veto_layout = QVBoxLayout(self.veto_log_container)
        veto_layout.setContentsMargins(10, 10, 10, 10)

        veto_header = QHBoxLayout()
        veto_title = QLabel("Kernel Veto Log")
        veto_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        veto_header.addWidget(veto_title)
        veto_header.addStretch()

        self.toggle_veto_btn = QPushButton("▼")
        self.toggle_veto_btn.setMaximumWidth(30)
        self.toggle_veto_btn.setToolTip("Toggle veto log visibility")
        self.toggle_veto_btn.clicked.connect(self._toggle_veto_log)
        veto_header.addWidget(self.toggle_veto_btn)

        veto_layout.addLayout(veto_header)

        veto_placeholder = QLabel(
            "Veto log viewer will display kernel rejection reasons here."
        )
        veto_placeholder.setStyleSheet("color: #666; font-style: italic;")
        veto_placeholder.setAlignment(Qt.AlignCenter)
        veto_layout.addWidget(veto_placeholder)

        self.right_splitter.addWidget(self.veto_log_container)

        # Add right splitter to main splitter
        self.main_splitter.addWidget(self.right_splitter)

        # Set initial sizes (2:1 ratio favoring right pane)
        self.main_splitter.setSizes([350, 700])
        self.right_splitter.setSizes([500, 150])

        # Set stretch factors
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 2)
        self.right_splitter.setStretchFactor(0, 2)
        self.right_splitter.setStretchFactor(1, 1)

        # Connect splitter moved signals for state persistence
        self.main_splitter.splitterMoved.connect(self._on_splitter_moved)
        self.right_splitter.splitterMoved.connect(self._on_splitter_moved)

        layout.addWidget(self.main_splitter)

        # Set minimum sizes to prevent collapsing
        left_container.setMinimumWidth(250)
        self.live_preview.setMinimumHeight(150)
        self.veto_log_container.setMinimumHeight(100)

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Handle splitter movement - debounced save state.

        Args:
            pos: New position of splitter handle.
            index: Index of splitter handle that moved.
        """
        # Restart save timer for debounced save
        self.save_timer.stop()
        self.save_timer.start(500)

    def _save_splitter_state(self) -> None:
        """Save splitter states to QSettings."""
        main_state = self.main_splitter.saveState()
        right_state = self.right_splitter.saveState()

        self.settings.setValue("split_editor/main_splitter_state", main_state)
        self.settings.setValue("split_editor/right_splitter_state", right_state)
        self.settings.setValue(
            "split_editor/veto_log_collapsed", self.veto_log_container.isVisible()
        )

    def _restore_splitter_state(self) -> None:
        """Restore splitter states from QSettings."""
        main_state = self.settings.value("split_editor/main_splitter_state")
        if main_state and isinstance(main_state, QByteArray):
            self.main_splitter.restoreState(main_state)

        right_state = self.settings.value("split_editor/right_splitter_state")
        if right_state and isinstance(right_state, QByteArray):
            self.right_splitter.restoreState(right_state)

        veto_collapsed = self.settings.value("split_editor/veto_log_collapsed", False)
        if veto_collapsed:
            self.veto_log_container.setVisible(False)
            self.toggle_veto_btn.setText("▶")

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

                self.race_combo.addItem(display_text, race_id)

            if races:
                self.race_combo.setCurrentIndex(0)
                self._on_race_changed(0)

        except Exception as e:
            logger.error(f"Error loading races: {e}")

    def _on_race_changed(self, index: int) -> None:
        """Handle race selection change.

        Args:
            index: Index of selected race in combo box.
        """
        if index < 0:
            self.current_race_id = None
            return

        self.current_race_id = self.race_combo.itemData(index)

        # Reload presets for this race context
        if self.preset_manager:
            self._load_presets()

    def _load_presets(self) -> None:
        """Load available presets into dropdown and recent buttons."""
        if not self.preset_manager:
            return

        # Guard: preset_combo may not exist if widget initialized without preset_manager
        if not hasattr(self, 'preset_combo'):
            return

        try:
            # Load all presets for dropdown
            presets = self.preset_manager.get_all_presets()
            self.preset_combo.clear()
            self.preset_combo.addItem("Select preset...", None)

            for preset in presets:
                self.preset_combo.addItem(preset["name"], preset["id"])

            # Load recent presets for quick buttons
            while self.recent_presets_layout.count():
                item = self.recent_presets_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            recent = self.preset_manager.get_recent_presets(limit=5)
            for preset in recent:
                btn = QPushButton(preset["name"])
                btn.setMaximumWidth(100)
                btn.setStyleSheet("font-size: 10px; padding: 2px 5px;")
                btn.setToolTip(
                    f"Apply preset: {preset['name']} (used {preset.get('usage_count', 0)} times)"
                )
                btn.clicked.connect(
                    lambda checked, pid=preset["id"]: self._apply_preset(pid)
                )
                self.recent_presets_layout.addWidget(btn)

            self.recent_presets_layout.addStretch()

        except Exception as e:
            logger.error(f"Error loading presets: {e}")

    def _on_preset_changed(self, index: int) -> None:
        """Handle preset selection from dropdown.

        Args:
            index: Index of selected preset.
        """
        if index <= 0:
            return

        preset_id = self.preset_combo.currentData()
        if preset_id:
            self._apply_preset(preset_id)

    def _apply_preset(self, preset_id: int) -> None:
        """Apply a preset to the constraint panel.

        Args:
            preset_id: ID of preset to apply.
        """
        if not self.preset_manager:
            return

        try:
            preset = self.preset_manager.load_preset(preset_id)
            config = preset.get("config", {})

            # Strip internal fields
            clean_config = {k: v for k, v in config.items() if not k.startswith("_")}

            self.constraint_panel.set_constraints(clean_config)

            # Record usage
            self.preset_manager.record_preset_usage(preset_id)

            # Trigger optimization after preset load
            if self.live_optimization_enabled:
                self._restart_debounce_timer()

        except Exception as e:
            logger.error(f"Error applying preset: {e}")

    def _on_constraints_changed(self) -> None:
        """Handle constraint changes - trigger debounced optimization."""
        if not self.live_optimization_enabled:
            return

        if self.real_time_mode:
            # Real-time mode: trigger immediately
            self._trigger_optimization()
        else:
            # Debounced mode: restart timer
            self._restart_debounce_timer()

    def _restart_debounce_timer(self) -> None:
        """Restart the debounce timer for optimization trigger."""
        self.debounce_timer.stop()
        self.debounce_timer.start(self.debounce_ms)
        self.live_preview.set_status("Waiting...", "constraint change detected")

    def _on_debounce_timeout(self) -> None:
        """Handle debounce timer timeout - trigger optimization."""
        self._trigger_optimization()

    def _trigger_optimization(self) -> None:
        """Trigger optimization job submission."""
        if not self.current_drivers:
            self.live_preview.set_status(
                "No drivers loaded", "import driver data first"
            )
            return

        if not self.constraint_panel.is_valid():
            self.live_preview.set_status("Invalid constraints", "fix validation errors")
            return

        if self.job_manager is None:
            self.live_preview.set_status("No JobManager", "optimization unavailable")
            return

        # Cancel pending job if exists
        if self.pending_job_id:
            try:
                self.job_manager.cancel_job(self.pending_job_id)
            except Exception:
                pass
            self.pending_job_id = None

        # Build job config
        race_id = self.current_race_id or 1
        race_name = (
            self.race_combo.currentText()
            if self.race_combo.currentIndex() >= 0
            else f"Race {race_id}"
        )
        track_name = race_name.split(" (")[0] if " (" in race_name else race_name

        constraints = self.constraint_panel.get_constraints()

        config = {
            "race_id": race_id,
            "race_name": race_name,
            "drivers": self.current_drivers,
            "num_lineups": 20,  # Default for live preview
            "iterations": 1000,  # Default for live preview
            "gpu_offload": False,  # Live preview uses local CPU
            "constraints": constraints,
        }

        job_name = f"{track_name} Live Optimization"

        try:
            # Submit job
            self.pending_job_id = self.job_manager.submit_job(config, job_name=job_name)
            self.live_preview.set_status("Optimizing...", f"Job: {job_name}")

            # Connect to job signals for this specific job
            self.job_manager.job_completed.connect(self._on_job_completed)
            self.job_manager.job_failed.connect(self._on_job_failed)
            self.job_manager.job_cancelled.connect(self._on_job_cancelled)

        except Exception as e:
            self.live_preview.set_status("Submit failed", str(e))

    def _on_job_completed(self, job_id: str, lineups: List[Dict[str, Any]]) -> None:
        """Handle job completion.

        Args:
            job_id: ID of completed job.
            lineups: Generated lineup results.
        """
        # Only process if this is our pending job
        if job_id != self.pending_job_id:
            return

        self.pending_job_id = None
        self.live_preview.update_lineups(lineups)
        self.live_preview.set_status(
            f"{len(lineups)} lineups ready", "optimization complete"
        )

        # Emit signals
        self.lineups_generated.emit(lineups)
        self.optimization_complete.emit()
        self.notify_complete.emit(len(lineups))

        # Disconnect job signals
        self._disconnect_job_signals()

    def _on_job_failed(self, job_id: str, error_message: str) -> None:
        """Handle job failure.

        Args:
            job_id: ID of failed job.
            error_message: Error message.
        """
        if job_id != self.pending_job_id:
            return

        self.pending_job_id = None
        self.live_preview.set_status("Optimization failed", error_message)
        self._disconnect_job_signals()

    def _on_job_cancelled(self, job_id: str) -> None:
        """Handle job cancellation.

        Args:
            job_id: ID of cancelled job.
        """
        if job_id != self.pending_job_id:
            return

        self.pending_job_id = None
        self.live_preview.set_status("Cancelled", "optimization cancelled")
        self._disconnect_job_signals()

    def _disconnect_job_signals(self) -> None:
        """Disconnect job manager signals."""
        if self.job_manager:
            try:
                self.job_manager.job_completed.disconnect(self._on_job_completed)
                self.job_manager.job_failed.disconnect(self._on_job_failed)
                self.job_manager.job_cancelled.disconnect(self._on_job_cancelled)
            except Exception:
                pass  # Signals may not be connected

    def _on_live_toggle(self, enabled: bool) -> None:
        """Handle live optimization toggle.

        Args:
            enabled: Whether live optimization is enabled.
        """
        self.live_optimization_enabled = enabled
        if enabled:
            self.live_opt_check.setStyleSheet("font-weight: bold; color: #4CAF50;")
        else:
            self.live_opt_check.setStyleSheet("")
            self.live_preview.set_status(
                "Live optimization off", "changes won't trigger optimization"
            )

    def _on_realtime_toggle(self, enabled: bool) -> None:
        """Handle real-time mode toggle.

        Args:
            enabled: Whether real-time mode is enabled.
        """
        self.real_time_mode = enabled
        if enabled:
            self.debounce_label.setText("Debounce: OFF")
            self.debounce_label.setStyleSheet(
                "font-size: 11px; color: #ff9800; font-weight: bold;"
            )
        else:
            self.debounce_label.setText(f"Debounce: {self.debounce_ms}ms")
            self.debounce_label.setStyleSheet("font-size: 11px; color: #666;")

    def _toggle_veto_log(self) -> None:
        """Toggle veto log visibility."""
        is_visible = self.veto_log_container.isVisible()
        self.veto_log_container.setVisible(not is_visible)
        self.toggle_veto_btn.setText("▶" if is_visible else "▼")

        # Save state
        self.settings.setValue("split_editor/veto_log_collapsed", is_visible)

    def set_drivers(self, drivers: List[Dict[str, Any]]) -> None:
        """Set the current drivers for optimization.

        Args:
            drivers: List of driver dictionaries.
        """
        self.current_drivers = drivers
        self.live_preview.set_status(
            f"Loaded {len(drivers)} drivers", "ready for optimization"
        )

    def set_debounce_delay(self, ms: int) -> None:
        """Set the debounce delay in milliseconds.

        Args:
            ms: Debounce delay in milliseconds (100-2000).
        """
        self.debounce_ms = max(100, min(2000, ms))
        if not self.real_time_mode:
            self.debounce_label.setText(f"Debounce: {self.debounce_ms}ms")

    def set_job_manager(self, job_manager: Optional[Any]) -> None:
        """Set the JobManager for this tab.

        Called from MainWindow to wire up job submission.

        Args:
            job_manager: JobManager instance for submitting jobs.
        """
        self.job_manager = job_manager

    def set_undo_manager(self, undo_manager: Optional[Any]) -> None:
        """Set the UndoManager for this tab.

        Called from MainWindow to wire up undo/redo functionality.

        Args:
            undo_manager: UndoManager instance for undo/redo operations.
        """
        self.undo_manager = undo_manager
        if self.constraint_panel:
            self.constraint_panel.set_undo_manager(undo_manager)

    def focus_constraints(self) -> None:
        """Set focus to the constraint panel (for keyboard shortcuts)."""
        if self.constraint_panel:
            self.constraint_panel.setFocus()

    def focus_preview(self) -> None:
        """Set focus to the live preview (for keyboard shortcuts)."""
        if self.live_preview:
            self.live_preview.setFocus()

    def focus_logs(self) -> None:
        """Set focus to the veto log (for keyboard shortcuts)."""
        if self.veto_log_container:
            self.veto_log_container.setFocus()

    def toggle_split_view(self) -> None:
        """Toggle split view mode (collapse/expand panes)."""
        sizes = self.main_splitter.sizes()
        if sizes[0] > 0:
            # Collapse left pane
            self.main_splitter.setSizes([0, sum(sizes)])
        else:
            # Restore default sizes
            self.main_splitter.setSizes([350, 700])
