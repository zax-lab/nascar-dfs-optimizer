"""QUndoCommand subclasses for all undoable actions.

This module provides command classes for every undoable action in the app:
- SetConstraintCommand: For constraint panel changes
- LoadPresetCommand: For loading constraint presets (macro command)
- EditLineupCommand: For lineup edits (add/remove/replace driver)
- SwitchTabCommand: For tab navigation (global scope)
- ImportDataCommand: For CSV imports (global scope)
- SetLineupCountCommand: For changing number of lineups to generate

Each command follows the Qt command pattern:
- Stores minimal state (IDs, values) not full objects
- Implements undo() and redo() methods
- Calls super().__init__(descriptive_text) for menu display
- Some implement id() and mergeWith() for high-frequency actions
"""

from enum import IntEnum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTabWidget, QSpinBox


class COMMAND_IDS(IntEnum):
    """Unique command IDs for merge identification."""

    SET_CONSTRAINT = 1001
    SET_LINEUP_COUNT = 1002
    ADJUST_SLIDER = 1003
    EDIT_LINEUP = 2001
    LOAD_PRESET = 3001
    SWITCH_TAB = 4001
    IMPORT_DATA = 5001


class SetConstraintCommand(QUndoCommand):
    """Command for constraint panel changes.

    Supports merging consecutive changes to the same constraint
    to avoid cluttering the undo stack with rapid adjustments.

    Attributes:
        model: The constraint model to modify
        constraint_id: Identifier for the constraint (e.g., 'salary_cap')
        old_value: Previous value of the constraint
        new_value: New value of the constraint
    """

    def __init__(
        self,
        model: Any,
        constraint_id: str,
        old_value: Any,
        new_value: Any,
        parent: Optional[QUndoCommand] = None,
    ):
        """Initialize the constraint change command.

        Args:
            model: The constraint model to modify
            constraint_id: Identifier for the constraint
            old_value: Previous value
            new_value: New value
            parent: Optional parent command for macros
        """
        super().__init__(f"Set {constraint_id}", parent)
        self.model = model
        self.constraint_id = constraint_id
        self.old_value = old_value
        self.new_value = new_value

    def undo(self) -> None:
        """Restore the constraint to its old value."""
        if self.model is not None:
            self.model.set_constraint(self.constraint_id, self.old_value)

    def redo(self) -> None:
        """Apply the constraint's new value."""
        if self.model is not None:
            self.model.set_constraint(self.constraint_id, self.new_value)

    def id(self) -> int:
        """Return unique ID for merge identification."""
        return COMMAND_IDS.SET_CONSTRAINT

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Merge with another SetConstraintCommand if same constraint.

        This allows rapid slider/spinbox changes to be merged into
        a single undo action.

        Args:
            other: The command to potentially merge with

        Returns:
            True if merged, False otherwise
        """
        if other.id() != self.id():
            return False
        if not isinstance(other, SetConstraintCommand):
            return False
        if other.constraint_id != self.constraint_id:
            return False
        # Merge: keep our old_value, adopt other's new_value
        self.new_value = other.new_value
        return True


class LoadPresetCommand(QUndoCommand):
    """Command for loading constraint presets (macro command).

    This is a composite command that restores all constraints to their
    previous state on undo, making preset changes atomic operations.

    Attributes:
        model: The constraint model to modify
        old_config: Dict of all constraint values before preset load
        new_config: Dict of all constraint values from the preset
    """

    def __init__(
        self,
        model: Any,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        preset_name: str = "Preset",
        parent: Optional[QUndoCommand] = None,
    ):
        """Initialize the preset load command.

        Args:
            model: The constraint model to modify
            old_config: Complete constraint configuration before load
            new_config: Complete constraint configuration from preset
            preset_name: Name of the preset for display
            parent: Optional parent command for macros
        """
        super().__init__(f"Load {preset_name}", parent)
        self.model = model
        self.old_config = old_config.copy()
        self.new_config = new_config.copy()
        self.preset_name = preset_name

    def undo(self) -> None:
        """Restore all constraints to their previous state."""
        if self.model is not None:
            for key, value in self.old_config.items():
                self.model.set_constraint(key, value)

    def redo(self) -> None:
        """Apply all constraints from the preset."""
        if self.model is not None:
            for key, value in self.new_config.items():
                self.model.set_constraint(key, value)


class EditLineupCommand(QUndoCommand):
    """Command for lineup edits (add/remove/replace driver).

    Attributes:
        lineup_model: The lineup model to modify
        lineup_index: Index of the lineup being edited (or -1 for new)
        old_lineup: Previous lineup state
        new_lineup: New lineup state
    """

    def __init__(
        self,
        lineup_model: Any,
        lineup_index: int,
        old_lineup: List[Dict[str, Any]],
        new_lineup: List[Dict[str, Any]],
        action_description: str = "Edit Lineup",
        parent: Optional[QUndoCommand] = None,
    ):
        """Initialize the lineup edit command.

        Args:
            lineup_model: The lineup model to modify
            lineup_index: Index of lineup being edited (-1 for append)
            old_lineup: Previous lineup state (list of drivers)
            new_lineup: New lineup state (list of drivers)
            action_description: Description for undo menu (e.g., "Add Driver")
            parent: Optional parent command for macros
        """
        super().__init__(action_description, parent)
        self.lineup_model = lineup_model
        self.lineup_index = lineup_index
        self.old_lineup = old_lineup.copy()
        self.new_lineup = new_lineup.copy()

    def undo(self) -> None:
        """Restore the lineup to its previous state."""
        if self.lineup_model is not None:
            if self.lineup_index >= 0:
                self.lineup_model.update_lineup(self.lineup_index, self.old_lineup)
            else:
                # Was an add, now remove
                self.lineup_model.remove_lineup(
                    len(self.lineup_model.get_lineups()) - 1
                )

    def redo(self) -> None:
        """Apply the lineup changes."""
        if self.lineup_model is not None:
            if self.lineup_index >= 0:
                self.lineup_model.update_lineup(self.lineup_index, self.new_lineup)
            else:
                # Was a remove, now add back
                self.lineup_model.add_lineup(self.new_lineup)


class SwitchTabCommand(QUndoCommand):
    """Command for tab navigation (global scope).

    This command tracks tab switches so users can undo/redo their
    navigation history, which is useful for quickly returning to
    previous views.

    Attributes:
        tab_widget: The QTabWidget to control
        old_index: Previous tab index
        new_index: New tab index
    """

    def __init__(
        self,
        tab_widget: Any,  # QTabWidget
        old_index: int,
        new_index: int,
        parent: Optional[QUndoCommand] = None,
    ):
        """Initialize the tab switch command.

        Args:
            tab_widget: The QTabWidget to control
            old_index: Previous tab index
            new_index: New tab index
            parent: Optional parent command for macros
        """
        super().__init__("Switch Tab", parent)
        self.tab_widget = tab_widget
        self.old_index = old_index
        self.new_index = new_index

    def undo(self) -> None:
        """Switch back to the previous tab."""
        if self.tab_widget is not None:
            self.tab_widget.setCurrentIndex(self.old_index)

    def redo(self) -> None:
        """Switch to the new tab."""
        if self.tab_widget is not None:
            self.tab_widget.setCurrentIndex(self.new_index)

    def id(self) -> int:
        """Return unique ID for merge identification."""
        return COMMAND_IDS.SWITCH_TAB

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Merge consecutive tab switches.

        If user rapidly switches tabs, only keep the start and end.

        Args:
            other: The command to potentially merge with

        Returns:
            True if merged, False otherwise
        """
        if other.id() != self.id():
            return False
        if not isinstance(other, SwitchTabCommand):
            return False
        if other.tab_widget != self.tab_widget:
            return False
        # Merge: keep our old_index, adopt other's new_index
        self.new_index = other.new_index
        return True


