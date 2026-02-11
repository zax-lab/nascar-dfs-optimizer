#!/usr/bin/env bash
# Build script for NASCAR DFS Optimizer macOS app bundle
#
# Usage:
#   cd apps/native_mac
#   ./scripts/build.sh

set -e  # Exit on error

echo "=========================================="
echo "Building NASCAR DFS Optimizer"
echo "=========================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Use Python 3.12.7 (py2app 0.28.9 incompatible with Python 3.14.2)
echo ""
echo "[1/5] Setting Python version to 3.12.7..."
pyenv local 3.12.7
PYTHON_VERSION=$(python --version)
echo "   ✓ Using $PYTHON_VERSION"

# Clean previous builds (required for reproducible builds)
echo ""
echo "[2/5] Cleaning previous builds..."
rm -rf build dist
echo "   ✓ Cleaned build/ and dist/"

# Temporarily rename pyproject.toml (py2app incompatibility workaround)
echo ""
echo "[3/5] Preparing build environment..."
if [ -f "pyproject.toml" ]; then
    mv pyproject.toml pyproject.toml.bak
    echo "   ✓ Temporarily renamed pyproject.toml"
fi

# Build with py2app
echo ""
echo "[4/5] Building .app bundle with py2app..."
python setup.py py2app

# Restore pyproject.toml
if [ -f "pyproject.toml.bak" ]; then
    mv pyproject.toml.bak pyproject.toml
    echo "   ✓ Restored pyproject.toml"
fi

# Verify bundle was created
if [ ! -d "dist/NASCAR DFS Optimizer.app" ]; then
    echo ""
    echo "   ✗ ERROR: Build failed - .app bundle not found"
    exit 1
fi
echo "   ✓ App bundle created: dist/NASCAR DFS Optimizer.app"

# Sign with ad-hoc signature for personal distribution
echo ""
echo "[5/6] Signing app bundle (ad-hoc signature)..."
codesign --force --deep --sign - "dist/NASCAR DFS Optimizer.app"

# Verify signature
echo "   Verifying signature..."
codesign -vvv "dist/NASCAR DFS Optimizer.app" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo ""
    echo "   ✗ ERROR: Code signing failed"
    exit 1
fi
echo "   ✓ App bundle signed and verified"

# Report bundle size
echo ""
echo "[6/6] Build statistics..."
BUNDLE_SIZE=$(du -sh "dist/NASCAR DFS Optimizer.app" | cut -f1)
echo "   Bundle size: $BUNDLE_SIZE"
echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo ""
echo "Location: apps/native_mac/dist/NASCAR DFS Optimizer.app"
echo ""
echo "Note: Users will need to Control-click → Open on first launch"
echo "      (Gatekeeper requirement for personal distribution)"
echo ""
