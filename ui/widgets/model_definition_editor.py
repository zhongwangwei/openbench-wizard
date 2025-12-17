# -*- coding: utf-8 -*-
"""
Dialog for creating and editing model definition files.
"""

import os
import yaml
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
    QGroupBox, QDialogButtonBox, QFileDialog, QMessageBox,
    QHeaderView, QLabel
)
from PySide6.QtCore import Qt


# Common evaluation variables
EVALUATION_VARIABLES = [
    "Sensible_Heat",
    "Latent_Heat",
    "Ground_Heat",
    "Net_Radiation",
    "Surface_Upward_SW_Radiation",
    "Surface_Upward_LW_Radiation",
    "Gross_Primary_Productivity",
    "Ecosystem_Respiration",
    "Leaf_Area_Index",
    "Evapotranspiration",
    "Canopy_Transpiration",
    "Ground_Evaporation",
    "Total_Runoff",
    "Surface_Runoff",
    "Subsurface_Runoff",
    "Snow_Water_Equivalent",
    "Snow_Depth",
    "Surface_Soil_Moisture",
    "Root_Zone_Soil_Moisture",
    "Surface_Soil_Temperature",
    "Streamflow",
    "Water_Table_Depth",
    "Terrestrial_Water_Storage_Change",
]


class ModelDefinitionEditor(QDialog):
    """Dialog for creating new model definition files."""

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.initial_data = initial_data or {}
        self._saved_path = ""

        self.setWindowTitle("New Model Definition")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Model name
        name_group = QGroupBox("Model Information")
        name_layout = QFormLayout(name_group)

        self.model_name = QLineEdit()
        self.model_name.setPlaceholderText("e.g., CoLM, CLM5, Noah-MP")
        name_layout.addRow("Model Name:", self.model_name)

        layout.addWidget(name_group)

        # Variable mappings
        var_group = QGroupBox("Variable Mappings")
        var_layout = QVBoxLayout(var_group)

        hint_label = QLabel("Define variable names and units for each evaluation variable:")
        hint_label.setStyleSheet("color: #666; font-style: italic;")
        var_layout.addWidget(hint_label)

        # Table for variable mappings
        self.var_table = QTableWidget()
        self.var_table.setColumnCount(3)
        self.var_table.setHorizontalHeaderLabels(["Variable", "Variable Name in File", "Unit"])
        self.var_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.var_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.var_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Populate with common variables
        self.var_table.setRowCount(len(EVALUATION_VARIABLES))
        for i, var_name in enumerate(EVALUATION_VARIABLES):
            # Variable name (read-only)
            item = QTableWidgetItem(var_name.replace("_", " "))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setData(Qt.UserRole, var_name)
            self.var_table.setItem(i, 0, item)

            # Variable name in file (editable)
            self.var_table.setItem(i, 1, QTableWidgetItem(""))

            # Unit (editable)
            self.var_table.setItem(i, 2, QTableWidgetItem(""))

        var_layout.addWidget(self.var_table)

        layout.addWidget(var_group, 1)

        # Dialog buttons
        btn_layout = QHBoxLayout()

        self.btn_save = QPushButton("Save As...")
        self.btn_save.clicked.connect(self._save_file)
        btn_layout.addWidget(self.btn_save)

        btn_layout.addStretch()

        btn_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        btn_box.rejected.connect(self.reject)
        btn_layout.addWidget(btn_box)

        layout.addLayout(btn_layout)

    def _load_data(self):
        """Load initial data into form."""
        if not self.initial_data:
            return

        general = self.initial_data.get("general", {})
        if "model" in general:
            self.model_name.setText(general["model"])

        # Load variable mappings
        for i in range(self.var_table.rowCount()):
            var_item = self.var_table.item(i, 0)
            var_name = var_item.data(Qt.UserRole)

            if var_name in self.initial_data:
                var_data = self.initial_data[var_name]
                if "varname" in var_data:
                    self.var_table.item(i, 1).setText(str(var_data["varname"]))
                if "varunit" in var_data:
                    self.var_table.item(i, 2).setText(str(var_data["varunit"]))

    def get_data(self) -> Dict[str, Any]:
        """Get form data as dictionary."""
        data = {
            "general": {
                "model": self.model_name.text()
            }
        }

        # Collect variable mappings
        for i in range(self.var_table.rowCount()):
            var_item = self.var_table.item(i, 0)
            var_name = var_item.data(Qt.UserRole)

            varname = self.var_table.item(i, 1).text().strip()
            varunit = self.var_table.item(i, 2).text().strip()

            # Only include if at least varname is provided
            if varname or varunit:
                data[var_name] = {
                    "varname": varname,
                    "varunit": varunit
                }

        return data

    def _save_file(self):
        """Save model definition to file."""
        model_name = self.model_name.text().strip()
        if not model_name:
            QMessageBox.warning(self, "Error", "Please enter a model name.")
            return

        # Suggest default path
        default_dir = os.path.join(os.getcwd(), "nml", "nml-yaml", "Mod_variables_definition")
        os.makedirs(default_dir, exist_ok=True)
        default_path = os.path.join(default_dir, f"{model_name}.yaml")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Model Definition",
            default_path,
            "YAML Files (*.yaml)"
        )

        if not file_path:
            return

        # Generate and save YAML
        data = self.get_data()

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2
                )

            self._saved_path = file_path
            QMessageBox.information(
                self,
                "Success",
                f"Model definition saved to:\n{file_path}"
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

    def get_saved_path(self) -> str:
        """Get the path where the file was saved."""
        return self._saved_path
