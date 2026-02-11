# Phase 8: Workflow Accelerators - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Power-user features for rapid iteration and debugging: split-view editing, constraint presets, undo/redo, kernel veto log viewer, and comprehensive keyboard shortcuts.

</domain>

<decisions>
## Implementation Decisions

### Split-pane layout
- **Layout style:** User-configurable like iTerm/VSCode — draggable splitters, both horizontal and vertical splits supported
- **Pane content:** Left/top = constraints/editing; Right/bottom = live lineup preview
- **Update behavior:** User-configurable debounce (300ms default) OR real-time — toggle in settings
- **Flexibility:** Users can create multiple splits, collapse/expand, and save preferred layouts

### Constraint presets
- **Storage:** Dedicated Presets tab/space in the UI — a "library" view for managing all presets
- **Preset types:** Named user-saved presets + auto-saved "recent" configurations with quick-add feature
- **Scope:** Both race-specific presets (appear only for that race type/track) and global presets (available everywhere)
- **Portability:** Full import/export functionality — share presets as JSON files

### Undo/redo scope
- **Undoable actions:** ALL actions — lineup edits, constraint changes, tab switches, preset loads, imports, exports
- **Scope:** Both per-race undo context AND global undo stack — user can undo across different races
- **Stack depth:** Unlimited (infinite) — storage is cheap, don't lose user work
- **Shortcuts:** Standard macOS CMD+Z (undo) and CMD+Shift+Z (redo)

### Kernel veto log viewer
- **Timing:** Post-hoc analysis — viewable after optimization completes (not real-time stream)
- **Content:** All veto information available but collapsible — rule name, explanation, affected drivers, lineup context
- **Filtering:** Yes — filter by rule type, driver, severity; full-text search across veto reasons
- **Export:** Export veto logs to JSON/CSV for external analysis

### Keyboard shortcuts
- **Coverage:** As many actions as possible — goal is full keyboard-driven workflow (no mouse required)
- **Customizability:** Semi-customizable — users can override default shortcuts, but all actions have sensible defaults
- **Style:** Standard macOS conventions (CMD+letter) — no Emacs/Vim modal editing, keep it native Mac

### Claude's Discretion
- Default debounce delay (suggest 300ms)
- Pane splitter appearance and behavior
- Preset card/list layout in the library
- Undo stack UI indicator (status bar badge?)
- Veto log color-coding by severity
- Shortcut conflict resolution UI
- Which specific actions get shortcuts (beyond obvious ones)

</decisions>

<specifics>
## Specific Ideas

- "Like iTerm or VSCode" for split-pane — familiar to power users
- Quick-add feature for recent presets — one-click reapply of recent configurations
- Collapsible veto information — show summary, expand for full details
- Goal: Full keyboard-driven workflow without mouse

</specifics>

<deferred>
## Deferred Ideas

- Real-time veto log streaming during optimization — complex threading, defer to future enhancement
- Vim/Emacs modal keybindings — niche audience, stick to standard macOS conventions
- Preset sharing service/cloud sync — network feature, out of scope for local app
- Layout templates (pre-defined split configurations) — can add later if requested

</deferred>

---

*Phase: 08-workflow-accelerators*
*Context gathered: 2026-01-30*
