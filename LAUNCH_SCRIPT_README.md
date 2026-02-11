# Launch Script Instructions

## Quick Start

1. **Double-click** `Launch App.command` to launch the NASCAR DFS Optimizer

The script will automatically:
- Create a virtual environment if needed
- Install all dependencies
- Launch the application

## What This Does

- **No app bundle needed** - runs directly from source
- **Automatic setup** - creates venv and installs dependencies on first run
- **Easy backup** - just zip the project folder

## Portability (Transfer to New Mac)

To transfer the app to a new Mac:

### Option 1: Zip Archive (Recommended)
```bash
zip -r NASCAR-DFS-Optimizer.zip \
    .venv/ \
    apps/ \
    packages/ \
    "Launch App.command"
```

### Option 2: Copy Folder
1. Copy entire project folder to new Mac
2. Double-click `Launch App.command`

### Option 3: Clean Reinstall
If virtual environment has issues, delete `.venv/` folder and re-run launch script.

## Troubleshooting

**"Python 3.12.7 not found!"**
- Install: `pyenv install 3.12.7`

**"ModuleNotFoundError"**
- Delete `.venv/` folder
- Re-run `Launch App.command`

**App crashes on launch**
- Check Console.app for error logs
- See TROUBLESHOOTING.md for common issues

## Requirements

- macOS 11.0 (Big Sur) or later
- Python 3.12.7 (auto-installed via pyenv if needed)
- 500MB free disk space for virtual environment

## Current Status

✅ Launch script works
✅ App imports correctly
✅ GUI starts up
❌ Database layer has bug (missing `get_all_races` method)

The launch script approach successfully avoids the py2app packaging issue!
