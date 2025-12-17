# -*- coding: utf-8 -*-
"""
Main window with sidebar navigation and page container.
"""

import os
import yaml

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget,
    QPushButton, QLabel, QFrame, QMessageBox,
    QFileDialog, QSplitter
)
from PySide6.QtCore import Qt, QSize

from ui.wizard_controller import WizardController
from ui.pages import (
    PageGeneral, PageEvaluation, PageMetrics, PageScores,
    PageComparisons, PageStatistics, PageRefData, PageSimData,
    PagePreview, PageRunMonitor
)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenBench NML Wizard")
        self.setMinimumSize(1200, 800)

        # Initialize controller
        self.controller = WizardController(self)

        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._update_navigation()

    def _setup_ui(self):
        """Initialize the user interface."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for sidebar and content
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # === Sidebar ===
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet("QWidget#sidebar { background-color: #2d2d2d; }")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo/Title area
        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: #252525; padding: 20px;")
        title_layout = QVBoxLayout(title_frame)

        title_label = QLabel("OpenBench")
        title_label.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("NML Configuration Wizard")
        subtitle_label.setStyleSheet("color: #888888; font-size: 12px;")
        title_layout.addWidget(subtitle_label)

        sidebar_layout.addWidget(title_frame)

        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("nav_sidebar")
        self.nav_list.setFocusPolicy(Qt.NoFocus)
        sidebar_layout.addWidget(self.nav_list)

        # Sidebar buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background-color: #252525; padding: 10px;")
        btn_layout = QVBoxLayout(btn_frame)

        self.btn_load = QPushButton("Load Config...")
        self.btn_load.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #cccccc;
                border: none;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        btn_layout.addWidget(self.btn_load)

        self.btn_new = QPushButton("New Config")
        self.btn_new.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #cccccc;
                border: none;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        btn_layout.addWidget(self.btn_new)

        sidebar_layout.addWidget(btn_frame)

        splitter.addWidget(sidebar)

        # === Content Area ===
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Page stack
        self.page_stack = QStackedWidget()
        self._setup_pages()
        content_layout.addWidget(self.page_stack, 1)

        # Bottom navigation bar
        nav_bar = QFrame()
        nav_bar.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-top: 1px solid #e0e0e0;
            }
        """)
        nav_bar_layout = QHBoxLayout(nav_bar)
        nav_bar_layout.setContentsMargins(20, 15, 20, 15)

        self.btn_back = QPushButton("Back")
        self.btn_back.setProperty("secondary", True)
        self.btn_back.setMinimumWidth(100)
        nav_bar_layout.addWidget(self.btn_back)

        nav_bar_layout.addStretch()

        # Page indicator
        self.page_indicator = QLabel("Step 1 of 10")
        self.page_indicator.setStyleSheet("color: #666666;")
        nav_bar_layout.addWidget(self.page_indicator)

        nav_bar_layout.addStretch()

        self.btn_next = QPushButton("Next")
        self.btn_next.setMinimumWidth(100)
        nav_bar_layout.addWidget(self.btn_next)

        content_layout.addWidget(nav_bar)

        splitter.addWidget(content)

        # Set splitter sizes (sidebar: 220px, content: rest)
        splitter.setSizes([220, 980])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

    def _setup_pages(self):
        """Create and add all pages to the stack."""
        self.pages = {}

        page_classes = {
            "general": PageGeneral,
            "evaluation_items": PageEvaluation,
            "metrics": PageMetrics,
            "scores": PageScores,
            "comparisons": PageComparisons,
            "statistics": PageStatistics,
            "ref_data": PageRefData,
            "sim_data": PageSimData,
            "preview": PagePreview,
            "run_monitor": PageRunMonitor,
        }

        for page_id, page_class in page_classes.items():
            page = page_class(self.controller)
            self.pages[page_id] = page
            self.page_stack.addWidget(page)

        # Connect preview page run signal to monitor page
        if "preview" in self.pages and "run_monitor" in self.pages:
            self.pages["preview"].run_requested.connect(
                self.pages["run_monitor"].start_run
            )

    def _connect_signals(self):
        """Connect signals to slots."""
        # Navigation buttons
        self.btn_back.clicked.connect(self._on_back_clicked)
        self.btn_next.clicked.connect(self._on_next_clicked)
        self.btn_load.clicked.connect(self._on_load_clicked)
        self.btn_new.clicked.connect(self._on_new_clicked)

        # Sidebar navigation
        self.nav_list.currentRowChanged.connect(self._on_nav_selected)

        # Controller signals
        self.controller.page_changed.connect(self._on_page_changed)
        self.controller.pages_visibility_changed.connect(self._update_navigation)

    def _update_navigation(self):
        """Update sidebar navigation based on visible pages."""
        current = self.controller.current_page
        visible_pages = self.controller.get_visible_pages()

        self.nav_list.blockSignals(True)
        self.nav_list.clear()

        for page_id in self.controller.ALL_PAGES:
            item = QListWidgetItem(self.controller.get_page_name(page_id))
            item.setData(Qt.UserRole, page_id)

            if page_id not in visible_pages:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setForeground(Qt.gray)

            self.nav_list.addItem(item)

            if page_id == current:
                self.nav_list.setCurrentItem(item)

        self.nav_list.blockSignals(False)
        self._update_buttons()
        self._update_page_indicator()

    def _update_buttons(self):
        """Update Back/Next button states."""
        self.btn_back.setEnabled(self.controller.prev_page() is not None)

        next_page = self.controller.next_page()
        if next_page is None:
            self.btn_next.setText("Finish")
        elif self.controller.current_page == "preview":
            self.btn_next.setText("Run")
        else:
            self.btn_next.setText("Next")

    def _update_page_indicator(self):
        """Update the step indicator."""
        visible = self.controller.get_visible_pages()
        current = self.controller.current_page
        try:
            idx = visible.index(current) + 1
            self.page_indicator.setText(f"Step {idx} of {len(visible)}")
        except ValueError:
            self.page_indicator.setText("")

    def _on_nav_selected(self, row: int):
        """Handle sidebar navigation selection."""
        item = self.nav_list.item(row)
        if item and item.flags() & Qt.ItemIsEnabled:
            page_id = item.data(Qt.UserRole)
            self.controller.go_to_page(page_id)

    def _on_page_changed(self, page_id: str):
        """Handle page change."""
        if page_id in self.pages:
            self.page_stack.setCurrentWidget(self.pages[page_id])
            self._update_navigation()

    def _on_back_clicked(self):
        """Handle Back button click."""
        self.controller.go_prev()

    def _on_next_clicked(self):
        """Handle Next button click."""
        # Validate current page before proceeding
        current_page = self.pages.get(self.controller.current_page)
        if current_page and callable(getattr(current_page, 'validate', None)):
            if not current_page.validate():
                return

        # Special handling for Preview page - trigger export and run
        if self.controller.current_page == "preview":
            preview_page = self.pages.get("preview")
            if preview_page:
                preview_page.export_and_run()
            return

        if not self.controller.go_next():
            # At the end - show completion message and close app
            QMessageBox.information(
                self,
                "Complete",
                "Configuration wizard completed!"
            )
            self.close()

    def _on_load_clicked(self):
        """Handle Load Config button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        if file_path:
            self._load_config_file(file_path)

    def _load_config_file(self, file_path: str):
        """Load configuration from a YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f) or {}

            # Get the directory of the config file for resolving relative paths
            config_dir = os.path.dirname(os.path.abspath(file_path))
            base_dir = os.path.dirname(config_dir)  # Assume nml-yaml is one level down from base

            # Start with default config
            new_config = self.controller._default_config()

            # Check if this is a main config file (has reference_nml and simulation_nml)
            general = loaded_config.get("general", {})

            if "reference_nml" in general or "simulation_nml" in general:
                # This is a main config file
                self._load_main_config(loaded_config, new_config, config_dir, base_dir)
            elif any(key.endswith("_ref_source") for key in general.keys()):
                # This is a ref config file
                new_config["ref_data"] = loaded_config
                self._extract_evaluation_items_from_ref(loaded_config, new_config)
            elif any(key.endswith("_sim_source") for key in general.keys()):
                # This is a sim config file
                new_config["sim_data"] = loaded_config
                self._extract_evaluation_items_from_sim(loaded_config, new_config)
            else:
                # Unknown format, try to load as-is
                new_config.update(loaded_config)

            # Update the controller with the new config
            self.controller.config = new_config

            # Navigate to the first page
            self.controller.go_to_page("general")

            # Refresh all pages
            for page in self.pages.values():
                if hasattr(page, 'load_from_config'):
                    page.load_from_config()

            QMessageBox.information(
                self,
                "Configuration Loaded",
                f"Successfully loaded configuration from:\n{file_path}"
            )

        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "Error",
                f"File not found:\n{file_path}"
            )
        except yaml.YAMLError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to parse YAML file:\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load configuration:\n{str(e)}"
            )

    def _load_main_config(self, loaded_config: dict, new_config: dict,
                          config_dir: str, base_dir: str):
        """Load a main config file and its referenced ref/sim configs."""
        general = loaded_config.get("general", {})

        # Copy general settings
        for key, value in general.items():
            if key not in ("reference_nml", "simulation_nml", "statistics_nml", "figure_nml"):
                new_config["general"][key] = value

        # Copy other sections
        for section in ("evaluation_items", "metrics", "scores", "comparisons", "statistics"):
            if section in loaded_config:
                new_config[section] = loaded_config[section]

        # Load reference NML if specified
        ref_nml_path = general.get("reference_nml", "")
        if ref_nml_path:
            ref_full_path = self._resolve_path(ref_nml_path, config_dir, base_dir)
            if ref_full_path and os.path.exists(ref_full_path):
                try:
                    with open(ref_full_path, 'r', encoding='utf-8') as f:
                        ref_config = yaml.safe_load(f) or {}
                    new_config["ref_data"] = ref_config
                except Exception as e:
                    print(f"Warning: Failed to load reference NML: {e}")

        # Load simulation NML if specified
        sim_nml_path = general.get("simulation_nml", "")
        if sim_nml_path:
            sim_full_path = self._resolve_path(sim_nml_path, config_dir, base_dir)
            if sim_full_path and os.path.exists(sim_full_path):
                try:
                    with open(sim_full_path, 'r', encoding='utf-8') as f:
                        sim_config = yaml.safe_load(f) or {}
                    new_config["sim_data"] = sim_config
                except Exception as e:
                    print(f"Warning: Failed to load simulation NML: {e}")

    def _resolve_path(self, path: str, config_dir: str, base_dir: str) -> str:
        """Resolve a path that might be relative to different base directories."""
        if os.path.isabs(path):
            return path

        # Try relative to base_dir first (for paths like ./nml/nml-yaml/...)
        if path.startswith("./"):
            relative_path = path[2:]

            # Try from current working directory first
            full_path = os.path.normpath(os.path.join(os.getcwd(), relative_path))
            if os.path.exists(full_path):
                return full_path

            # Try from project root (parent of nml directory, i.e., OpenBench)
            project_root = os.path.dirname(base_dir)
            full_path = os.path.normpath(os.path.join(project_root, relative_path))
            if os.path.exists(full_path):
                return full_path

            # Try from base_dir
            full_path = os.path.normpath(os.path.join(base_dir, relative_path))
            if os.path.exists(full_path):
                return full_path

            # Try from config_dir
            full_path = os.path.normpath(os.path.join(config_dir, relative_path))
            if os.path.exists(full_path):
                return full_path

        # Try relative to config_dir
        full_path = os.path.normpath(os.path.join(config_dir, path))
        if os.path.exists(full_path):
            return full_path

        # Try relative to base_dir
        full_path = os.path.normpath(os.path.join(base_dir, path))
        if os.path.exists(full_path):
            return full_path

        # Return the path as-is if nothing works
        return path

    def _extract_evaluation_items_from_ref(self, ref_config: dict, new_config: dict):
        """Extract evaluation items from ref config source keys."""
        general = ref_config.get("general", {})
        for key in general.keys():
            if key.endswith("_ref_source"):
                var_name = key.replace("_ref_source", "")
                new_config["evaluation_items"][var_name] = True

    def _extract_evaluation_items_from_sim(self, sim_config: dict, new_config: dict):
        """Extract evaluation items from sim config source keys."""
        general = sim_config.get("general", {})
        for key in general.keys():
            if key.endswith("_sim_source"):
                var_name = key.replace("_sim_source", "")
                new_config["evaluation_items"][var_name] = True

    def _on_new_clicked(self):
        """Handle New Config button click."""
        reply = QMessageBox.question(
            self,
            "New Configuration",
            "Create a new configuration? Any unsaved changes will be lost.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.controller.reset()
