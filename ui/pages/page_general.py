# -*- coding: utf-8 -*-
"""
General settings page.
"""

import os
import sys

from PySide6.QtWidgets import (
    QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QGroupBox, QHBoxLayout,
    QGridLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout
)

from ui.pages.base_page import BasePage
from ui.widgets import PathSelector
from core.path_utils import to_absolute_path, get_openbench_root


class PageGeneral(BasePage):
    """General configuration page."""

    PAGE_ID = "general"
    PAGE_TITLE = "General Settings"
    PAGE_SUBTITLE = "Configure basic project settings and evaluation options"

    def _setup_content(self):
        """Setup page content."""
        # === Project Info ===
        project_group = QGroupBox("Project Information")
        project_layout = QFormLayout(project_group)

        # Output directory first
        self.basedir_input = PathSelector(mode="directory", placeholder="Output directory")
        self.basedir_input.path_changed.connect(self._on_basedir_changed)
        project_layout.addRow("Output Directory:", self.basedir_input)

        # Project name with confirm button
        name_layout = QHBoxLayout()
        self.basename_input = QLineEdit()
        self.basename_input.setPlaceholderText("Project name (e.g., Initial_test)")
        self.basename_input.textChanged.connect(self._on_project_name_changed)
        name_layout.addWidget(self.basename_input)

        self.btn_confirm_name = QPushButton("Confirm")
        self.btn_confirm_name.setFixedWidth(80)
        self.btn_confirm_name.clicked.connect(self._on_confirm_project)
        name_layout.addWidget(self.btn_confirm_name)

        project_layout.addRow("Project Name:", name_layout)

        self.content_layout.addWidget(project_group)

        # === Spatial-Temporal Settings ===
        st_group = QGroupBox("Spatial-Temporal Settings")
        st_layout = QGridLayout(st_group)

        # Year range
        self.year_range_label = QLabel("Year Range:")
        st_layout.addWidget(self.year_range_label, 0, 0)
        self.syear_spin = QSpinBox()
        self.syear_spin.setRange(1900, 2100)
        self.syear_spin.setValue(2000)
        self.syear_spin.valueChanged.connect(self._on_year_range_changed)
        st_layout.addWidget(self.syear_spin, 0, 1)
        self.year_range_to_label = QLabel("to")
        st_layout.addWidget(self.year_range_to_label, 0, 2)
        self.eyear_spin = QSpinBox()
        self.eyear_spin.setRange(1900, 2100)
        self.eyear_spin.setValue(2020)
        self.eyear_spin.valueChanged.connect(self._on_year_range_changed)
        st_layout.addWidget(self.eyear_spin, 0, 3)

        # Minimum year threshold
        st_layout.addWidget(QLabel("Min Year Threshold:"), 1, 0)
        self.min_year_spin = QDoubleSpinBox()
        self.min_year_spin.setRange(0.0, 100.0)
        self.min_year_spin.setValue(1.0)
        self.min_year_spin.setSingleStep(0.5)
        self.min_year_spin.setToolTip("Minimum number of years of valid data required")
        st_layout.addWidget(self.min_year_spin, 1, 1)

        # Latitude range
        st_layout.addWidget(QLabel("Latitude Range:"), 2, 0)
        self.min_lat_spin = QDoubleSpinBox()
        self.min_lat_spin.setRange(-90.0, 90.0)
        self.min_lat_spin.setValue(-90.0)
        st_layout.addWidget(self.min_lat_spin, 2, 1)
        st_layout.addWidget(QLabel("to"), 2, 2)
        self.max_lat_spin = QDoubleSpinBox()
        self.max_lat_spin.setRange(-90.0, 90.0)
        self.max_lat_spin.setValue(90.0)
        st_layout.addWidget(self.max_lat_spin, 2, 3)

        # Longitude range
        st_layout.addWidget(QLabel("Longitude Range:"), 3, 0)
        self.min_lon_spin = QDoubleSpinBox()
        self.min_lon_spin.setRange(-180.0, 180.0)
        self.min_lon_spin.setValue(-180.0)
        st_layout.addWidget(self.min_lon_spin, 3, 1)
        st_layout.addWidget(QLabel("to"), 3, 2)
        self.max_lon_spin = QDoubleSpinBox()
        self.max_lon_spin.setRange(-180.0, 180.0)
        self.max_lon_spin.setValue(180.0)
        st_layout.addWidget(self.max_lon_spin, 3, 3)

        # Resolution
        st_layout.addWidget(QLabel("Time Resolution:"), 4, 0)
        self.tim_res_combo = QComboBox()
        self.tim_res_combo.addItems(["month", "day", "hour", "year"])
        st_layout.addWidget(self.tim_res_combo, 4, 1)

        st_layout.addWidget(QLabel("Grid Resolution:"), 4, 2)
        self.grid_res_spin = QDoubleSpinBox()
        self.grid_res_spin.setRange(0.01, 10.0)
        self.grid_res_spin.setValue(2.0)
        self.grid_res_spin.setSingleStep(0.1)
        self.grid_res_spin.setSuffix("°")
        st_layout.addWidget(self.grid_res_spin, 4, 3)

        # Timezone
        st_layout.addWidget(QLabel("Timezone:"), 5, 0)
        self.timezone_spin = QDoubleSpinBox()
        self.timezone_spin.setRange(-12.0, 14.0)
        self.timezone_spin.setValue(0.0)
        self.timezone_spin.setSingleStep(0.5)
        st_layout.addWidget(self.timezone_spin, 5, 1)

        # Weight
        st_layout.addWidget(QLabel("Weight:"), 5, 2)
        self.weight_combo = QComboBox()
        self.weight_combo.addItems(["None", "area", "mass"])
        self.weight_combo.setToolTip("Weight method for spatial averaging (None, area-weighted, or mass-weighted)")
        st_layout.addWidget(self.weight_combo, 5, 3)

        self.content_layout.addWidget(st_group)

        # === Feature Toggles ===
        toggle_group = QGroupBox("Feature Toggles")
        toggle_layout = QGridLayout(toggle_group)

        self.cb_evaluation = QCheckBox("Evaluation")
        self.cb_evaluation.setChecked(True)
        self.cb_evaluation.stateChanged.connect(self._on_toggle_changed)
        toggle_layout.addWidget(self.cb_evaluation, 0, 0)

        self.cb_comparison = QCheckBox("Comparison")
        self.cb_comparison.setChecked(True)
        self.cb_comparison.stateChanged.connect(self._on_toggle_changed)
        toggle_layout.addWidget(self.cb_comparison, 0, 1)

        self.cb_statistics = QCheckBox("Statistics")
        self.cb_statistics.stateChanged.connect(self._on_toggle_changed)
        toggle_layout.addWidget(self.cb_statistics, 0, 2)

        self.cb_debug = QCheckBox("Debug Mode")
        self.cb_debug.stateChanged.connect(self._on_toggle_changed)
        toggle_layout.addWidget(self.cb_debug, 1, 0)

        self.cb_report = QCheckBox("Generate Report")
        self.cb_report.setChecked(True)
        self.cb_report.stateChanged.connect(self._on_toggle_changed)
        toggle_layout.addWidget(self.cb_report, 1, 1)

        self.cb_only_drawing = QCheckBox("Only Drawing")
        self.cb_only_drawing.stateChanged.connect(self._on_toggle_changed)
        toggle_layout.addWidget(self.cb_only_drawing, 1, 2)

        self.cb_unified_mask = QCheckBox("Unified Mask")
        self.cb_unified_mask.setChecked(True)
        self.cb_unified_mask.stateChanged.connect(self._on_toggle_changed)
        toggle_layout.addWidget(self.cb_unified_mask, 2, 0)

        self.content_layout.addWidget(toggle_group)

        # === Groupby Options ===
        groupby_group = QGroupBox("Groupby Options")
        groupby_layout = QHBoxLayout(groupby_group)

        self.cb_igbp = QCheckBox("IGBP Groupby")
        self.cb_igbp.setChecked(True)
        groupby_layout.addWidget(self.cb_igbp)

        self.cb_pft = QCheckBox("PFT Groupby")
        self.cb_pft.setChecked(True)
        groupby_layout.addWidget(self.cb_pft)

        self.cb_climate = QCheckBox("Climate Zone Groupby")
        self.cb_climate.setChecked(True)
        groupby_layout.addWidget(self.cb_climate)

        groupby_layout.addStretch()

        self.content_layout.addWidget(groupby_group)

        # === Runtime Environment ===
        runtime_group = QGroupBox("Runtime Environment")
        runtime_layout = QFormLayout(runtime_group)

        # Python path with auto-detect and browse
        python_layout = QHBoxLayout()
        self.python_path_combo = QComboBox()
        self.python_path_combo.setEditable(True)
        self.python_path_combo.setMinimumWidth(300)
        self.python_path_combo.currentTextChanged.connect(self._on_python_path_changed)
        python_layout.addWidget(self.python_path_combo)

        self.btn_detect_python = QPushButton("Detect")
        self.btn_detect_python.setFixedWidth(60)
        self.btn_detect_python.clicked.connect(self._detect_python_interpreters)
        self.btn_detect_python.setToolTip("Auto-detect available Python interpreters")
        python_layout.addWidget(self.btn_detect_python)

        self.btn_browse_python = QPushButton("Browse")
        self.btn_browse_python.setFixedWidth(60)
        self.btn_browse_python.clicked.connect(self._browse_python)
        python_layout.addWidget(self.btn_browse_python)

        runtime_layout.addRow("Python Path:", python_layout)

        # Conda environment selector
        env_layout = QHBoxLayout()
        self.conda_env_combo = QComboBox()
        self.conda_env_combo.setMinimumWidth(200)
        self.conda_env_combo.addItem("(Not using conda environment)")
        self.conda_env_combo.currentTextChanged.connect(self._on_conda_env_changed)
        env_layout.addWidget(self.conda_env_combo)

        self.btn_refresh_envs = QPushButton("Refresh")
        self.btn_refresh_envs.setFixedWidth(60)
        self.btn_refresh_envs.clicked.connect(self._refresh_conda_envs)
        self.btn_refresh_envs.setToolTip("Refresh available conda environments")
        env_layout.addWidget(self.btn_refresh_envs)

        env_layout.addStretch()
        runtime_layout.addRow("Conda Environment:", env_layout)

        # CPU cores
        self.num_cores_spin = QSpinBox()
        self.num_cores_spin.setRange(1, 128)
        self.num_cores_spin.setValue(4)
        runtime_layout.addRow("CPU Cores:", self.num_cores_spin)

        self.content_layout.addWidget(runtime_group)

        # Initial detection of Python interpreters
        self._detect_python_interpreters()

    def _detect_python_interpreters(self):
        """Auto-detect available Python interpreters."""
        import shutil
        import subprocess

        detected = []
        is_windows = sys.platform == 'win32'
        user_home = os.path.expanduser('~')

        # PRIORITY 1: Check active conda environment (CONDA_PREFIX)
        conda_prefix = os.environ.get('CONDA_PREFIX')
        if conda_prefix:
            if is_windows:
                conda_python = os.path.join(conda_prefix, 'python.exe')
            else:
                conda_python = os.path.join(conda_prefix, 'bin', 'python')
            if os.path.exists(conda_python):
                detected.append(f"{conda_python} (active conda)")

        # PRIORITY 2: Check common conda/miniforge locations
        if is_windows:
            conda_paths = [
                (os.path.join(user_home, 'anaconda3', 'python.exe'), 'anaconda3'),
                (os.path.join(user_home, 'miniconda3', 'python.exe'), 'miniconda3'),
                (os.path.join(user_home, 'miniforge3', 'python.exe'), 'miniforge3'),
                (os.path.join(user_home, 'Anaconda3', 'python.exe'), 'Anaconda3'),
                (os.path.join(user_home, 'Miniconda3', 'python.exe'), 'Miniconda3'),
            ]
        else:
            conda_paths = [
                (os.path.join(user_home, 'miniforge3', 'bin', 'python'), 'miniforge3'),
                (os.path.join(user_home, 'miniconda3', 'bin', 'python'), 'miniconda3'),
                (os.path.join(user_home, 'anaconda3', 'bin', 'python'), 'anaconda3'),
                ('/opt/homebrew/bin/python3', 'homebrew'),
                ('/usr/local/bin/python3', 'local'),
            ]

        for path, label in conda_paths:
            if os.path.exists(path) and path not in [d.split(' ')[0] for d in detected]:
                detected.append(f"{path} ({label})")

        # PRIORITY 3: Check PATH
        if is_windows:
            python_names = ['python', 'python3']
        else:
            python_names = ['python3', 'python']

        for name in python_names:
            path = shutil.which(name)
            if path and path not in [d.split(' ')[0] for d in detected]:
                # Skip system Python on macOS/Linux
                if path == '/usr/bin/python3':
                    detected.append(f"{path} (system - may lack packages)")
                else:
                    detected.append(f"{path} (PATH)")

        # Update combo box
        current_text = self.python_path_combo.currentText()
        self.python_path_combo.blockSignals(True)
        self.python_path_combo.clear()

        for item in detected:
            self.python_path_combo.addItem(item)

        # Restore previous selection if valid
        if current_text:
            idx = self.python_path_combo.findText(current_text)
            if idx >= 0:
                self.python_path_combo.setCurrentIndex(idx)
            else:
                # Try to find by path only
                current_path = current_text.split(' ')[0]
                for i in range(self.python_path_combo.count()):
                    if self.python_path_combo.itemText(i).startswith(current_path):
                        self.python_path_combo.setCurrentIndex(i)
                        break

        self.python_path_combo.blockSignals(False)

        # Also refresh conda environments
        self._refresh_conda_envs()

    def _browse_python(self):
        """Open file dialog to select Python interpreter."""
        from PySide6.QtWidgets import QFileDialog

        if sys.platform == 'win32':
            filter_str = "Python (python.exe);;All Files (*)"
        else:
            filter_str = "All Files (*)"

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python Interpreter",
            os.path.expanduser("~"),
            filter_str
        )

        if path:
            self.python_path_combo.setCurrentText(path)

    def _on_python_path_changed(self, text):
        """Handle Python path change."""
        self._save_to_config_no_sync()
        # Refresh conda environments based on the selected Python
        self._refresh_conda_envs()

    def _refresh_conda_envs(self):
        """Refresh the list of available conda environments."""
        import subprocess

        current_python = self.python_path_combo.currentText().split(' ')[0]
        envs = self._get_conda_envs(current_python)

        current_env = self.conda_env_combo.currentText()
        self.conda_env_combo.blockSignals(True)
        self.conda_env_combo.clear()
        self.conda_env_combo.addItem("(Not using conda environment)")

        for env_name, env_path in envs:
            self.conda_env_combo.addItem(f"{env_name}", env_path)

        # Restore previous selection
        if current_env:
            idx = self.conda_env_combo.findText(current_env)
            if idx >= 0:
                self.conda_env_combo.setCurrentIndex(idx)

        self.conda_env_combo.blockSignals(False)

    def _get_conda_envs(self, python_path: str) -> list:
        """Get list of conda environments.

        Returns list of (env_name, env_path) tuples.
        """
        import subprocess
        import json

        envs = []

        # Try to find conda executable based on the Python path
        if not python_path:
            return envs

        # Determine conda base path from Python path
        python_dir = os.path.dirname(python_path)
        if sys.platform == 'win32':
            # Windows: python is in base/python.exe or base/envs/name/python.exe
            if 'envs' in python_dir:
                conda_base = python_dir.split('envs')[0].rstrip(os.sep)
            else:
                conda_base = python_dir
            conda_exe = os.path.join(conda_base, 'Scripts', 'conda.exe')
            if not os.path.exists(conda_exe):
                conda_exe = os.path.join(conda_base, 'condabin', 'conda.bat')
        else:
            # Unix: python is in base/bin/python or base/envs/name/bin/python
            if 'envs' in python_dir:
                conda_base = python_dir.split('envs')[0].rstrip(os.sep)
            else:
                conda_base = os.path.dirname(python_dir)  # go up from bin/
            conda_exe = os.path.join(conda_base, 'bin', 'conda')

        if not os.path.exists(conda_exe):
            # Try common locations
            user_home = os.path.expanduser('~')
            for base in ['miniforge3', 'miniconda3', 'anaconda3']:
                if sys.platform == 'win32':
                    test_exe = os.path.join(user_home, base, 'Scripts', 'conda.exe')
                else:
                    test_exe = os.path.join(user_home, base, 'bin', 'conda')
                if os.path.exists(test_exe):
                    conda_exe = test_exe
                    conda_base = os.path.join(user_home, base)
                    break

        if not os.path.exists(conda_exe):
            return envs

        try:
            result = subprocess.run(
                [conda_exe, 'env', 'list', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for env_path in data.get('envs', []):
                    env_name = os.path.basename(env_path)
                    if env_name == conda_base.split(os.sep)[-1]:
                        env_name = 'base'
                    envs.append((env_name, env_path))
        except Exception:
            pass

        return envs

    def _on_conda_env_changed(self, text):
        """Handle conda environment selection change."""
        if text == "(Not using conda environment)":
            self._save_to_config_no_sync()
            return

        # Get the environment path from combo box data
        idx = self.conda_env_combo.currentIndex()
        if idx > 0:
            env_path = self.conda_env_combo.itemData(idx)
            if env_path:
                # Update Python path to use the environment's Python
                if sys.platform == 'win32':
                    env_python = os.path.join(env_path, 'python.exe')
                else:
                    env_python = os.path.join(env_path, 'bin', 'python')

                if os.path.exists(env_python):
                    self.python_path_combo.blockSignals(True)
                    self.python_path_combo.setCurrentText(f"{env_python} ({text})")
                    self.python_path_combo.blockSignals(False)

        self._save_to_config_no_sync()

    def _on_toggle_changed(self, state):
        """Handle feature toggle changes."""
        self.save_to_config()

    def _on_year_range_changed(self, value):
        """Handle year range changes - save and sync namelists."""
        self.save_to_config()
        self.controller.sync_namelists()

    def _has_per_var_time_range(self) -> bool:
        """Check if any source has per_var_time_range enabled."""
        # Check ref_data source_configs
        ref_source_configs = self.controller.config.get("ref_data", {}).get("source_configs", {})
        for source_config in ref_source_configs.values():
            general = source_config.get("general", {})
            if general.get("per_var_time_range", False):
                return True

        # Check sim_data source_configs
        sim_source_configs = self.controller.config.get("sim_data", {}).get("source_configs", {})
        for source_config in sim_source_configs.values():
            general = source_config.get("general", {})
            if general.get("per_var_time_range", False):
                return True

        return False

    def update_year_range_state(self):
        """Update Year Range tooltip based on per_var_time_range settings.

        Year Range is always editable. When per-variable time range is enabled
        on any source, these values are used as defaults but may be overridden.
        """
        has_per_var = self._has_per_var_time_range()

        if has_per_var:
            tooltip = "Some sources use per-variable time range. This value is used for sources without per-variable settings."
            self.syear_spin.setToolTip(tooltip)
            self.eyear_spin.setToolTip(tooltip)
        else:
            self.syear_spin.setToolTip("")
            self.eyear_spin.setToolTip("")

    def _on_project_name_changed(self, text):
        """Handle project name changes.

        Note: Only saves to config without triggering sync_namelists.
        Directory creation happens only when Confirm button is clicked.
        """
        self._save_to_config_no_sync()

    def _on_basedir_changed(self, path):
        """Handle output directory changes.

        Note: Only saves to config without triggering sync_namelists.
        Directory creation happens only when Confirm button is clicked.
        """
        self._save_to_config_no_sync()

    def _on_confirm_project(self):
        """Handle confirm project button click."""
        import os
        import re

        basename = self.basename_input.text().strip()
        if not basename:
            QMessageBox.warning(self, "Error", "Please enter a project name.")
            return

        # Validate filesystem-safe characters
        # Allow letters, numbers, underscores, hyphens, and dots
        if not re.match(r'^[a-zA-Z0-9_.-]+$', basename):
            QMessageBox.warning(
                self, "Invalid Name",
                "Project name can only contain:\n"
                "• Letters (a-z, A-Z)\n"
                "• Numbers (0-9)\n"
                "• Underscores (_)\n"
                "• Hyphens (-)\n"
                "• Dots (.)"
            )
            return

        # Check for reserved names on Windows
        reserved_names = {'CON', 'PRN', 'AUX', 'NUL',
                         'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                         'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        if basename.upper() in reserved_names:
            QMessageBox.warning(self, "Invalid Name", f"'{basename}' is a reserved system name.")
            return

        # Check if output directory is set
        basedir = self.basedir_input.path().strip()
        if not basedir:
            QMessageBox.warning(self, "Error", "Please select an output directory first.")
            return

        # Save config first so get_output_dir() can compute correctly
        self.save_to_config()

        # Use controller.get_output_dir() to get the proper output path (basedir/basename)
        output_dir = self.controller.get_output_dir()

        # Create the output directory and nml subdirectories
        try:
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(os.path.join(output_dir, "nml", "sim"), exist_ok=True)
            os.makedirs(os.path.join(output_dir, "nml", "ref"), exist_ok=True)

            # Trigger namelist sync
            self.controller.sync_namelists()

            QMessageBox.information(
                self,
                "Project Created",
                f"Project folder created:\n{output_dir}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project folder:\n{str(e)}")

    def load_from_config(self):
        """Load settings from controller config."""
        import os
        import sys

        general = self.controller.config.get("general", {})
        basename = general.get("basename", "")

        # Block signals to prevent save_to_config from being called during load
        self.basename_input.blockSignals(True)
        self.basename_input.setText(basename)
        self.basename_input.blockSignals(False)

        # Get basedir and convert to absolute path (without appending project name)
        basedir = general.get("basedir", "")

        # Find OpenBench root directory
        openbench_root = self._get_openbench_root()

        if not basedir or basedir == "./output":
            # Set default to OpenBench/output (without project name)
            basedir = os.path.join(openbench_root, "output")
        elif not os.path.isabs(basedir):
            # Convert relative path to absolute
            if basedir.startswith("./"):
                basedir = basedir[2:]
            basedir = os.path.normpath(os.path.join(openbench_root, basedir))

        # Set path without emitting signal to prevent save_to_config loop
        self.basedir_input.set_path(basedir, emit_signal=False)

        self.syear_spin.setValue(general.get("syear", 2000))
        self.eyear_spin.setValue(general.get("eyear", 2020))
        self.min_year_spin.setValue(general.get("min_year", 1.0))
        self.min_lat_spin.setValue(general.get("min_lat", -90.0))
        self.max_lat_spin.setValue(general.get("max_lat", 90.0))
        self.min_lon_spin.setValue(general.get("min_lon", -180.0))
        self.max_lon_spin.setValue(general.get("max_lon", 180.0))

        tim_res = general.get("compare_tim_res", "month")
        idx = self.tim_res_combo.findText(tim_res)
        if idx >= 0:
            self.tim_res_combo.setCurrentIndex(idx)

        self.grid_res_spin.setValue(general.get("compare_grid_res", 2.0))
        self.timezone_spin.setValue(general.get("compare_tzone", 0.0))

        self.cb_evaluation.setChecked(general.get("evaluation", True))
        self.cb_comparison.setChecked(general.get("comparison", True))
        self.cb_statistics.setChecked(general.get("statistics", False))
        self.cb_debug.setChecked(general.get("debug_mode", False))
        self.cb_report.setChecked(general.get("generate_report", True))
        self.cb_only_drawing.setChecked(general.get("only_drawing", False))

        self.cb_igbp.setChecked(general.get("IGBP_groupby", True))
        self.cb_pft.setChecked(general.get("PFT_groupby", True))
        self.cb_climate.setChecked(general.get("Climate_zone_groupby", True))
        self.cb_unified_mask.setChecked(general.get("unified_mask", True))

        self.num_cores_spin.setValue(general.get("num_cores", 4))

        # Load Python path (after detection has run)
        python_path = general.get("python_path", "")
        if python_path:
            self.python_path_combo.blockSignals(True)
            # Check if it's already in the list
            found = False
            for i in range(self.python_path_combo.count()):
                if self.python_path_combo.itemText(i).startswith(python_path):
                    self.python_path_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.python_path_combo.setCurrentText(python_path)
            self.python_path_combo.blockSignals(False)

        # Load conda environment
        conda_env = general.get("conda_env", "")
        if conda_env:
            self.conda_env_combo.blockSignals(True)
            idx = self.conda_env_combo.findText(conda_env)
            if idx >= 0:
                self.conda_env_combo.setCurrentIndex(idx)
            self.conda_env_combo.blockSignals(False)

        weight = general.get("weight", "none")
        if weight is None:
            weight = "none"
        # Map lowercase to display text
        weight_map = {"none": "None", "area": "area", "mass": "mass"}
        display_weight = weight_map.get(str(weight).lower(), "None")
        idx = self.weight_combo.findText(display_weight)
        if idx >= 0:
            self.weight_combo.setCurrentIndex(idx)

        # Update Year Range state based on per_var_time_range settings
        self.update_year_range_state()

    def _save_to_config_no_sync(self):
        """Save settings to controller config WITHOUT triggering sync_namelists.

        Used for intermediate saves (like typing project name) where we don't
        want to create directories yet.
        """
        import os

        new_basename = self.basename_input.text().strip()
        new_basedir = self.basedir_input.path().strip()

        # If basedir ends with basename, use the parent directory as basedir
        # This prevents path duplication like /path/F58/F58
        if new_basename and new_basedir:
            if os.path.basename(new_basedir.rstrip(os.sep)) == new_basename:
                new_basedir = os.path.dirname(new_basedir.rstrip(os.sep))

        general = {
            "basename": new_basename,
            "basedir": new_basedir,
            "syear": self.syear_spin.value(),
            "eyear": self.eyear_spin.value(),
            "min_year": self.min_year_spin.value(),
            "min_lat": self.min_lat_spin.value(),
            "max_lat": self.max_lat_spin.value(),
            "min_lon": self.min_lon_spin.value(),
            "max_lon": self.max_lon_spin.value(),
            "compare_tim_res": self.tim_res_combo.currentText(),
            "compare_grid_res": self.grid_res_spin.value(),
            "compare_tzone": self.timezone_spin.value(),
            "evaluation": self.cb_evaluation.isChecked(),
            "comparison": self.cb_comparison.isChecked(),
            "statistics": self.cb_statistics.isChecked(),
            "debug_mode": self.cb_debug.isChecked(),
            "generate_report": self.cb_report.isChecked(),
            "only_drawing": self.cb_only_drawing.isChecked(),
            "IGBP_groupby": self.cb_igbp.isChecked(),
            "PFT_groupby": self.cb_pft.isChecked(),
            "Climate_zone_groupby": self.cb_climate.isChecked(),
            "unified_mask": self.cb_unified_mask.isChecked(),
            "num_cores": self.num_cores_spin.value(),
            "weight": self.weight_combo.currentText().lower(),
            "python_path": self.python_path_combo.currentText().split(' ')[0],  # Extract path only
            "conda_env": self.conda_env_combo.currentText() if self.conda_env_combo.currentIndex() > 0 else "",
        }
        self.controller.update_section("general", general)

    def save_to_config(self):
        """Save settings to controller config."""
        import os

        # Check if basename or basedir changed (affects output directory)
        old_general = self.controller.config.get("general", {})
        old_basename = old_general.get("basename", "")
        old_basedir = old_general.get("basedir", "")

        # Save config first
        self._save_to_config_no_sync()

        new_basename = self.basename_input.text().strip()
        new_basedir = self.basedir_input.path().strip()

        # Trigger namelist sync if output location changed
        if new_basename != old_basename or new_basedir != old_basedir:
            self.controller.sync_namelists()

    def validate(self) -> bool:
        """Validate page input."""
        if not self.basename_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Project name is required.")
            self.basename_input.setFocus()
            return False

        if not self.basedir_input.path().strip():
            QMessageBox.warning(self, "Validation Error", "Output directory is required.")
            self.basedir_input.setFocus()
            return False

        if self.syear_spin.value() > self.eyear_spin.value():
            QMessageBox.warning(self, "Validation Error", "Start year must be <= end year.")
            self.syear_spin.setFocus()
            return False

        if self.min_lat_spin.value() > self.max_lat_spin.value():
            QMessageBox.warning(self, "Validation Error", "Minimum latitude must be <= maximum latitude.")
            self.min_lat_spin.setFocus()
            return False

        if self.min_lon_spin.value() > self.max_lon_spin.value():
            QMessageBox.warning(self, "Validation Error", "Minimum longitude must be <= maximum longitude.")
            self.min_lon_spin.setFocus()
            return False

        self.save_to_config()
        return True

    def _get_openbench_root(self) -> str:
        """Get the OpenBench root directory."""
        # Use controller's project_root if available
        if self.controller.project_root:
            return self.controller.project_root
        return get_openbench_root()