class ImportDataCommand(QUndoCommand):
    """Command for CSV imports (global scope).

    This command stores the previous data state so imports can be undone,
    restoring the previous dataset.

    Attributes:
        data_controller: The data controller managing the dataset
        old_data: Previous dataset state
        new_data: New dataset from import
        import_type: Type of import ("drivers", "lineups", etc.)
    """

    def __init__(
        self,
        data_controller: Any,
        old_data: Optional[List[Dict[str, Any]]],
        new_data: List[Dict[str, Any]],
        import_type: str = "Data",
        parent: Optional[QUndoCommand] = None,
    ):
        """Initialize the data import command.

        Args:
            data_controller: The data controller to modify
            old_data: Previous dataset state (None if no previous data)
            new_data: New dataset from import
            import_type: Type of import for display (e.g., "Import Drivers")
            parent: Optional parent command for macros
        """
        super().__init__(f"Import {import_type}", parent)
        self.data_controller = data_controller
        self.old_data = old_data.copy() if old_data is not None else None
        self.new_data = new_data.copy()
        self.import_type = import_type

    def undo(self) -> None:
        """Restore the previous dataset."""
        if self.data_controller is not None:
            if self.old_data is not None:
                self.data_controller.set_data(self.old_data)
            else:
                self.data_controller.clear_data()

    def redo(self) -> None:
        """Apply the imported dataset."""
        if self.data_controller is not None:
            self.data_controller.set_data(self.new_data)


