# NASCAR DFS Optimizer v1.2.0 - Release Notes

## 🚀 Overview

NASCAR DFS Optimizer is a native macOS desktop application for DraftKings NASCAR DFS lineup optimization using JAX-based MCMC sampling and Neo4j graph database constraints.

## ✨ Features

- **Native macOS GUI** with PySide6/Qt6
- **Tabbed Interface**: Race Data, Optimization, Lineups, Jobs, Settings
- **CSV Import/Export** for race data and DraftKings lineup uploads
- **Local Optimization** with JAX-based MCMC engine (Apple Silicon optimized)
- **Constraint Presets** for saving/loading optimization configurations
- **Undo/Redo** system with CMD+Z / CMD+Shift+Z
- **Keyboard Shortcuts** with full customization
- **Split-View Editor** for real-time optimization preview
- **Background Jobs** with dock badge and menubar status
- **GPU Offload** (optional Windows GPU for heavy jobs)
- **Settings Backup** to JSON for data portability

## 📦 Installation

### Method 1: Development Alias Build (Current Release)

1. Install Python 3.9+ from python.org or pyenv
2. Clone or download this repository
3. Install dependencies:
   ```bash
   pip install PySide6 pandas jax[cpu] jaxlib numpy neo4j pulp
   ```
4. Run the app:
   ```bash
   cd apps/native_mac
   python3 main.py
   ```

### Method 2: Full App Bundle (Coming Soon)

We're working on a standalone .app bundle that includes all dependencies. Check back for v1.2.1.

## 🐛 Known Issues

- Neo4j connection tests fail if Neo4j is not running (optional feature)
- Pulp/CBC solver may need manual installation for advanced portfolio optimization
- Full app bundle build in progress (see Method 2 above)

## ✅ What's New in v1.2.0

- Restructured project for proper GitHub layout
- Added MIT License
- Fixed all import paths for new directory structure
- 7/12 integration tests passing
- Screenshots added to documentation
- Ready for distribution

## 🏗️ Architecture

```
Application Layer (PySide6 GUI)
         ↓
Ontology Layer (Neo4j Graph DB)
         ↓
Kernel Layer (Immutable Rules)
```

## 🔧 Requirements

- macOS 12.0 (Monterey) or later
- Apple Silicon (M1/M2/M3) or Intel Mac
- Python 3.9+ for development mode
- 4GB RAM minimum, 8GB recommended
- Neo4j 5.x or 4.x (optional, for constraint ontology)

## 📖 Documentation

- [README](README.md) - Full documentation
- [INSTALL.md](INSTALL.md) - Installation guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues

## 🤝 Contributing

Issues and pull requests welcome! Check [CONTRIBUTING](CONTRIBUTING.md) (to be added).

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🎯 Roadmap

- v1.2.1: Standalone .app bundle with all dependencies
- v1.3.0: Enhanced GUI features
- v1.4.0: Web interface improvements

---

Built with ⚡ by Zachary Kelsey
