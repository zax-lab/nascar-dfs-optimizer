"""Presets tab for browsing and managing constraint presets."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QTableView,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QHeaderView,
    QSizePolicy,
    QScrollArea,
    QFrame,
    QGridLayout,
    QApplication,
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from typing import Dict, Any, List, Optional, Callable
import json


class PresetTableModel(QAbstractTableModel):
    """Table model for displaying constraint presets."""

    def __init__(self, presets: List[Dict[str, Any]] = None):
        super().__init__()
        self.presets = presets or []
        self.headers = ["Name", "Scope", "Race Type", "Track", "Usage"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.presets)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.presets):
            return None

        preset = self.presets[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return preset.get("name", "")
            elif col == 1:
                return "Global" if preset.get("is_global") else "Race-Specific"
            elif col == 2:
                return preset.get("race_type") or "-"
            elif col == 3:
                return preset.get("track_name") or "-"
            elif col == 4:
                return str(preset.get("usage_count", 0))

        elif role == Qt.BackgroundRole:
            if col == 1:
                if preset.get("is_global"):
                    return QColor(200, 255, 200)  # Light green for global
                else:
                    return QColor(255, 255, 200)  # Light yellow for race-specific

        elif role == Qt.UserRole:
            return preset

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def set_presets(self, presets: List[Dict[str, Any]]) -> None:
        """Update the model with new preset data."""
        self.beginResetModel()
        self.presets = presets
        self.endResetModel()

    def get_preset_at(self, row: int) -> Optional[Dict[str, Any]]:
        """Get preset data at given row."""
        if 0 <= row < len(self.presets):
            return self.presets[row]
        return None


class RecentPresetButton(QWidget):
    """Button widget for displaying a recent preset chip."""

    clicked = Signal(int)  # Emits preset_id when clicked

    def __init__(self, preset: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.preset_id = preset.get("id")
        self.setup_ui(preset)

    def setup_ui(self, preset: Dict[str, Any]) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # Name label
        name_label = QLabel(preset.get("name", "Unknown"))
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)

        # Scope indicator
        if preset.get("is_global"):
            scope_label = QLabel("[G]")
            scope_label.setStyleSheet("color: green; font-size: 10px;")
            scope_label.setToolTip("Global preset")
            layout.addWidget(scope_label)

        # Usage count
        usage = preset.get("usage_count", 0)
        if usage > 0:
            usage_label = QLabel(f"({usage})")
            usage_label.setStyleSheet("color: gray; font-size: 10px;")
            layout.addWidget(usage_label)

        layout.addStretch()

        # Style the widget like a button
        self.setStyleSheet("""
            RecentPresetButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            RecentPresetButton:hover {
                background-color: #e0e0e0;
                border-color: #999;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.preset_id)


class PresetsTab(QWidget):
    """Tab for browsing, loading, and managing constraint presets.

    Provides a library view with:
    - Filterable preset list with details
    - Quick-access recent presets row
    - Import/export functionality
    """

    # Signals
    preset_loaded = Signal(dict)  # Emits config dict when user loads a preset
    preset_selected = Signal(int)  # Emits preset_id when user selects a preset

    def __init__(
        self,
        preset_manager,
        race_type: Optional[str] = None,
        track_name: Optional[str] = None,
        parent=None,
    ):
        """Initialize the presets tab.

        Args:
            preset_manager: PresetManager instance for data operations
            race_type: Current race type for filtering (optional)
            track_name: Current track name for filtering (optional)
            parent: Parent widget
        """
        super().__init__(parent)

        self.preset_manager = preset_manager
        self.current_race_type = race_type
        self.current_track_name = track_name
        self.selected_preset_id: Optional[int] = None

        self._setup_ui()
        self._connect_signals()
        self._refresh_presets()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Recent presets row
        recent_group = QGroupBox("Recent Presets (Quick Access)")
        recent_layout = QHBoxLayout(recent_group)
        recent_layout.setSpacing(8)

        self.recent_container = QWidget()
        self.recent_layout = QHBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(8)
        self.recent_layout.addStretch()

        recent_layout.addWidget(self.recent_container, stretch=1)

        refresh_recent_btn = QPushButton("Refresh")
        refresh_recent_btn.setToolTip("Refresh recent presets list")
        refresh_recent_btn.setMaximumWidth(80)
        recent_layout.addWidget(refresh_recent_btn)
        self.refresh_recent_btn = refresh_recent_btn

        layout.addWidget(recent_group)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left side: Filters and preset list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Filters group
        filters_group = QGroupBox("Filters")
        filters_layout = QGridLayout(filters_group)

        # Race type filter
        filters_layout.addWidget(QLabel("Race Type:"), 0, 0)
        self.race_type_combo = QComboBox()
        self.race_type_combo.setEditable(True)
        self.race_type_combo.addItem("All", None)
        self.race_type_combo.addItem("Cup", "Cup")
        self.race_type_combo.addItem("Xfinity", "Xfinity")
        self.race_type_combo.addItem("Truck", "Truck")
        filters_layout.addWidget(self.race_type_combo, 0, 1)

        # Track filter
        filters_layout.addWidget(QLabel("Track:"), 1, 0)
        self.track_edit = QLineEdit()
        self.track_edit.setPlaceholderText("Filter by track name...")
        filters_layout.addWidget(self.track_edit, 1, 1)

        # Scope filter
        self.global_only_check = QCheckBox("Global presets only")
        self.global_only_check.setChecked(False)
        filters_layout.addWidget(self.global_only_check, 2, 0, 1, 2)

        # Search filter
        filters_layout.addWidget(QLabel("Search:"), 3, 0)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name or description...")
        filters_layout.addWidget(self.search_edit, 3, 1)

        left_layout.addWidget(filters_group)

        # Preset list
        list_group = QGroupBox("Presets")
        list_layout = QVBoxLayout(list_group)

        self.preset_table = QTableView()
        self.preset_model = PresetTableModel()
        self.preset_table.setModel(self.preset_model)
        self.preset_table.setSelectionBehavior(QTableView.SelectRows)
        self.preset_table.setSelectionMode(QTableView.SingleSelection)
        self.preset_table.setAlternatingRowColors(True)
        self.preset_table.horizontalHeader().setStretchLastSection(False)
        self.preset_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.preset_table.setSortingEnabled(True)

        list_layout.addWidget(self.preset_table)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.load_btn = QPushButton("Load Preset")
        self.load_btn.setToolTip("Load selected preset into constraints")
        buttons_layout.addWidget(self.load_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setToolTip("Delete selected preset")
        buttons_layout.addWidget(self.delete_btn)

        buttons_layout.addStretch()

        self.import_btn = QPushButton("Import...")
        self.import_btn.setToolTip("Import preset from JSON file")
        buttons_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export...")
        self.export_btn.setToolTip("Export selected preset to JSON file")
        self.export_btn.setEnabled(False)
        buttons_layout.addWidget(self.export_btn)

        list_layout.addLayout(buttons_layout)

        left_layout.addWidget(list_group, stretch=1)

        splitter.addWidget(left_widget)

        # Right side: Preset details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Details group
        details_group = QGroupBox("Preset Details")
        details_layout = QVBoxLayout(details_group)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_label = QLabel("Select a preset to view details")
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        name_layout.addWidget(self.name_label, stretch=1)
        details_layout.addLayout(name_layout)

        # Scope
        scope_layout = QHBoxLayout()
        scope_layout.addWidget(QLabel("Scope:"))
        self.scope_label = QLabel("-")
        self.scope_label.setStyleSheet("font-style: italic;")
        scope_layout.addWidget(self.scope_label, stretch=1)
        details_layout.addLayout(scope_layout)

        # Race type
        race_type_layout = QHBoxLayout()
        race_type_layout.addWidget(QLabel("Race Type:"))
        self.race_type_label = QLabel("-")
        race_type_layout.addWidget(self.race_type_label, stretch=1)
        details_layout.addLayout(race_type_layout)

        # Track
        track_layout = QHBoxLayout()
        track_layout.addWidget(QLabel("Track:"))
        self.track_label = QLabel("-")
        track_layout.addWidget(self.track_label, stretch=1)
        details_layout.addLayout(track_layout)

        # Usage
        usage_layout = QHBoxLayout()
        usage_layout.addWidget(QLabel("Usage Count:"))
        self.usage_label = QLabel("-")
        usage_layout.addWidget(self.usage_label, stretch=1)
        details_layout.addLayout(usage_layout)

        # Description
        details_layout.addWidget(QLabel("Description:"))
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(60)
        self.description_text.setPlaceholderText("No description available")
        details_layout.addWidget(self.description_text)

        # Constraints preview
        details_layout.addWidget(QLabel("Constraint Preview:"))
        self.constraints_preview = QTextEdit()
        self.constraints_preview.setReadOnly(True)
        self.constraints_preview.setPlaceholderText(
            "Select a preset to view constraints"
        )
        details_layout.addWidget(self.constraints_preview)

        right_layout.addWidget(details_group)

        # Metadata
        meta_group = QGroupBox("Metadata")
        meta_layout = QVBoxLayout(meta_group)

        created_layout = QHBoxLayout()
        created_layout.addWidget(QLabel("Created:"))
        self.created_label = QLabel("-")
        created_layout.addWidget(self.created_label, stretch=1)
        meta_layout.addLayout(created_layout)

        updated_layout = QHBoxLayout()
        updated_layout.addWidget(QLabel("Updated:"))
        self.updated_label = QLabel("-")
        updated_layout.addWidget(self.updated_label, stretch=1)
        meta_layout.addLayout(updated_layout)

        right_layout.addWidget(meta_group)

        right_layout.addStretch()

        splitter.addWidget(right_widget)

        # Set splitter proportions
        splitter.setSizes([400, 400])

        layout.addWidget(splitter, stretch=1)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        # Filter changes
        self.race_type_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.track_edit.textChanged.connect(self._on_filter_changed)
        self.global_only_check.toggled.connect(self._on_filter_changed)
        self.search_edit.textChanged.connect(self._on_filter_changed)

        # Table selection
        self.preset_table.selectionModel().currentRowChanged.connect(
            self._on_preset_selected
        )

        # Buttons
        self.load_btn.clicked.connect(self._on_load_preset)
        self.delete_btn.clicked.connect(self._on_delete_preset)
        self.import_btn.clicked.connect(self._on_import_preset)
        self.export_btn.clicked.connect(self._on_export_preset)
        self.refresh_recent_btn.clicked.connect(self._refresh_recent_presets)

    def _on_filter_changed(self) -> None:
        """Handle filter changes."""
        self._refresh_presets()

    def _refresh_presets(self) -> None:
        """Refresh the preset list based on current filters."""
        if not self.preset_manager:
            return

        try:
            # Get filter values
            race_type = self.race_type_combo.currentData()
            if race_type is None and self.race_type_combo.currentText():
                race_type = self.race_type_combo.currentText()

            track_name = self.track_edit.text() or None
            global_only = self.global_only_check.isChecked()
            search_query = self.search_edit.text()

            # Get presets
            if global_only:
                presets = self.preset_manager.get_presets_for_race(None, None)
            elif race_type or track_name:
                presets = self.preset_manager.get_presets_for_race(
                    race_type if race_type else self.current_race_type,
                    track_name if track_name else self.current_track_name,
                )
            else:
                presets = self.preset_manager.get_all_presets()

            # Apply search filter if present
            if search_query:
                presets = [
                    p
                    for p in presets
                    if search_query.lower() in p.get("name", "").lower()
                    or search_query.lower() in p.get("description", "").lower()
                ]

            self.preset_model.set_presets(presets)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load presets: {str(e)}")

    def _refresh_recent_presets(self) -> None:
        """Refresh the recent presets row."""
        # Clear existing buttons
        while self.recent_layout.count() > 1:  # Keep the stretch
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.preset_manager:
            return

        try:
            recent = self.preset_manager.get_recent_presets(limit=5)

            for preset in recent:
                btn = RecentPresetButton(preset)
                btn.clicked.connect(self._on_recent_preset_clicked)
                self.recent_layout.insertWidget(self.recent_layout.count() - 1, btn)

        except Exception as e:
            print(f"Error loading recent presets: {e}")

    def _on_preset_selected(self, current: QModelIndex, previous: QModelIndex) -> None:
        """Handle preset selection change."""
        preset = self.preset_model.get_preset_at(current.row())

        if preset:
            self.selected_preset_id = preset.get("id")
            self._update_details_panel(preset)
            self.export_btn.setEnabled(True)
            self.preset_selected.emit(self.selected_preset_id)
        else:
            self.selected_preset_id = None
            self._clear_details_panel()
            self.export_btn.setEnabled(False)

    def _update_details_panel(self, preset: Dict[str, Any]) -> None:
        """Update the details panel with preset information."""
        self.name_label.setText(preset.get("name", "Unknown"))

        scope = "Global" if preset.get("is_global") else "Race-Specific"
        self.scope_label.setText(scope)

        self.race_type_label.setText(preset.get("race_type") or "Any")
        self.track_label.setText(preset.get("track_name") or "Any")
        self.usage_label.setText(str(preset.get("usage_count", 0)))

        self.description_text.setText(preset.get("description", ""))

        # Format constraints as readable text
        config = preset.get("config", {})
        preview_text = self._format_constraints_preview(config)
        self.constraints_preview.setText(preview_text)

        self.created_label.setText(preset.get("created_at", "-")[:19])
        self.updated_label.setText(preset.get("updated_at", "-")[:19])

    def _clear_details_panel(self) -> None:
        """Clear the details panel."""
        self.name_label.setText("Select a preset to view details")
        self.scope_label.setText("-")
        self.race_type_label.setText("-")
        self.track_label.setText("-")
        self.usage_label.setText("-")
        self.description_text.clear()
        self.constraints_preview.clear()
        self.created_label.setText("-")
        self.updated_label.setText("-")

    def _format_constraints_preview(self, config: Dict[str, Any]) -> str:
        """Format constraints config as readable text."""
        lines = []

        # Salary constraints
        if "salary_cap" in config:
            lines.append(f"Salary Cap: ${config['salary_cap']:,}")
        if "min_salary" in config:
            lines.append(f"Min Salary: ${config['min_salary']:,}")

        # Ownership constraints
        if "max_ownership" in config:
            lines.append(f"Max Ownership: {config['max_ownership']:.1%}")
        if "min_ownership" in config:
            lines.append(f"Min Ownership: {config['min_ownership']:.1%}")

        # Stacking rules
        stacking = config.get("stacking", {})
        if stacking:
            allow_teammates = stacking.get("allow_teammates", True)
            lines.append(f"Allow Teammates: {'Yes' if allow_teammates else 'No'}")
            if allow_teammates and "max_teammates" in stacking:
                lines.append(f"Max Teammates: {stacking['max_teammates']}")

        # Portfolio settings
        if "lineup_count" in config:
            lines.append(f"Lineup Count: {config['lineup_count']}")
        if "iterations" in config:
            lines.append(f"MCMC Iterations: {config['iterations']}")

        return "\n".join(lines) if lines else "No constraints configured"

    def _on_load_preset(self) -> None:
        """Handle load preset button."""
        if not self.selected_preset_id or not self.preset_manager:
            QMessageBox.warning(self, "No Selection", "Please select a preset to load.")
            return

        try:
            preset = self.preset_manager.load_preset(self.selected_preset_id)
            config = preset.get("config", {})

            # Strip internal fields before emitting
            clean_config = {k: v for k, v in config.items() if not k.startswith("_")}

            # Record usage
            self.preset_manager.record_preset_usage(self.selected_preset_id)

            # Emit signal
            self.preset_loaded.emit(clean_config)

            # Refresh recent presets
            self._refresh_recent_presets()

            QMessageBox.information(
                self, "Preset Loaded", f"Loaded preset: {preset.get('name', 'Unknown')}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load preset: {str(e)}")

    def _on_delete_preset(self) -> None:
        """Handle delete preset button."""
        if not self.selected_preset_id or not self.preset_manager:
            QMessageBox.warning(
                self, "No Selection", "Please select a preset to delete."
            )
            return

        preset = self.preset_model.get_preset_at(self.preset_table.currentIndex().row())
        preset_name = preset.get("name", "Unknown") if preset else "Unknown"

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the preset '{preset_name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                success = self.preset_manager.delete_preset(self.selected_preset_id)
                if success:
                    self._refresh_presets()
                    self._clear_details_panel()
                    self.selected_preset_id = None
                    self.export_btn.setEnabled(False)
                    QMessageBox.information(
                        self, "Deleted", f"Preset '{preset_name}' deleted."
                    )
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete preset.")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to delete preset: {str(e)}"
                )

    def _on_import_preset(self) -> None:
        """Handle import preset button."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Preset", "", "JSON Files (*.json);;All Files (*.*)"
        )

        if not filepath:
            return

        try:
            preset_id = self.preset_manager.import_preset_from_json(filepath)
            self._refresh_presets()

            # Show success message
            preset = self.preset_manager.load_preset(preset_id)
            QMessageBox.information(
                self,
                "Import Successful",
                f"Imported preset: {preset.get('name', 'Unknown')}",
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Import Failed", f"Failed to import preset: {str(e)}"
            )

    def _on_export_preset(self) -> None:
        """Handle export preset button."""
        if not self.selected_preset_id:
            return

        preset = self.preset_model.get_preset_at(self.preset_table.currentIndex().row())
        if not preset:
            return

        default_name = f"{preset.get('name', 'preset').replace(' ', '_')}.json"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Preset", default_name, "JSON Files (*.json);;All Files (*.*)"
        )

        if not filepath:
            return

        try:
            self.preset_manager.export_preset_to_json(self.selected_preset_id, filepath)
            QMessageBox.information(
                self, "Export Successful", f"Exported preset to:\n{filepath}"
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Export Failed", f"Failed to export preset: {str(e)}"
            )

    def _on_recent_preset_clicked(self, preset_id: int) -> None:
        """Handle click on a recent preset button."""
        try:
            preset = self.preset_manager.load_preset(preset_id)
            config = preset.get("config", {})

            # Strip internal fields
            clean_config = {k: v for k, v in config.items() if not k.startswith("_")}

            # Record usage
            self.preset_manager.record_preset_usage(preset_id)

            # Emit signal
            self.preset_loaded.emit(clean_config)

            # Refresh recent presets to update order
            self._refresh_recent_presets()

            QMessageBox.information(
                self, "Preset Loaded", f"Loaded preset: {preset.get('name', 'Unknown')}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load preset: {str(e)}")

    def set_race_context(
        self, race_type: Optional[str], track_name: Optional[str]
    ) -> None:
        """Update the race context for filtering.

        Args:
            race_type: Current race type
            track_name: Current track name
        """
        self.current_race_type = race_type
        self.current_track_name = track_name

        # Update UI if values provided
        if race_type:
            index = self.race_type_combo.findData(race_type)
            if index >= 0:
                self.race_type_combo.setCurrentIndex(index)
            else:
                self.race_type_combo.setCurrentText(race_type)

        if track_name:
            self.track_edit.setText(track_name)

        # Refresh presets
        self._refresh_presets()
