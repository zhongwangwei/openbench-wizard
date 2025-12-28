#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for creating standalone executable.
Uses the existing openbench_wizard.spec file for cross-platform builds.
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
