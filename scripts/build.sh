#!/usr/bin/env bash
# Build script for NASCAR DFS Optimizer macOS app bundle
# Usage: ./scripts/build.sh
#
# Note: Uses Python 3.12.7 for building because py2app 0.28.9
# is incompatible with Python 3.14.2
BUILD_PYTHON="${BUILD_PYTHON:-$HOME/.pyenv/versions/3.12.7/bin/python3.12}"

set -e  # Exit on error

echo "=========================================="
echo "Building NASCAR DFS Optimizer..."
echo "=========================================="

# Navigate to app directory
# Script is at scripts/build.sh, so we need to go up one level, then into apps/native_mac
cd "$(dirname "$0")/../apps/native_mac"

# Clean previous builds for reproducible builds
echo ""
echo "Cleaning previous build artifacts..."
rm -rf build dist

# Workaround: py2app has issues with pyproject.toml present
# Temporarily rename it during build (Phase 6 workaround)
if [ -f "pyproject.toml" ]; then
    echo "Temporarily moving pyproject.toml for py2app compatibility..."
    mv pyproject.toml pyproject.toml.backup
    PYPROJECT_MOVED=true
fi

# Run py2app build
echo ""
echo "Building with py2app..."
echo "Using Python: $BUILD_PYTHON"
"$BUILD_PYTHON" setup.py py2app

# Verify .app bundle was created
echo ""
echo "Verifying build artifacts..."
if [ ! -d "dist/NASCAR DFS Optimizer.app" ]; then
    echo "ERROR: Build failed - .app bundle not found"
    echo "Expected: dist/NASCAR DFS Optimizer.app"
    exit 1
fi

echo "✓ .app bundle created: dist/NASCAR DFS Optimizer.app"

# Restore pyproject.toml if it was moved
if [ "$PYPROJECT_MOVED" = true ]; then
    echo "Restoring pyproject.toml..."
    mv pyproject.toml.backup pyproject.toml
fi

# Sign bundle with ad-hoc signature for personal distribution
# Note: Ad-hoc signing uses "-" as identity; personal Apple ID signing
# can be configured by replacing "-" with "Developer ID Application: Your Name"
echo ""
echo "Signing app bundle..."
codesign --force --deep --sign - "dist/NASCAR DFS Optimizer.app"

# Verify signature
echo ""
echo "Verifying signature..."
codesign -dv "dist/NASCAR DFS Optimizer.app"

echo ""
echo "=========================================="
echo "✓ Build complete!"
echo "=========================================="
echo ""
echo "Bundle location: apps/native_mac/dist/NASCAR DFS Optimizer.app"
echo ""
echo "To test the app:"
echo "  open apps/native_mac/dist/NASCAR\ DFS\ Optimizer.app"
echo ""
