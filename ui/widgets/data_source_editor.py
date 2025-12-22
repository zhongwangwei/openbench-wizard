# -*- coding: utf-8 -*-
"""
Dialog for editing data source configuration.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QPushButton, QGroupBox, QRadioButton, QButtonGroup,
    QDialogButtonBox, QLabel, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt

from ui.widgets.path_selector import PathSelector
from core.path_utils import to_absolute_path, validate_path, get_openbench_root


class DataSourceEditor(QDialog):
    """Dialog for editing data source configuration.

    For reference data:
        - Each variable has its own sub_dir, varname, prefix, suffix, varunit
        - These are stored per-variable in the YAML file

    For simulation data:
        - prefix/suffix are shared at the general level for all variables
        - All variables from the same case share the same naming pattern
    """

    def __init__(
        self,
        source_name: str = "",
        source_type: str = "ref",  # "ref" or "sim"
        var_name: str = "",  # Variable name (for ref data context)
        initial_data: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.source_name = source_name
        self.source_type = source_type
        self.var_name = var_name
        self.initial_data = initial_data or {}

        # Build title with context
        if source_name and var_name:
            title = f"Configure {source_name} for {var_name.replace('_', ' ')}"
        elif source_name:
            title = f"Configure Data Source: {source_name}"
        elif var_name:
            title = f"New Data Source for {var_name.replace('_', ' ')}"
        else:
            title = "New Data Source"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setModal(True)

        self._setup_ui()
        self._on_data_type_changed()  # Initial show/hide
        self._load_data()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # === Load from File Button ===
        load_layout = QHBoxLayout()
        self.btn_load_file = QPushButton("Load from File...")
        self.btn_load_file.setToolTip("Load configuration from an existing YAML file")
        self.btn_load_file.clicked.connect(self._load_from_file)
        load_layout.addWidget(self.btn_load_file)
        load_layout.addStretch()
        layout.addLayout(load_layout)

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

        # === Variable Mapping (for ref data) or File Naming (for sim data) ===
        if self.source_type == "ref":
            # For reference data: variable-specific settings
            var_group_title = f"Variable Settings ({self.var_name.replace('_', ' ')})" if self.var_name else "Variable Settings"
            var_group = QGroupBox(var_group_title)
            var_layout = QFormLayout(var_group)

            # Sub directory (optional, relative to root_dir)
            self.sub_dir_input = QLineEdit()
            self.sub_dir_input.setPlaceholderText("Subdirectory (e.g., Latent_Heat/FLUXCOM)")
            var_layout.addRow("Sub Directory:", self.sub_dir_input)

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
            self.suffix_input.setPlaceholderText("File suffix (e.g., _GLEAM_v4.2a)")
            var_layout.addRow("File Suffix:", self.suffix_input)

            layout.addWidget(var_group)
        else:
            # For simulation data: variable settings with defaults from model definition
            var_group_title = f"Variable Settings ({self.var_name.replace('_', ' ')})" if self.var_name else "Variable Settings"
            var_group = QGroupBox(var_group_title)
            var_layout = QFormLayout(var_group)

            # Sub directory (optional, relative to root_dir)
            self.sub_dir_input = QLineEdit()
            self.sub_dir_input.setPlaceholderText("Subdirectory (optional)")
            var_layout.addRow("Sub Directory:", self.sub_dir_input)

            self.varname_input = QLineEdit()
            self.varname_input.setPlaceholderText("Variable name in file (from model definition)")
            var_layout.addRow("Variable Name:", self.varname_input)

            self.varunit_input = QLineEdit()
            self.varunit_input.setPlaceholderText("Variable unit (from model definition)")
            var_layout.addRow("Variable Unit:", self.varunit_input)

            layout.addWidget(var_group)

            # File naming at general level (shared across variables)
            naming_group = QGroupBox("File Naming (Shared)")
            naming_layout = QFormLayout(naming_group)

            self.prefix_input = QLineEdit()
            self.prefix_input.setPlaceholderText("File prefix (e.g., Case01_hist_)")
            naming_layout.addRow("File Prefix:", self.prefix_input)

            self.suffix_input = QLineEdit()
            self.suffix_input.setPlaceholderText("File suffix (optional)")
            naming_layout.addRow("File Suffix:", self.suffix_input)

            layout.addWidget(naming_group)

        # === Simulation-specific: Model definition ===
        if self.source_type == "sim":
            model_group = QGroupBox("Model Settings")
            model_layout = QFormLayout(model_group)

            # Model definition with New and Show Variables buttons
            model_row = QHBoxLayout()
            self.model_nml = PathSelector(
                mode="file",
                filter="YAML Files (*.yaml)",
                placeholder="Model definition file"
            )
            model_row.addWidget(self.model_nml, 1)

            self.btn_new_model = QPushButton("New...")
            self.btn_new_model.setFixedWidth(60)
            self.btn_new_model.clicked.connect(self._create_new_model)
            model_row.addWidget(self.btn_new_model)

            self.btn_edit_model = QPushButton("Edit")
            self.btn_edit_model.setFixedWidth(50)
            self.btn_edit_model.setToolTip("Edit variables defined in the model file")
            self.btn_edit_model.clicked.connect(self._edit_model_definition)
            model_row.addWidget(self.btn_edit_model)

            model_layout.addRow("Model Definition:", model_row)

            # Connect model path change to auto-populate variable defaults
            self.model_nml.path_changed.connect(self._on_model_changed)

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
        """Load initial data into form.

        For ref data: prefix/suffix are variable-specific (at top level of data)
        For sim data: prefix/suffix are in general section (shared across variables)
        """
        data = self.initial_data
        if not data:
            return

        general = data.get("general", data)
        openbench_root = get_openbench_root()

        # Handle both "root_dir" (ref) and "dir" (sim) field names
        root_dir_value = general.get("root_dir") or general.get("dir", "")
        if root_dir_value:
            root_dir_value = to_absolute_path(root_dir_value, openbench_root)
            self.root_dir.set_path(root_dir_value)

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

        # Load variable mapping fields (for both ref and sim)
        # Check top level first, then general section for backward compatibility
        if "sub_dir" in data:
            self.sub_dir_input.setText(str(data["sub_dir"]))
        if "varname" in data:
            self.varname_input.setText(str(data["varname"]))
        if "varunit" in data:
            self.varunit_input.setText(str(data["varunit"]))

        # Load prefix/suffix from top level or general section
        if "prefix" in data:
            self.prefix_input.setText(str(data["prefix"]))
        elif "prefix" in general:
            self.prefix_input.setText(str(general["prefix"]))
        if "suffix" in data:
            self.suffix_input.setText(str(data["suffix"]))
        elif "suffix" in general:
            self.suffix_input.setText(str(general["suffix"]))

        # Model definition for sim - convert to absolute path
        if self.source_type == "sim" and "model_namelist" in general:
            model_nml = general["model_namelist"]
            if model_nml:
                model_nml = to_absolute_path(model_nml, openbench_root)
            self.model_nml.set_path(model_nml)

    def _load_from_file(self):
        """Load configuration from an existing YAML file."""
        import os

        # Get file path from user
        file_path = self._prompt_for_yaml_file()
        if not file_path:
            return

        # Load and parse YAML content
        content = self._load_yaml_content(file_path)
        if content is None:
            return

        # Extract source name from filename if creating new source
        if hasattr(self, 'name_input') and not self.name_input.text():
            source_name = os.path.splitext(os.path.basename(file_path))[0]
            self.name_input.setText(source_name)

        # Populate form fields
        general = content.get("general", {})
        self._populate_general_settings(general)
        self._populate_variable_settings(content, general)

        QMessageBox.information(
            self, "Loaded",
            f"Configuration loaded from:\n{os.path.basename(file_path)}"
        )

    def _prompt_for_yaml_file(self) -> str:
        """Open file dialog to select a YAML file. Returns file path or empty string."""
        import os

        openbench_root = get_openbench_root()
        default_dir = os.path.join(openbench_root, "nml", "nml-yaml")

        if self.source_type == "ref":
            ref_dir = os.path.join(default_dir, "Ref_variables_definition_LowRes")
            if os.path.exists(ref_dir):
                default_dir = ref_dir
        else:
            user_dir = os.path.join(default_dir, "user")
            if os.path.exists(user_dir):
                default_dir = user_dir

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration from YAML",
            default_dir,
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        return file_path

    def _load_yaml_content(self, file_path: str) -> dict:
        """Load and parse YAML file. Returns content dict or None on error."""
        import yaml

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            QMessageBox.warning(
                self, "Load Error",
                f"Failed to load file:\n{file_path}\n\nError: {str(e)}"
            )
            return None

    def _populate_general_settings(self, general: dict):
        """Populate form fields from general section of config."""
        openbench_root = get_openbench_root()

        # Root directory
        root_dir = general.get("root_dir") or general.get("dir", "")
        if root_dir:
            root_dir = to_absolute_path(root_dir, openbench_root)
            self.root_dir.set_path(root_dir)

        # Data type
        if "data_type" in general:
            if general["data_type"] in ("stn", "station"):
                self.radio_station.setChecked(True)
            else:
                self.radio_grid.setChecked(True)
            self._on_data_type_changed()

        # Data groupby
        if "data_groupby" in general:
            idx = self.groupby_combo.findText(general["data_groupby"], Qt.MatchFixedString)
            if idx >= 0:
                self.groupby_combo.setCurrentIndex(idx)

        # Time settings
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
        if "fulllist" in general and general["fulllist"]:
            self.fulllist.set_path(to_absolute_path(general["fulllist"], openbench_root))

    def _populate_variable_settings(self, content: dict, general: dict):
        """Populate variable-specific settings based on source type."""
        openbench_root = get_openbench_root()

        if self.source_type == "ref":
            self._populate_ref_variable_settings(content)
        else:
            self._populate_sim_variable_settings(content, general, openbench_root)

    def _populate_ref_variable_settings(self, content: dict):
        """Populate reference data variable-specific fields."""
        var_config = None
        if self.var_name and self.var_name in content:
            var_config = content[self.var_name]
        elif self.var_name:
            # Variable not found in file, show info
            available_vars = [k for k in content.keys() if k != "general"]
            if available_vars:
                QMessageBox.information(
                    self, "Variable Not Found",
                    f"Variable '{self.var_name}' not found in file.\n\n"
                    f"Available variables: {', '.join(available_vars[:10])}"
                    f"{'...' if len(available_vars) > 10 else ''}\n\n"
                    "General settings have been loaded."
                )

        if var_config:
            if "sub_dir" in var_config:
                self.sub_dir_input.setText(str(var_config["sub_dir"]))
            if "varname" in var_config:
                self.varname_input.setText(str(var_config["varname"]))
            if "varunit" in var_config:
                self.varunit_input.setText(str(var_config["varunit"]))
            if "prefix" in var_config:
                self.prefix_input.setText(str(var_config["prefix"]))
            if "suffix" in var_config:
                self.suffix_input.setText(str(var_config["suffix"]))

    def _populate_sim_variable_settings(self, content: dict, general: dict, openbench_root: str):
        """Populate simulation data variable-specific fields."""
        # For sim data: prefix/suffix from general
        if "prefix" in general:
            self.prefix_input.setText(str(general["prefix"]))
        if "suffix" in general:
            self.suffix_input.setText(str(general["suffix"]))

        # Load variable-specific fields from content (top level)
        # These might be saved per-variable in the wizard config
        if "sub_dir" in content:
            self.sub_dir_input.setText(str(content["sub_dir"]))
        if "varname" in content:
            self.varname_input.setText(str(content["varname"]))
        if "varunit" in content:
            self.varunit_input.setText(str(content["varunit"]))

        # Model namelist
        if "model_namelist" in general and general["model_namelist"]:
            model_path = to_absolute_path(general["model_namelist"], openbench_root)
            self.model_nml.set_path(model_path)

    def _on_model_changed(self, path: str, force: bool = False):
        """Auto-populate varname and varunit from model definition when model is selected.

        Args:
            path: Path to the model definition file
            force: If True, update fields even if they already have values
        """
        if not path or not self.var_name:
            return

        import yaml
        import os

        openbench_root = get_openbench_root()
        full_path = to_absolute_path(path, openbench_root)

        if not os.path.exists(full_path):
            return

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f) or {}
        except Exception:
            return

        # Look up current variable in model definition
        if self.var_name in content:
            var_config = content[self.var_name]

            # Update fields (only if empty, unless force=True)
            if "varname" in var_config:
                if force or not self.varname_input.text():
                    self.varname_input.setText(str(var_config["varname"]))
            if "varunit" in var_config:
                if force or not self.varunit_input.text():
                    self.varunit_input.setText(str(var_config["varunit"]))

    def _edit_model_definition(self):
        """Edit the selected model definition file."""
        import yaml
        import os
        from ui.widgets.model_definition_editor import ModelDefinitionEditor

        model_path = self.model_nml.path()
        if not model_path:
            QMessageBox.information(
                self, "No Model Selected",
                "Please select a model definition file first."
            )
            return

        # Resolve path
        openbench_root = get_openbench_root()
        full_path = to_absolute_path(model_path, openbench_root)

        if not os.path.exists(full_path):
            QMessageBox.warning(
                self, "File Not Found",
                f"Model definition file not found:\n{full_path}"
            )
            return

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f) or {}
        except Exception as e:
            QMessageBox.warning(
                self, "Load Error",
                f"Failed to load model file:\n{str(e)}"
            )
            return

        # Open editor with existing data
        dialog = ModelDefinitionEditor(
            initial_data=content,
            file_path=full_path,
            parent=self
        )
        dialog.exec()
        # Always refresh after dialog closes (user may have saved)
        self._on_model_changed(model_path, force=True)

    def get_data(self) -> Dict[str, Any]:
        """Get form data as dictionary with absolute paths.

        For ref data: variable-specific fields (sub_dir, varname, varunit, prefix, suffix)
                     are stored at top level of returned dict
        For sim data: prefix/suffix are stored in general section
        """
        is_station = self.radio_station.isChecked()
        openbench_root = get_openbench_root()

        # Convert root_dir to absolute path
        root_dir = self.root_dir.path()
        if root_dir:
            root_dir = to_absolute_path(root_dir, openbench_root)

        # Build general section
        # Use "dir" for sim data, "root_dir" for ref data
        general = {
            "data_type": "stn" if is_station else "grid",
            "data_groupby": self.groupby_combo.currentText(),
            "tim_res": self.tim_res_combo.currentText(),
            "timezone": self.timezone_spin.value(),
        }
        if self.source_type == "sim":
            general["dir"] = root_dir
        else:
            general["root_dir"] = root_dir

        # Handle year fields (preserve empty strings for station data)
        syear_text = self.syear_input.text().strip()
        eyear_text = self.eyear_input.text().strip()
        # Use try/except for robust int conversion (handles negative numbers too)
        if syear_text:
            try:
                general["syear"] = int(syear_text)
            except ValueError:
                general["syear"] = syear_text  # Keep as string if not a valid int
        else:
            general["syear"] = ""
        if eyear_text:
            try:
                general["eyear"] = int(eyear_text)
            except ValueError:
                general["eyear"] = eyear_text  # Keep as string if not a valid int
        else:
            general["eyear"] = ""

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

        # Variable-specific fields at top level (for both ref and sim)
        if self.sub_dir_input.text():
            data["sub_dir"] = self.sub_dir_input.text()
        if self.varname_input.text():
            data["varname"] = self.varname_input.text()
        if self.varunit_input.text():
            data["varunit"] = self.varunit_input.text()
        if self.prefix_input.text():
            data["prefix"] = self.prefix_input.text()
        if self.suffix_input.text():
            data["suffix"] = self.suffix_input.text()

        # For sim data: also store prefix/suffix in general section (for backward compatibility)
        if self.source_type == "sim":
            if self.prefix_input.text():
                general["prefix"] = self.prefix_input.text()
            if self.suffix_input.text():
                general["suffix"] = self.suffix_input.text()

        # Add model definition for sim - convert to absolute
        if self.source_type == "sim":
            model_path = self.model_nml.path()
            if model_path:
                model_path = to_absolute_path(model_path, openbench_root)
            data["general"]["model_namelist"] = model_path

        return data

    def accept(self):
        """Override accept to validate required fields and paths before closing."""
        # Validate source name (required for new sources)
        if hasattr(self, 'name_input'):
            source_name = self.name_input.text().strip()
            if not source_name:
                QMessageBox.warning(
                    self, "Validation Error",
                    "Source name is required."
                )
                self.name_input.setFocus()
                return

        # Validate root_dir (required)
        root_dir = self.root_dir.path()
        if not root_dir:
            QMessageBox.warning(
                self, "Validation Error",
                "Root directory is required."
            )
            return

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
