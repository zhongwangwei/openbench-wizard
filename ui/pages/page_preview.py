# -*- coding: utf-8 -*-
"""
Preview and Export page.
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QMessageBox, QFileDialog
)
from PySide6.QtCore import Signal

from ui.pages.base_page import BasePage
from ui.widgets import PathSelector, YamlPreview
from core.config_manager import ConfigManager
from core.path_utils import get_openbench_root, to_absolute_path


class PagePreview(BasePage):
    """Preview and Export page."""

    PAGE_ID = "preview"
    PAGE_TITLE = "Preview & Export"
    PAGE_SUBTITLE = "Review generated configuration and export files"

    run_requested = Signal(str)  # Emits output directory

    def _setup_content(self):
        """Setup page content."""
        self.config_manager = ConfigManager()

        # Tab widget for different files
        self.tab_widget = QTabWidget()

        # Main NML preview
        self.main_preview = YamlPreview()
        self.tab_widget.addTab(self.main_preview, "main.yaml")

        # Ref NML preview
        self.ref_preview = YamlPreview()
        self.tab_widget.addTab(self.ref_preview, "ref.yaml")

        # Sim NML preview
        self.sim_preview = YamlPreview()
        self.tab_widget.addTab(self.sim_preview, "sim.yaml")

        self.content_layout.addWidget(self.tab_widget, 1)

        # Export section
        export_layout = QHBoxLayout()

        export_layout.addWidget(QLabel("Export Directory:"))

        self.export_path = PathSelector(
            mode="directory",
            placeholder="Select export directory"
        )
        # Set default to OpenBench nml-yaml directory if available
        default_export = self._get_default_export_path()
        self.export_path.set_path(default_export)
        export_layout.addWidget(self.export_path, 1)

        self.content_layout.addLayout(export_layout)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_validate = QPushButton("Validate")
        self.btn_validate.setProperty("secondary", True)
        self.btn_validate.clicked.connect(self._validate_config)
        btn_layout.addWidget(self.btn_validate)

        btn_layout.addStretch()

        self.btn_export = QPushButton("Export All")
        self.btn_export.setProperty("secondary", True)
        self.btn_export.clicked.connect(self._export_all)
        btn_layout.addWidget(self.btn_export)

        self.content_layout.addLayout(btn_layout)

    def load_from_config(self):
        """Load and generate previews."""
        import os
        config = self.controller.config

        # Update export path with current project name
        default_export = self._get_default_export_path()
        self.export_path.set_path(default_export)

        # Generate previews with absolute paths
        openbench_root = self._get_openbench_root()
        main_yaml = self.config_manager.generate_main_nml(config, openbench_root)
        self.main_preview.set_content(main_yaml)

        ref_yaml = self.config_manager.generate_ref_nml(config)
        self.ref_preview.set_content(ref_yaml)

        sim_yaml = self.config_manager.generate_sim_nml(config)
        self.sim_preview.set_content(sim_yaml)

    def _validate_config(self):
        """Validate the configuration."""
        errors = self.config_manager.validate(self.controller.config)

        if errors:
            error_msg = "Validation errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "Validation Failed", error_msg)
        else:
            QMessageBox.information(self, "Validation Passed", "Configuration is valid!")

    def _export_all(self):
        """Export all NML files."""
        import os

        output_dir = self.export_path.path()
        if not output_dir:
            QMessageBox.warning(self, "Error", "Please select an export directory.")
            return

        # If path is relative, resolve it relative to OpenBench root
        if not os.path.isabs(output_dir):
            openbench_root = self._get_openbench_root()
            if output_dir.startswith("./"):
                output_dir = output_dir[2:]
            output_dir = os.path.join(openbench_root, output_dir)

        try:
            files = self.config_manager.export_all(
                self.controller.config,
                output_dir
            )
            file_list = "\n".join(f"• {f}" for f in files.values())
            QMessageBox.information(
                self,
                "Export Complete",
                f"Files exported successfully:\n\n{file_list}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _get_openbench_root(self) -> str:
        """Get the OpenBench root directory."""
        # Use controller's project_root if available
        if self.controller.project_root:
            return self.controller.project_root
        return get_openbench_root()

    def _get_default_export_path(self) -> str:
        """Get the default export path (OpenBench/nml/nml-yaml/project_name)."""
        import os
        openbench_root = self._get_openbench_root()
        basename = self.controller.config.get("general", {}).get("basename", "")

        # Build absolute path: OpenBench/nml/nml-yaml/project_name
        nml_yaml_path = os.path.join(openbench_root, "nml", "nml-yaml")
        if basename:
            nml_yaml_path = os.path.join(nml_yaml_path, basename)

        return nml_yaml_path

    def export_and_run(self) -> bool:
        """Export files and trigger run. Returns True if successful."""
        import os

        output_dir = self.export_path.path()
        if not output_dir:
            QMessageBox.warning(self, "Error", "Please select an export directory.")
            return False

        # If path is relative, resolve it relative to OpenBench root
        if not os.path.isabs(output_dir):
            openbench_root = self._get_openbench_root()
            if output_dir.startswith("./"):
                output_dir = output_dir[2:]
            output_dir = os.path.join(openbench_root, output_dir)

        # Validate first
        errors = self.config_manager.validate(self.controller.config)
        if errors:
            error_msg = "Cannot run with validation errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "Validation Failed", error_msg)
            return False

        # Create output directory (path already includes project name from _get_default_export_path)
        os.makedirs(output_dir, exist_ok=True)

        try:
            files = self.config_manager.export_all(
                self.controller.config,
                output_dir
            )

            # Navigate to run page
            self.controller.go_to_page("run_monitor")

            # Emit signal with main config path
            self.run_requested.emit(files["main"])
            return True

        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            return False
