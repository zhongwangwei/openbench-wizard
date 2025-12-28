#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for creating standalone executable.
Uses the existing openbench_wizard.spec file for cross-platform builds.
"""

import os
import sys
import subprocess


def install_dependencies():
    """Install required dependencies before building."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_file = os.path.join(base_dir, "requirements.txt")

    # Core build dependencies
    build_deps = ["pyinstaller"]

    print("Checking dependencies...")

    # Install from requirements.txt if exists
    if os.path.exists(requirements_file):
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", requirements_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    # Install build dependencies
    for dep in build_deps:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "--upgrade", dep],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    print("Dependencies OK.")


def build():
    """Build standalone executable using PyInstaller."""
    install_dependencies()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    spec_file = os.path.join(base_dir, "openbench_wizard.spec")

    if not os.path.exists(spec_file):
        print(f"Error: Spec file not found: {spec_file}")
        sys.exit(1)

    # Use existing spec file for build
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        spec_file
    ]

    print("Building application using spec file...")
    print(" ".join(cmd))

    subprocess.check_call(cmd)

    print("\nBuild complete!")
    print("Executable location: dist/")


if __name__ == "__main__":
    build()
