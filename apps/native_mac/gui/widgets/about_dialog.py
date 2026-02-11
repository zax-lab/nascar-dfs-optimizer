"""About dialog for NASCAR DFS Optimizer.

Follows macOS Human Interface Guidelines for standard About windows.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QWidget,
    QApplication,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
from typing import Optional

from ...version import VERSION, APP_NAME, COPYRIGHT


class AboutDialog(QDialog):
    """Standard macOS About dialog.

    Displays:
    - Application icon (128x128)
    - Application name (large bold)
    - Version number
    - Copyright notice
    - Credits and License buttons

    Follows macOS Human Interface Guidelines for About windows.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the About dialog.

        Args:
            parent: Parent widget for dialog positioning.
        """
        super().__init__(parent)

        self._setup_dialog_properties()
        self._setup_ui()

    def _setup_dialog_properties(self) -> None:
        """Configure dialog window properties.

        Standard macOS About windows have no title bar text
        and are non-resizable with a fixed size.
        """
        self.setWindowTitle("")  # About windows have no title
        self.setFixedSize(400, 300)
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowContextHelpButtonHint
            & ~Qt.WindowMaximizeButtonHint
        )

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(10)

        # App icon
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(128, 128)

        # Try to load app icon, use placeholder if not available
        icon_pixmap = self._load_app_icon()
        if icon_pixmap:
            icon_label.setPixmap(
                icon_pixmap.scaled(
                    128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        else:
            # Create a placeholder with app initial
            icon_label.setStyleSheet("""
                background-color: #4CAF50;
                border-radius: 20px;
                color: white;
                font-size: 48px;
                font-weight: bold;
            """)
            icon_label.setText("N")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_label)

        # App name
        name_label = QLabel(APP_NAME)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_font = QFont()
        name_font.setPointSize(18)
        name_font.setBold(True)
        name_label.setFont(name_font)
        layout.addWidget(name_label)

        # Version
        version_label = QLabel(f"Version {VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(version_label)

        # Spacer
        layout.addSpacing(10)

        # Copyright
        copyright_label = QLabel(COPYRIGHT)
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(copyright_label)

        # Spacer
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Credits button
        credits_button = QPushButton("Credits")
        credits_button.setFixedWidth(100)
        credits_button.clicked.connect(self._show_credits)
        button_layout.addWidget(credits_button)

        # License button
        license_button = QPushButton("License")
        license_button.setFixedWidth(100)
        license_button.clicked.connect(self._show_license)
        button_layout.addWidget(license_button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _load_app_icon(self) -> Optional[QPixmap]:
        """Load the application icon.

        Returns:
            QPixmap if icon found, None otherwise.
        """
        # Try common icon locations
        icon_paths = [
            "resources/icon.png",
            "assets/icon.png",
            "icon.png",
        ]

        for path in icon_paths:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap

        return None

    def _show_credits(self) -> None:
        """Show the credits dialog."""
        dialog = CreditsDialog(self)
        dialog.exec()

    def _show_license(self) -> None:
        """Show the license dialog."""
        dialog = LicenseDialog(self)
        dialog.exec()


class CreditsDialog(QDialog):
    """Dialog displaying developer credits and acknowledgments."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the credits dialog.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self.setWindowTitle("Credits")
        self.setMinimumSize(400, 350)
        self.setMaximumSize(500, 450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Credits & Acknowledgments")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Credits text
        credits_text = QTextBrowser()
        credits_text.setOpenExternalLinks(True)
        credits_text.setHtml("""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px;">
        <h3>Development</h3>
        <p>NASCAR DFS Optimizer was built with care for racing enthusiasts.</p>

        <h3>Open Source Libraries</h3>
        <p>This application uses the following open source projects:</p>
        <ul>
            <li><b>PySide6</b> - Qt bindings for Python<br>
                <a href="https://www.qt.io/qt-for-python">https://www.qt.io/qt-for-python</a></li>
            <li><b>JAX</b> - High-performance numerical computing<br>
                <a href="https://github.com/google/jax">https://github.com/google/jax</a></li>
            <li><b>pandas</b> - Data analysis and manipulation<br>
                <a href="https://pandas.pydata.org">https://pandas.pydata.org</a></li>
            <li><b>NumPy</b> - Scientific computing<br>
                <a href="https://numpy.org">https://numpy.org</a></li>
        </ul>

        <h3>Special Thanks</h3>
        <p>To the NASCAR community and DFS players who inspire continuous improvement.</p>
        </body>
        </html>
        """)
        layout.addWidget(credits_text)

        # Close button
        close_button = QPushButton("Close")
        close_button.setFixedWidth(100)
        close_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)


class LicenseDialog(QDialog):
    """Dialog displaying license information."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the license dialog.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self.setWindowTitle("License")
        self.setMinimumSize(400, 350)
        self.setMaximumSize(500, 450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("License Agreement")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # License text
        license_text = QTextBrowser()
        license_text.setHtml("""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px;">
        <p><b>NASCAR DFS Optimizer</b></p>
        <p>Copyright 2025. All rights reserved.</p>

        <p>This software is proprietary and confidential. Unauthorized copying, 
        distribution, modification, public display, or public performance of 
        this software is strictly prohibited.</p>

        <p>This software is provided for personal use only. Commercial use 
        requires a separate license agreement.</p>

        <h4>Third-Party Licenses</h4>
        <p>This application includes software licensed under various open source 
        licenses including MIT, BSD, and Apache 2.0. See the Credits dialog for 
        links to individual project licenses.</p>

        <h4>Disclaimer</h4>
        <p>THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, 
        EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED 
        WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.</p>
        </body>
        </html>
        """)
        layout.addWidget(license_text)

        # Close button
        close_button = QPushButton("Close")
        close_button.setFixedWidth(100)
        close_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
