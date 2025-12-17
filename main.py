# -*- coding: utf-8 -*-
"""
OpenBench NML Wizard - Desktop application for generating NML configuration files.

Supports SSH X11 forwarding for remote server usage.
Usage:
    Local:  python main.py
    Remote: ssh -X user@server "cd /path/to/openbench_wizard && python main.py"
"""

import sys
import os
import platform
from pathlib import Path


def check_display_environment():
    """
    Check if DISPLAY environment is properly configured for X11.
    Returns tuple (is_valid, message).
    """
    system = platform.system()

    if system == "Darwin":
        # macOS - usually has native display
        return True, "macOS native display"

    if system == "Windows":
        # Windows - usually has native display
        return True, "Windows native display"

    # Linux/Unix - check DISPLAY environment
    display = os.environ.get("DISPLAY")

    if not display:
        return False, """
DISPLAY environment variable is not set.

If you're connecting via SSH, use X11 forwarding:
    ssh -X user@server    # Basic X11 forwarding
    ssh -Y user@server    # Trusted X11 forwarding (if -X doesn't work)

Or set DISPLAY manually:
    export DISPLAY=:0     # For local display
    export DISPLAY=localhost:10.0  # For X11 forwarding

Alternative: Use the CLI version for server environments:
    python cli.py --interactive
    python cli.py --config config.yaml
"""

    # Check if X11 forwarding is likely working
    if display.startswith("localhost:") or display.startswith(":"):
        return True, f"X11 display configured: {display}"

    return True, f"Using display: {display}"


def setup_x11_environment():
    """
    Setup X11 environment for optimal performance over SSH.
    """
    # Disable OpenGL for better X11 forwarding performance
    if "SSH_CONNECTION" in os.environ or "SSH_CLIENT" in os.environ:
        # We're in an SSH session
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        os.environ.setdefault("LIBGL_ALWAYS_INDIRECT", "1")

        # Reduce visual effects for better performance
        os.environ.setdefault("QT_GRAPHICSSYSTEM", "native")

        print("Detected SSH session, optimizing for X11 forwarding...")
        return True
    return False


def main():
    """Application entry point."""
    # Check display environment before importing Qt
    is_valid, message = check_display_environment()

    if not is_valid:
        print("Error: Cannot initialize display")
        print(message)
        sys.exit(1)

    # Setup X11 environment if needed
    is_ssh = setup_x11_environment()

    # Now import Qt modules
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from ui.main_window import MainWindow

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("OpenBench Wizard")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("OpenBench")

    # Load stylesheet
    styles_dir = Path(__file__).parent / "ui" / "styles"
    stylesheet_path = styles_dir / "theme.qss"
    checkmark_path = styles_dir / "checkmark.png"

    try:
        with open(stylesheet_path, "r") as f:
            stylesheet = f.read()
            # Replace placeholder with actual checkmark image path
            stylesheet = stylesheet.replace(
                "CHECKMARK_PATH",
                str(checkmark_path).replace("\\", "/")
            )
            app.setStyleSheet(stylesheet)
    except FileNotFoundError:
        pass  # Use default style

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
