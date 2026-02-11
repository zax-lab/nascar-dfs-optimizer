# Phase 8: Workflow Accelerators - Research

**Researched:** 2026-01-30
**Domain:** PySide6/Qt6 GUI Development
**Confidence:** HIGH

## Summary

This research covers Qt6/PySide6 implementations for power-user workflow features: split-pane layouts, undo/redo systems, keyboard shortcuts, constraint presets, and log viewers. Qt provides comprehensive built-in support for all these features — the key is selecting the right classes and following established patterns rather than building custom solutions.

**Primary recommendation:** Use QSplitter for split-pane (not QDockWidget), QUndoStack in QtGui for unlimited undo, QAction/QKeySequence for keyboard shortcuts, and SQLite JSON columns for preset storage. Implement debouncing with QTimer.singleShot restart pattern.

---

## Standard Stack

### Core Qt Classes for This Phase

| Class | Module | Purpose | Why Standard |
|-------|--------|---------|--------------|
| **QSplitter** | QtWidgets | Split-pane layouts with draggable handles | Native Qt support, state persistence, nested layouts |
| **QUndoStack** | QtGui | Undo/redo command management | Industry standard, unlimited depth support, macro commands |
| **QUndoCommand** | QtGui | Base class for undoable actions | Clean command pattern implementation |
| **QAction** | QtGui | Actions with shortcuts, menus, toolbars | Unified action system across UI elements |
| **QKeySequence** | QtGui | Platform-aware keyboard shortcuts | Automatic macOS Cmd vs Linux/Windows Ctrl mapping |
| **QTimer** | QtCore | Debounced execution, delayed operations | Single-shot and repeating timer support |
| **QSettings** | QtCore | User preferences storage | Cross-platform, automatic format handling |
| **QTableView** | QtWidgets | Tabular data display (veto logs) | Model/View architecture, efficient for large datasets |
| **QSortFilterProxyModel** | QtCore | Runtime filtering and sorting | Dynamic updates, regex support, column-specific filtering |

### Supporting Classes

| Class | Module | Purpose | When to Use |
|-------|--------|---------|-------------|
| **QSplitterHandle** | QtWidgets | Custom splitter appearance | When default handle styling insufficient |
| **QUndoView** | QtWidgets | Visual undo stack (optional) | If adding undo history sidebar |
| **QShortcut** | QtGui | Global shortcuts without menus | For shortcuts not tied to QAction |
| **QStandardItemModel** | QtGui | Simple table model for logs | When custom model overhead unnecessary |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| QSplitter | QDockWidget | QDockWidget supports floating/detaching but adds complexity; QSplitter simpler for fixed workspace |
| QUndoStack | Custom stack | QUndoStack has macro support, clean integration; custom loses Qt ecosystem benefits |
| QSettings | SQLite for prefs | QSettings handles OS-specific locations; SQLite better for structured/queryable data |
| QTableView | QListView | Table better for multi-column veto logs with filtering; List simpler but less capable |

---

## Architecture Patterns

### Pattern 1: Nested QSplitter Layout (iTerm/VSCode Style)

**What:** Create arbitrarily nested horizontal and vertical splits
**When to use:** Complex workspace with multiple resizable panes
**Structure:**

```
MainWindow
└── central_splitter (Horizontal)
    ├── left_container (Widget)
    │   └── constraints_view
    └── right_splitter (Vertical)  
        ├── top_pane (lineup_preview)
        └── bottom_pane (veto_logs)
```

**Example:**
```python
# Source: Qt docs + research compilation
from PySide6.QtWidgets import QSplitter, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

# Create nested splitters for flexible layout
main_splitter = QSplitter(Qt.Horizontal)

# Left side: constraints panel
left_widget = ConstraintsWidget()
main_splitter.addWidget(left_widget)

# Right side: vertical splitter for preview + logs
right_splitter = QSplitter(Qt.Vertical)
preview_widget = LineupPreviewWidget()
log_widget = VetoLogWidget()
right_splitter.addWidget(preview_widget)
right_splitter.addWidget(log_widget)

main_splitter.addWidget(right_splitter)

# Set initial sizes (percentages roughly)
main_splitter.setSizes([400, 600])
right_splitter.setSizes([500, 200])

# Persist state
settings = QSettings("MyApp", "NascarOptimizer")
splitter_state = settings.value("main_splitter_state")
if splitter_state:
    main_splitter.restoreState(splitter_state)

# Save on change
main_splitter.splitterMoved.connect(
    lambda: settings.setValue("main_splitter_state", main_splitter.saveState())
)
```

