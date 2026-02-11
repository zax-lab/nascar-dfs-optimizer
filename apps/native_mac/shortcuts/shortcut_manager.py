"""ShortcutManager for customizable keyboard shortcuts.

Manages QAction creation with customizable keyboard shortcuts using QKeySequence.
Follows standard macOS conventions (CMD+letter) and persists customizations to QSettings.
"""

from typing import Dict, List, Optional, Callable, Any
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt, QSettings, QObject
from PySide6.QtWidgets import QWidget


class ShortcutManager(QObject):
    """Manages customizable keyboard shortcuts for the application.

    Provides QAction factory with default shortcuts following macOS conventions.
    Supports customization, conflict detection, import/export, and persistence
    via QSettings.

    Attributes:
        actions: Dictionary mapping action_id to QAction instances
        DEFAULT_SHORTCUTS: Class-level default shortcuts dictionary
    """

    # Default shortcuts following standard macOS conventions
    DEFAULT_SHORTCUTS = {
        # File menu
        "new_race": QKeySequence.StandardKey.New,  # Cmd+N
        "open_data": QKeySequence.StandardKey.Open,  # Cmd+O
        "save_lineups": QKeySequence.StandardKey.Save,  # Cmd+S
        # Edit menu
        "undo": QKeySequence.StandardKey.Undo,  # Cmd+Z
        "redo": QKeySequence.StandardKey.Redo,  # Cmd+Shift+Z
        "preferences": QKeySequence.StandardKey.Preferences,  # Cmd+,
        # Optimization menu
        "optimize": QKeySequence(
            "Ctrl+Return"
        ),  # Cmd+Return on Mac (Ctrl+Return interpreted)
        "cancel": QKeySequence.StandardKey.Cancel,  # Cmd+.
        # View menu
        "toggle_split": QKeySequence("Ctrl+\\"),  # Ctrl+Backslash
        "focus_constraints": QKeySequence("Ctrl+1"),  # Focus left pane
        "focus_preview": QKeySequence("Ctrl+2"),  # Focus right pane
        "focus_logs": QKeySequence("Ctrl+3"),  # Focus veto logs
        # Presets
        "apply_preset": QKeySequence("Ctrl+P"),  # Apply constraint preset
        "save_preset": QKeySequence("Ctrl+Shift+P"),  # Save current as preset
        # Navigation
        "next_tab": QKeySequence("Ctrl+Tab"),  # Next tab
        "prev_tab": QKeySequence("Ctrl+Shift+Tab"),  # Previous tab
        "show_jobs": QKeySequence("Ctrl+J"),  # Switch to Jobs tab
        "show_lineups": QKeySequence("Ctrl+L"),  # Switch to Lineups tab
        # Find/Search
        "find": QKeySequence.StandardKey.Find,  # Cmd+F
        # Export
        "export_csv": QKeySequence("Ctrl+E"),  # Export to DraftKings
        # Application
        "quit": QKeySequence.StandardKey.Quit,  # Cmd+Q
        "customize_shortcuts": QKeySequence(),  # No default, accessed via menu
    }

    # Action categories for organization
    CATEGORIES = {
        "File": ["new_race", "open_data", "save_lineups", "export_csv"],
        "Edit": ["undo", "redo", "preferences"],
        "Optimization": ["optimize", "cancel", "apply_preset", "save_preset"],
        "View": ["toggle_split", "focus_constraints", "focus_preview", "focus_logs"],
        "Navigation": ["next_tab", "prev_tab", "show_jobs", "show_lineups", "find"],
        "Application": ["quit", "customize_shortcuts"],
    }

    # Action display names
    ACTION_NAMES = {
        "new_race": "New Race",
        "open_data": "Open Data File",
        "save_lineups": "Save Lineups",
        "export_csv": "Export to DraftKings",
        "undo": "Undo",
        "redo": "Redo",
        "preferences": "Preferences",
        "optimize": "Run Optimization",
        "cancel": "Cancel Operation",
        "toggle_split": "Toggle Split View",
        "focus_constraints": "Focus Constraints Panel",
        "focus_preview": "Focus Preview Panel",
        "focus_logs": "Focus Log Panel",
        "apply_preset": "Apply Constraint Preset",
        "save_preset": "Save Constraint Preset",
        "next_tab": "Next Tab",
        "prev_tab": "Previous Tab",
        "show_jobs": "Show Jobs Tab",
        "show_lineups": "Show Lineups Tab",
        "find": "Find",
        "quit": "Quit Application",
        "customize_shortcuts": "Customize Keyboard Shortcuts",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the ShortcutManager.

        Args:
            parent: Optional parent widget for QAction parent-child relationships.
        """
        super().__init__(parent)
        self.parent_widget = parent
        self.actions: Dict[str, QAction] = {}
        self.custom_shortcuts: Dict[str, QKeySequence] = {}
        self.settings = QSettings("Zax", "NASCAR DFS Optimizer")

        # Load custom shortcuts from settings
        self._load_custom_shortcuts()

    def create_action(
        self,
        action_id: str,
        text: str,
        callback: Callable,
        icon=None,
        parent: Optional[QWidget] = None,
    ) -> QAction:
        """Create a QAction with a customizable shortcut.

        Args:
            action_id: Unique identifier for this action.
            text: Display text for the action (will be shown in menus).
            callback: Function to call when action is triggered.
            icon: Optional icon for the action.
            parent: Optional parent widget (defaults to self.parent_widget).

        Returns:
            The created QAction with shortcut applied.
        """
        parent_widget = parent or self.parent_widget

        # Create action
        if icon:
            action = QAction(icon, text, parent_widget)
        else:
            action = QAction(text, parent_widget)

        # Connect callback
        action.triggered.connect(callback)

        # Apply shortcut (custom or default)
        shortcut = self.get_shortcut(action_id)
        if shortcut and not shortcut.isEmpty():
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ApplicationShortcut)  # Global within app

        # Store action
        self.actions[action_id] = action

        return action

    def set_custom_shortcut(self, action_id: str, key_sequence: QKeySequence) -> None:
        """Update the shortcut for an action.

        Args:
            action_id: The action identifier.
            key_sequence: The new QKeySequence to apply.

        Raises:
            KeyError: If action_id doesn't exist.
        """
        # Update the action if it exists
        if action_id in self.actions:
            action = self.actions[action_id]
            if key_sequence and not key_sequence.isEmpty():
                action.setShortcut(key_sequence)
            else:
                action.setShortcut(QKeySequence())  # Clear shortcut

        # Store custom shortcut
        self.custom_shortcuts[action_id] = key_sequence

        # Persist to settings
        self._save_custom_shortcuts()

    def reset_to_defaults(self) -> None:
        """Reset all shortcuts to their default values."""
        # Clear custom shortcuts
        self.custom_shortcuts.clear()

        # Reset all existing actions to defaults
        for action_id, action in self.actions.items():
            default = self.DEFAULT_SHORTCUTS.get(action_id)
            if default and not default.isEmpty():
                action.setShortcut(default)
            else:
                action.setShortcut(QKeySequence())

        # Clear settings
        self.settings.beginGroup("shortcuts")
        self.settings.remove("")
        self.settings.endGroup()

    def check_conflicts(self, key_sequence: QKeySequence) -> List[str]:
        """Check which actions use a given shortcut.

        Args:
            key_sequence: The shortcut to check for conflicts.

        Returns:
            List of action_ids that use this shortcut.
        """
        if not key_sequence or key_sequence.isEmpty():
            return []

        conflicts = []
        for action_id, action in self.actions.items():
            if action.shortcut() == key_sequence:
                conflicts.append(action_id)

        return conflicts

    def get_shortcut(self, action_id: str) -> QKeySequence:
        """Get the current shortcut for an action.

        Returns the custom shortcut if set, otherwise the default.

        Args:
            action_id: The action identifier.

        Returns:
            The QKeySequence for this action, or empty if none.
        """
        # Return custom shortcut if set
        if action_id in self.custom_shortcuts:
            return self.custom_shortcuts[action_id]

        # Otherwise return default
        return self.DEFAULT_SHORTCUTS.get(action_id, QKeySequence())

    def get_action(self, action_id: str) -> Optional[QAction]:
        """Get an action by its ID.

        Args:
            action_id: The action identifier.

        Returns:
            The QAction if found, None otherwise.
        """
        return self.actions.get(action_id)

    def get_all_actions(self) -> Dict[str, QAction]:
        """Get all registered actions.

        Returns:
            Dictionary mapping action_id to QAction.
        """
        return self.actions.copy()

    def get_category_for_action(self, action_id: str) -> str:
        """Get the category for an action.

        Args:
            action_id: The action identifier.

        Returns:
            Category name (File, Edit, Optimization, View, Navigation, Application).
        """
        for category, actions in self.CATEGORIES.items():
            if action_id in actions:
                return category
        return "Other"

    def get_action_display_name(self, action_id: str) -> str:
        """Get the display name for an action.

        Args:
            action_id: The action identifier.

        Returns:
            Human-readable name for the action.
        """
        return self.ACTION_NAMES.get(action_id, action_id.replace("_", " ").title())

    def export_shortcuts(self, filepath: str) -> None:
        """Export shortcuts to a JSON file.

        Args:
            filepath: Path to the export file.

        Raises:
            IOError: If file cannot be written.
        """
        import json

        data = {"version": "1.0", "shortcuts": {}}

        # Export all actions with their shortcuts
        for action_id in self.DEFAULT_SHORTCUTS.keys():
            shortcut = self.get_shortcut(action_id)
            data["shortcuts"][action_id] = {
                "name": self.get_action_display_name(action_id),
                "category": self.get_category_for_action(action_id),
                "shortcut": shortcut.toString() if not shortcut.isEmpty() else "",
                "is_custom": action_id in self.custom_shortcuts,
            }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def import_shortcuts(self, filepath: str) -> None:
        """Import shortcuts from a JSON file.

        Args:
            filepath: Path to the import file.

        Raises:
            IOError: If file cannot be read.
            ValueError: If file format is invalid.
        """
        import json

        with open(filepath, "r") as f:
            data = json.load(f)

        if "shortcuts" not in data:
            raise ValueError("Invalid shortcuts file: missing 'shortcuts' key")

        # Apply imported shortcuts
        for action_id, shortcut_data in data["shortcuts"].items():
            if action_id in self.DEFAULT_SHORTCUTS:
                shortcut_str = shortcut_data.get("shortcut", "")
                if shortcut_str:
                    self.set_custom_shortcut(action_id, QKeySequence(shortcut_str))
                else:
                    self.set_custom_shortcut(action_id, QKeySequence())

    def _load_custom_shortcuts(self) -> None:
        """Load custom shortcuts from QSettings."""
        self.custom_shortcuts.clear()
        self.settings.beginGroup("shortcuts")

        for key in self.settings.allKeys():
            value = self.settings.value(key)
            if value:
                self.custom_shortcuts[key] = QKeySequence(value)

        self.settings.endGroup()

    def _save_custom_shortcuts(self) -> None:
        """Save custom shortcuts to QSettings."""
        self.settings.beginGroup("shortcuts")

        # Clear existing
        self.settings.remove("")

        # Save current
        for action_id, shortcut in self.custom_shortcuts.items():
            if shortcut and not shortcut.isEmpty():
                self.settings.setValue(action_id, shortcut.toString())

        self.settings.endGroup()
        self.settings.sync()

    def format_shortcut_for_display(self, key_sequence: QKeySequence) -> str:
        """Format a shortcut for display in UI.

        Args:
            key_sequence: The shortcut to format.

        Returns:
            Human-readable string representation.
        """
        if not key_sequence or key_sequence.isEmpty():
            return "None"

        # Get string representation and format for macOS
        text = key_sequence.toString()

        # Replace common sequences with macOS symbols
        replacements = {
            "Ctrl": "⌃",
            "Meta": "⌘",  # Command key on Mac
            "Alt": "⌥",  # Option key on Mac
            "Shift": "⇧",
        }

        for key, symbol in replacements.items():
            text = text.replace(key, symbol)

        return text