class SetLineupCountCommand(QUndoCommand):
    """Command for changing number of lineups to generate.

    Supports merging consecutive changes to avoid cluttering the
    undo stack with rapid spinbox adjustments.

    Attributes:
        spin_box: The QSpinBox controlling lineup count
        old_value: Previous lineup count value
        new_value: New lineup count value
        callback: Optional callback to trigger on change
    """

    def __init__(
        self,
        spin_box: Any,  # QSpinBox
        old_value: int,
        new_value: int,
        callback: Optional[callable] = None,
        parent: Optional[QUndoCommand] = None,
    ):
        """Initialize the lineup count change command.

        Args:
            spin_box: The QSpinBox controlling lineup count
            old_value: Previous value
            new_value: New value
            callback: Optional callback to trigger on change
            parent: Optional parent command for macros
        """
        super().__init__(f"Set Lineup Count to {new_value}", parent)
        self.spin_box = spin_box
        self.old_value = old_value
        self.new_value = new_value
        self.callback = callback

    def undo(self) -> None:
        """Restore the previous lineup count."""
        if self.spin_box is not None:
            self.spin_box.setValue(self.old_value)
        if self.callback:
            self.callback(self.old_value)

    def redo(self) -> None:
        """Apply the new lineup count."""
        if self.spin_box is not None:
            self.spin_box.setValue(self.new_value)
        if self.callback:
            self.callback(self.new_value)

    def id(self) -> int:
        """Return unique ID for merge identification."""
        return COMMAND_IDS.SET_LINEUP_COUNT

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Merge with another SetLineupCountCommand.

        Rapid spinbox adjustments merge into a single undo.

        Args:
            other: The command to potentially merge with

        Returns:
            True if merged, False otherwise
        """
        if other.id() != self.id():
            return False
        if not isinstance(other, SetLineupCountCommand):
            return False
        if other.spin_box != self.spin_box:
            return False
        # Merge: keep our old_value, adopt other's new_value
        self.new_value = other.new_value
        self.setText(f"Set Lineup Count to {self.new_value}")
        return True


class AdjustSliderCommand(QUndoCommand):
    """Command for slider adjustments with merge support.

    Generic slider/spinbox adjustment command that merges consecutive
    changes to avoid cluttering the undo stack.

    Attributes:
        model: The model to modify
        slider_id: Identifier for the slider/setting
        old_value: Previous value
        new_value: New value
        setter_func: Function to call to set the value
    """

    def __init__(
        self,
        model: Any,
        slider_id: str,
        old_value: float,
        new_value: float,
        setter_func: Optional[callable] = None,
        parent: Optional[QUndoCommand] = None,
    ):
        """Initialize the slider adjustment command.

        Args:
            model: The model to modify
            slider_id: Identifier for the slider
            old_value: Previous value
            new_value: New value
            setter_func: Optional setter function (model.set_slider_value by default)
            parent: Optional parent command for macros
        """
        super().__init__(f"Adjust {slider_id}", parent)
        self.model = model
        self.slider_id = slider_id
        self.old_value = old_value
        self.new_value = new_value
        self.setter_func = setter_func

    def undo(self) -> None:
        """Restore the previous value."""
        if self.model is not None:
            if self.setter_func:
                self.setter_func(self.slider_id, self.old_value)
            else:
                self.model.set_slider_value(self.slider_id, self.old_value)

    def redo(self) -> None:
        """Apply the new value."""
        if self.model is not None:
            if self.setter_func:
                self.setter_func(self.slider_id, self.new_value)
            else:
                self.model.set_slider_value(self.slider_id, self.new_value)

    def id(self) -> int:
        """Return unique ID for merge identification."""
        return COMMAND_IDS.ADJUST_SLIDER

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Merge with another AdjustSliderCommand if same slider.

        Args:
            other: The command to potentially merge with

        Returns:
            True if merged, False otherwise
        """
        if other.id() != self.id():
            return False
        if not isinstance(other, AdjustSliderCommand):
            return False
        if other.slider_id != self.slider_id:
            return False
        # Merge: keep our old_value, adopt other's new_value
        self.new_value = other.new_value
        return True


class CompositeCommand(QUndoCommand):
    """Composite command for grouping multiple actions.

    This is useful for creating macro commands where multiple
    changes should be undone/redone as a single unit.

    Example:
        composite = CompositeCommand("Update Race Settings")
        composite.add_command(SetConstraintCommand(model, 'salary_cap', 50000, 55000))
        composite.add_command(SetConstraintCommand(model, 'max_ownership', 50, 60))
        undo_manager.push(composite)
    """

    def __init__(self, description: str, parent: Optional[QUndoCommand] = None):
        """Initialize the composite command.

        Args:
            description: Description for undo menu
            parent: Optional parent command
        """
        super().__init__(description, parent)
        self.commands: List[QUndoCommand] = []

    def add_command(self, command: QUndoCommand) -> None:
        """Add a child command to this composite.

        Args:
            command: The command to add
        """
        self.commands.append(command)

    def undo(self) -> None:
        """Undo all child commands in reverse order."""
        for command in reversed(self.commands):
            command.undo()

    def redo(self) -> None:
        """Redo all child commands in order."""
        for command in self.commands:
            command.redo()


__all__ = [
    "COMMAND_IDS",
    "SetConstraintCommand",
    "LoadPresetCommand",
    "EditLineupCommand",
    "SwitchTabCommand",
    "ImportDataCommand",
    "SetLineupCountCommand",
    "AdjustSliderCommand",
    "CompositeCommand",
]
