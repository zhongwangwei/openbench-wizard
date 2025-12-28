# -*- coding: utf-8 -*-
"""
Runtime Environment page for configuring local or remote execution.
"""

import logging
import os
import sys
import shutil
import yaml

from PySide6.QtWidgets import (
    QHBoxLayout, QFormLayout, QSpinBox, QLabel,
    QGroupBox, QRadioButton, QButtonGroup, QComboBox,
    QPushButton, QFileDialog, QMessageBox
)

from ui.pages.base_page import BasePage
from ui.widgets.remote_config import RemoteConfigWidget

logger = logging.getLogger(__name__)


def get_default_runtime_settings_path() -> str:
    """Get the default path for runtime settings file."""
    config_dir = os.path.join(os.path.expanduser("~"), ".openbench_wizard")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "runtime_settings.yaml")


class PageRuntime(BasePage):
    """Runtime Environment configuration page."""

    PAGE_ID = "runtime"
    PAGE_TITLE = "Runtime Environment"
    PAGE_SUBTITLE = "Configure where OpenBench will run - locally on this machine or on a remote server."

    def _setup_content(self):
        """Setup page content."""
        # === Execution Mode ===
        mode_group = QGroupBox("Execution Mode")
        mode_layout = QFormLayout(mode_group)
        mode_layout.setSpacing(12)

        mode_buttons = QHBoxLayout()
        mode_buttons.setSpacing(20)
        self.execution_mode_group = QButtonGroup(self)
        self.radio_local = QRadioButton("Local")
        self.radio_remote = QRadioButton("Remote Server")
        self.radio_local.setChecked(True)
        self.execution_mode_group.addButton(self.radio_local)
        self.execution_mode_group.addButton(self.radio_remote)
        self.radio_local.toggled.connect(self._on_execution_mode_changed)
        mode_buttons.addWidget(self.radio_local)
        mode_buttons.addWidget(self.radio_remote)
        mode_buttons.addStretch()

        # Save/Load Settings buttons
        self.btn_save_settings = QPushButton("Save Settings")
        self.btn_save_settings.setToolTip("Save runtime settings to a file")
        self.btn_save_settings.clicked.connect(self._save_runtime_settings)
        mode_buttons.addWidget(self.btn_save_settings)

        self.btn_load_settings = QPushButton("Load Settings")
        self.btn_load_settings.setToolTip("Load runtime settings from a file")
        self.btn_load_settings.clicked.connect(self._load_runtime_settings)
        mode_buttons.addWidget(self.btn_load_settings)

        mode_layout.addRow("Mode:", mode_buttons)

        self.content_layout.addWidget(mode_group)

        # === Parallel Processing (always visible) ===
        self.parallel_group = QGroupBox("Parallel Processing")
        parallel_layout = QFormLayout(self.parallel_group)
        parallel_layout.setSpacing(12)

        # Number of CPU cores
        cores_layout = QHBoxLayout()
        self.num_cores_spin = QSpinBox()
        self.num_cores_spin.setRange(1, 128)
        self.num_cores_spin.setValue(min(4, os.cpu_count() or 4))
        self.num_cores_spin.setToolTip("Number of CPU cores to use for parallel processing")
        self.num_cores_spin.valueChanged.connect(self._on_config_changed)
        cores_layout.addWidget(self.num_cores_spin)
        self.cpu_available_label = QLabel(f"(Available: {os.cpu_count() or 'N/A'})")
        cores_layout.addWidget(self.cpu_available_label)
        cores_layout.addStretch()
        parallel_layout.addRow("CPU Cores:", cores_layout)

        self.content_layout.addWidget(self.parallel_group)

        # === Local Python Environment ===
        self.local_env_group = QGroupBox("Local Python Environment")
        local_layout = QFormLayout(self.local_env_group)
        local_layout.setSpacing(12)

        # Python path with Detect and Browse buttons
        python_layout = QHBoxLayout()
        python_layout.setSpacing(8)
        self.python_combo = QComboBox()
        self.python_combo.setEditable(True)
        self.python_combo.setMinimumWidth(300)
        self.python_combo.currentTextChanged.connect(self._on_python_changed)
        python_layout.addWidget(self.python_combo, 1)

        self.btn_detect_python = QPushButton("Detect")
        self.btn_detect_python.setFixedWidth(60)
        self.btn_detect_python.setToolTip("Auto-detect Python interpreters")
        self.btn_detect_python.clicked.connect(self._detect_python)
        python_layout.addWidget(self.btn_detect_python)

        self.btn_browse_python = QPushButton("Browse")
        self.btn_browse_python.setFixedWidth(60)
        self.btn_browse_python.setToolTip("Browse for Python interpreter")
        self.btn_browse_python.clicked.connect(self._browse_python)
        python_layout.addWidget(self.btn_browse_python)

        local_layout.addRow("Python:", python_layout)

        # Conda environment with Refresh button
        conda_layout = QHBoxLayout()
        conda_layout.setSpacing(8)
        self.conda_combo = QComboBox()
        self.conda_combo.addItem("(Not using conda environment)")
        self.conda_combo.currentTextChanged.connect(self._on_conda_changed)
        conda_layout.addWidget(self.conda_combo, 1)

        self.btn_refresh_conda = QPushButton("Refresh")
        self.btn_refresh_conda.setFixedWidth(60)
        self.btn_refresh_conda.setToolTip("Refresh conda environments")
        self.btn_refresh_conda.clicked.connect(self._refresh_conda)
        conda_layout.addWidget(self.btn_refresh_conda)

        local_layout.addRow("Conda Env:", conda_layout)

        self.content_layout.addWidget(self.local_env_group)

        # === Remote Configuration ===
        self.remote_config_widget = RemoteConfigWidget()
        self.remote_config_widget.config_changed.connect(self._on_config_changed)
        self.remote_config_widget.connection_status_changed.connect(self._on_connection_status_changed)
        self.remote_config_widget.hide()  # Hidden by default (Local mode)
        self.content_layout.addWidget(self.remote_config_widget)

        # Auto-detect Python on startup
        self._detect_python()

        # Try to auto-load last saved settings
        self._auto_load_settings()

    def _on_execution_mode_changed(self, checked: bool):
        """Handle execution mode change."""
        if self.radio_local.isChecked():
            self.parallel_group.show()
            self.local_env_group.show()
            self.remote_config_widget.hide()
            # Reset CPU available label to local
            self.cpu_available_label.setText(f"(Available: {os.cpu_count() or 'N/A'})")
        else:
            self.parallel_group.hide()  # Parallel Processing is inside RemoteConfigWidget
            self.local_env_group.hide()
            self.remote_config_widget.show()
        self._on_config_changed()

    def _on_config_changed(self):
        """Handle any configuration change."""
        self.save_to_config()
        # Auto-save to default path for next startup
        self._auto_save_settings()

    def _on_connection_status_changed(self, connected: bool):
        """Handle SSH connection status change."""
        if connected:
            # Update controller's ssh_manager when connected
            self.controller.ssh_manager = self.remote_config_widget.get_ssh_manager()
            logger.debug("SSH manager set on controller")
        else:
            # Clear ssh_manager when disconnected
            self.controller.ssh_manager = None
            logger.debug("SSH manager cleared from controller")

    def _on_python_changed(self, text):
        """Handle Python path change."""
        self._refresh_conda()
        self._on_config_changed()

    def _on_conda_changed(self, text):
        """Handle conda environment change."""
        self._on_config_changed()

    def _detect_python(self):
        """Auto-detect available Python interpreters."""
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
        python_names = ['python3', 'python'] if not is_windows else ['python', 'python3']
        for name in python_names:
            path = shutil.which(name)
            if path and path not in [d.split(' ')[0] for d in detected]:
                if path == '/usr/bin/python3':
                    detected.append(f"{path} (system)")
                else:
                    detected.append(f"{path} (PATH)")

        # Update combo box
        current_text = self.python_combo.currentText()
        self.python_combo.blockSignals(True)
        self.python_combo.clear()

        for item in detected:
            self.python_combo.addItem(item)

        # Restore previous selection if valid
        if current_text:
            idx = self.python_combo.findText(current_text)
            if idx >= 0:
                self.python_combo.setCurrentIndex(idx)

        self.python_combo.blockSignals(False)

        # Also refresh conda environments
        self._refresh_conda()

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
            self.python_combo.setCurrentText(path)

    def _refresh_conda(self):
        """Refresh the list of available conda environments."""
        import subprocess
        import json

        current_python = self.python_combo.currentText().split(' ')[0]
        envs = self._get_conda_envs(current_python)

        current_env = self.conda_combo.currentText()
        self.conda_combo.blockSignals(True)
        self.conda_combo.clear()
        self.conda_combo.addItem("(Not using conda environment)")

        for env_name, env_path in envs:
            self.conda_combo.addItem(env_name, env_path)

        # Restore previous selection
        if current_env:
            idx = self.conda_combo.findText(current_env)
            if idx >= 0:
                self.conda_combo.setCurrentIndex(idx)

        self.conda_combo.blockSignals(False)

    def _get_conda_envs(self, python_path: str) -> list:
        """Get list of conda environments."""
        import subprocess
        import json

        envs = []
        if not python_path:
            return envs

        # Determine conda base path from Python path
        python_dir = os.path.dirname(python_path)
        if sys.platform == 'win32':
            if 'envs' in python_dir:
                conda_base = python_dir.split('envs')[0].rstrip(os.sep)
            else:
                conda_base = python_dir
            conda_exe = os.path.join(conda_base, 'Scripts', 'conda.exe')
            if not os.path.exists(conda_exe):
                conda_exe = os.path.join(conda_base, 'condabin', 'conda.bat')
        else:
            if 'envs' in python_dir:
                conda_base = python_dir.split('envs')[0].rstrip(os.sep)
            else:
                conda_base = os.path.dirname(python_dir)
            conda_exe = os.path.join(conda_base, 'bin', 'conda')

        if not os.path.exists(conda_exe):
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

    def load_from_config(self):
        """Load settings from controller config."""
        config = self.controller.config
        general = config.get("general", {})

        # Load execution mode
        execution_mode = general.get("execution_mode", "local")
        if execution_mode == "remote":
            self.radio_remote.setChecked(True)
            self.parallel_group.hide()
            self.local_env_group.hide()
            self.remote_config_widget.show()
        else:
            self.radio_local.setChecked(True)
            self.parallel_group.show()
            self.local_env_group.show()
            self.remote_config_widget.hide()

        # Load num_cores (for local mode)
        self.num_cores_spin.setValue(general.get("num_cores", 4))

        # Load Python path
        python_path = general.get("python_path", "")
        if python_path:
            self.python_combo.blockSignals(True)
            found = False
            for i in range(self.python_combo.count()):
                if self.python_combo.itemText(i).startswith(python_path):
                    self.python_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.python_combo.setCurrentText(python_path)
            self.python_combo.blockSignals(False)

        # Load conda environment
        conda_env = general.get("conda_env", "")
        if conda_env:
            self.conda_combo.blockSignals(True)
            idx = self.conda_combo.findText(conda_env)
            if idx >= 0:
                self.conda_combo.setCurrentIndex(idx)
            self.conda_combo.blockSignals(False)

        # Load remote config
        remote_config = general.get("remote", {})
        if remote_config:
            self.remote_config_widget.set_config(remote_config)

    def save_to_config(self):
        """Save settings to controller config."""
        config = self.controller.config
        if "general" not in config:
            config["general"] = {}
        general = config["general"]

        # Save execution mode
        general["execution_mode"] = "local" if self.radio_local.isChecked() else "remote"

        # Save num_cores
        general["num_cores"] = self.num_cores_spin.value()

        # Save Python path and conda env for local mode
        general["python_path"] = self.python_combo.currentText().split(' ')[0]
        general["conda_env"] = self.conda_combo.currentText() if self.conda_combo.currentIndex() > 0 else ""

        # Save remote config if in remote mode
        if self.radio_remote.isChecked():
            remote_config = self.remote_config_widget.get_config()
            general["remote"] = remote_config

    def validate(self) -> bool:
        """Validate the page configuration."""
        if self.radio_remote.isChecked():
            # Check if remote server is configured
            if not self.remote_config_widget.is_connected():
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "Not Connected",
                    "You haven't connected to the remote server yet.\n\n"
                    "Do you want to continue anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                return reply == QMessageBox.Yes
        return True

    def get_remote_config_widget(self):
        """Get the remote config widget for external access."""
        return self.remote_config_widget

    def is_remote_mode(self) -> bool:
        """Check if remote execution mode is selected."""
        return self.radio_remote.isChecked()

    def _save_runtime_settings(self):
        """Save runtime settings to a file."""
        default_path = get_default_runtime_settings_path()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Runtime Settings",
            default_path,
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )

        if not file_path:
            return

        try:
            settings = self._collect_runtime_settings()
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(settings, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            QMessageBox.information(
                self, "Settings Saved",
                f"Runtime settings saved to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error",
                f"Failed to save settings:\n{str(e)}"
            )

    def _load_runtime_settings(self):
        """Load runtime settings from a file."""
        default_path = get_default_runtime_settings_path()
        start_dir = os.path.dirname(default_path) if os.path.exists(default_path) else os.path.expanduser("~")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Runtime Settings",
            start_dir,
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f) or {}

            self._apply_runtime_settings(settings)

            QMessageBox.information(
                self, "Settings Loaded",
                f"Runtime settings loaded from:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Load Error",
                f"Failed to load settings:\n{str(e)}"
            )

    def _collect_runtime_settings(self) -> dict:
        """Collect current runtime settings into a dictionary."""
        settings = {
            "execution_mode": "local" if self.radio_local.isChecked() else "remote",
            "num_cores": self.num_cores_spin.value(),
            "python_path": self.python_combo.currentText().split(' ')[0],
            "conda_env": self.conda_combo.currentText() if self.conda_combo.currentIndex() > 0 else "",
        }

        # Include remote config if in remote mode
        if self.radio_remote.isChecked():
            settings["remote"] = self.remote_config_widget.get_config()

        return settings

    def _apply_runtime_settings(self, settings: dict):
        """Apply runtime settings from a dictionary."""
        # Apply execution mode
        execution_mode = settings.get("execution_mode", "local")
        if execution_mode == "remote":
            self.radio_remote.setChecked(True)
        else:
            self.radio_local.setChecked(True)

        # Apply num_cores
        self.num_cores_spin.setValue(settings.get("num_cores", 4))

        # Apply Python path
        python_path = settings.get("python_path", "")
        if python_path:
            self.python_combo.blockSignals(True)
            found = False
            for i in range(self.python_combo.count()):
                if self.python_combo.itemText(i).startswith(python_path):
                    self.python_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.python_combo.setCurrentText(python_path)
            self.python_combo.blockSignals(False)

        # Apply conda environment
        conda_env = settings.get("conda_env", "")
        if conda_env:
            self.conda_combo.blockSignals(True)
            idx = self.conda_combo.findText(conda_env)
            if idx >= 0:
                self.conda_combo.setCurrentIndex(idx)
            self.conda_combo.blockSignals(False)

        # Apply remote config
        remote_config = settings.get("remote", {})
        if remote_config:
            self.remote_config_widget.set_config(remote_config)

        # Save to controller config
        self.save_to_config()

    def _auto_load_settings(self):
        """Try to auto-load settings from default path on startup."""
        default_path = get_default_runtime_settings_path()
        if os.path.exists(default_path):
            try:
                with open(default_path, 'r', encoding='utf-8') as f:
                    settings = yaml.safe_load(f) or {}
                self._apply_runtime_settings(settings)
            except Exception:
                pass  # Silently ignore errors on auto-load

    def _auto_save_settings(self):
        """Auto-save settings to default path for next startup."""
        try:
            default_path = get_default_runtime_settings_path()
            settings = self._collect_runtime_settings()
            with open(default_path, 'w', encoding='utf-8') as f:
                yaml.dump(settings, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception:
            pass  # Silently ignore errors on auto-save
