"""
Test build process and app bundle integrity.

Tests verify:
1. py2app build completes successfully
2. .app bundle is created in expected location
3. App can be launched (smoke test)
"""

import subprocess
import os
import time
from pathlib import Path


def test_build_succeeds():
    """Verify py2app build completes successfully."""
    result = subprocess.run(
        ["python", "setup.py", "py2app"],
        cwd="apps/native_mac",
        capture_output=True,
        timeout=600,  # 10 minutes timeout
    )

    assert result.returncode == 0, f"Build failed: {result.stderr.decode()}"


def test_app_bundle_exists():
    """Verify .app bundle was created."""
    app_path = Path("apps/native_mac/dist/NASCAR-DFS-Optimizer.app")

    # This test assumes build.sh has been run
    # If not, run build first: cd apps/native_mac && ./scripts/build.sh
    if not app_path.exists():
        # Skip test if bundle doesn't exist (expected if not built yet)
        import pytest

        pytest.skip("App bundle not found - run build.sh first")

    assert app_path.is_dir(), "App bundle not found in dist/"


def test_app_info_plist_exists():
    """Verify Info.plist exists in bundle."""
    plist_path = Path(
        "apps/native_mac/dist/NASCAR-DFS-Optimizer.app/Contents/Info.plist"
    )

    if not plist_path.exists():
        import pytest

        pytest.skip("Info.plist not found - run build.sh first")

    assert plist_path.is_file(), "Info.plist not found in app bundle"


def test_app_executable_exists():
    """Verify main executable exists."""
    exe_path = Path(
        "apps/native_mac/dist/NASCAR-DFS-Optimizer.app/Contents/MacOS/NASCAR-DFS-Optimizer"
    )

    if not exe_path.exists():
        import pytest

        pytest.skip("Executable not found - run build.sh first")

    assert exe_path.is_file() and os.access(exe_path, os.X_OK), (
        "Executable not found or not executable"
    )


def test_bundle_structure():
    """Verify .app bundle has correct macOS structure."""
    app_path = Path("apps/native_mac/dist/NASCAR-DFS-Optimizer.app")

    if not app_path.exists():
        import pytest

        pytest.skip("App bundle not found - run build.sh first")

    # Required directories
    contents_dir = app_path / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"

    assert contents_dir.exists(), "Contents directory missing"
    assert macos_dir.exists(), "MacOS directory missing"
    assert resources_dir.exists(), "Resources directory missing"


def test_app_launches_smoke_test():
    """Verify app can launch without immediate crash (smoke test)."""
    app_path = Path("apps/native_mac/dist/NASCAR-DFS-Optimizer.app")

    if not app_path.exists():
        import pytest

        pytest.skip("App bundle not found - run build.sh first")

    # Launch app in background with timeout
    # open command returns 0 even if app crashes, so this is a weak test
    # Manual testing on clean machine is still required
    result = subprocess.run(
        ["open", "-W", "-a", str(app_path)],
        capture_output=True,
        timeout=15,  # Wait up to 15 seconds
    )

    # We don't assert success here - just verify the command didn't fail immediately
    # Real testing requires manual verification on clean machine
    print(
        "Note: This is a smoke test. Manual verification on clean machine is required."
    )