### Pattern 2: Command Pattern for Undo/Redo

**What:** Each user action becomes a QUndoCommand subclass
**When to use:** Any mutable state that should be undoable
**Key insight:** QUndoStack.push() automatically calls redo() — design commands accordingly

**Command Structure:**
```python
# Source: Qt documentation + verified examples
from PySide6.QtGui import QUndoCommand, QUndoStack

class SetConstraintCommand(QUndoCommand):
    def __init__(self, model, constraint_id, old_value, new_value, parent=None):
        super().__init__(f"Set {constraint_id}", parent)
        self.model = model
        self.constraint_id = constraint_id
        self.old_value = old_value
        self.new_value = new_value
    
    def undo(self):
        self.model.set_constraint(self.constraint_id, self.old_value)
    
    def redo(self):
        self.model.set_constraint(self.constraint_id, self.new_value)

# Usage in widget
class ConstraintWidget(QWidget):
    def __init__(self, undo_stack: QUndoStack):
        super().__init__()
        self.undo_stack = undo_stack
        
    def on_constraint_changed(self, constraint_id, new_value):
        old_value = self.model.get_constraint(constraint_id)
        if old_value != new_value:
            command = SetConstraintCommand(
                self.model, constraint_id, old_value, new_value
            )
            self.undo_stack.push(command)  # Automatically executes redo()
```

### Pattern 3: Unlimited Undo Stack

**What:** Configure QUndoStack for infinite depth
**When to use:** Per requirements "unlimited (infinite)" undo
**Implementation:**

```python
# Source: Qt documentation verification
self.undo_stack = QUndoStack(self)
self.undo_stack.setUndoLimit(0)  # 0 = unlimited

# macOS standard shortcuts
undo_action = self.undo_stack.createUndoAction(self, "&Undo")
undo_action.setShortcut(QKeySequence.Undo)  # Cmd+Z on Mac
redo_action = self.undo_stack.createRedoAction(self, "&Redo")
redo_action.setShortcut(QKeySequence.Redo)  # Cmd+Shift+Z on Mac

# Add to menu (shortcuts work even without menu visible)
edit_menu.addAction(undo_action)
edit_menu.addAction(redo_action)
```

### Pattern 4: Per-Race + Global Undo Context

**What:** Maintain separate undo stacks per race + global stack
**When to use:** Requirements specify "both per-race undo context AND global"
**Approach:**

```python
class UndoManager(QObject):
    """Manages per-race and global undo stacks"""
    
    def __init__(self):
        super().__init__()
        self.global_stack = QUndoStack()
        self.global_stack.setUndoLimit(0)
        self.race_stacks = {}  # race_id -> QUndoStack
        self.current_race_id = None
    
    def set_current_race(self, race_id):
        self.current_race_id = race_id
        if race_id not in self.race_stacks:
            stack = QUndoStack()
            stack.setUndoLimit(0)
            self.race_stacks[race_id] = stack
    
    def push(self, command, scope="auto"):
        """
        scope: "race" = current race only, 
               "global" = global stack only,
               "auto" = both (race-specific actions go to race, 
                             global actions go to global)
        """
        if scope in ("race", "auto") and self.current_race_id:
            self.race_stacks[self.current_race_id].push(command)
        if scope in ("global", "auto"):
            self.global_stack.push(command.clone() if scope == "auto" else command)
```

### Pattern 5: Debounced Constraint Updates

**What:** Delay optimization trigger until user stops typing/changing
**When to use:** Real-time optimization with configurable debounce
**Implementation:**

