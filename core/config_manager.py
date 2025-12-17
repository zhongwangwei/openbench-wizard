# -*- coding: utf-8 -*-
"""
Configuration manager for loading, saving, and validating NML configs.
"""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path

import yaml


class ConfigManager:
    """Manages NML configuration loading, saving, and validation."""

    def __init__(self):
        self._last_dir = os.path.expanduser("~")

    def load_from_yaml(self, path: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.

        Args:
            path: Path to the YAML file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self._last_dir = os.path.dirname(path)
        return config or {}

    def save_to_yaml(self, config: Dict[str, Any], path: str):
        """
        Save configuration to a YAML file.

        Args:
            config: Configuration dictionary
            path: Output file path
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(
                config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2
            )

    def generate_main_nml(self, config: Dict[str, Any]) -> str:
        """
        Generate main NML YAML content.

        Args:
            config: Full configuration dictionary

        Returns:
            YAML string
        """
        main_config = {}

        # General section
        general = config.get("general", {})
        main_config["general"] = {
            "basename": general.get("basename", ""),
            "basedir": general.get("basedir", "./output"),
            "compare_tim_res": general.get("compare_tim_res", "month"),
            "compare_tzone": general.get("compare_tzone", 0.0),
            "compare_grid_res": general.get("compare_grid_res", 2.0),
            "syear": general.get("syear", 2000),
            "eyear": general.get("eyear", 2020),
            "min_year": general.get("min_year", 1.0),
            "max_lat": general.get("max_lat", 90.0),
            "min_lat": general.get("min_lat", -90.0),
            "max_lon": general.get("max_lon", 180.0),
            "min_lon": general.get("min_lon", -180.0),
            "reference_nml": f"./nml/nml-yaml/{general.get('basename', 'config')}/ref-{general.get('basename', 'config')}.yaml",
            "simulation_nml": f"./nml/nml-yaml/{general.get('basename', 'config')}/sim-{general.get('basename', 'config')}.yaml",
            "statistics_nml": "./nml/nml-yaml/stats.yaml",
            "figure_nml": "./nml/nml-yaml/figlib.yaml",
            "num_cores": general.get("num_cores", 4),
            "evaluation": general.get("evaluation", True),
            "comparison": general.get("comparison", False),
            "statistics": general.get("statistics", False),
            "debug_mode": general.get("debug_mode", False),
            "only_drawing": general.get("only_drawing", False),
            "weight": "None",
            "IGBP_groupby": general.get("IGBP_groupby", True),
            "PFT_groupby": general.get("PFT_groupby", True),
            "Climate_zone_groupby": general.get("Climate_zone_groupby", True),
            "unified_mask": general.get("unified_mask", True),
            "generate_report": general.get("generate_report", True),
        }

        # Evaluation items
        main_config["evaluation_items"] = config.get("evaluation_items", {})

        # Metrics
        main_config["metrics"] = config.get("metrics", {})

        # Scores
        main_config["scores"] = config.get("scores", {})

        # Comparisons
        main_config["comparisons"] = config.get("comparisons", {})

        # Statistics
        main_config["statistics"] = config.get("statistics", {})

        return yaml.dump(
            main_config,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            indent=2
        )

    def generate_ref_nml(self, config: Dict[str, Any]) -> str:
        """
        Generate reference NML YAML content.

        Args:
            config: Full configuration dictionary

        Returns:
            YAML string
        """
        ref_data = config.get("ref_data", {})
        return yaml.dump(
            ref_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            indent=2
        )

    def generate_sim_nml(self, config: Dict[str, Any]) -> str:
        """
        Generate simulation NML YAML content.

        Args:
            config: Full configuration dictionary

        Returns:
            YAML string
        """
        sim_data = config.get("sim_data", {})
        return yaml.dump(
            sim_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            indent=2
        )

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration completeness.

        Args:
            config: Configuration dictionary

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        general = config.get("general", {})

        # Check required fields
        if not general.get("basename"):
            errors.append("Project name is required")

        if not general.get("basedir"):
            errors.append("Output directory is required")

        # Check year range
        syear = general.get("syear", 0)
        eyear = general.get("eyear", 0)
        if syear > eyear:
            errors.append("Start year must be less than or equal to end year")

        # Check evaluation items
        eval_items = config.get("evaluation_items", {})
        selected_items = [k for k, v in eval_items.items() if v]
        if not selected_items:
            errors.append("At least one evaluation item must be selected")

        # Check metrics
        metrics = config.get("metrics", {})
        selected_metrics = [k for k, v in metrics.items() if v]
        if not selected_metrics:
            errors.append("At least one metric must be selected")

        # Check ref data if any items selected
        if selected_items:
            ref_data = config.get("ref_data", {}).get("general", {})
            for item in selected_items:
                key = f"{item}_ref_source"
                if not ref_data.get(key):
                    errors.append(f"Reference data source required for {item}")

        return errors

    def export_all(
        self,
        config: Dict[str, Any],
        output_dir: str,
        basename: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Export all NML files to directory.

        Args:
            config: Configuration dictionary
            output_dir: Output directory path
            basename: Base name for files (defaults to config basename)

        Returns:
            Dictionary of {file_type: file_path}
        """
        if basename is None:
            basename = config.get("general", {}).get("basename", "config")

        os.makedirs(output_dir, exist_ok=True)

        files = {}

        # Main NML
        main_path = os.path.join(output_dir, f"main-{basename}.yaml")
        main_content = self.generate_main_nml(config)
        with open(main_path, 'w', encoding='utf-8') as f:
            f.write(main_content)
        files["main"] = main_path

        # Ref NML
        ref_path = os.path.join(output_dir, f"ref-{basename}.yaml")
        ref_content = self.generate_ref_nml(config)
        with open(ref_path, 'w', encoding='utf-8') as f:
            f.write(ref_content)
        files["ref"] = ref_path

        # Sim NML
        sim_path = os.path.join(output_dir, f"sim-{basename}.yaml")
        sim_content = self.generate_sim_nml(config)
        with open(sim_path, 'w', encoding='utf-8') as f:
            f.write(sim_content)
        files["sim"] = sim_path

        return files
