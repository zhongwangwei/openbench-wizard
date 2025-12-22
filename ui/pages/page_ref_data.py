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

from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QScrollArea,
    QWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt

from ui.pages.base_page import BasePage
from ui.widgets import DataSourceEditor
from core.path_utils import to_absolute_path, get_openbench_root, convert_paths_in_dict


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
        dialog = DataSourceEditor(
            source_type="ref",
            var_name=var_name,  # Pass variable name for context
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
        dialog = DataSourceEditor(
            source_type="ref",
            var_name=var_name,
            initial_data=copied_data,
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

        dialog = DataSourceEditor(
            source_name=source_name,
            source_type="ref",
            var_name=var_name,  # Pass variable name for context
            initial_data=existing_data,
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
        general = ref_data.get("general", {})
        def_nml = ref_data.get("def_nml", {})
        # saved_source_configs now uses compound key: "var_name::source_name"
        saved_source_configs = ref_data.get("source_configs", {})

        # Parse existing config into source configs
        eval_items = self.controller.config.get("evaluation_items", {})
        selected = [k for k, v in eval_items.items() if v]

        for var_name in selected:
            key = f"{var_name}_ref_source"
            sources = general.get(key, [])
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
                    full_path = self._resolve_def_nml_path(def_nml_path)

                    if full_path and os.path.exists(full_path):
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                nml_content = yaml.safe_load(f) or {}

                            # Load general section
                            if "general" in nml_content:
                                source_data["general"] = nml_content["general"].copy()

                            # Load variable-specific settings (sub_dir, varname, prefix, suffix, varunit)
                            if var_name in nml_content:
                                var_config = nml_content[var_name]
                                # Store var-specific fields at top level for DataSourceEditor
                                for field in ["sub_dir", "varname", "varunit", "prefix", "suffix"]:
                                    if field in var_config:
                                        source_data[field] = var_config[field]

                        except Exception as e:
                            print(f"Warning: Failed to load def_nml file {full_path}: {e}")

                self._source_configs[var_name][source_name] = source_data

            self._update_source_list(var_name)

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

    def _get_openbench_root(self) -> str:
        """Get the OpenBench root directory."""
        # Use controller's project_root if available
        if self.controller.project_root:
            return self.controller.project_root
        return get_openbench_root()

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