```python
# Source: Qt QTimer documentation patterns
from PySide6.QtCore import QTimer

class OptimizerWidget(QWidget):
    def __init__(self, job_manager):
        super().__init__()
        self.job_manager = job_manager
        
        # Debounce timer - restarted on each change
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.trigger_optimization)
        
        self.debounce_ms = 300  # Configurable default
        self.real_time_mode = False  # Toggle in settings
    
    def on_constraint_changed(self):
        if self.real_time_mode:
            self.trigger_optimization()
        else:
            self.debounce_timer.stop()
            self.debounce_timer.start(self.debounce_ms)
    
    def trigger_optimization(self):
        self.job_manager.submit_optimization_job(self.get_constraints())
```

### Pattern 6: Constraint Preset Storage (SQLite + JSON)

**What:** Store constraint configurations as JSON in SQLite
**When to use:** Presets need querying, user management, persistence
**Schema:**

```sql
-- Source: SQLite JSON best practices
CREATE TABLE constraint_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    is_global BOOLEAN DEFAULT 0,  -- 1 = available everywhere
    race_type TEXT,               -- NULL = global, else specific race type
    track_name TEXT,              -- NULL = all tracks of race_type
    config_json TEXT NOT NULL,    -- SQLite JSON storage
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 0
);

CREATE TABLE recent_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_id INTEGER REFERENCES constraint_presets(id),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_presets_global ON constraint_presets(is_global, race_type);
CREATE INDEX idx_presets_track ON constraint_presets(track_name);
```

**Python Implementation:**
```python
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

class PresetManager:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def save_preset(self, name: str, config: Dict, 
                    is_global: bool = False,
                    race_type: Optional[str] = None,
                    track_name: Optional[str] = None) -> int:
        """Save a new preset, return preset_id"""
        cursor = self.conn.execute(
            """INSERT INTO constraint_presets 
               (name, config_json, is_global, race_type, track_name)
               VALUES (?, ?, ?, ?, ?)""",
            (name, json.dumps(config), is_global, race_type, track_name)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def load_preset(self, preset_id: int) -> Dict:
        """Load preset by ID"""
        row = self.conn.execute(
            "SELECT config_json FROM constraint_presets WHERE id = ?",
            (preset_id,)
        ).fetchone()
        if row:
            return json.loads(row['config_json'])
        raise KeyError(f"Preset {preset_id} not found")
    
    def get_presets_for_race(self, race_type: str, track_name: str) -> List[Dict]:
        """Get applicable presets: global + race-specific + track-specific"""
        rows = self.conn.execute(
            """SELECT * FROM constraint_presets 
               WHERE is_global = 1 
                  OR (race_type = ? AND track_name IS NULL)
                  OR (race_type = ? AND track_name = ?)
               ORDER BY is_global DESC, name""",
            (race_type, race_type, track_name)
        ).fetchall()
        return [dict(row) for row in rows]
    
    def export_preset_to_json(self, preset_id: int, filepath: str):
        """Export single preset to JSON file for sharing"""
        row = self.conn.execute(
            """SELECT name, description, config_json, 
                      race_type, track_name
               FROM constraint_presets WHERE id = ?""",
            (preset_id,)
        ).fetchone()
        if row:
            export_data = {
                'name': row['name'],
                'description': row['description'],
                'race_type': row['race_type'],
                'track_name': row['track_name'],
                'config': json.loads(row['config_json']),
                'exported_at': datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
    
    def import_preset_from_json(self, filepath: str) -> int:
        """Import preset from JSON file, return new preset_id"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return self.save_preset(
            name=data['name'],
            config=data['config'],
            race_type=data.get('race_type'),
            track_name=data.get('track_name')
        )
```

### Pattern 7: Keyboard Shortcut Management

**What:** Comprehensive QAction-based shortcuts with customization
**When to use:** Full keyboard-driven workflow
**Implementation:**

