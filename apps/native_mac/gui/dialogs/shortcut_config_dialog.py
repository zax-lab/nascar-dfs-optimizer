"""ShortcutConfigDialog for customizing keyboard shortcuts.

Provides a macOS-style preferences dialog for viewing and customizing
keyboard shortcuts with conflict detection, category grouping, and
import/export functionality.
"""

from typing import Optional, Dict
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QKeySequenceEdit,
    QDialogButtonBox,
    QGroupBox,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QSplitter,
    QWidget,
    QFrame,
)
from PySide6.QtGui import QKeySequence, QColor
from PySide6.QtCore import Qt, QSize

from ...shortcuts.shortcut_manager import ShortcutManager


class ShortcutConfigDialog(QDialog):
    """Dialog for customizing keyboard shortcuts.

    Features:
    - List view of all actions grouped by category
    - Real-time conflict detection when setting shortcuts
    - QKeySequenceEdit for capturing new shortcuts
    - Import/export shortcuts to JSON
    - Reset to defaults

    Attributes:
        shortcut_manager: The ShortcutManager being configured
        selected_action_id: Currently selected action for editing
    """

    def __init__(
        self,
        shortcut_manager: ShortcutManager,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the shortcut configuration dialog.

        Args:
            shortcut_manager: ShortcutManager instance to configure.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.shortcut_manager = shortcut_manager
        self.selected_action_id: Optional[str] = None
        self._pending_shortcuts: Dict[str, QKeySequence] = {}  # Unsaved changes

        self._setup_ui()
        self._populate_list()

        # Set minimum size for readability
        self.setMinimumSize(600, 500)
        self.resize(700, 550)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Keyboard Shortcuts")

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Description
        desc = QLabel(
            "Double-click an action to change its shortcut. "
            "Conflicts will be highlighted in red."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # Category filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        for category in self.shortcut_manager.CATEGORIES.keys():
            self.category_combo.addItem(category)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        filter_layout.addWidget(self.category_combo)

        # Search field
        filter_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter actions...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.search_edit)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Splitter for list and editor
        splitter = QSplitter(Qt.Vertical)

        # Actions list (top)
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.itemClicked.connect(self._on_item_selected)
        self.list_widget.setMinimumHeight(200)

        list_layout.addWidget(self.list_widget)
        splitter.addWidget(list_container)

        # Editor section (bottom)
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # Current selection group
        self.editor_group = QGroupBox("Selected Action")
        editor_form = QVBoxLayout(self.editor_group)

        # Action name label
        self.action_name_label = QLabel("No action selected")
        self.action_name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        editor_form.addWidget(self.action_name_label)

        # Current shortcut display
        shortcut_layout = QHBoxLayout()
        shortcut_layout.addWidget(QLabel("Current shortcut:"))
        self.current_shortcut_label = QLabel("None")
        self.current_shortcut_label.setStyleSheet(
            "font-family: monospace; font-size: 13px;"
        )
        shortcut_layout.addWidget(self.current_shortcut_label)
        shortcut_layout.addStretch()
        editor_form.addLayout(shortcut_layout)

        # Shortcut editor
        editor_form.addWidget(QLabel("Press keys to set new shortcut:"))
        self.shortcut_edit = QKeySequenceEdit()
        self.shortcut_edit.setMinimumHeight(40)
        self.shortcut_edit.setStyleSheet("""
            QKeySequenceEdit {
                font-size: 16px;
                padding: 8px;
                border: 2px solid #ccc;
                border-radius: 4px;
            }
            QKeySequenceEdit:focus {
                border-color: #007AFF;
            }
        """)
        self.shortcut_edit.keySequenceChanged.connect(self._on_shortcut_changed)
        editor_form.addWidget(self.shortcut_edit)

        # Conflict warning
        self.conflict_label = QLabel()
        self.conflict_label.setWordWrap(True)
        self.conflict_label.setStyleSheet("color: #FF3B30; font-size: 12px;")
        self.conflict_label.hide()
        editor_form.addWidget(self.conflict_label)

        # Buttons for selected action
        btn_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear Shortcut")
        self.clear_btn.clicked.connect(self._on_clear_shortcut)
        self.clear_btn.setEnabled(False)
        btn_layout.addWidget(self.clear_btn)

        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self._on_reset_action)
        self.reset_btn.setEnabled(False)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()
        editor_form.addLayout(btn_layout)

        editor_layout.addWidget(self.editor_group)
        splitter.addWidget(editor_container)

        # Set splitter proportions
        splitter.setSizes([300, 200])
        layout.addWidget(splitter, 1)  # Stretch factor

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ddd;")
        layout.addWidget(line)

        # Import/Export buttons
        io_layout = QHBoxLayout()

        self.import_btn = QPushButton("Import...")
        self.import_btn.setToolTip("Import shortcuts from JSON file")
        self.import_btn.clicked.connect(self._on_import)
        io_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export...")
        self.export_btn.setToolTip("Export shortcuts to JSON file")
        self.export_btn.clicked.connect(self._on_export)
        io_layout.addWidget(self.export_btn)

        self.reset_all_btn = QPushButton("Reset All to Defaults")
        self.reset_all_btn.setToolTip("Restore all shortcuts to factory defaults")
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        io_layout.addWidget(self.reset_all_btn)

        io_layout.addStretch()
        layout.addLayout(io_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        layout.addWidget(button_box)

    def _populate_list(self) -> None:
        """Populate the list widget with actions grouped by category."""
        self.list_widget.clear()

        # Get all actions from shortcut manager
        all_actions = list(self.shortcut_manager.DEFAULT_SHORTCUTS.keys())

        # Filter by category if selected
        selected_category = self.category_combo.currentText()
        if selected_category != "All Categories":
            all_actions = [
                aid
                for aid in all_actions
                if self.shortcut_manager.get_category_for_action(aid)
                == selected_category
            ]

        # Filter by search if entered
        search_text = self.search_edit.text().lower()
        if search_text:
            all_actions = [
                aid
                for aid in all_actions
                if search_text
                in self.shortcut_manager.get_action_display_name(aid).lower()
                or search_text in aid.lower()
            ]

        # Group by category
        current_category = None
        for category in self.shortcut_manager.CATEGORIES.keys():
            category_actions = [
                aid
                for aid in all_actions
                if aid in self.shortcut_manager.CATEGORIES[category]
            ]

            if not category_actions:
                continue

            # Category header
            if selected_category == "All Categories":
                header = QListWidgetItem(f"  {category}")
                header.setFlags(Qt.NoItemFlags)  # Not selectable
                header.setBackground(QColor(240, 240, 240))
                header.setForeground(QColor(100, 100, 100))
                font = header.font()
                font.setBold(True)
                header.setFont(font)
                self.list_widget.addItem(header)

            # Actions in this category
            for action_id in category_actions:
                display_name = self.shortcut_manager.get_action_display_name(action_id)
                shortcut = self._get_effective_shortcut(action_id)
                shortcut_text = self.shortcut_manager.format_shortcut_for_display(
                    shortcut
                )

                # Check if modified from default
                is_custom = (
                    action_id in self._pending_shortcuts
                    or action_id in self.shortcut_manager.custom_shortcuts
                )

                item_text = f"{display_name:<35} {shortcut_text}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, action_id)

                if is_custom:
                    item.setForeground(QColor(0, 122, 255))  # Blue for custom
                    item.setToolTip("Custom shortcut (modified from default)")

                self.list_widget.addItem(item)

        # If no items, show message
        if self.list_widget.count() == 0:
            item = QListWidgetItem("No actions match the current filter")
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(QColor(150, 150, 150))
            self.list_widget.addItem(item)

    def _get_effective_shortcut(self, action_id: str) -> QKeySequence:
        """Get the effective shortcut (including pending changes)."""
        if action_id in self._pending_shortcuts:
            return self._pending_shortcuts[action_id]
        return self.shortcut_manager.get_shortcut(action_id)

    def _on_category_changed(self, category: str) -> None:
        """Handle category filter change."""
        self._populate_list()

    def _on_search_changed(self, text: str) -> None:
        """Handle search filter change."""
        self._populate_list()

    def _on_item_selected(self, item: QListWidgetItem) -> None:
        """Handle item selection."""
        action_id = item.data(Qt.UserRole)
        if not action_id:
            return

        self.selected_action_id = action_id
        self._update_editor()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle item double-click - focus the shortcut editor."""
        action_id = item.data(Qt.UserRole)
        if not action_id:
            return

        self.selected_action_id = action_id
        self._update_editor()
        self.shortcut_edit.setFocus()
        self.shortcut_edit.clear()

    def _update_editor(self) -> None:
        """Update the editor section for the selected action."""
        if not self.selected_action_id:
            self.editor_group.setTitle("Selected Action")
            self.action_name_label.setText("No action selected")
            self.current_shortcut_label.setText("None")
            self.shortcut_edit.clear()
            self.clear_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)
            return

        # Update labels
        display_name = self.shortcut_manager.get_action_display_name(
            self.selected_action_id
        )
        category = self.shortcut_manager.get_category_for_action(
            self.selected_action_id
        )

        self.editor_group.setTitle(f"Selected Action - {category}")
        self.action_name_label.setText(display_name)

        # Show current shortcut
        shortcut = self._get_effective_shortcut(self.selected_action_id)
        shortcut_text = self.shortcut_manager.format_shortcut_for_display(shortcut)
        self.current_shortcut_label.setText(shortcut_text)

        # Set in editor
        self.shortcut_edit.setKeySequence(shortcut)

        # Enable buttons
        self.clear_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)

        # Check if it's a custom shortcut
        default = self.shortcut_manager.DEFAULT_SHORTCUTS.get(self.selected_action_id)
        is_custom = (
            self.selected_action_id in self.shortcut_manager.custom_shortcuts
            or self.selected_action_id in self._pending_shortcuts
        )

        if is_custom:
            self.reset_btn.setEnabled(True)
        else:
            self.reset_btn.setEnabled(False)

        # Clear conflict warning
        self.conflict_label.hide()

    def _on_shortcut_changed(self, key_sequence: QKeySequence) -> None:
        """Handle shortcut editor change."""
        if not self.selected_action_id:
            return

        if key_sequence.isEmpty():
            return

        # Check for conflicts
        conflicts = self.shortcut_manager.check_conflicts(key_sequence)

        # Remove self from conflicts
        if self.selected_action_id in conflicts:
            conflicts.remove(self.selected_action_id)

        # Also check against pending changes
        for action_id, pending_shortcut in self._pending_shortcuts.items():
            if (
                action_id != self.selected_action_id
                and pending_shortcut == key_sequence
            ):
                conflicts.append(action_id)

        if conflicts:
            # Show conflict warning
            conflict_names = [
                self.shortcut_manager.get_action_display_name(aid) for aid in conflicts
            ]
            self.conflict_label.setText(
                f"⚠️ Conflicts with: {', '.join(conflict_names)}"
            )
            self.conflict_label.show()
        else:
            self.conflict_label.hide()

        # Store pending change
        self._pending_shortcuts[self.selected_action_id] = QKeySequence(key_sequence)

        # Update list display
        self._update_list_item(self.selected_action_id)

    def _update_list_item(self, action_id: str) -> None:
        """Update the display of a list item."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == action_id:
                display_name = self.shortcut_manager.get_action_display_name(action_id)
                shortcut = self._get_effective_shortcut(action_id)
                shortcut_text = self.shortcut_manager.format_shortcut_for_display(
                    shortcut
                )

                item_text = f"{display_name:<35} {shortcut_text}"
                item.setText(item_text)

                # Mark as custom (blue)
                is_custom = action_id in self._pending_shortcuts
                if is_custom:
                    item.setForeground(QColor(0, 122, 255))
                    item.setToolTip("Custom shortcut (modified from default)")
                break

    def _on_clear_shortcut(self) -> None:
        """Clear the shortcut for the selected action."""
        if not self.selected_action_id:
            return

        self._pending_shortcuts[self.selected_action_id] = QKeySequence()
        self.shortcut_edit.clear()
        self._update_editor()
        self._update_list_item(self.selected_action_id)

    def _on_reset_action(self) -> None:
        """Reset the selected action to its default shortcut."""
        if not self.selected_action_id:
            return

        # Remove from pending if present
        if self.selected_action_id in self._pending_shortcuts:
            del self._pending_shortcuts[self.selected_action_id]

        # Set to default
        default = self.shortcut_manager.DEFAULT_SHORTCUTS.get(
            self.selected_action_id, QKeySequence()
        )
        self._pending_shortcuts[self.selected_action_id] = QKeySequence(default)

        self._update_editor()
        self._update_list_item(self.selected_action_id)

    def _on_import(self) -> None:
        """Import shortcuts from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Shortcuts", "", "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            self.shortcut_manager.import_shortcuts(file_path)
            self._pending_shortcuts.clear()
            self._populate_list()

            QMessageBox.information(
                self, "Import Successful", f"Shortcuts imported from:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Import Error", f"Failed to import shortcuts:\n\n{str(e)}"
            )

    def _on_export(self) -> None:
        """Export shortcuts to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Shortcuts",
            "nascar_shortcuts.json",
            "JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        try:
            self.shortcut_manager.export_shortcuts(file_path)
            QMessageBox.information(
                self, "Export Successful", f"Shortcuts exported to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error", f"Failed to export shortcuts:\n\n{str(e)}"
            )

    def _on_reset_all(self) -> None:
        """Reset all shortcuts to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset All Shortcuts",
            "Are you sure you want to reset all shortcuts to factory defaults?\n\n"
            "This will discard any custom shortcuts.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.shortcut_manager.reset_to_defaults()
            self._pending_shortcuts.clear()
            self._populate_list()
            self._update_editor()

    def _apply_changes(self) -> None:
        """Apply all pending shortcut changes."""
        for action_id, shortcut in self._pending_shortcuts.items():
            self.shortcut_manager.set_custom_shortcut(action_id, shortcut)
        self._pending_shortcuts.clear()

    def _on_apply(self) -> None:
        """Handle Apply button."""
        self._apply_changes()
        self._populate_list()
        self._update_editor()

    def _on_ok(self) -> None:
        """Handle OK button."""
        self._apply_changes()
        self.accept()
