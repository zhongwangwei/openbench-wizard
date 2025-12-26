# -*- coding: utf-8 -*-
"""
Remote server configuration widget.

Provides UI for configuring SSH connection to remote servers,
including authentication, compute node (multi-hop), and Python environment.
"""

import os
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QRadioButton,
    QButtonGroup, QCheckBox, QComboBox, QLabel,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Signal, Qt

from core.ssh_manager import SSHManager, SSHConnectionError
from core.credential_manager import CredentialManager


class RemoteConfigWidget(QWidget):
    """Widget for configuring remote server connection.

    Provides comprehensive UI for:
    - SSH host configuration with authentication options
    - Optional compute node (multi-hop) connection
    - Remote Python environment detection and selection

    Signals:
        connection_status_changed(bool): Emitted when connection state changes
        credentials_saved(str): Emitted when credentials are saved (host string)
        config_changed(): Emitted when any configuration value changes
    """

    # Signals
    connection_status_changed = Signal(bool)  # Connection state changed
    credentials_saved = Signal(str)  # Credentials saved for host
    config_changed = Signal()  # Configuration changed

    def __init__(self, parent=None):
        """Initialize RemoteConfigWidget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._ssh_manager: Optional[SSHManager] = None
        self._credential_manager = CredentialManager()
        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # === Remote Server Group ===
        server_group = QGroupBox("Remote Server")
        server_layout = QFormLayout(server_group)
        server_layout.setSpacing(8)

        # Host input with Test button
        host_layout = QHBoxLayout()
        host_layout.setSpacing(8)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("user@192.168.1.100")
        self.host_input.textChanged.connect(self._on_config_changed)
        host_layout.addWidget(self.host_input, 1)

        self.btn_test = QPushButton("Test")
        self.btn_test.setFixedWidth(60)
        self.btn_test.setToolTip("Test SSH connection")
        self.btn_test.clicked.connect(self._test_connection)
        host_layout.addWidget(self.btn_test)

        server_layout.addRow("Host:", host_layout)

        # Authentication type radio buttons
        auth_layout = QHBoxLayout()
        auth_layout.setSpacing(15)
        self.auth_group = QButtonGroup(self)
        self.radio_password = QRadioButton("Password")
        self.radio_password.setChecked(True)
        self.radio_key = QRadioButton("SSH Key")
        self.auth_group.addButton(self.radio_password)
        self.auth_group.addButton(self.radio_key)
        self.radio_password.toggled.connect(self._on_auth_type_changed)
        auth_layout.addWidget(self.radio_password)
        auth_layout.addWidget(self.radio_key)
        auth_layout.addStretch()
        server_layout.addRow("Auth:", auth_layout)

        # Password input with Save checkbox
        pwd_layout = QHBoxLayout()
        pwd_layout.setSpacing(8)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Password")
        self.password_input.textChanged.connect(self._on_config_changed)
        pwd_layout.addWidget(self.password_input, 1)

        self.cb_save_password = QCheckBox("Save")
        self.cb_save_password.setToolTip("Save password (encrypted)")
        pwd_layout.addWidget(self.cb_save_password)

        self.password_row_widget = QWidget()
        self.password_row_widget.setLayout(pwd_layout)
        server_layout.addRow("", self.password_row_widget)

        # SSH Key input with Browse button
        key_layout = QHBoxLayout()
        key_layout.setSpacing(8)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("~/.ssh/id_rsa")
        self.key_input.textChanged.connect(self._on_config_changed)
        key_layout.addWidget(self.key_input, 1)

        self.btn_browse_key = QPushButton("Browse")
        self.btn_browse_key.setFixedWidth(60)
        self.btn_browse_key.clicked.connect(self._browse_key)
        key_layout.addWidget(self.btn_browse_key)

        self.key_row_widget = QWidget()
        self.key_row_widget.setLayout(key_layout)
        self.key_row_widget.hide()  # Hidden by default (password mode)
        server_layout.addRow("", self.key_row_widget)

        # Connection status indicator
        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("color: #999;")
        server_layout.addRow("Status:", self.status_label)

        layout.addWidget(server_group)

        # === Compute Node Group (Optional) ===
        node_group = QGroupBox("Compute Node (Optional)")
        node_group.setCheckable(True)
        node_group.setChecked(False)
        node_group.toggled.connect(self._on_config_changed)
        self.node_group = node_group
        node_layout = QFormLayout(node_group)
        node_layout.setSpacing(8)

        # Node name input
        self.node_input = QLineEdit()
        self.node_input.setPlaceholderText("node110")
        self.node_input.textChanged.connect(self._on_config_changed)
        node_layout.addRow("Node:", self.node_input)

        # Node authentication type
        node_auth_layout = QHBoxLayout()
        node_auth_layout.setSpacing(15)
        self.node_auth_group = QButtonGroup(self)
        self.radio_node_none = QRadioButton("None (internal trust)")
        self.radio_node_none.setChecked(True)
        self.radio_node_password = QRadioButton("Password")
        self.node_auth_group.addButton(self.radio_node_none)
        self.node_auth_group.addButton(self.radio_node_password)
        self.radio_node_password.toggled.connect(self._on_node_auth_changed)
        node_auth_layout.addWidget(self.radio_node_none)
        node_auth_layout.addWidget(self.radio_node_password)
        node_auth_layout.addStretch()
        node_layout.addRow("Auth:", node_auth_layout)

        # Node password input
        self.node_password_input = QLineEdit()
        self.node_password_input.setEchoMode(QLineEdit.Password)
        self.node_password_input.setPlaceholderText("Node password")
        self.node_password_input.textChanged.connect(self._on_config_changed)
        self.node_password_input.hide()
        node_layout.addRow("", self.node_password_input)

        layout.addWidget(node_group)

        # === Remote Python Environment Group ===
        env_group = QGroupBox("Remote Python Environment")
        env_layout = QFormLayout(env_group)
        env_layout.setSpacing(8)

        # Python path with Detect button
        python_layout = QHBoxLayout()
        python_layout.setSpacing(8)
        self.python_combo = QComboBox()
        self.python_combo.setEditable(True)
        self.python_combo.setMinimumWidth(250)
        self.python_combo.currentTextChanged.connect(self._on_config_changed)
        python_layout.addWidget(self.python_combo, 1)

        self.btn_detect_python = QPushButton("Detect")
        self.btn_detect_python.setFixedWidth(60)
        self.btn_detect_python.setToolTip("Detect Python interpreters on remote server")
        self.btn_detect_python.clicked.connect(self._detect_python)
        python_layout.addWidget(self.btn_detect_python)

        env_layout.addRow("Python:", python_layout)

        # Conda environment with Refresh button
        conda_layout = QHBoxLayout()
        conda_layout.setSpacing(8)
        self.conda_combo = QComboBox()
        self.conda_combo.addItem("(Not using conda environment)")
        self.conda_combo.currentTextChanged.connect(self._on_config_changed)
        conda_layout.addWidget(self.conda_combo, 1)

        self.btn_refresh_conda = QPushButton("Refresh")
        self.btn_refresh_conda.setFixedWidth(60)
        self.btn_refresh_conda.setToolTip("Refresh conda environments from remote server")
        self.btn_refresh_conda.clicked.connect(self._refresh_conda)
        conda_layout.addWidget(self.btn_refresh_conda)

        env_layout.addRow("Conda:", conda_layout)

        # OpenBench path with Install button
        ob_layout = QHBoxLayout()
        ob_layout.setSpacing(8)
        self.openbench_input = QLineEdit()
        self.openbench_input.setPlaceholderText("/home/user/OpenBench")
        self.openbench_input.textChanged.connect(self._on_config_changed)
        ob_layout.addWidget(self.openbench_input, 1)

        self.btn_install_ob = QPushButton("Install...")
        self.btn_install_ob.setFixedWidth(70)
        self.btn_install_ob.setToolTip("Install OpenBench on remote server")
        self.btn_install_ob.clicked.connect(self._install_openbench)
        ob_layout.addWidget(self.btn_install_ob)

        env_layout.addRow("OpenBench:", ob_layout)

        layout.addWidget(env_group)
        layout.addStretch()

    def _on_auth_type_changed(self, checked: bool):
        """Handle auth type radio button change.

        Args:
            checked: Whether password radio is checked
        """
        if self.radio_password.isChecked():
            self.password_row_widget.show()
            self.key_row_widget.hide()
        else:
            self.password_row_widget.hide()
            self.key_row_widget.show()
        self._on_config_changed()

    def _on_node_auth_changed(self, checked: bool):
        """Handle node auth type change.

        Args:
            checked: Whether password radio is checked
        """
        self.node_password_input.setVisible(checked)
        self._on_config_changed()

    def _on_config_changed(self):
        """Handle any configuration change."""
        self.config_changed.emit()

    def _browse_key(self):
        """Open file dialog to browse for SSH key file."""
        start_path = os.path.expanduser("~/.ssh")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SSH Key",
            start_path,
            "All Files (*)"
        )
        if path:
            self.key_input.setText(path)

    def _test_connection(self):
        """Test SSH connection with current settings."""
        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "Error", "Please enter host address")
            return

        # Update status
        self.status_label.setText("Connecting...")
        self.status_label.setStyleSheet("color: #f39c12;")  # Orange
        self.btn_test.setEnabled(False)

        # Force UI update
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            self._ssh_manager = SSHManager()

            # Connect based on auth type
            if self.radio_password.isChecked():
                password = self.password_input.text()
                self._ssh_manager.connect(host, password=password)
            else:
                key_file = os.path.expanduser(self.key_input.text().strip())
                self._ssh_manager.connect(host, key_file=key_file)

            # Test jump connection if enabled
            if self.node_group.isChecked():
                node = self.node_input.text().strip()
                if node:
                    node_password = None
                    if self.radio_node_password.isChecked():
                        node_password = self.node_password_input.text()
                    self._ssh_manager.connect_with_jump(
                        main_host=node,
                        main_password=node_password
                    )

            # Update status to connected
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #27ae60;")  # Green
            self.connection_status_changed.emit(True)

            # Save credentials if requested
            if self.cb_save_password.isChecked():
                self._save_current_credentials()

            QMessageBox.information(self, "Success", "Connection successful!")

        except SSHConnectionError as e:
            self.status_label.setText("Connection failed")
            self.status_label.setStyleSheet("color: #e74c3c;")  # Red
            self.connection_status_changed.emit(False)
            QMessageBox.critical(self, "Connection Failed", str(e))
        except Exception as e:
            self.status_label.setText("Error")
            self.status_label.setStyleSheet("color: #e74c3c;")  # Red
            self.connection_status_changed.emit(False)
            QMessageBox.critical(self, "Error", f"Unexpected error: {e}")
        finally:
            self.btn_test.setEnabled(True)

    def _save_current_credentials(self):
        """Save current credentials using CredentialManager."""
        host = self.host_input.text().strip()
        if not host:
            return

        auth_type = "password" if self.radio_password.isChecked() else "key"
        password = self.password_input.text() if self.radio_password.isChecked() else None
        key_file = self.key_input.text().strip() if self.radio_key.isChecked() else None
        jump_node = self.node_input.text().strip() if self.node_group.isChecked() else None
        jump_auth = "password" if self.radio_node_password.isChecked() else "none"

        self._credential_manager.save_credential(
            host=host,
            auth_type=auth_type,
            password=password,
            key_file=key_file,
            jump_node=jump_node,
            jump_auth=jump_auth
        )
        self.credentials_saved.emit(host)

    def _detect_python(self):
        """Detect Python interpreters on remote server."""
        if not self._ssh_manager or not self._ssh_manager.is_connected:
            QMessageBox.warning(
                self, "Error",
                "Please connect to server first using the Test button"
            )
            return

        try:
            self.btn_detect_python.setEnabled(False)
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            pythons = self._ssh_manager.detect_python_interpreters()
            self.python_combo.clear()
            if pythons:
                for p in pythons:
                    self.python_combo.addItem(p)
                QMessageBox.information(
                    self, "Detection Complete",
                    f"Found {len(pythons)} Python interpreter(s)"
                )
            else:
                QMessageBox.information(
                    self, "Detection Complete",
                    "No Python interpreters found. You can enter the path manually."
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to detect Python: {e}")
        finally:
            self.btn_detect_python.setEnabled(True)

    def _refresh_conda(self):
        """Refresh conda environments from remote server."""
        if not self._ssh_manager or not self._ssh_manager.is_connected:
            QMessageBox.warning(
                self, "Error",
                "Please connect to server first using the Test button"
            )
            return

        try:
            self.btn_refresh_conda.setEnabled(False)
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            envs = self._ssh_manager.detect_conda_envs()
            self.conda_combo.clear()
            self.conda_combo.addItem("(Not using conda environment)")
            if envs:
                for name, path in envs:
                    self.conda_combo.addItem(name, path)
                QMessageBox.information(
                    self, "Refresh Complete",
                    f"Found {len(envs)} conda environment(s)"
                )
            else:
                QMessageBox.information(
                    self, "Refresh Complete",
                    "No conda environments found on remote server."
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to refresh conda environments: {e}")
        finally:
            self.btn_refresh_conda.setEnabled(True)

    def _install_openbench(self):
        """Open OpenBench installation dialog."""
        # TODO: Implement installation dialog in a future task
        QMessageBox.information(
            self, "Coming Soon",
            "OpenBench installation wizard will be implemented in a future update."
        )

    def get_ssh_manager(self) -> Optional[SSHManager]:
        """Get the current SSH manager instance.

        Returns:
            SSHManager instance if connected, None otherwise
        """
        return self._ssh_manager

    def is_connected(self) -> bool:
        """Check if currently connected to remote server.

        Returns:
            True if connected
        """
        return self._ssh_manager is not None and self._ssh_manager.is_connected

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration as dictionary.

        Returns:
            Configuration dictionary with all settings
        """
        conda_env = ""
        if self.conda_combo.currentIndex() > 0:
            conda_env = self.conda_combo.currentText()

        return {
            "host": self.host_input.text().strip(),
            "auth_type": "password" if self.radio_password.isChecked() else "key",
            "key_file": self.key_input.text().strip(),
            "use_jump": self.node_group.isChecked(),
            "jump_node": self.node_input.text().strip(),
            "jump_auth": "password" if self.radio_node_password.isChecked() else "none",
            "python_path": self.python_combo.currentText().strip(),
            "conda_env": conda_env,
            "openbench_path": self.openbench_input.text().strip(),
        }

    def set_config(self, config: Dict[str, Any]):
        """Set configuration from dictionary.

        Args:
            config: Configuration dictionary
        """
        # Block signals during batch update
        self.blockSignals(True)

        # Set host
        self.host_input.setText(config.get("host", ""))

        # Set auth type
        if config.get("auth_type") == "key":
            self.radio_key.setChecked(True)
        else:
            self.radio_password.setChecked(True)

        # Set key file
        self.key_input.setText(config.get("key_file", ""))

        # Set jump/compute node settings
        self.node_group.setChecked(config.get("use_jump", False))
        self.node_input.setText(config.get("jump_node", ""))

        if config.get("jump_auth") == "password":
            self.radio_node_password.setChecked(True)
        else:
            self.radio_node_none.setChecked(True)

        # Set Python environment
        python_path = config.get("python_path", "")
        if python_path:
            idx = self.python_combo.findText(python_path)
            if idx >= 0:
                self.python_combo.setCurrentIndex(idx)
            else:
                self.python_combo.setCurrentText(python_path)

        # Set conda environment
        conda_env = config.get("conda_env", "")
        if conda_env:
            idx = self.conda_combo.findText(conda_env)
            if idx >= 0:
                self.conda_combo.setCurrentIndex(idx)
        else:
            self.conda_combo.setCurrentIndex(0)

        # Set OpenBench path
        self.openbench_input.setText(config.get("openbench_path", ""))

        # Restore signals
        self.blockSignals(False)

        # Try to load saved credentials for this host
        host = config.get("host", "")
        if host:
            self._load_saved_credentials(host)

    def _load_saved_credentials(self, host: str):
        """Load saved credentials for a host.

        Args:
            host: Host string to load credentials for
        """
        cred = self._credential_manager.get_credential(host)
        if cred:
            # Load password if saved
            if cred.get("password"):
                self.password_input.setText(cred["password"])
                self.cb_save_password.setChecked(True)
            # Load key file if saved
            if cred.get("key_file"):
                self.key_input.setText(cred["key_file"])
            # Load jump node settings
            if cred.get("jump_node"):
                self.node_group.setChecked(True)
                self.node_input.setText(cred["jump_node"])
                if cred.get("jump_auth") == "password":
                    self.radio_node_password.setChecked(True)

    def disconnect(self):
        """Disconnect from remote server."""
        if self._ssh_manager:
            try:
                self._ssh_manager.disconnect()
            except Exception:
                pass
            self._ssh_manager = None
        self.status_label.setText("Not connected")
        self.status_label.setStyleSheet("color: #999;")
        self.connection_status_changed.emit(False)

    def clear_credentials(self):
        """Clear all saved credentials."""
        self._credential_manager.clear_all()
        self.password_input.clear()
        self.cb_save_password.setChecked(False)