```python
# Source: Qt documentation + Python GUIs tutorial
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import QSettings

class ShortcutManager:
    """Manages customizable keyboard shortcuts"""
    
    DEFAULT_SHORTCUTS = {
        'new_lineup': QKeySequence.New,
        'open_lineup': QKeySequence.Open,
        'save_lineup': QKeySequence.Save,
        'undo': QKeySequence.Undo,           # Cmd+Z on Mac
        'redo': QKeySequence.Redo,           # Cmd+Shift+Z on Mac
        'optimize': QKeySequence("Ctrl+Return"),  # Cmd+Return on Mac
        'toggle_split': QKeySequence("Ctrl+\\"),
        'focus_constraints': QKeySequence("Ctrl+1"),
        'focus_preview': QKeySequence("Ctrl+2"),
        'focus_logs': QKeySequence("Ctrl+3"),
        'apply_preset': QKeySequence("Ctrl+P"),
        'save_preset': QKeySequence("Ctrl+Shift+P"),
    }
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.actions = {}
        self.settings = QSettings("MyApp", "NascarOptimizer")
        self._load_custom_shortcuts()
    
    def create_action(self, action_id: str, text: str, 
                      callback, icon=None) -> QAction:
        """Create action with customizable shortcut"""
        action = QAction(icon, text, self.parent) if icon else QAction(text, self.parent)
        action.triggered.connect(callback)
        
        # Apply shortcut (custom or default)
        shortcut = self.custom_shortcuts.get(action_id, self.DEFAULT_SHORTCUTS.get(action_id))
        if shortcut:
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ApplicationShortcut)  # Global within app
        
        self.actions[action_id] = action
        return action
    
    def _load_custom_shortcuts(self):
        """Load user-customized shortcuts from QSettings"""
        self.custom_shortcuts = {}
        self.settings.beginGroup("shortcuts")
        for key in self.settings.allKeys():
            self.custom_shortcuts[key] = QKeySequence(self.settings.value(key))
        self.settings.endGroup()
    
    def set_custom_shortcut(self, action_id: str, key_sequence: QKeySequence):
        """Update shortcut for an action"""
        if action_id in self.actions:
            self.actions[action_id].setShortcut(key_sequence)
        self.custom_shortcuts[action_id] = key_sequence
        
        # Persist
        self.settings.beginGroup("shortcuts")
        self.settings.setValue(action_id, key_sequence.toString())
        self.settings.endGroup()
    
    def check_conflicts(self, key_sequence: QKeySequence) -> List[str]:
        """Return list of action_ids that use this shortcut"""
        conflicts = []
        for action_id, action in self.actions.items():
            if action.shortcut() == key_sequence:
                conflicts.append(action_id)
        return conflicts
```

### Pattern 8: Filterable Veto Log Viewer

**What:** Table view with runtime filtering by rule type, driver, severity
**When to use:** Post-hoc veto log analysis
**Implementation:**

