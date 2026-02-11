"""Constraint panel widget for optimization settings."""

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from typing import Dict, Any, Optional


class ConstraintPanel(QWidget):
    """Widget for configuring optimization constraints.

    Provides input fields for:
    - Salary cap and minimum salary
    - Ownership exposure limits (min/max)
    - Stacking rules (teammate stacking)

    Includes preset save/load functionality for quick constraint switching.
    """

    # Signal emitted when constraints change
    constraints_changed = Signal()

    # Signal emitted when a preset is applied
    preset_applied = Signal(dict)

    def __init__(self, preset_manager=None, parent: Optional[QWidget] = None):
        """Initialize the constraint panel.

        Args:
            preset_manager: PresetManager instance for saving/loading presets.
                           If None, preset functionality is disabled.
            parent: Parent widget.
        """
        super().__init__(parent)

        self.preset_manager = preset_manager
        self._validation_label = QLabel()
        self._validation_label.setStyleSheet("color: red;")
        self._validation_label.setVisible(False)

        self._setup_ui()
        self._connect_signals()
        self._load_presets()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Salary constraints section
        salary_group = QGroupBox("Salary Constraints")
        salary_layout = QFormLayout(salary_group)

        # Salary cap: $40,000 - $60,000, default $50,000, step $100
        self.salary_cap_spin = QSpinBox()
        self.salary_cap_spin.setRange(40000, 60000)
        self.salary_cap_spin.setValue(50000)
        self.salary_cap_spin.setSingleStep(100)
        self.salary_cap_spin.setPrefix("$")
        self.salary_cap_spin.setGroupSeparatorShown(True)
        salary_layout.addRow("Salary Cap:", self.salary_cap_spin)

        # Min salary: $0 - $45,000, default $46,000, step $100
        self.min_salary_spin = QSpinBox()
        self.min_salary_spin.setRange(0, 45000)
        self.min_salary_spin.setValue(46000)
        self.min_salary_spin.setSingleStep(100)
        self.min_salary_spin.setPrefix("$")
        self.min_salary_spin.setGroupSeparatorShown(True)
        salary_layout.addRow("Min Salary:", self.min_salary_spin)

        layout.addWidget(salary_group)

        # Ownership constraints section
        ownership_group = QGroupBox("Ownership Constraints")
        ownership_layout = QFormLayout(ownership_group)

        # Max ownership: 0-100%, default 50%, step 1%
        self.max_ownership_spin = QDoubleSpinBox()
        self.max_ownership_spin.setRange(0, 100)
        self.max_ownership_spin.setValue(50)
        self.max_ownership_spin.setSingleStep(1)
        self.max_ownership_spin.setSuffix("%")
        ownership_layout.addRow("Max Ownership:", self.max_ownership_spin)

        # Min ownership: 0-100%, default 0%, step 1%
        self.min_ownership_spin = QDoubleSpinBox()
        self.min_ownership_spin.setRange(0, 100)
        self.min_ownership_spin.setValue(0)
        self.min_ownership_spin.setSingleStep(1)
        self.min_ownership_spin.setSuffix("%")
        ownership_layout.addRow("Min Ownership:", self.min_ownership_spin)

        layout.addWidget(ownership_group)

        # Stacking rules section
        stacking_group = QGroupBox("Stacking Rules")
        stacking_layout = QFormLayout(stacking_group)

        # Allow teammates checkbox (default checked)
        self.allow_teammates_check = QCheckBox("Allow teammates in lineup")
        self.allow_teammates_check.setChecked(True)
        stacking_layout.addRow(self.allow_teammates_check)

        # Max teammates: 2-6, default 3
        self.max_teammates_spin = QSpinBox()
        self.max_teammates_spin.setRange(2, 6)
        self.max_teammates_spin.setValue(3)
        stacking_layout.addRow("Max Teammates:", self.max_teammates_spin)

        layout.addWidget(stacking_group)

        # Validation label
        layout.addWidget(self._validation_label)

        # Preset management section
        if self.preset_manager:
            preset_group = QGroupBox("Presets")
            preset_layout = QHBoxLayout(preset_group)

            self.preset_combo = QComboBox()
            self.preset_combo.setPlaceholderText("Select preset...")
            preset_layout.addWidget(self.preset_combo, stretch=1)

            self.load_preset_btn = QPushButton("Load")
            self.load_preset_btn.setToolTip("Load selected preset")
            preset_layout.addWidget(self.load_preset_btn)

            self.save_preset_btn = QPushButton("Save")
            self.save_preset_btn.setToolTip("Save current constraints as preset")
            preset_layout.addWidget(self.save_preset_btn)

            layout.addWidget(preset_group)

        # Add stretch to push everything to the top
        layout.addStretch()

    def _connect_signals(self) -> None:
        """Connect widget signals to validation."""
        # Connect all spin boxes to validation
        self.salary_cap_spin.valueChanged.connect(self._validate_constraints)
        self.min_salary_spin.valueChanged.connect(self._validate_constraints)
        self.max_ownership_spin.valueChanged.connect(self._validate_constraints)
        self.min_ownership_spin.valueChanged.connect(self._validate_constraints)

        # Connect stacking rules
        self.allow_teammates_check.toggled.connect(self._on_teammates_toggled)

        # Connect preset buttons if available
        if self.preset_manager:
            self.load_preset_btn.clicked.connect(self._on_load_preset)
            self.save_preset_btn.clicked.connect(self._on_save_preset)

    def _on_teammates_toggled(self, checked: bool) -> None:
        """Handle teammates checkbox toggle.

        Args:
            checked: Whether teammates are allowed.
        """
        self.max_teammates_spin.setEnabled(checked)
        self.constraints_changed.emit()

    def _validate_constraints(self) -> None:
        """Validate constraint values and show errors."""
        errors = []

        # Min salary must be < salary cap
        if self.min_salary_spin.value() >= self.salary_cap_spin.value():
            errors.append("Min salary must be less than salary cap")

        # Min ownership must be < max ownership
        if self.min_ownership_spin.value() >= self.max_ownership_spin.value():
            errors.append("Min ownership must be less than max ownership")

        if errors:
            self._validation_label.setText("\n".join(errors))
            self._validation_label.setVisible(True)
        else:
            self._validation_label.setVisible(False)

        self.constraints_changed.emit()

    def is_valid(self) -> bool:
        """Check if current constraints are valid.

        Returns:
            True if all constraints are valid, False otherwise.
        """
        # Min salary must be < salary cap
        if self.min_salary_spin.value() >= self.salary_cap_spin.value():
            return False

        # Min ownership must be < max ownership
        if self.min_ownership_spin.value() >= self.max_ownership_spin.value():
            return False

        return True

    def get_constraints(self) -> Dict[str, Any]:
        """Return current constraint values as dict.

        Returns:
            Dictionary containing all constraint values:
            - salary_cap: int
            - min_salary: int
            - max_ownership: float (0-1)
            - min_ownership: float (0-1)
            - stacking: dict with allow_teammates and max_teammates
        """
        return {
            "salary_cap": self.salary_cap_spin.value(),
            "min_salary": self.min_salary_spin.value(),
            "max_ownership": self.max_ownership_spin.value() / 100,
            "min_ownership": self.min_ownership_spin.value() / 100,
            "stacking": {
                "allow_teammates": self.allow_teammates_check.isChecked(),
                "max_teammates": self.max_teammates_spin.value(),
            },
        }

    def set_constraints(self, constraints: Dict[str, Any]) -> None:
        """Set constraint values from dict.

        Args:
            constraints: Dictionary with constraint values matching
                        the format returned by get_constraints().
        """
        # Set salary constraints
        if "salary_cap" in constraints:
            self.salary_cap_spin.setValue(constraints["salary_cap"])
        if "min_salary" in constraints:
            self.min_salary_spin.setValue(constraints["min_salary"])

        # Set ownership constraints (convert from 0-1 to 0-100)
        if "max_ownership" in constraints:
            self.max_ownership_spin.setValue(constraints["max_ownership"] * 100)
        if "min_ownership" in constraints:
            self.min_ownership_spin.setValue(constraints["min_ownership"] * 100)

        # Set stacking rules
        if "stacking" in constraints:
            stacking = constraints["stacking"]
            if "allow_teammates" in stacking:
                self.allow_teammates_check.setChecked(stacking["allow_teammates"])
            if "max_teammates" in stacking:
                self.max_teammates_spin.setValue(stacking["max_teammates"])

        # Re-validate after setting
        self._validate_constraints()

    def _load_presets(self) -> None:
        """Load available presets from database."""
        if not self.preset_manager:
            return

        try:
            presets = self.preset_manager.get_all_presets()
            self.preset_combo.clear()
            for preset in presets:
                self.preset_combo.addItem(preset["name"], preset["id"])
        except Exception as e:
            print(f"Error loading presets: {e}")

    def _on_load_preset(self) -> None:
        """Handle load preset button click."""
        preset_id = self.preset_combo.currentData()
        if preset_id is None:
            QMessageBox.warning(
                self, "No Preset Selected", "Please select a preset to load."
            )
            return

        if not self.preset_manager:
            return

        try:
            preset = self.preset_manager.load_preset(preset_id)
            config = preset.get("config", {})

            # Strip internal fields before setting
            clean_config = {k: v for k, v in config.items() if not k.startswith("_")}

            self.set_constraints(clean_config)

            # Record usage
            self.preset_manager.record_preset_usage(preset_id)

            # Emit signal
            self.preset_applied.emit(clean_config)

            QMessageBox.information(
                self, "Preset Loaded", f"Loaded preset: {preset.get('name', 'Unknown')}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load preset: {str(e)}")

    def _on_save_preset(self) -> None:
        """Handle save preset button click."""
        if not self.preset_manager:
            return

        # Get preset name from user
        from PySide6.QtWidgets import QInputDialog

        preset_name, ok = QInputDialog.getText(
            self, "Save Preset", "Enter preset name:"
        )

        if not ok or not preset_name:
            return

        try:
            constraints = self.get_constraints()

            # Check if preset already exists
            existing_id = None
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemText(i) == preset_name:
                    existing_id = self.preset_combo.itemData(i)
                    break

            if existing_id:
                # Update existing preset
                self.preset_manager.update_preset(existing_id, config=constraints)
                QMessageBox.information(
                    self, "Preset Updated", f"Updated preset: {preset_name}"
                )
            else:
                # Create new preset as global by default
                preset_id = self.preset_manager.save_preset(
                    name=preset_name, config=constraints, is_global=True, description=""
                )

                # Add to combo box
                self.preset_combo.addItem(preset_name, preset_id)
                self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)

                QMessageBox.information(
                    self, "Preset Saved", f"Saved preset: {preset_name}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save preset: {str(e)}")
