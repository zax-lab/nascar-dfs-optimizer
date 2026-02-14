# NASCAR DFS Optimizer - Project Status

**Date:** 2026-02-14 01:10 EST

---

## Current State: ✅ **STABLE & SHIPPING**

### What This Is

**NASCAR DFS Optimizer v1.2.1** - A working, native macOS desktop application for DraftKings DFS optimization.

### Purpose

Optimize lineups for NASCAR DFS contests using:
- Real NASCAR historical data (2019-2025)
- Physics-compliant simulation (MCMC with JAX)
- Constraint-based reasoning
- Local Apple Silicon optimization

### What Works

✅ **Core Features:**
- Native macOS GUI with PySide6/Qt6
- 663 real NASCAR races (Cup, Trucks, Xfinity)
- 416 real drivers with actual IDs
- 24,702 race results
- JAX MCMC optimization engine
- Constraint management (salary cap, exposure, stacking)
- Lineup generation and display
- CSV import/export for DraftKings
- Undo/Redo system
- Keyboard shortcuts
- Background job queue
- Session persistence
- SQLite database

✅ **Launch:**
- App launches without crashes
- PySide6 6.10.2 working correctly
- All imports successful

---

## Installation

### Requirements

- macOS 12.0 (Monterey) or later
- Apple Silicon (M1/M2/M3) or Intel Mac
- 4GB RAM minimum, 8GB recommended
- Python 3.9+

### Dependencies

```bash
pip install "PySide6==6.10.2" "shiboken6==6.10.2" pandas "jax[cpu]" jaxlib numpy neo4j pulp
```

### Launch Commands

```bash
# From project root
cd /Users/zax/Desktop/NASCAR-DFS-Optimizer/apps/native_mac
PYTHONPATH=/Users/zax/Desktop/NASCAR-DFS-Optimizer:$PYTHONPATH python3 main.py

# On first launch, database will auto-seed with real data
```

---

## Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │    Native macOS GUI (PySide6/Qt6)           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐         │  │
│  │  │  MainWindow    │  │  SettingsTab   │         │  │
│  │  │  (Tabbed UI)  │  │  (Neo4j conn)  │         │  │
│  │  └─────────────────┘  └─────────────────┘         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               ▲
                               │
┌─────────────────────────────────────────────────────────────┐
│                      Ontology Layer                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Neo4j Graph Database                   │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │
│  │  │ Driver  │  │  Track  │  │  Race   │            │   │
│  │  │  Nodes  │  │  Nodes  │  │  Nodes  │            │   │
│  │  └─────────┘  └─────────┘  └─────────┘            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                               ▲
                               │
┌─────────────────────────────────────────────────────────────┐
│                        Kernel Layer                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            KernelLogic (Immutable Rules)             │   │
│  │  • Position validation (1 to field_size)      │   │
│  │  • Unique position enforcement                  │   │
│  │  • Lineup size validation (6 drivers)        │   │
│  │  • Salary cap constraints                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
NASCAR-DFS-Optimizer/
├── apps/
│   ├── backend/          # FastAPI backend, Neo4j integration
│   ├── frontend/         # Next.js web dashboard
│   └── native_mac/      # Main macOS GUI app
│       ├── gui/          # UI components (tabs, widgets)
│       ├── optimization/   # JAX MCMC engine
│       ├── persistence/    # SQLite database, session manager
│       └── main.py        # Application entry point
├── scripts/             # Utilities (data seeding, testing)
├── .planning/           # Project documentation (roadmap, state)
├── race-logs.csv       # 663 races, 416 drivers, 24,702 results
└── docs/               # Screenshots, blueprints
```

---

## Current Releases

### v1.2.1 - Real Data Edition ⭐ **STABLE**

**Release Date:** 2026-02-04  
**GitHub:** https://github.com/zax-lab/nascar-dfs-optimizer/releases/tag/v1.2.1

**Features:**
- ✅ Real NASCAR historical data (2019-2025)
- ✅ Native macOS GUI with PySide6/Qt6
- ✅ JAX MCMC optimization engine
- ✅ Constraint presets and undo/redo
- ✅ CSV import/export for DraftKings
- ✅ Background job queue with dock badge
- ✅ Real data auto-seeding on first launch

**What's Included:**
- 663 races (Cup, Trucks, Xfinity)
- 416 drivers with real IDs
- 24,702 race results
- All NASCAR tracks represented

---

## Documentation

### Essential Files

- **README.md** - Quick start guide
- **INSTALL.md** - Installation instructions with Neo4j setup
- **TROUBLESHOOTING.md** - Common issues and solutions
- **CHANGELOG.md** - Version history and release notes
- **PROJECT.md** - Project purpose and scope
- **REQUIREMENTS.md** - Detailed requirements
- **ROADMAP.md** - Phase breakdown and progress

### Blueprints & Research

- **Blueprint for Axiomatic AI** - Theoretical AI architecture (documented, not implemented)
- **Product Definition** - NASCAR DFS Optimizer scope

---

## Known Issues & Limitations

### Non-Critical
- py2app full build not working (use alias mode instead)
- Neo4j optional (works without it)
- Pulp/CBC solver optional (for advanced portfolio optimization)

### Out of Scope (for v1.2.x)
- Axiomatic AI / Neural-symbolic reasoning
- BDH architecture implementation
- Formal logic proofs
- Causal Bayesian Networks
- Real-time live race optimization
- Mobile apps (iOS/Android)
- Multi-site DFS support (FanDuel, Yahoo)
- Public web API or SaaS deployment

---

## Development Notes

### Recent Fixes (2026-02-14)

**PySide6 Crash Fix:**
- Changed `DEFAULT_SHORTCUTS` from QKeySequence objects to strings
- Convert to QKeySequence on-demand in `get_shortcut()`
- Added missing `set_undo_manager()` method to MainWindow
- Added guard in `SplitEditorTab._load_presets()` for `preset_combo`

**Result:** App launches successfully without SIGSEGV crashes.

---

## Next Steps (v1.3+)

### Optional Enhancements
- Fix py2app full build for standalone .app bundle
- Implement race history viewer GUI
- Live race data integration (2025+ seasons)
- Enhanced projection models using historical data
- Portfolio optimization with CVaR/Conditional Upside

### Research Directions
- Axiomatic AI integration (if value proven)
- Causal Bayesian Networks for race modeling
- Driver performance meta-learning across tracks
- Advanced constraint ontology

---

## Summary

**Status:** ✅ **COMPLETE & STABLE**
**App:** Working, launching, functional
**Data:** 663 real races, 416 drivers
**Architecture:** Clean three-layer design
**Next:** Ready for production use

---

*Last updated: 2026-02-14*