```python
# Source: Qt Model/View documentation + filtering examples
from PySide6.QtWidgets import QTableView, QLineEdit, QComboBox
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

class VetoLogViewer(QWidget):
    def __init__(self):
        super().__init__()
        
        # Source model
        self.source_model = QStandardItemModel()
        self.source_model.setHorizontalHeaderLabels(
            ['Time', 'Rule', 'Driver', 'Severity', 'Reason', 'Lineup Context']
        )
        
        # Proxy model for filtering
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setDynamicSortFilter(True)  # Update on source changes
        
        # View
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        
        # Filter controls
        self.rule_filter = QComboBox()
        self.rule_filter.addItem("All Rules")
        self.rule_filter.currentTextChanged.connect(self.apply_filters)
        
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "Info", "Warning", "Error", "Fatal"])
        self.severity_filter.currentIndexChanged.connect(self.apply_filters)
        
        self.driver_filter = QLineEdit()
        self.driver_filter.setPlaceholderText("Filter by driver...")
        self.driver_filter.textChanged.connect(self.apply_filters)
        
        self.text_search = QLineEdit()
        self.text_search.setPlaceholderText("Search in reasons...")
        self.text_search.textChanged.connect(self.apply_filters)
    
    def add_veto_entry(self, timestamp, rule_name, driver, severity, reason, lineup_context):
        """Add entry to log"""
        row = [
            QStandardItem(timestamp),
            QStandardItem(rule_name),
            QStandardItem(driver),
            QStandardItem(severity),
            QStandardItem(reason),
            QStandardItem(lineup_context)
        ]
        # Color-code by severity
        severity_colors = {
            'Fatal': QColor(255, 200, 200),
            'Error': QColor(255, 220, 180),
            'Warning': QColor(255, 255, 180),
            'Info': QColor(200, 255, 200)
        }
        if severity in severity_colors:
            for item in row:
                item.setBackground(severity_colors[severity])
        
        self.source_model.appendRow(row)
    
    def apply_filters(self):
        """Apply all active filters to proxy model"""
        # Column 1 = Rule
        if self.rule_filter.currentIndex() > 0:
            self.proxy_model.setFilterKeyColumn(1)
            self.proxy_model.setFilterFixedString(self.rule_filter.currentText())
        else:
            # Multi-column text search
            self.proxy_model.setFilterKeyColumn(-1)  # All columns
            self.proxy_model.setFilterFixedString(self.text_search.text())
        
        # Could extend with custom filter accepting multiple criteria
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Draggable split panes | Custom mouse handling | QSplitter | Built-in handle dragging, cursor changes, state persistence, nesting support |
| Undo/redo stack | List + index tracking | QUndoStack | Command merging, macros, clean/dirty state, Qt integration |
| Keyboard shortcuts | Key event filtering | QAction + QKeySequence | Automatic platform mapping, menu integration, shortcut context handling |
| Debounce logic | Manual timer management | QTimer restart pattern | Clean, race-condition-free, Qt signal/slot native |
| Settings persistence | File I/O code | QSettings | OS-specific locations, registry/plist handling, automatic typing |
| Table filtering | Manual row hiding | QSortFilterProxyModel | Efficient, dynamic updates, regex support, sort+filter combo |
| JSON serialization | String concatenation | json module + SQLite JSON1 | Proper escaping, schema validation, queryable storage |
| Shortcut customization | Custom key capture | QKeySequenceEdit + QSettings | Standard dialog, validation, persistence |

**Key insight:** Qt's undo system looks simple but has sophisticated features (command merging via mergeWith(), macros, clean state tracking) that are hard to replicate correctly. QSplitter handles edge cases (minimum sizes, collapse/expand, nested proportions) that custom drag implementations miss.

---

## Common Pitfalls

### Pitfall 1: QUndoStack Automatically Calls redo()
**What goes wrong:** Developer manually calls command.redo() before push(), causing double execution
**Why it happens:** Qt documentation notes this but it's easy to miss; intuition says "I need to execute the action"
**How to avoid:** Pass all state to command constructor, let push() handle execution
**Warning signs:** Actions execute twice, values appear doubled

### Pitfall 2: QAction Shortcuts Without Context
**What goes wrong:** Shortcuts fire when inappropriate (e.g., editing text field)
**Why it happens:** Default shortcut context is WindowShortcut, applies to all widgets in window
**How to avoid:** Use Qt.ApplicationShortcut for truly global shortcuts, Qt.WidgetShortcut for local, check focus in handler
**Warning signs:** Shortcuts work when they shouldn't, text input interrupted

### Pitfall 3: QSplitter State Binary Format
**What goes wrong:** saveState() returns QByteArray, JSON serialization fails
**Why it happens:** Attempting to store binary state in JSON/text settings
**How to avoid:** Use toBase64().data().decode() for JSON storage, or use QSettings directly (handles binary)
**Warning signs:** Settings corruption, state not restoring, encoding errors

### Pitfall 4: Debounce Timer Not Restarted
**What goes wrong:** Multiple rapid changes trigger multiple delayed executions
**Why it happens:** Forgetting to stop() timer before start(), or not using singleShot
**How to avoid:** Always stop() then start(), or use singleShot pattern; track pending state
**Warning signs:** Laggy UI, multiple optimization jobs queued, race conditions

### Pitfall 5: Filter Proxy Model Column Confusion
**What goes wrong:** Filtering applies to wrong column or no effect
**Why it happens:** setFilterKeyColumn() uses source model columns, not view display order
**How to avoid:** Always reference source model column indices, update when source model changes
**Warning signs:** Filter text appears in wrong rows, no filtering occurring

### Pitfall 6: Undo Stack Memory Growth
**What goes wrong:** "Unlimited" undo consumes excessive memory over long sessions
**Why it happens:** Commands hold references to large objects, no cleanup
**How to avoid:** Commands should store minimal state (IDs, deltas, not full objects); implement id() + mergeWith() for high-frequency actions
**Warning signs:** Memory usage growing steadily, app slowing down

### Pitfall 7: SQLite JSON Storage Without Schema
**What goes wrong:** JSON structure changes, old presets fail to load
**Why it happens:** No versioning or migration strategy for preset format
**How to avoid:** Include 'version' field in JSON, validate on load, provide upgrade path
**Warning signs:** Presets disappear or error on load after app update

---

## Code Examples

### Example 1: Save/Restore Splitter State

```python
# Source: Qt docs + maxpython.com tutorial
from PySide6.QtWidgets import QSplitter
from PySide6.QtCore import QSettings, QByteArray
import base64

