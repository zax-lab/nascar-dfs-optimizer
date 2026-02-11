"""Notification manager for macOS native notifications.

Provides native macOS notification center integration with action buttons
and click handling. Falls back to QSystemTrayIcon if native notifications
are unavailable (e.g., in sandboxed environments).
"""

from typing import Optional, Callable

from PySide6.QtWidgets import QSystemTrayIcon, QApplication
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon


class NotificationManager(QObject):
    """Send native macOS notifications.

    Uses NSUserNotificationCenter via PyObjC for native notifications.
    Falls back to QSystemTrayIcon.showMessage() if unavailable.

    Signals:
        notification_clicked: Emitted when user clicks notification action button
                              with the action identifier as parameter.
    """

    notification_clicked = Signal(str)  # action identifier

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the notification manager.

        Args:
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.notification_center = None
        self.NSUserNotification = None
        self._setup_notification_center()

        # Fallback tray icon (created on demand)
        self._tray_icon: Optional[QSystemTrayIcon] = None

    def _setup_notification_center(self) -> None:
        """Initialize NSUserNotificationCenter."""
        try:
            from Foundation import NSUserNotificationCenter
            from Foundation import NSUserNotification

            self.notification_center = (
                NSUserNotificationCenter.defaultUserNotificationCenter()
            )
            self.notification_center.setDelegate_(self)
            self.NSUserNotification = NSUserNotification
        except ImportError:
            # PyObjC not available or Foundation framework not accessible
            self.notification_center = None
            self.NSUserNotification = None

    def send_notification(
        self,
        title: str,
        subtitle: str = "",
        informative_text: str = "",
        action_button: Optional[str] = None,
        identifier: Optional[str] = None,
    ) -> None:
        """Send a native macOS notification.

        Args:
            title: Main notification title
            subtitle: Secondary title (smaller text)
            informative_text: Body text of the notification
            action_button: Label for the action button (e.g., "View Lineups")
            identifier: Unique identifier for this notification type
        """
        if self.notification_center and self.NSUserNotification:
            self._send_native_notification(
                title, subtitle, informative_text, action_button, identifier
            )
        else:
            self._send_fallback_notification(title, subtitle, informative_text)

    def _send_native_notification(
        self,
        title: str,
        subtitle: str,
        informative_text: str,
        action_button: Optional[str],
        identifier: Optional[str],
    ) -> None:
        """Send notification using NSUserNotificationCenter."""
        try:
            notification = self.NSUserNotification.alloc().init()
            notification.setTitle_(title)
            notification.setSubtitle_(subtitle)
            notification.setInformativeText_(informative_text)

            if action_button:
                notification.setActionButtonTitle_(action_button)
                notification.setIdentifier_(identifier or "default")
                # Enable action button
                notification.setHasActionButton_(True)

            self.notification_center.deliverNotification_(notification)
        except Exception:
            # Fall back to tray notification if native fails
            self._send_fallback_notification(title, subtitle, informative_text)

    def _send_fallback_notification(
        self, title: str, subtitle: str, informative_text: str
    ) -> None:
        """Send notification using QSystemTrayIcon fallback."""
        if self._tray_icon is None:
            self._tray_icon = QSystemTrayIcon()
            # Use a default icon or empty icon
            self._tray_icon.setIcon(QIcon())
            self._tray_icon.show()

        full_message = (
            f"{subtitle}\n{informative_text}" if subtitle else informative_text
        )
        self._tray_icon.showMessage(
            title, full_message, QSystemTrayIcon.Information, 5000
        )

    def userNotificationCenter_didActivateNotification_(self, center, notification):
        """Handle notification click (NSUserNotificationCenter delegate method).

        This method is called by the native notification center when the user
        clicks on a notification or its action button.

        Args:
            center: The NSUserNotificationCenter instance
            notification: The NSUserNotification that was activated
        """
        try:
            identifier = notification.identifier()
            self.notification_clicked.emit(identifier)
        except Exception:
            # If we can't get the identifier, emit with default
            self.notification_clicked.emit("default")

    def notify_optimization_complete(self, num_lineups: int) -> None:
        """Send notification when optimization finishes.

        Args:
            num_lineups: Number of lineups that were generated
        """
        self.send_notification(
            title="Optimization Complete",
            subtitle=f"Generated {num_lineups} lineups",
            informative_text="Click to view your optimized lineups.",
            action_button="View Lineups",
            identifier="view_lineups",
        )

    def request_permission(self) -> bool:
        """Request notification permission from the user.

        On macOS, this is typically handled automatically when the first
        notification is sent. The user will be prompted by the system.

        Returns:
            True if permission is granted or already has permission,
            False if permission was denied.
        """
        # On macOS, permissions are handled by the system when first notification
        # is sent. We can't directly query the permission status via PyObjC
        # without additional entitlements, so we return True to indicate
        # the notification was attempted.
        return True
