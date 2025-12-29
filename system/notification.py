# ===============================
# NOTIFICATION FUNCTIONS
# ===============================
"""
Handles desktop notifications
"""
try:
    from plyer import notification
    NOTIFIER_ENABLED = True
except ImportError:
    print("Warning: 'plyer' library not found. Desktop notifications are disabled.")
    NOTIFIER_ENABLED = False

def send_notification(title, message):
    """Send desktop notification."""
    if NOTIFIER_ENABLED:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name='Novel Processor',
                timeout=10
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")