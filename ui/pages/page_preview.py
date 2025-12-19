# -*- coding: utf-8 -*-
"""
Preview and Export page.
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Signal

from ui.pages.base_page import BasePage
from ui.widgets import YamlPreview
from core.config_manager import ConfigManager
from core.path_utils import get_openbench_root


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

        # Output directory info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Output Directory:"))
        self.output_dir_label = QLabel("")
        self.output_dir_label.setStyleSheet("color: #666; font-style: italic;")
        info_layout.addWidget(self.output_dir_label, 1)
        self.content_layout.addLayout(info_layout)


    def load_from_config(self):
        """Load and generate previews."""
        import os
        config = self.controller.config

        # Update output directory display
        output_dir = self.controller.get_output_dir()
        self.output_dir_label.setText(output_dir)

        # Generate previews with absolute paths
        openbench_root = self._get_openbench_root()
        main_yaml = self.config_manager.generate_main_nml(config, openbench_root, output_dir)
        self.main_preview.set_content(main_yaml)

        ref_yaml = self.config_manager.generate_ref_nml(config, openbench_root, output_dir)
        self.ref_preview.set_content(ref_yaml)

        sim_yaml = self.config_manager.generate_sim_nml(config, openbench_root, output_dir)
        self.sim_preview.set_content(sim_yaml)


    def _get_openbench_root(self) -> str:
        """Get the OpenBench root directory."""
        # Use controller's project_root if available
        if self.controller.project_root:
            return self.controller.project_root
        return get_openbench_root()

    def export_and_run(self) -> bool:
        """Export files and trigger run. Returns True if successful."""
        import os

        # Use the controller's output directory
        output_dir = self.controller.get_output_dir()

        # Validate first
        errors = self.config_manager.validate(self.controller.config)
        if errors:
            error_msg = "Cannot run with validation errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "Validation Failed", error_msg)
            return False

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        try:
            openbench_root = self._get_openbench_root()
            files = self.config_manager.export_all(
                self.controller.config,
                output_dir,
                openbench_root=openbench_root
            )

            # Navigate to run page
            self.controller.go_to_page("run_monitor")

            # Emit signal with main config path
            self.run_requested.emit(files["main"])
            return True

        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            return False
