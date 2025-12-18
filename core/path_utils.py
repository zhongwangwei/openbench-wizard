# -*- coding: utf-8 -*-
"""
Cross-platform path utilities for converting and validating paths.
"""

import os
import sys
from typing import Optional, Tuple


def get_openbench_root() -> str:
    """
    Find the OpenBench root directory.

    Returns:
        Absolute path to OpenBench root directory
    """
    # Try to load saved path first
    try:
        home_dir = os.path.expanduser("~")
        config_file = os.path.join(home_dir, ".openbench_wizard", "config.txt")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                path = f.read().strip()
                if path and os.path.exists(path):
                    return os.path.normpath(path)
    except Exception:
        pass

    # Search common locations
    possible_roots = [
        os.path.join(os.path.expanduser("~"), "Desktop", "OpenBench"),
        os.path.join(os.path.expanduser("~"), "Documents", "OpenBench"),
        os.path.join(os.path.expanduser("~"), "OpenBench"),
    ]

    for root in possible_roots:
        if root and os.path.exists(os.path.join(root, "openbench", "openbench.py")):
            return os.path.normpath(root)

    # Fallback to current working directory
    return os.path.normpath(os.getcwd())


def to_absolute_path(path: str, base_dir: Optional[str] = None) -> str:
    """
    Convert a path to absolute path.

    Args:
        path: Path to convert (can be relative or absolute)
        base_dir: Base directory for relative paths (defaults to OpenBench root)

    Returns:
        Absolute path with normalized separators for current platform
    """
    if not path:
        return ""

    # Normalize path separators for current platform
    path = normalize_path_separators(path)

    # If already absolute, just normalize and return
    if os.path.isabs(path):
        return os.path.normpath(path)

    # Get base directory
    if base_dir is None:
        base_dir = get_openbench_root()
    else:
        base_dir = os.path.normpath(base_dir)

    # Handle relative paths starting with ./
    if path.startswith("./") or path.startswith(".\\"):
        path = path[2:]

    # Join with base directory and normalize
    return os.path.normpath(os.path.join(base_dir, path))


def normalize_path_separators(path: str) -> str:
    """
    Normalize path separators for the current platform.

    Args:
        path: Path string with potentially mixed separators

    Returns:
        Path with correct separators for current platform
    """
    if not path:
        return ""

    # Replace both types of separators with the current platform's separator
    if os.sep == '/':
        return path.replace('\\', '/')
    else:
        return path.replace('/', '\\')


def validate_path(path: str, path_type: str = "file", must_exist: bool = True) -> Tuple[bool, str]:
    """
    Validate a path exists and is the correct type.

    Args:
        path: Path to validate
        path_type: "file" or "directory"
        must_exist: If True, path must exist; if False, parent directory must exist

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return True, ""  # Empty paths are OK (optional fields)

    # Normalize path
    path = os.path.normpath(path)

    if must_exist:
        if not os.path.exists(path):
            return False, f"Path does not exist: {path}"

        if path_type == "file" and not os.path.isfile(path):
            return False, f"Path is not a file: {path}"

        if path_type == "directory" and not os.path.isdir(path):
            return False, f"Path is not a directory: {path}"
    else:
        # Check parent directory exists
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            return False, f"Parent directory does not exist: {parent}"

    return True, ""


def convert_paths_in_dict(data: dict, base_dir: Optional[str] = None, path_keys: Optional[list] = None,
                          all_values_are_paths_keys: Optional[list] = None) -> dict:
    """
    Recursively convert all path values in a dictionary to absolute paths.

    Args:
        data: Dictionary containing paths
        base_dir: Base directory for relative paths
        path_keys: List of keys that contain paths (if None, uses default list)
        all_values_are_paths_keys: List of keys whose child dict has ALL values as paths
                                   (e.g., 'def_nml' where all values are path strings)

    Returns:
        Dictionary with converted paths
    """
    if path_keys is None:
        path_keys = [
            "root_dir", "basedir", "fulllist", "model_namelist",
            "reference_nml", "simulation_nml", "statistics_nml", "figure_nml",
            "def_nml_path", "data_path", "file_path", "output_dir"
        ]

    if all_values_are_paths_keys is None:
        all_values_are_paths_keys = ["def_nml"]

    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        # Special handling for sections where ALL values are paths (like def_nml)
        if key in all_values_are_paths_keys and isinstance(value, dict):
            result[key] = {
                k: to_absolute_path(v, base_dir) if isinstance(v, str) and v else v
                for k, v in value.items()
            }
        elif isinstance(value, dict):
            result[key] = convert_paths_in_dict(value, base_dir, path_keys, all_values_are_paths_keys)
        elif isinstance(value, list):
            result[key] = [
                convert_paths_in_dict(item, base_dir, path_keys, all_values_are_paths_keys) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str) and key in path_keys and value:
            result[key] = to_absolute_path(value, base_dir)
        else:
            result[key] = value

    return result


def validate_paths_in_dict(data: dict, path_keys: Optional[list] = None) -> list:
    """
    Validate all paths in a dictionary.

    Args:
        data: Dictionary containing paths
        path_keys: List of keys that contain paths

    Returns:
        List of (key, path, error_message) tuples for invalid paths
    """
    if path_keys is None:
        path_keys = [
            "root_dir", "basedir", "fulllist", "model_namelist",
            "reference_nml", "simulation_nml", "statistics_nml", "figure_nml"
        ]

    errors = []

    def _validate_recursive(d, prefix=""):
        if not isinstance(d, dict):
            return

        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                _validate_recursive(value, full_key)
            elif isinstance(value, str) and key in path_keys and value:
                # Determine path type
                path_type = "directory" if key in ["root_dir", "basedir", "output_dir"] else "file"
                is_valid, error = validate_path(value, path_type)
                if not is_valid:
                    errors.append((full_key, value, error))

    _validate_recursive(data)
    return errors
