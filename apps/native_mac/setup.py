"""
py2app setup script for NASCAR DFS Optimizer macOS app bundle.

Usage:
    python setup.py py2app -A    # Development build (alias mode)
    python setup.py py2app       # Production build
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    # Note: argv_emulation disabled - conflicts with PySide6 event loop
    # Use Qt's native file-open handling instead
    "packages": [
        "PySide6",
        "shiboken6",
        "pandas",
        "numpy",
        "jax",
        "jaxlib",
        "neo4j",
    ],
    "includes": [
        # PySide6 submodules for full Qt integration
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtGui",
        "shiboken6",
    ],
    "excludes": [
        # Exclude development/testing dependencies from bundle
        "pytest",
        "setuptools",
    ],
    # Universal binary for Apple Silicon (arm64) + Intel (x86_64)
    "arch": "universal2",
    # Include image format plugins for screenshot/icon loading
    "qt_plugins": ["imageformats"],
    "plist": {
        "CFBundleName": "NASCAR DFS Optimizer",
        "CFBundleDisplayName": "NASCAR DFS Optimizer",
        "CFBundleIdentifier": "com.zax.nascar-dfs",
        "CFBundleVersion": "1.2.0",
        "CFBundleShortVersionString": "1.2.0",
        "NSHighResolutionCapable": True,
        # Enable dark mode support
        "NSRequiresAquaSystemAppearance": False,
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
)
