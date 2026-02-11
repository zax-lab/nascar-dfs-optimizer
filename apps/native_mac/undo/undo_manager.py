"""UndoManager - Centralized undo/redo system with per-race and global stacks.

This module provides comprehensive undo/redo functionality using Qt's QUndoStack
with unlimited depth. It supports both per-race undo contexts (isolating changes
to specific races) and a global undo stack for app-level actions.

Pattern: Per-Race + Global Undo Context (Pattern 4 from research)
- global_stack: QUndoStack for app-level actions (tab switches, imports, exports)
- race_stacks: Dict[str, QUndoStack] mapping race_id to per-race stack
- current_race_id: str tracking which race is active

Usage:
    undo_manager = UndoManager()
    undo_manager.set_current_race('race_123')

    # Push a command (scope="race" for race-specific, "global" for app-level)
    undo_manager.push(SetConstraintCommand(model, 'salary_cap', 50000, 55000), scope="race")

    # Undo/redo
    if undo_manager.can_undo():
        undo_manager.undo()
    if undo_manager.can_redo():
        undo_manager.redo()
"""

from typing import Dict, Optional, Any
from PySide6.QtGui import QUndoStack, QUndoCommand, QAction
from PySide6.QtCore import QObject, Signal


class UndoManager(QObject):
    """Manages per-race and global undo stacks with unlimited depth.

    This class provides a centralized undo/redo system that maintains separate
    undo histories for each race and a global history for app-level actions.

    Signals:
        can_undo_changed(bool): Emitted when undo availability changes
        can_redo_changed(bool): Emitted when redo availability changes
        stack_clean_changed(bool): Emitted when clean/dirty state changes

    Attributes:
        global_stack: QUndoStack for app-level actions
        race_stacks: Dict mapping race_id to per-race QUndoStack
        current_race_id: Currently active race ID
    """

    # Signals for UI updates
    can_undo_changed = Signal(bool)
    can_redo_changed = Signal(bool)
    stack_clean_changed = Signal(bool)

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the UndoManager.

        Args:
            parent: Optional parent QObject.
        """
        super().__init__(parent)

        # Global stack for app-level actions (unlimited depth)
        self.global_stack = QUndoStack(self)
        self.global_stack.setUndoLimit(0)  # 0 = unlimited

        # Per-race stacks
        self.race_stacks: Dict[str, QUndoStack] = {}
        self.current_race_id: Optional[str] = None

        # Connect global stack signals
        self.global_stack.canUndoChanged.connect(self.can_undo_changed)
        self.global_stack.canRedoChanged.connect(self.can_redo_changed)
        self.global_stack.cleanChanged.connect(self.stack_clean_changed)

    def set_current_race(self, race_id: str) -> None:
        """Switch to a different race context.

        Creates a new undo stack for the race if it doesn't exist.
        Disconnects old race stack signals and connects new ones.

        Args:
            race_id: The race ID to switch to.
        """
        # Disconnect old race stack signals if exists
        if self.current_race_id and self.current_race_id in self.race_stacks:
            old_stack = self.race_stacks[self.current_race_id]
            try:
                old_stack.canUndoChanged.disconnect(self.can_undo_changed)
                old_stack.canRedoChanged.disconnect(self.can_redo_changed)
                old_stack.cleanChanged.disconnect(self.stack_clean_changed)
            except RuntimeError:
                # Signals may not be connected
                pass

        self.current_race_id = race_id

        # Create new stack if needed
        if race_id not in self.race_stacks:
            stack = QUndoStack(self)
            stack.setUndoLimit(0)  # Unlimited depth
            self.race_stacks[race_id] = stack

        # Connect new race stack signals
        new_stack = self.race_stacks[race_id]
        new_stack.canUndoChanged.connect(self.can_undo_changed)
        new_stack.canRedoChanged.connect(self.can_redo_changed)
        new_stack.cleanChanged.connect(self.stack_clean_changed)

        # Emit current state
        self.can_undo_changed.emit(self.can_undo())
        self.can_redo_changed.emit(self.can_redo())

    def push(self, command: QUndoCommand, scope: str = "auto") -> None:
        """Push a command to the appropriate undo stack(s).

        IMPORTANT: QUndoStack.push() automatically calls redo() on the command,
        so commands should NOT call redo() in their constructors.

        Args:
            command: The QUndoCommand to push.
            scope: Where to push the command:
                - "race": Push to current race stack only
                - "global": Push to global stack only
                - "auto": Push to both (race-specific actions to race,
                         global actions to global)

        Raises:
            ValueError: If no current race is set and scope requires race.
        """
        if scope in ("race", "auto"):
            if self.current_race_id is None:
                if scope == "race":
                    raise ValueError(
                        "No current race set. Call set_current_race() first."
                    )
                # For "auto", skip race if no race set
            else:
                race_stack = self.race_stacks[self.current_race_id]
                if scope == "auto":
                    # For auto scope, we need to clone for global if also going there
                    race_stack.push(command)
                else:
                    race_stack.push(command)
                return  # Don't also push to global for "race" scope

        if scope in ("global", "auto"):
            if scope == "auto" and self.current_race_id is not None:
                # For auto with race context, clone command for global
                # Note: In practice, "auto" with race set means race-only
                # Global actions are explicitly marked as "global"
                pass
            self.global_stack.push(command)

    def can_undo(self, scope: str = "auto") -> bool:
        """Check if undo is available.

        Args:
            scope: Which stack to check ("race", "global", or "auto")
                - "race": Check current race stack only
                - "global": Check global stack only
                - "auto": Check both (returns True if either can undo)

        Returns:
            True if undo is available in the specified scope.
        """
        if scope == "race":
            if self.current_race_id is None:
                return False
            return self.race_stacks[self.current_race_id].canUndo()
        elif scope == "global":
            return self.global_stack.canUndo()
        else:  # auto
            race_can = False
            if self.current_race_id is not None:
                race_can = self.race_stacks[self.current_race_id].canUndo()
            global_can = self.global_stack.canUndo()
            return race_can or global_can

    def can_redo(self, scope: str = "auto") -> bool:
        """Check if redo is available.

        Args:
            scope: Which stack to check ("race", "global", or "auto")

        Returns:
            True if redo is available in the specified scope.
        """
        if scope == "race":
            if self.current_race_id is None:
                return False
            return self.race_stacks[self.current_race_id].canRedo()
        elif scope == "global":
            return self.global_stack.canRedo()
        else:  # auto
            race_can = False
            if self.current_race_id is not None:
                race_can = self.race_stacks[self.current_race_id].canRedo()
            global_can = self.global_stack.canRedo()
            return race_can or global_can

    def undo(self, scope: str = "auto") -> None:
        """Perform undo on the appropriate stack.

        Priority for "auto": Try race first, then global if race can't undo.

        Args:
            scope: Which stack to undo ("race", "global", or "auto")
        """
        if scope == "race":
            if self.current_race_id is not None:
                self.race_stacks[self.current_race_id].undo()
        elif scope == "global":
            self.global_stack.undo()
        else:  # auto
            # Try race first, then global
            if self.current_race_id is not None:
                race_stack = self.race_stacks[self.current_race_id]
                if race_stack.canUndo():
                    race_stack.undo()
                    return
            # Fall back to global
            if self.global_stack.canUndo():
                self.global_stack.undo()

    def redo(self, scope: str = "auto") -> None:
        """Perform redo on the appropriate stack.

        Priority for "auto": Try race first, then global if race can't redo.

        Args:
            scope: Which stack to redo ("race", "global", or "auto")
        """
        if scope == "race":
            if self.current_race_id is not None:
                self.race_stacks[self.current_race_id].redo()
        elif scope == "global":
            self.global_stack.redo()
        else:  # auto
            # Try race first, then global
            if self.current_race_id is not None:
                race_stack = self.race_stacks[self.current_race_id]
                if race_stack.canRedo():
                    race_stack.redo()
                    return
            # Fall back to global
            if self.global_stack.canRedo():
                self.global_stack.redo()

    def get_undo_text(self, scope: str = "auto") -> str:
        """Get the description of the next undoable action.

        Args:
            scope: Which stack to query ("race", "global", or "auto")

        Returns:
            The command text for the next undo action, or empty string.
        """
        if scope == "race":
            if self.current_race_id is None:
                return ""
            stack = self.race_stacks[self.current_race_id]
            return stack.undoText() if stack.canUndo() else ""
        elif scope == "global":
            return self.global_stack.undoText() if self.global_stack.canUndo() else ""
        else:  # auto
            # Prefer race text if available
            if self.current_race_id is not None:
                race_stack = self.race_stacks[self.current_race_id]
                if race_stack.canUndo():
                    return race_stack.undoText()
            return self.global_stack.undoText() if self.global_stack.canUndo() else ""

    def get_redo_text(self, scope: str = "auto") -> str:
        """Get the description of the next redoable action.

        Args:
            scope: Which stack to query ("race", "global", or "auto")

        Returns:
            The command text for the next redo action, or empty string.
        """
        if scope == "race":
            if self.current_race_id is None:
                return ""
            stack = self.race_stacks[self.current_race_id]
            return stack.redoText() if stack.canRedo() else ""
        elif scope == "global":
            return self.global_stack.redoText() if self.global_stack.canRedo() else ""
        else:  # auto
            # Prefer race text if available
            if self.current_race_id is not None:
                race_stack = self.race_stacks[self.current_race_id]
                if race_stack.canRedo():
                    return race_stack.redoText()
            return self.global_stack.redoText() if self.global_stack.canRedo() else ""

    def create_undo_action(self, parent: Any, text: str = "&Undo") -> QAction:
        """Create an undo QAction with standard shortcut.

        The action is automatically connected to the appropriate stack
        and will update its enabled state based on can_undo().

        Args:
            parent: The parent object for the action.
            text: The text for the action (default "&Undo" with U shortcut).

        Returns:
            A configured QAction with QKeySequence.Undo shortcut.
        """
        from PySide6.QtGui import QKeySequence

        action = QAction(text, parent)
        action.setShortcut(QKeySequence.Undo)  # Cmd+Z on Mac
        action.triggered.connect(self.undo)

        # Update enabled state
        def update_enabled(can_undo: bool):
            action.setEnabled(can_undo)

        self.can_undo_changed.connect(update_enabled)
        action.setEnabled(self.can_undo())

        return action

    def create_redo_action(self, parent: Any, text: str = "&Redo") -> QAction:
        """Create a redo QAction with standard shortcut.

        The action is automatically connected to the appropriate stack
        and will update its enabled state based on can_redo().

        Args:
            parent: The parent object for the action.
            text: The text for the action (default "&Redo" with R shortcut).

        Returns:
            A configured QAction with QKeySequence.Redo shortcut.
        """
        from PySide6.QtGui import QKeySequence

        action = QAction(text, parent)
        action.setShortcut(QKeySequence.Redo)  # Cmd+Shift+Z on Mac
        action.triggered.connect(self.redo)

        # Update enabled state
        def update_enabled(can_redo: bool):
            action.setEnabled(can_redo)

        self.can_redo_changed.connect(update_enabled)
        action.setEnabled(self.can_redo())

        return action

    def clear(self, scope: str = "auto") -> None:
        """Clear the undo stack(s).

        Args:
            scope: Which stack(s) to clear ("race", "global", or "auto")
        """
        if scope in ("race", "auto"):
            if self.current_race_id is not None:
                self.race_stacks[self.current_race_id].clear()
        if scope in ("global", "auto"):
            self.global_stack.clear()

    def count(self, scope: str = "auto") -> int:
        """Get the number of commands in the undo stack.

        Args:
            scope: Which stack to count ("race", "global", or "auto")
                - "race": Count current race stack
                - "global": Count global stack
                - "auto": Sum of both

        Returns:
            Number of commands in the specified stack(s).
        """
        if scope == "race":
            if self.current_race_id is None:
                return 0
            return self.race_stacks[self.current_race_id].count()
        elif scope == "global":
            return self.global_stack.count()
        else:  # auto
            total = self.global_stack.count()
            if self.current_race_id is not None:
                total += self.race_stacks[self.current_race_id].count()
            return total

    def set_clean(self, scope: str = "auto") -> None:
        """Mark the current state as clean (saved).

        This is useful for tracking whether there are unsaved changes.

        Args:
            scope: Which stack to mark clean ("race", "global", or "auto")
        """
        if scope in ("race", "auto"):
            if self.current_race_id is not None:
                self.race_stacks[self.current_race_id].setClean()
        if scope in ("global", "auto"):
            self.global_stack.setClean()

    def is_clean(self, scope: str = "auto") -> bool:
        """Check if the stack is in a clean (saved) state.

        Args:
            scope: Which stack to check ("race", "global", or "auto")

        Returns:
            True if the stack is clean (no unsaved changes).
        """
        if scope == "race":
            if self.current_race_id is None:
                return True
            return self.race_stacks[self.current_race_id].isClean()
        elif scope == "global":
            return self.global_stack.isClean()
        else:  # auto - both must be clean
            race_clean = True
            if self.current_race_id is not None:
                race_clean = self.race_stacks[self.current_race_id].isClean()
            return race_clean and self.global_stack.isClean()
