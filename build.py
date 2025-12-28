#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for creating standalone executable.
"""

import os
import sys
import subprocess


def build():
    """Build standalone executable using PyInstaller."""
    # Ensure PyInstaller is installed and up to date
    print("Checking/updating PyInstaller...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    styles_dir = os.path.join(base_dir, "ui", "styles")
    resources_path = os.path.join(base_dir, "resources")
    icon_path = os.path.join(base_dir, "resources", "icons", "app.ico")
    main_path = os.path.join(base_dir, "main.py")

    # Build command - use onedir for macOS (onefile deprecated with windowed mode)
    import platform
    onefile_flag = "--onedir" if platform.system() == "Darwin" else "--onefile"

    # Hidden imports - PyInstaller often misses these dynamic imports
    hidden_imports = [
        # PySide6
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",
        "shiboken6",
        # Paramiko (SSH)
        "paramiko",
        "paramiko.transport",
        "paramiko.sftp",
        "paramiko.sftp_client",
        "paramiko.rsakey",
        "paramiko.ecdsakey",
        "paramiko.ed25519key",
        "paramiko.dsskey",
        # Cryptography (required by paramiko)
        "cryptography",
        "cryptography.hazmat.backends.openssl",
        "cryptography.hazmat.bindings.openssl",
        "cryptography.hazmat.primitives.ciphers",
        # Other
        "psutil",
        "yaml",
    ]

    # Libraries that need all submodules collected
    collect_all = [
        "PySide6",
        "paramiko",
        "cryptography",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "OpenBench-Wizard",
        "--windowed",
        onefile_flag,
        "--add-data", f"{styles_dir}{os.pathsep}ui/styles/",
        "--add-data", f"{resources_path}{os.pathsep}resources",
        main_path
    ]

    # Add collect-all for complex packages
    for pkg in collect_all:
        cmd.insert(-1, "--collect-all")
        cmd.insert(-1, pkg)

    # Add hidden imports
    for imp in hidden_imports:
        cmd.insert(-1, "--hidden-import")
        cmd.insert(-1, imp)

    # Add icon option if file exists
    if os.path.exists(icon_path):
        cmd.insert(-1, "--icon")
        cmd.insert(-1, icon_path)

    print("Building application...")
    print(" ".join(cmd))

    subprocess.check_call(cmd)

    print("\nBuild complete!")
    print("Executable location: dist/OpenBench-Wizard")


if __name__ == "__main__":
    build()
