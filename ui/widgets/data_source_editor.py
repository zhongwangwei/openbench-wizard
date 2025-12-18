# -*- coding: utf-8 -*-
"""
Dialog for editing data source configuration.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QPushButton, QGroupBox, QRadioButton, QButtonGroup,
    QDialogButtonBox, QLabel, QMessageBox
)
from PySide6.QtCore import Qt

from ui.widgets.path_selector import PathSelector
from core.path_utils import to_absolute_path, validate_path, get_openbench_root


class DataSourceEditor(QDialog):
    """Dialog for editing data source configuration."""

    def __init__(
        self,
        source_name: str = "",
        source_type: str = "ref",  # "ref" or "sim"
        initial_data: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.source_name = source_name
        self.source_type = source_type
        self.initial_data = initial_data or {}

        self.setWindowTitle(f"Configure Data Source: {source_name}" if source_name else "New Data Source")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._setup_ui()
        self._on_data_type_changed()  # Initial show/hide
        self._load_data()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Source name (if new)
        if not self.source_name:
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Source Name:"))
            self.name_input = QLineEdit()
            self.name_input.setPlaceholderText("e.g., GLEAM4.2a_monthly")
            name_layout.addWidget(self.name_input)
            layout.addLayout(name_layout)

        # === Basic Settings ===
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout(basic_group)

        # Root directory
        self.root_dir = PathSelector(mode="directory", placeholder="Data root directory")
        basic_layout.addRow("Root Directory:", self.root_dir)

        # Data type
        type_layout = QHBoxLayout()
        self.type_group = QButtonGroup(self)
        self.radio_grid = QRadioButton("Grid")
        self.radio_station = QRadioButton("Station")
        self.type_group.addButton(self.radio_grid)
        self.type_group.addButton(self.radio_station)
        self.radio_grid.setChecked(True)
        type_layout.addWidget(self.radio_grid)
        type_layout.addWidget(self.radio_station)
        type_layout.addStretch()
        basic_layout.addRow("Data Type:", type_layout)

        # Data groupby
        self.groupby_combo = QComboBox()
        self.groupby_combo.addItems(["Year", "Month", "Day", "Single"])
        basic_layout.addRow("Data Groupby:", self.groupby_combo)

        # Station list file (for station data, optional)
        self.fulllist_label = QLabel("Station List:")
        self.fulllist = PathSelector(
            mode="file",
            filter="CSV Files (*.csv);;All Files (*)",
            placeholder="Station list CSV file (optional)"
        )
        basic_layout.addRow(self.fulllist_label, self.fulllist)

        # Connect radio buttons to show/hide station fields
        self.radio_grid.toggled.connect(self._on_data_type_changed)
        self.radio_station.toggled.connect(self._on_data_type_changed)

        layout.addWidget(basic_group)

        # === Time Settings ===
        time_group = QGroupBox("Time Settings")
        time_layout = QFormLayout(time_group)

        # Time resolution
        self.tim_res_combo = QComboBox()
        self.tim_res_combo.addItems(["Month", "Day", "Hour", "Year"])
        time_layout.addRow("Time Resolution:", self.tim_res_combo)

        # Year range (use QLineEdit to allow empty values for station data)
        year_layout = QHBoxLayout()
        self.syear_input = QLineEdit()
        self.syear_input.setPlaceholderText("Start year (e.g., 2000)")
        self.syear_input.setFixedWidth(120)
        year_layout.addWidget(self.syear_input)
        year_layout.addWidget(QLabel("to"))
        self.eyear_input = QLineEdit()
        self.eyear_input.setPlaceholderText("End year (e.g., 2020)")
        self.eyear_input.setFixedWidth(120)
        year_layout.addWidget(self.eyear_input)
        year_layout.addStretch()
        time_layout.addRow("Year Range:", year_layout)

        # Timezone
        self.timezone_spin = QDoubleSpinBox()
        self.timezone_spin.setRange(-12.0, 14.0)
        self.timezone_spin.setValue(0.0)
        self.timezone_spin.setSingleStep(0.5)
        time_layout.addRow("Timezone Offset:", self.timezone_spin)

        # Grid resolution (for grid data, use QLineEdit to allow empty values)
        self.grid_res_label = QLabel("Grid Resolution:")
        self.grid_res_input = QLineEdit()
        self.grid_res_input.setPlaceholderText("e.g., 2.0")
        self.grid_res_input.setFixedWidth(120)
        time_layout.addRow(self.grid_res_label, self.grid_res_input)

        layout.addWidget(time_group)

        # === Variable Mapping ===
        var_group = QGroupBox("Variable Mapping")
        var_layout = QFormLayout(var_group)

        self.varname_input = QLineEdit()
        self.varname_input.setPlaceholderText("Variable name in file (e.g., E)")
        var_layout.addRow("Variable Name:", self.varname_input)

        self.varunit_input = QLineEdit()
        self.varunit_input.setPlaceholderText("e.g., mm month-1")
        var_layout.addRow("Variable Unit:", self.varunit_input)

        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("File prefix (e.g., E_)")
        var_layout.addRow("File Prefix:", self.prefix_input)

        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("File suffix (e.g., _GLEAM_v4.2a_MO)")
        var_layout.addRow("File Suffix:", self.suffix_input)

        layout.addWidget(var_group)

        # === Simulation-specific: Model definition ===
        if self.source_type == "sim":
            model_group = QGroupBox("Model Settings")
            model_layout = QFormLayout(model_group)

            # Model definition with New button
            model_row = QHBoxLayout()
            self.model_nml = PathSelector(
                mode="file",
                filter="YAML Files (*.yaml)",
                placeholder="Model definition file"
            )
            model_row.addWidget(self.model_nml, 1)

            self.btn_new_model = QPushButton("New...")
            self.btn_new_model.setFixedWidth(70)
            self.btn_new_model.clicked.connect(self._create_new_model)
            model_row.addWidget(self.btn_new_model)

            model_layout.addRow("Model Definition:", model_row)

            layout.addWidget(model_group)

        # === Dialog Buttons ===
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_data_type_changed(self):
        """Show/hide fields based on data type selection."""
        is_station = self.radio_station.isChecked()
        # Show fulllist only for station data
        self.fulllist_label.setVisible(is_station)
        self.fulllist.setVisible(is_station)
        # Show grid_res only for grid data
        self.grid_res_label.setVisible(not is_station)
        self.grid_res_input.setVisible(not is_station)

    def _load_data(self):
        """Load initial data into form."""
        data = self.initial_data
        if not data:
            return

        general = data.get("general", data)
        openbench_root = get_openbench_root()

        if "root_dir" in general:
            # Convert to absolute path when loading
            root_dir = general["root_dir"]
            if root_dir:
                root_dir = to_absolute_path(root_dir, openbench_root)
            self.root_dir.set_path(root_dir)

        if "data_type" in general:
            # Support both "stn" and "station" as station data type
            if general["data_type"] in ("stn", "station"):
                self.radio_station.setChecked(True)
            else:
                self.radio_grid.setChecked(True)
            self._on_data_type_changed()  # Update visibility

        if "data_groupby" in general:
            idx = self.groupby_combo.findText(general["data_groupby"], Qt.MatchFixedString)
            if idx >= 0:
                self.groupby_combo.setCurrentIndex(idx)

        if "tim_res" in general:
            idx = self.tim_res_combo.findText(general["tim_res"], Qt.MatchFixedString)
            if idx >= 0:
                self.tim_res_combo.setCurrentIndex(idx)

        if "syear" in general:
            self.syear_input.setText(str(general["syear"]))
        if "eyear" in general:
            self.eyear_input.setText(str(general["eyear"]))
        if "timezone" in general:
            try:
                self.timezone_spin.setValue(float(general["timezone"]))
            except (ValueError, TypeError):
                pass
        if "grid_res" in general:
            self.grid_res_input.setText(str(general["grid_res"]))
        if "fulllist" in general:
            # Convert fulllist to absolute path when loading
            fulllist = general["fulllist"]
            if fulllist:
                fulllist = to_absolute_path(fulllist, openbench_root)
            self.fulllist.set_path(fulllist)

        # Variable mapping (might be at top level for ref data)
        var_data = data if "varname" in data else general
        if "varname" in var_data:
            self.varname_input.setText(str(var_data["varname"]))
        if "varunit" in var_data:
            self.varunit_input.setText(str(var_data["varunit"]))
        if "prefix" in var_data:
            self.prefix_input.setText(str(var_data["prefix"]))
        if "suffix" in var_data:
            self.suffix_input.setText(str(var_data["suffix"]))

        # Model definition for sim - convert to absolute path
        if self.source_type == "sim" and "model_namelist" in general:
            model_nml = general["model_namelist"]
            if model_nml:
                model_nml = to_absolute_path(model_nml, openbench_root)
            self.model_nml.set_path(model_nml)

    def get_data(self) -> Dict[str, Any]:
        """Get form data as dictionary with absolute paths."""
        is_station = self.radio_station.isChecked()
        openbench_root = get_openbench_root()

        # Convert root_dir to absolute path
        root_dir = self.root_dir.path()
        if root_dir:
            root_dir = to_absolute_path(root_dir, openbench_root)

        # Build general section
        general = {
            "root_dir": root_dir,
            "data_type": "stn" if is_station else "grid",
            "data_groupby": self.groupby_combo.currentText(),
            "tim_res": self.tim_res_combo.currentText(),
            "timezone": self.timezone_spin.value(),
        }

        # Handle year fields (preserve empty strings for station data)
        syear_text = self.syear_input.text().strip()
        eyear_text = self.eyear_input.text().strip()
        general["syear"] = int(syear_text) if syear_text.isdigit() else syear_text
        general["eyear"] = int(eyear_text) if eyear_text.isdigit() else eyear_text

        # Handle grid_res (preserve empty strings)
        grid_res_text = self.grid_res_input.text().strip()
        if grid_res_text:
            try:
                general["grid_res"] = float(grid_res_text)
            except ValueError:
                general["grid_res"] = grid_res_text
        else:
            general["grid_res"] = ""

        # Add fulllist for station data (optional) - convert to absolute
        if is_station:
            fulllist_path = self.fulllist.path()
            if fulllist_path:
                general["fulllist"] = to_absolute_path(fulllist_path, openbench_root)

        data = {"general": general}

        # Add variable mapping
        if self.varname_input.text():
            data["varname"] = self.varname_input.text()
        if self.varunit_input.text():
            data["varunit"] = self.varunit_input.text()
        if self.prefix_input.text():
            data["prefix"] = self.prefix_input.text()
        if self.suffix_input.text():
            data["suffix"] = self.suffix_input.text()

        # Add model definition for sim - convert to absolute
        if self.source_type == "sim":
            model_path = self.model_nml.path()
            if model_path:
                model_path = to_absolute_path(model_path, openbench_root)
            data["general"]["model_namelist"] = model_path

        return data

    def accept(self):
        """Override accept to validate paths before closing."""
        # Validate root_dir
        root_dir = self.root_dir.path()
        if root_dir:
            root_dir = to_absolute_path(root_dir, get_openbench_root())
            is_valid, error = validate_path(root_dir, "directory")
            if not is_valid:
                QMessageBox.warning(
                    self, "Invalid Path",
                    f"Root directory path is invalid:\n{root_dir}\n\n{error}"
                )
                return

        # Validate fulllist if station data
        if self.radio_station.isChecked():
            fulllist_path = self.fulllist.path()
            if fulllist_path:
                fulllist_path = to_absolute_path(fulllist_path, get_openbench_root())
                is_valid, error = validate_path(fulllist_path, "file")
                if not is_valid:
                    QMessageBox.warning(
                        self, "Invalid Path",
                        f"Station list file path is invalid:\n{fulllist_path}\n\n{error}"
                    )
                    return

        # Validate model_namelist for sim data
        if self.source_type == "sim":
            model_path = self.model_nml.path()
            if model_path:
                model_path = to_absolute_path(model_path, get_openbench_root())
                is_valid, error = validate_path(model_path, "file")
                if not is_valid:
                    QMessageBox.warning(
                        self, "Invalid Path",
                        f"Model definition file path is invalid:\n{model_path}\n\n{error}"
                    )
                    return

        super().accept()

    def get_source_name(self) -> str:
        """Get source name."""
        if hasattr(self, 'name_input'):
            return self.name_input.text()
        return self.source_name

    def _create_new_model(self):
        """Create a new model definition file."""
        from ui.widgets.model_definition_editor import ModelDefinitionEditor
        dialog = ModelDefinitionEditor(parent=self)
        if dialog.exec():
            file_path = dialog.get_saved_path()
            if file_path:
                self.model_nml.set_path(file_path)
