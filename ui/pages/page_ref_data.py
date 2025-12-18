# -*- coding: utf-8 -*-
"""
Reference Data configuration page.
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


class PageRefData(BasePage):
    """Reference Data configuration page."""

    PAGE_ID = "ref_data"
    PAGE_TITLE = "Reference Data"
    PAGE_SUBTITLE = "Configure reference data sources for each evaluation variable"

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

            # Source list
            source_list = QListWidget()
            source_list.setMaximumHeight(100)
            source_list.setProperty("var_name", var_name)
            self._source_lists[var_name] = source_list
            group_layout.addWidget(source_list)

            # Buttons
            btn_layout = QHBoxLayout()

            btn_add = QPushButton("+ Add Source")
            btn_add.setProperty("secondary", True)
            btn_add.clicked.connect(lambda checked, v=var_name: self._add_source(v))
            btn_layout.addWidget(btn_add)

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

            self.var_layout.addWidget(group)

        self.var_layout.addStretch()

    def _add_source(self, var_name: str):
        """Add new data source for variable."""
        dialog = DataSourceEditor(source_type="ref", parent=self)
        if dialog.exec():
            source_name = dialog.get_source_name()
            if source_name:
                if var_name not in self._source_configs:
                    self._source_configs[var_name] = {}
                self._source_configs[var_name][source_name] = dialog.get_data()
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
        """Load from config."""
        import os
        import yaml

        self._rebuild_variable_groups()

        ref_data = self.controller.config.get("ref_data", {})
        general = ref_data.get("general", {})
        def_nml = ref_data.get("def_nml", {})

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
                def_nml_path = def_nml.get(source_name, "")
                source_data = {"def_nml_path": def_nml_path}

                # Try to load the actual def_nml file content
                if def_nml_path:
                    full_path = self._resolve_def_nml_path(def_nml_path)

                    if full_path and os.path.exists(full_path):
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                nml_content = yaml.safe_load(f) or {}
                            # Merge the loaded content into source_data
                            source_data.update(nml_content)
                            # Also get variable-specific settings if available
                            if var_name in nml_content:
                                source_data.update(nml_content[var_name])
                        except Exception as e:
                            print(f"Warning: Failed to load def_nml file {full_path}: {e}")

                self._source_configs[var_name][source_name] = source_data

            self._update_source_list(var_name)

    def _resolve_def_nml_path(self, def_nml_path: str) -> str:
        """Resolve def_nml path to YAML file."""
        import os

        if not def_nml_path:
            return ""

        # If already absolute, return as-is
        if os.path.isabs(def_nml_path):
            if os.path.exists(def_nml_path):
                return def_nml_path
            # Try converting .nml to .yaml
            yaml_path = def_nml_path.replace("nml-Fortran", "nml-yaml").replace(".nml", ".yaml")
            return yaml_path if os.path.exists(yaml_path) else def_nml_path

        # Normalize the path
        if def_nml_path.startswith("./"):
            base_path = def_nml_path[2:]
        else:
            base_path = def_nml_path

        # Convert to YAML path if it's a Fortran .nml path
        if "nml-Fortran" in base_path or base_path.endswith(".nml"):
            base_path = base_path.replace("nml-Fortran", "nml-yaml").replace(".nml", ".yaml")

        # Get OpenBench root
        openbench_root = self._get_openbench_root()

        # Build full path using OpenBench root
        full_path = os.path.join(openbench_root, base_path)

        return full_path if os.path.exists(full_path) else ""

    def _get_openbench_root(self) -> str:
        """Get the OpenBench root directory."""
        import os
        import sys

        # Use controller's project_root if available
        if self.controller.project_root:
            return self.controller.project_root

        # Try to load saved path
        try:
            home_dir = os.path.expanduser("~")
            config_file = os.path.join(home_dir, ".openbench_wizard", "config.txt")
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    path = f.read().strip()
                    if os.path.exists(path):
                        return path
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
                return root

        # Fallback to current working directory
        return os.getcwd()

    def save_to_config(self):
        """Save to config."""
        general = {}
        def_nml = {}

        for var_name, sources in self._source_configs.items():
            if sources:
                key = f"{var_name}_ref_source"
                general[key] = list(sources.keys())

                for source_name, source_data in sources.items():
                    def_nml[source_name] = source_data.get("def_nml_path", "")

        ref_data = {"general": general, "def_nml": def_nml}
        self.controller.update_section("ref_data", ref_data)
