# -*- coding: utf-8 -*-
"""
General settings page.
"""

from PySide6.QtWidgets import (
    QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QGroupBox, QHBoxLayout,
    QGridLayout, QLabel, QMessageBox
)

from ui.pages.base_page import BasePage
from ui.widgets import PathSelector


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

        self.basename_input = QLineEdit()
        self.basename_input.setPlaceholderText("Project name (e.g., Initial_test)")
        project_layout.addRow("Project Name:", self.basename_input)

        self.basedir_input = PathSelector(mode="directory", placeholder="Output directory")
        project_layout.addRow("Output Directory:", self.basedir_input)

        self.content_layout.addWidget(project_group)

        # === Spatial-Temporal Settings ===
        st_group = QGroupBox("Spatial-Temporal Settings")
        st_layout = QGridLayout(st_group)

        # Year range
        st_layout.addWidget(QLabel("Year Range:"), 0, 0)
        self.syear_spin = QSpinBox()
        self.syear_spin.setRange(1900, 2100)
        self.syear_spin.setValue(2000)
        st_layout.addWidget(self.syear_spin, 0, 1)
        st_layout.addWidget(QLabel("to"), 0, 2)
        self.eyear_spin = QSpinBox()
        self.eyear_spin.setRange(1900, 2100)
        self.eyear_spin.setValue(2020)
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

        # === Performance ===
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout(perf_group)

        self.num_cores_spin = QSpinBox()
        self.num_cores_spin.setRange(1, 128)
        self.num_cores_spin.setValue(4)
        perf_layout.addRow("CPU Cores:", self.num_cores_spin)

        self.content_layout.addWidget(perf_group)

    def _on_toggle_changed(self, state):
        """Handle feature toggle changes."""
        self.save_to_config()

    def load_from_config(self):
        """Load settings from controller config."""
        import os
        import sys

        general = self.controller.config.get("general", {})
        basename = general.get("basename", "")

        self.basename_input.setText(basename)

        # Get basedir and convert to absolute path with project name
        basedir = general.get("basedir", "")

        # Find OpenBench root directory
        openbench_root = self._get_openbench_root()

        if not basedir or basedir.startswith("./output") or basedir == "./output":
            # Set default to OpenBench/output/project_name
            basedir = os.path.join(openbench_root, "output")
            if basename:
                basedir = os.path.join(basedir, basename)
        elif not os.path.isabs(basedir):
            # Convert relative path to absolute
            if basedir.startswith("./"):
                basedir = basedir[2:]
            basedir = os.path.normpath(os.path.join(openbench_root, basedir))

        self.basedir_input.set_path(basedir)

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

        weight = general.get("weight", "none")
        if weight is None:
            weight = "none"
        # Map lowercase to display text
        weight_map = {"none": "None", "area": "area", "mass": "mass"}
        display_weight = weight_map.get(str(weight).lower(), "None")
        idx = self.weight_combo.findText(display_weight)
        if idx >= 0:
            self.weight_combo.setCurrentIndex(idx)

    def save_to_config(self):
        """Save settings to controller config."""
        general = {
            "basename": self.basename_input.text(),
            "basedir": self.basedir_input.path(),
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
        }
        self.controller.update_section("general", general)

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

        # Fallback to wizard's directory
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