class SplitterManager:
    """Handles persistence of QSplitter states"""
    
    @staticmethod
    def save_state(splitter: QSplitter, settings: QSettings, key: str):
        """Save splitter state to QSettings (handles binary data)"""
        state = splitter.saveState()
        settings.setValue(key, state)
    
    @staticmethod
    def save_state_json(splitter: QSplitter) -> str:
        """Save splitter state as base64 string for JSON"""
        state = splitter.saveState()
        return base64.b64encode(state.data()).decode('ascii')
    
    @staticmethod
    def restore_state(splitter: QSplitter, settings: QSettings, key: str):
        """Restore splitter state from QSettings"""
        state = settings.value(key)
        if state:
            if isinstance(state, str):
                # JSON-encoded base64
                state = QByteArray(base64.b64decode(state))
            splitter.restoreState(state)
```

### Example 2: Composite Undo Command (Macro)

```python
# Source: Qt documentation patterns
from PySide6.QtGui import QUndoCommand

class LoadPresetCommand(QUndoCommand):
    """Command that groups multiple constraint changes as single undo"""
    
    def __init__(self, model, preset_config, previous_config):
        super().__init__("Load Preset")
        self.model = model
        self.preset_config = preset_config
        self.previous_config = previous_config
    
    def undo(self):
        # Restore all constraints to previous state
        for key, value in self.previous_config.items():
            self.model.set_constraint(key, value)
    
    def redo(self):
        # Apply all preset constraints
        for key, value in self.preset_config.items():
            self.model.set_constraint(key, value)

# Usage
command = LoadPresetCommand(model, new_preset, old_state)
undo_stack.push(command)  # Single undo restores all constraints
```

### Example 3: High-Frequency Command Merging

```python
# Source: Qt QUndoCommand::mergeWith() documentation
from PySide6.QtGui import QUndoCommand

class AdjustSliderCommand(QUndoCommand):
    """Command that merges consecutive slider adjustments"""
    
    ID = 1001  # Unique ID for merge identification
    
    def __init__(self, model, slider_id, old_value, new_value):
        super().__init__("Adjust Slider")
        self.model = model
        self.slider_id = slider_id
        self.old_value = old_value
        self.new_value = new_value
    
    def undo(self):
        self.model.set_slider_value(self.slider_id, self.old_value)
    
    def redo(self):
        self.model.set_slider_value(self.slider_id, self.new_value)
    
    def id(self):
        """Return unique ID for this command type"""
        return self.ID
    
    def mergeWith(self, other: QUndoCommand):
        """Merge with another AdjustSliderCommand if same slider"""
        if other.id() != self.id():
            return False
        if other.slider_id != self.slider_id:
            return False
        # Merge: keep our old_value, adopt other's new_value
        self.new_value = other.new_value
        return True

# Usage: rapid slider adjustments merge into single undo
# User drags slider from 0->10->20->30, undo once returns to 0
```

### Example 4: Customizable Shortcut Dialog

```python
# Source: Qt patterns + QKeySequenceEdit usage
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QListWidget)
from PySide6.QtGui import QKeySequence

