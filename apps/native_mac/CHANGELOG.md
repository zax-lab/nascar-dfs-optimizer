# Changelog

All notable changes to NASCAR DFS Optimizer are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.2.0] - 2026-01-30

### Added
- **macOS native app distribution** (.app bundle)
  - Complete .app bundle with py2app
  - Universal binary (Apple Silicon + Intel) support
  - Ad-hoc code signing for personal distribution
  - Drag-and-drop installation to Applications folder

- **PySide6 GUI with native macOS look and feel**
  - Native menu bar integration
  - System tray icon for job notifications
  - Dock integration (badge count, menu actions)
  - Dark mode support (automatic, follows system)
  - High-resolution display support

- **Undo/Redo functionality**
  - Full undo stack for constraint changes
  - Keyboard shortcuts: Cmd+Z (undo), Cmd+Shift+Z (redo)
  - Visual indication of undo/redo availability
  - Undo manager integrates with all constraint modifications

- **Preset system for saving and loading constraint configurations**
  - Save named presets from current constraints
  - Load presets to restore settings
  - Delete unused presets
  - Preset validation before loading

- **Background job management with GPU offload support**
  - Jobs tab for viewing optimization history
  - Queue multiple optimizations
  - Cancel running jobs
  - GPU worker integration for accelerated optimization
  - Job status notifications (dock badge, tray icon)

- **Export/import backup of all application data**
  - Full backup: lineups, presets, settings, veto logs
  - Selective export: lineups only, presets only
  - Import with merge strategies (replace, merge, skip)
  - Automatic backup before import
  - JSON format for easy inspection

- **Veto logging for tracking constraint violations**
  - Log veto events with timestamp and reason
  - View veto history in Veto Log tab
  - Filter by race or veto reason
  - Export veto logs for analysis

### Changed
- **Optimized driver table rendering with live preview**
  - Faster table updates with large driver lists
  - Live preview of lineup effects when toggling drivers
  - Better sorting and filtering UI
  - Salary counter updates in real-time

- **Improved constraint panel with collapsible sections**
  - Grouped constraints by category (salary, positions, drivers)
  - Collapse/expand sections for cleaner UI
  - Visual indicators of active vs inactive constraints
  - Better validation error messages

- **Enhanced optimization progress reporting**
  - Real-time progress percentage in Jobs tab
  - Estimated time remaining
  - Lineup count updates as optimization progresses
  - Detailed job status (queued, running, completed, failed)

- **Better error messages for Neo4j connection failures**
  - Specific error messages for common issues
  - Actionable guidance for each error type
  - Connection retry option in Settings tab
  - Better error display in Console.app logs

- **Improved CSV import validation**
  - Better error messages for malformed CSVs
  - Support for various DraftKings CSV formats
  - Clear indication of missing required columns
  - Preview of imported data before confirmation

### Fixed
- **Fixed crash when importing malformed CSV files**
  - Added proper error handling for CSV parsing
  - Graceful degradation with partial data
  - Clear error message without app crash

- **Fixed settings persistence on app quit**
  - Settings now properly save before quit
  - No lost preferences on app restart
  - Better session state management

- **Fixed keyboard shortcuts not working in some contexts**
  - Improved shortcut handling for global shortcuts
  - Fixed conflict with system shortcuts
  - Better focus management for key events

- **Fixed memory leak during long optimization runs**
  - Proper cleanup of optimization resources
  - Reduced memory footprint over time
  - Stable performance with 100+ lineups generated

- **Fixed incorrect lineup counting in status bar**
  - Accurate count of visible lineups
  - Updates correctly after filtering or sorting
  - Consistent with Lineups tab display

### Known Issues
- **Gatekeeper limitation:** First launch requires Control-click → Open workaround
  - This is macOS security requirement for personal distribution
  - Documented in INSTALL.md and TROUBLESHOOTING.md
  - Only needed once per download

- **Neo4j server dependency:** App requires Neo4j server to be running
  - Users must install and start Neo4j separately
  - Clear error message when connection fails
  - Connection can be tested in Settings tab

- **Optimization speed:** Optimization may be slow without GPU offload
  - CPU-only optimization is compute-intensive
  - Recommended: Use GPU worker for large lineups
  - Typical time: 5-30 seconds for 150 lineups (CPU), 1-5 seconds (GPU)

- **Bundle size:** Universal binary is larger than architecture-specific builds
  - Universal2 bundle includes both arm64 and x86_64 code
  - Estimated size: 150-250 MB
  - Future: Offer architecture-specific builds for reduced size

### Migration Notes

**Upgrading from v1.1.0:**
- All settings and presets are preserved
- Database schema is compatible (no migration needed)
- Export lineups from v1.1.0 if needed before upgrade
- Neo4j connection settings remain the same

---

## [1.1.0] - 2026-01-20

### Added
- **Initial release with core optimization engine**
  - DraftKings CSV import
  - Driver projection modeling
  - Constraint-based lineup generation
  - Multi-objective optimization (points + value)

- **Basic UI features**
  - Driver table with projection data
  - Simple constraint panel
  - Lineup generation button
  - Export lineups to JSON/CSV

### Known Issues
- **No persistent storage:** Settings not saved between sessions
- **No undo/redo:** Can't revert constraint changes
- **No presets:** Can't save/load constraint configurations
- **Basic UI:** Missing many polish features

---

## Version Format

- **MAJOR:** Incompatible API changes
- **MINOR:** Backwards-compatible functionality additions
- **PATCH:** Backwards-compatible bug fixes

Example: `1.2.0`
- `1` = Major version (breaking changes)
- `2` = Minor version (new features)
- `0` = Patch version (bug fixes)

---

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/[your-repo]/issues
- Documentation: See INSTALL.md and TROUBLESHOOTING.md
- Console logs: Include Console.app logs when reporting issues

---

*Last Updated: 2026-01-30*
*Current Version: 1.2.0*
