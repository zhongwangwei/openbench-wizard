# -*- coding: utf-8 -*-
"""
Preview and Export page.
"""

import logging
import os
import tempfile

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Signal

from ui.pages.base_page import BasePage
from ui.widgets import YamlPreview
from core.config_manager import ConfigManager
# get_openbench_root is now inherited from BasePage via _get_openbench_root()

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

    def export_and_run(self) -> bool:
        """Export files and trigger run. Returns True if successful."""
        # Use the controller's output directory
        output_dir = self.controller.get_output_dir()

        # Validate first
        errors = self.config_manager.validate(self.controller.config)
        if errors:
            error_msg = "Cannot run with validation errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "Validation Failed", error_msg)
            return False

        # Check if in remote mode
        general = self.controller.config.get("general", {})
        is_remote = general.get("execution_mode") == "remote"

        if is_remote:
            return self._export_and_run_remote(output_dir)
        else:
            return self._export_and_run_local(output_dir)

    def _export_and_run_local(self, output_dir: str) -> bool:
        """Export files locally and trigger run."""
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

    def _export_and_run_remote(self, output_dir: str) -> bool:
        """Export files to remote server and trigger run."""
        ssh_manager = get_remote_ssh_manager(self.controller)
        if not ssh_manager or not ssh_manager.is_connected:
            QMessageBox.warning(
                self, "Not Connected",
                "Please connect to the remote server first in the Runtime Environment page."
            )
            return False

        try:
            # Create output directory on remote server
            nml_dir = f"{output_dir}/nml"
            sim_nml_dir = f"{nml_dir}/sim"
            ref_nml_dir = f"{nml_dir}/ref"

            stdout, stderr, exit_code = ssh_manager.execute(
                f"mkdir -p '{nml_dir}' '{sim_nml_dir}' '{ref_nml_dir}'",
                timeout=30
            )
            if exit_code != 0:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to create remote directories:\n{stderr}"
                )
                return False

            # Export to local temp directory, but use remote paths in generated files
            with tempfile.TemporaryDirectory() as temp_dir:
                openbench_root = self._get_openbench_root()

                # Get remote OpenBench path from remote config
                remote_config = self.controller.config.get("general", {}).get("remote", {})
                remote_openbench_path = remote_config.get("openbench_path", "")

                # Generate config files with remote output_dir paths
                # This ensures paths like reference_nml point to remote locations
                files = self._export_for_remote(
                    temp_dir, output_dir, openbench_root, remote_openbench_path
                )

                # Upload files to remote server
                sftp = ssh_manager._client.open_sftp()
                try:
                    # Upload all files in nml directory
                    local_nml_dir = os.path.join(temp_dir, "nml")
                    self._upload_directory(sftp, local_nml_dir, nml_dir)
                finally:
                    sftp.close()

            # Navigate to run page
            self.controller.go_to_page("run_monitor")

            # Emit signal with remote main config path
            basename = self.controller.config.get("general", {}).get("basename", "config")
            remote_main_path = f"{nml_dir}/main-{basename}.yaml"
            self.run_requested.emit(remote_main_path)
            return True

        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            return False

    def _export_for_remote(self, local_dir: str, remote_dir: str, openbench_root: str,
                            remote_openbench_path: str = "") -> dict:
        """Export config files locally but with remote paths inside.

        Args:
            local_dir: Local directory to write files to
            remote_dir: Remote directory that paths should point to
            openbench_root: OpenBench root directory (local, for fallback)
            remote_openbench_path: OpenBench installation path on remote server

        Returns:
            Dictionary of {file_type: local_file_path}
        """
        import yaml

        config = self.controller.config
        basename = config.get("general", {}).get("basename", "config")

        # Create local nml directories
        nml_dir = os.path.join(local_dir, "nml")
        sim_nml_dir = os.path.join(nml_dir, "sim")
        ref_nml_dir = os.path.join(nml_dir, "ref")
        os.makedirs(sim_nml_dir, exist_ok=True)
        os.makedirs(ref_nml_dir, exist_ok=True)

        files = {}

        # Generate main config with remote paths
        remote_nml_dir = f"{remote_dir}/nml"
        main_content = self.config_manager.generate_main_nml(
            config, openbench_root, remote_dir, remote_openbench_path
        )
        main_path = os.path.join(nml_dir, f"main-{basename}.yaml")
        with open(main_path, 'w', encoding='utf-8') as f:
            f.write(main_content)
        files["main"] = main_path

        # Generate ref config with remote paths
        ref_content = self.config_manager.generate_ref_nml(config, openbench_root, remote_dir)
        ref_path = os.path.join(nml_dir, f"ref-{basename}.yaml")
        with open(ref_path, 'w', encoding='utf-8') as f:
            f.write(ref_content)
        files["ref"] = ref_path

        # Generate sim config with remote paths
        sim_content = self.config_manager.generate_sim_nml(config, openbench_root, remote_dir)
        sim_path = os.path.join(nml_dir, f"sim-{basename}.yaml")
        with open(sim_path, 'w', encoding='utf-8') as f:
            f.write(sim_content)
        files["sim"] = sim_path

        # Sync namelists (source definition files) with remote paths
        self._sync_namelists_for_remote(config, local_dir, remote_dir, openbench_root)

        return files

    def _sync_namelists_for_remote(self, config: dict, local_dir: str, remote_dir: str, openbench_root: str):
        """Sync namelist files with remote paths."""
        import yaml
        import shutil
        from core.path_utils import remote_join

        nml_dir = os.path.join(local_dir, "nml")
        sim_nml_dir = os.path.join(nml_dir, "sim")
        ref_nml_dir = os.path.join(nml_dir, "ref")
        sim_models_dir = os.path.join(sim_nml_dir, "models")

        os.makedirs(sim_nml_dir, exist_ok=True)
        os.makedirs(ref_nml_dir, exist_ok=True)
        os.makedirs(sim_models_dir, exist_ok=True)

        # Get SSH manager for remote file reading
        ssh_manager = get_remote_ssh_manager(self.controller)

        eval_items = config.get("evaluation_items", {})
        selected_items = [k for k, v in eval_items.items() if v]

        # Process simulation data namelists - group by source_name
        sim_data = config.get("sim_data", {})
        sim_source_configs = sim_data.get("source_configs", {})

        # Group configs by source_name
        sim_grouped = {}
        for key, source_config in sim_source_configs.items():
            if "::" in key:
                var_name, source_name = key.split("::", 1)
            else:
                source_name = key
                var_name = None

            if source_name not in sim_grouped:
                sim_grouped[source_name] = {"configs": [], "var_names": []}
            sim_grouped[source_name]["configs"].append(source_config)
            if var_name:
                sim_grouped[source_name]["var_names"].append(var_name)

        # Write grouped sim configs
        for source_name, group_data in sim_grouped.items():
            # Merge configs for the same source
            merged_config = self._merge_source_configs(group_data["configs"], group_data["var_names"])
            dest_path = os.path.join(sim_nml_dir, f"{source_name}.yaml")
            self._write_source_config_remote(merged_config, dest_path, selected_items, openbench_root)

        # Copy model definition files for sim (read from remote server)
        sim_def_nml = sim_data.get("def_nml", {})
        for source_name, model_path in sim_def_nml.items():
            if model_path:
                actual_path = self._resolve_model_path(model_path, openbench_root, is_remote=True)
                if actual_path:
                    # Extract model name from path
                    model_basename = actual_path.rstrip('/').split('/')[-1]
                    model_name = os.path.splitext(model_basename)[0] + ".yaml"
                    dest_path = os.path.join(sim_models_dir, model_name)
                    self._copy_model_definition_filtered(actual_path, dest_path, selected_items, is_remote=True, ssh_manager=ssh_manager)

        # Process reference data namelists - group by source_name
        ref_data = config.get("ref_data", {})
        ref_source_configs = ref_data.get("source_configs", {})

        # Group configs by source_name
        ref_grouped = {}
        for key, source_config in ref_source_configs.items():
            if "::" in key:
                var_name, source_name = key.split("::", 1)
            else:
                source_name = key
                var_name = None

            if source_name not in ref_grouped:
                ref_grouped[source_name] = {"configs": [], "var_names": []}
            ref_grouped[source_name]["configs"].append(source_config)
            if var_name:
                ref_grouped[source_name]["var_names"].append(var_name)

        # Write grouped ref configs
        for source_name, group_data in ref_grouped.items():
            # Merge configs for the same source
            merged_config = self._merge_source_configs(group_data["configs"], group_data["var_names"])
            dest_path = os.path.join(ref_nml_dir, f"{source_name}.yaml")
            self._write_source_config_remote(merged_config, dest_path, selected_items, openbench_root)

    def _merge_source_configs(self, configs: list, var_names: list) -> dict:
        """Merge multiple source configs into one."""
        if not configs:
            return {}

        merged = {}

        # Use the first config's general section
        for cfg in configs:
            if "general" in cfg and isinstance(cfg["general"], dict):
                merged["general"] = cfg["general"].copy()
                break

        # Merge all variable-specific configs
        for cfg, var_name in zip(configs, var_names or [None] * len(configs)):
            for key, value in cfg.items():
                if key in ("general", "_var_name", "def_nml_path"):
                    continue
                if isinstance(value, dict):
                    merged[key] = value.copy()
                else:
                    merged[key] = value

        return merged

    def _resolve_model_path(self, model_path: str, openbench_root: str, is_remote: bool = False) -> str:
        """Resolve model definition path, handling .nml to .yaml conversion."""
        from core.path_utils import to_absolute_path

        if not model_path:
            return ""

        if is_remote:
            # In remote mode, just normalize the path (don't check local existence)
            # The path is already a remote path
            path = model_path.replace('\\', '/')
            if not path.startswith('/') and openbench_root:
                if path.startswith('./'):
                    path = path[2:]
                path = f"{openbench_root.rstrip('/')}/{path}"
            return path

        # Local mode: Convert to absolute path
        abs_path = to_absolute_path(model_path, openbench_root)

        # If file exists, return it
        if os.path.exists(abs_path):
            return abs_path

        # Try .yaml extension if .nml was specified
        if abs_path.endswith('.nml'):
            yaml_path = abs_path[:-4] + '.yaml'
            if os.path.exists(yaml_path):
                return yaml_path

        return ""

    def _copy_model_definition_filtered(self, src_path: str, dest_path: str, selected_items: list, is_remote: bool = False, ssh_manager=None):
        """Copy model definition file with filtering for selected items."""
        import yaml

        content = {}

        if is_remote and ssh_manager:
            # Read from remote server via SSH
            try:
                # Try .yaml first, then .nml
                paths_to_try = [src_path]
                if src_path.endswith('.nml'):
                    paths_to_try.insert(0, src_path[:-4] + '.yaml')

                for path in paths_to_try:
                    stdout, stderr, exit_code = ssh_manager.execute(f"cat '{path}' 2>/dev/null", timeout=30)
                    if exit_code == 0 and stdout.strip():
                        content = yaml.safe_load(stdout) or {}
                        break
            except Exception:
                return
        else:
            # Read from local file
            try:
                with open(src_path, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f) or {}
            except Exception:
                return

        if not content:
            return

        # Filter to only include selected items
        filtered = {}
        for item in selected_items:
            if item in content and isinstance(content[item], dict):
                filtered[item] = content[item].copy()

        if filtered:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'w', encoding='utf-8') as f:
                yaml.dump(filtered, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)

    def _write_source_config_remote(self, source_data: dict, dest_path: str, selected_items: list, openbench_root: str):
        """Write source config file for remote execution."""
        import yaml

        if not source_data:
            return

        filtered = {}

        # Process general section
        if "general" in source_data and isinstance(source_data["general"], dict):
            general = source_data["general"].copy()
            # Keep paths as-is (they should already be remote paths)
            filtered["general"] = general

        # Include selected evaluation items (with type validation)
        for item in selected_items:
            if item in source_data:
                item_data = source_data[item]
                if isinstance(item_data, dict):
                    filtered[item] = item_data.copy()
                elif item_data is not None:
                    # Handle non-dict values (e.g., strings or other types)
                    filtered[item] = item_data

        # Add var-specific fields from top level to items that already exist in filtered
        # (i.e., items that were found in source_data - don't create entries for non-existent variables)
        for field in ["sub_dir", "varname", "varunit", "prefix", "suffix"]:
            if field in source_data:
                field_value = source_data[field]
                # Only apply to items that already exist in filtered
                for item in selected_items:
                    if item in filtered and isinstance(filtered[item], dict):
                        if field not in filtered[item]:
                            filtered[item][field] = field_value

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, 'w', encoding='utf-8') as f:
            yaml.dump(filtered, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)

    def _upload_directory(self, sftp, local_dir: str, remote_dir: str):
        """Recursively upload a directory to remote server."""
        if not os.path.exists(local_dir):
            return

        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = f"{remote_dir}/{item}"

            if os.path.isfile(local_path):
                sftp.put(local_path, remote_path)
            elif os.path.isdir(local_path):
                # Create remote directory
                try:
                    sftp.mkdir(remote_path)
                except IOError:
                    pass  # Directory may already exist
                self._upload_directory(sftp, local_path, remote_path)
