# -*- coding: utf-8 -*-
"""
Reference Data configuration page.

Data structure for _source_configs:
    _source_configs[var_name][source_name] = {
        "general": {...},           # Shared settings (root_dir, data_type, etc.)
        "var_config": {...},        # Variable-specific settings (sub_dir, varname, prefix, suffix, varunit)
    }

This allows the same source (e.g., GLEAM_v4.2a) to be used by multiple variables
with different per-variable configurations.
"""

import logging
import shlex
from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QScrollArea,
    QWidget, QFrame, QMessageBox, QDialog
)
from PySide6.QtCore import Qt

from ui.pages.base_page import BasePage
from ui.widgets import DataSourceEditor
from core.path_utils import to_absolute_path, convert_paths_in_dict

logger = logging.getLogger(__name__)


def get_remote_ssh_manager(controller):
    """Get SSH manager from the controller if in remote mode.

    Args:
        controller: The WizardController instance

    Returns:
        SSHManager instance if in remote mode and connected, None otherwise
    """
    general = controller.config.get("general", {})
    if general.get("execution_mode") != "remote":
        return None
    return controller.ssh_manager


class PageRefData(BasePage):
    """Reference Data configuration page."""

    PAGE_ID = "ref_data"
    PAGE_TITLE = "Reference Data"
    PAGE_SUBTITLE = "Configure reference data sources for each evaluation variable"
    CONTENT_EXPAND = True  # Allow content to fill available space

    def _setup_content(self):
        """Setup page content."""
        # Container for variable groups
        self.var_container = QWidget()
        self.var_layout = QVBoxLayout(self.var_container)
        self.var_layout.setContentsMargins(0, 0, 0, 0)
        self.var_layout.setSpacing(15)

        self.content_layout.addWidget(self.var_container)

        # Store references to source lists
        self._source_lists: Dict[str, QListWidget] = {}
        # Structure: _source_configs[var_name][source_name] = {"general": {...}, "var_config": {...}}
        self._source_configs: Dict[str, Dict[str, Any]] = {}

        # Add validate button at bottom
        validate_layout = QHBoxLayout()
        validate_layout.addStretch()
        self.validate_btn = QPushButton("验证数据")
        self.validate_btn.setToolTip("检查所有数据源的文件、变量名、时间和空间范围")
        self.validate_btn.clicked.connect(self._validate_data)
        validate_layout.addWidget(self.validate_btn)
        self.content_layout.addLayout(validate_layout)

    def _rebuild_variable_groups(self):
        """Rebuild variable groups based on selected evaluation items."""
        # Clear existing
        while self.var_layout.count():
            child = self.var_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._source_lists.clear()

        # Get selected evaluation items
        eval_items = self.controller.config.get("evaluation_items", {})
        selected = [k for k, v in eval_items.items() if v]

        if not selected:
            label = QLabel("No evaluation items selected. Please go back and select items.")
            label.setStyleSheet("color: #666; font-style: italic;")
            self.var_layout.addWidget(label)
            return

        # Create group for each variable
        for var_name in selected:
            group = QGroupBox(var_name.replace("_", " "))
            group_layout = QVBoxLayout(group)

            # Source list - use minimum height instead of maximum for better space usage
            source_list = QListWidget()
            source_list.setMinimumHeight(60)
            source_list.setProperty("var_name", var_name)
            self._source_lists[var_name] = source_list
            group_layout.addWidget(source_list, 1)  # stretch factor 1 to expand

            # Buttons
            btn_layout = QHBoxLayout()

            btn_add = QPushButton("+ Add Source")
            btn_add.setProperty("secondary", True)
            btn_add.clicked.connect(lambda checked, v=var_name: self._add_source(v))
            btn_layout.addWidget(btn_add)

            btn_copy = QPushButton("Copy")
            btn_copy.setProperty("secondary", True)
            btn_copy.setToolTip("Copy selected source as a new source")
            btn_copy.clicked.connect(lambda checked, v=var_name: self._copy_source(v))
            btn_layout.addWidget(btn_copy)

            btn_edit = QPushButton("Edit")
            btn_edit.setProperty("secondary", True)
            btn_edit.clicked.connect(lambda checked, v=var_name: self._edit_source(v))
            btn_layout.addWidget(btn_edit)

            btn_remove = QPushButton("Remove")
            btn_remove.setProperty("secondary", True)
            btn_remove.clicked.connect(lambda checked, v=var_name: self._remove_source(v))
            btn_layout.addWidget(btn_remove)

            btn_layout.addStretch()
            group_layout.addLayout(btn_layout)

            self.var_layout.addWidget(group, 1)  # stretch factor 1 to expand

        # No addStretch() here - let groups expand to fill space

    def _add_source(self, var_name: str):
        """Add new data source for variable."""
        ssh_manager = get_remote_ssh_manager(self.controller)
        dialog = DataSourceEditor(
            source_type="ref",
            var_name=var_name,  # Pass variable name for context
            ssh_manager=ssh_manager,
            parent=self
        )
        if dialog.exec():
            source_name = dialog.get_source_name()
            if source_name:
                if var_name not in self._source_configs:
                    self._source_configs[var_name] = {}
                self._source_configs[var_name][source_name] = dialog.get_data()
                self._update_source_list(var_name)
                self.save_to_config()

    def _copy_source(self, var_name: str):
        """Copy selected data source as a new source."""
        import copy

        source_list = self._source_lists.get(var_name)
        if not source_list:
            return

        current = source_list.currentItem()
        if not current:
            QMessageBox.information(self, "Info", "Please select a source to copy.")
            return

        source_name = current.text()
        existing_data = self._source_configs.get(var_name, {}).get(source_name, {})

        # Deep copy the data to avoid modifying the original
        copied_data = copy.deepcopy(existing_data)
        # Remove def_nml_path so a new one will be generated
        copied_data.pop("def_nml_path", None)

        # Open dialog with copied data but no source name (user must enter new name)
        ssh_manager = get_remote_ssh_manager(self.controller)
        dialog = DataSourceEditor(
            source_type="ref",
            var_name=var_name,
            initial_data=copied_data,
            ssh_manager=ssh_manager,
            parent=self
        )
        if dialog.exec():
            new_source_name = dialog.get_source_name()
            if new_source_name:
                if new_source_name == source_name:
                    QMessageBox.warning(
                        self, "Error",
                        "New source name must be different from the original."
                    )
                    return
                if var_name not in self._source_configs:
                    self._source_configs[var_name] = {}
                self._source_configs[var_name][new_source_name] = dialog.get_data()
                self._update_source_list(var_name)
                self.save_to_config()

    def _edit_source(self, var_name: str):
        """Edit selected data source."""
        source_list = self._source_lists.get(var_name)
        if not source_list:
            return

        current = source_list.currentItem()
        if not current:
            QMessageBox.information(self, "Info", "Please select a source to edit.")
            return

        source_name = current.text()
        existing_data = self._source_configs.get(var_name, {}).get(source_name, {})

        ssh_manager = get_remote_ssh_manager(self.controller)
        dialog = DataSourceEditor(
            source_name=source_name,
            source_type="ref",
            var_name=var_name,  # Pass variable name for context
            initial_data=existing_data,
            ssh_manager=ssh_manager,
            parent=self
        )
        if dialog.exec():
            self._source_configs[var_name][source_name] = dialog.get_data()
            self.save_to_config()

    def _remove_source(self, var_name: str):
        """Remove selected data source."""
        source_list = self._source_lists.get(var_name)
        if not source_list:
            return

        current = source_list.currentItem()
        if not current:
            QMessageBox.information(self, "Info", "Please select a source to remove.")
            return

        source_name = current.text()
        reply = QMessageBox.question(
            self, "Confirm",
            f"Remove source '{source_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if var_name in self._source_configs:
                self._source_configs[var_name].pop(source_name, None)
            self._update_source_list(var_name)
            self.save_to_config()

    def _update_source_list(self, var_name: str):
        """Update the source list widget for a variable."""
        source_list = self._source_lists.get(var_name)
        if not source_list:
            return

        source_list.clear()
        sources = self._source_configs.get(var_name, {})
        for source_name in sources.keys():
            source_list.addItem(source_name)

    def load_from_config(self):
        """Load from config.

        Properly loads per-variable configurations from source files.
        Each variable gets its own copy of the config with variable-specific settings.
        """
        import os
        import yaml

        self._rebuild_variable_groups()

        ref_data = self.controller.config.get("ref_data", {})
        general_section = ref_data.get("general", {})
        def_nml = ref_data.get("def_nml", {})
        # saved_source_configs now uses compound key: "var_name::source_name"
        saved_source_configs = ref_data.get("source_configs", {})

        # Check if in remote mode
        config_general = self.controller.config.get("general", {})
        is_remote = config_general.get("execution_mode") == "remote"
        ssh_manager = get_remote_ssh_manager(self.controller) if is_remote else None

        # Parse existing config into source configs
        eval_items = self.controller.config.get("evaluation_items", {})
        selected = [k for k, v in eval_items.items() if v]

        for var_name in selected:
            key = f"{var_name}_ref_source"
            sources = general_section.get(key, [])
            if isinstance(sources, str):
                sources = [sources]

            self._source_configs[var_name] = {}
            for source_name in sources:
                # Use compound key for per-variable storage
                compound_key = f"{var_name}::{source_name}"

                # First check if we have saved source config (from previous edits)
                if compound_key in saved_source_configs:
                    self._source_configs[var_name][source_name] = saved_source_configs[compound_key].copy()
                    self._update_source_list(var_name)
                    continue

                # Otherwise load from def_nml file
                def_nml_path = def_nml.get(source_name, "")
                source_data = {"def_nml_path": def_nml_path}

                # Try to load the actual def_nml file content
                if def_nml_path:
                    nml_content = None

                    if is_remote:
                        # In remote mode, only load from remote server
                        if ssh_manager and ssh_manager.is_connected:
                            remote_path = self._resolve_remote_def_nml_path(ssh_manager, def_nml_path)
                            nml_content = self._load_remote_nml_content(ssh_manager, remote_path)
                        # If not connected, don't fall back to local - just skip loading
                        # The paths in the config are already remote paths
                    else:
                        # Local mode - load from local file
                        full_path = self._resolve_def_nml_path(def_nml_path)
                        if full_path and os.path.exists(full_path):
                            try:
                                with open(full_path, 'r', encoding='utf-8') as f:
                                    nml_content = yaml.safe_load(f) or {}
                            except Exception as e:
                                print(f"Warning: Failed to load def_nml file {full_path}: {e}")

                    if nml_content:
                        # Load general section
                        if "general" in nml_content:
                            source_data["general"] = nml_content["general"].copy()

                        # Load variable-specific settings (sub_dir, varname, prefix, suffix, varunit, syear, eyear)
                        if var_name in nml_content:
                            var_config = nml_content[var_name]
                            # Store var-specific fields at top level for DataSourceEditor
                            for field in ["sub_dir", "varname", "varunit", "prefix", "suffix", "syear", "eyear"]:
                                if field in var_config:
                                    source_data[field] = var_config[field]

                self._source_configs[var_name][source_name] = source_data

            self._update_source_list(var_name)

        # Save loaded configs back to controller to ensure they're available for export
        if self._source_configs:
            self.save_to_config()

    def _load_remote_nml_content(self, ssh_manager, def_nml_path: str) -> dict:
        """Load NML content from remote server."""
        import yaml

        if not def_nml_path:
            return None

        try:
            stdout, stderr, exit_code = ssh_manager.execute(
                f"cat '{def_nml_path}'", timeout=30
            )
            if exit_code == 0 and stdout.strip():
                return yaml.safe_load(stdout) or {}
            else:
                print(f"Warning: Failed to read remote file {def_nml_path}: {stderr}")
        except Exception as e:
            print(f"Warning: Failed to load remote def_nml file {def_nml_path}: {e}")

        return None

    def _resolve_remote_def_nml_path(self, ssh_manager, def_nml_path: str) -> str:
        """Resolve def_nml path on remote server."""
        if not def_nml_path:
            return ""

        # If already absolute, return as-is
        if def_nml_path.startswith('/'):
            return def_nml_path

        # Get project root from controller
        project_root = self.controller.project_root or ""

        # Handle relative paths
        if def_nml_path.startswith('./'):
            relative_path = def_nml_path[2:]
        else:
            relative_path = def_nml_path

        # Try different base directories
        paths_to_try = []
        if project_root:
            paths_to_try.append(f"{project_root}/{relative_path}")
            # Also try output directory from config
            basedir = self.controller.config.get("general", {}).get("basedir", "")
            if basedir:
                if basedir.startswith('/'):
                    paths_to_try.append(f"{basedir.rstrip('/')}/{relative_path.lstrip('/')}")
                else:
                    paths_to_try.append(f"{project_root}/{basedir}/{relative_path}")

        # Check which path exists on remote
        for path in paths_to_try:
            try:
                quoted_path = shlex.quote(path)
                stdout, stderr, exit_code = ssh_manager.execute(
                    f"test -f {quoted_path} && echo 'exists'", timeout=10
                )
                if exit_code == 0 and 'exists' in stdout:
                    return path
            except Exception as e:
                logger.debug("Failed to check remote path %s: %s", path, e)

        # Return the first attempt if nothing found
        return paths_to_try[0] if paths_to_try else def_nml_path

    def _resolve_def_nml_path(self, def_nml_path: str) -> str:
        """Resolve def_nml path to YAML file."""
        import os

        if not def_nml_path:
            return ""

        # Get OpenBench root
        openbench_root = self._get_openbench_root()

        # Convert to absolute path
        full_path = to_absolute_path(def_nml_path, openbench_root)

        # If already absolute and exists, return it
        if os.path.exists(full_path):
            return full_path

        # Try converting .nml to .yaml
        yaml_path = full_path.replace("nml-Fortran", "nml-yaml").replace(".nml", ".yaml")
        if os.path.exists(yaml_path):
            return yaml_path

        return full_path  # Return even if doesn't exist, let validation catch it

    def save_to_config(self):
        """Save to config.

        Uses compound key "var_name::source_name" for source_configs to preserve
        per-variable configurations even when the same source is used by multiple variables.
        """
        general = {}
        def_nml = {}
        source_configs = {}  # Store full source configurations with compound keys

        for var_name, sources in self._source_configs.items():
            if sources:
                key = f"{var_name}_ref_source"
                general[key] = list(sources.keys())

                for source_name, source_data in sources.items():
                    # Get def_nml_path if it exists, otherwise generate one
                    def_nml_path = source_data.get("def_nml_path", "")
                    if not def_nml_path:
                        # Will be generated during namelist sync
                        basedir = self.controller.config.get("general", {}).get("basedir", "./output")
                        def_nml_path = f"{basedir}/nml/ref/{source_name}.yaml"
                    def_nml[source_name] = def_nml_path

                    # Store with compound key to preserve per-variable configs
                    compound_key = f"{var_name}::{source_name}"
                    source_configs[compound_key] = source_data.copy()
                    # Also store var_name in the config for later retrieval
                    source_configs[compound_key]["_var_name"] = var_name

        ref_data = {
            "general": general,
            "def_nml": def_nml,
            "source_configs": source_configs  # Include full configs for sync
        }
        self.controller.update_section("ref_data", ref_data)

        # Trigger namelist sync
        self.controller.sync_namelists()

    def validate(self) -> bool:
        """Validate page input - ensure all evaluation items have data sources."""
        from core.validation import ValidationError, ValidationManager

        eval_items = self.controller.config.get("evaluation_items", {})
        selected = [k for k, v in eval_items.items() if v]

        manager = ValidationManager(self)

        for var_name in selected:
            sources = self._source_configs.get(var_name, {})
            if not sources:
                error = ValidationError(
                    field_name="data_source",
                    message=f"{var_name.replace('_', ' ')} 缺少参考数据源配置",
                    page_id=self.PAGE_ID,
                    context={"var_name": var_name}
                )
                manager.show_error_and_focus(error)
                # Auto-open add source dialog
                self._add_source(var_name)
                return False

            # Validate each source has required fields
            for source_name, source_data in sources.items():
                # Check varname
                varname = source_data.get("varname", "")
                if not varname:
                    error = ValidationError(
                        field_name="varname",
                        message=f"变量名不能为空\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    # Auto-open edit source dialog
                    self._select_and_edit_source(var_name, source_name)
                    return False

                # Check prefix/suffix
                prefix = source_data.get("prefix", "")
                suffix = source_data.get("suffix", "")
                if not prefix and not suffix:
                    error = ValidationError(
                        field_name="prefix/suffix",
                        message=f"文件前缀和后缀至少填写一个\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    self._select_and_edit_source(var_name, source_name)
                    return False

                # Check root_dir
                general = source_data.get("general", {})
                root_dir = general.get("root_dir", "") or general.get("dir", "")
                if not root_dir:
                    error = ValidationError(
                        field_name="root_dir",
                        message=f"根目录不能为空\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    self._select_and_edit_source(var_name, source_name)
                    return False

        self.save_to_config()
        return True

    def _select_and_edit_source(self, var_name: str, source_name: str):
        """Select source in list and open edit dialog."""
        source_list = self._source_lists.get(var_name)
        if source_list:
            # Find and select the item
            for i in range(source_list.count()):
                if source_list.item(i).text() == source_name:
                    source_list.setCurrentRow(i)
                    break
            # Open edit dialog
            self._edit_source(var_name)

    def _validate_data(self):
        """Validate all configured data sources."""
        from core.data_validator import DataValidator
        from ui.widgets.validation_dialog import (
            ValidationProgressDialog, ValidationResultsDialog
        )

        # Check if any sources configured
        if not self._source_configs:
            QMessageBox.information(
                self, "无数据", "没有配置任何数据源，请先添加数据源。"
            )
            return

        # Get general config
        general_config = self.controller.config.get("general", {})

        # Check if remote mode
        is_remote = general_config.get("execution_mode") == "remote"
        ssh_manager = get_remote_ssh_manager(self.controller) if is_remote else None

        if is_remote and not ssh_manager:
            QMessageBox.warning(
                self, "未连接", "远程模式需要先连接到服务器。"
            )
            return

        # Create validator
        validator = DataValidator(is_remote=is_remote, ssh_manager=ssh_manager)

        # Show progress dialog
        progress_dialog = ValidationProgressDialog(
            validator,
            self._source_configs,
            general_config,
            parent=self
        )

        if progress_dialog.exec() == QDialog.Accepted:
            report = progress_dialog.get_report()
            if report:
                # Show results dialog
                results_dialog = ValidationResultsDialog(report, parent=self)
                results_dialog.exec()