class ShortcutConfigDialog(QDialog):
    """Dialog for customizing keyboard shortcuts"""
    
    def __init__(self, shortcut_manager, parent=None):
        super().__init__(parent)
        self.shortcut_manager = shortcut_manager
        
        layout = QVBoxLayout()
        
        # List current shortcuts
        self.list_widget = QListWidget()
        for action_id, action in shortcut_manager.actions.items():
            text = f"{action.text()}: {action.shortcut().toString()}"
            self.list_widget.addItem(text)
        
        layout.addWidget(QLabel("Double-click to change shortcut:"))
        layout.addWidget(self.list_widget)
        
        # Conflict warning
        self.conflict_label = QLabel()
        self.conflict_label.setStyleSheet("color: red;")
        layout.addWidget(self.conflict_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_defaults)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(QPushButton("OK", clicked=self.accept))
        btn_layout.addWidget(QPushButton("Cancel", clicked=self.reject))
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setWindowTitle("Keyboard Shortcuts")
    
    def reset_defaults(self):
        """Reset all shortcuts to defaults"""
        for action_id, default in self.shortcut_manager.DEFAULT_SHORTCUTS.items():
            self.shortcut_manager.set_custom_shortcut(action_id, default)
        self.accept()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Qt.WA_DeleteOnClose for cleanup | Parent-child hierarchy | Qt6 | Automatic memory management reduces leaks |
| QRegExp for filtering | QRegularExpression | Qt5→Qt6 | PCRE support, better performance |
| Manual shortcut strings | QKeySequence.StandardKey | Qt6 | Automatic platform adaptation |
| SQLite text blobs for JSON | SQLite JSON1 extension | SQLite 3.9+ (2015) | Queryable JSON, indexing support |

**Deprecated/outdated:**
- QRegExp: Replaced by QRegularExpression in Qt6
- Qt.KeyboardModifier enum values: Use proper flags (Qt.ControlModifier, not Qt.CTRL in new code)

---

## Open Questions

1. **Command Merging Threshold**
   - What we know: mergeWith() enables combining rapid changes
   - What's unclear: Time threshold for considering changes "rapid" (100ms? 500ms?)
   - Recommendation: Use 250ms inactivity as merge window, configurable

2. **Undo Stack Persistence**
   - What we know: QUndoStack supports clean state, not persistence
   - What's unclear: Should undo history survive app restart? (requirements say "unlimited" not "persistent")
   - Recommendation: In-memory only for MVP; persist to SQLite if user feedback requests

3. **Split-pane Layout Templates**
   - What we know: saveState/restoreState handles positions
   - What's unclear: Pre-defined layouts ("Default", "Debug", "Compact") vs user-saved only
   - Recommendation: Start with user-saved only, add templates if requested

4. **Kernel Veto Log Real-time vs Post-hoc**
   - What we know: Requirements specify "post-hoc analysis after optimization completes"
   - What's unclear: Whether to stream logs during optimization or batch at end
   - Recommendation: Batch at end (simpler), streaming deferred per Deferred Ideas

---

## Sources

### Primary (HIGH confidence)
- Qt for Python 6.5+ Official Documentation (doc.qt.io/qtforpython-6)
  - QSplitter, QSplitterHandle
  - QUndoStack, QUndoCommand
  - QAction, QKeySequence
  - QSortFilterProxyModel
  - QSettings, QTimer
- Riverbank Computing PyQt6 Docs (PyQt6 mirrors PySide6 APIs)
- Python GUIs PySide6 Tutorials (pythonguis.com)

### Secondary (MEDIUM confidence)
- Stack Overflow verified answers on QUndoStack redo() behavior
- Qt Centre forum discussions on shortcut contexts
- GitHub examples: dockwidgets, mdi, basicfiltermodel

### Tertiary (LOW confidence)
- Community blog posts on debounce patterns (pattern verified, implementations vary)
- SQLite JSON1 documentation (sqlite.org)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All from official Qt docs
- Architecture patterns: HIGH - Based on Qt examples and verified implementations
- Pitfalls: HIGH - From documented Qt behavior and community experience
- Code examples: MEDIUM-HIGH - Compiled from multiple sources, syntax verified

**Research date:** 2026-01-30
**Valid until:** 2026-07-30 (Qt6 stable, PySide6 mature)

**Qt/PySide6 version target:** 6.5+ (current stable, LTS recommended)
