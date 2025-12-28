#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenBench NML Wizard - Command Line Interface

For generating NML configuration files on servers without GUI.

Usage:
    python cli.py --interactive           # Interactive configuration
    python cli.py --config config.yaml    # Generate from config file
    python cli.py --template              # Generate config template
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.config_manager import ConfigManager


# Evaluation items definition
EVALUATION_ITEMS = {
    "Carbon Cycle": [
        "Biomass", "Ecosystem_Respiration", "Gross_Primary_Productivity",
        "Leaf_Area_Index", "Methane", "Net_Ecosystem_Exchange",
        "Nitrogen_Fixation", "Soil_Carbon"
    ],
    "Water Cycle": [
        "Canopy_Interception", "Canopy_Transpiration", "Evapotranspiration",
        "Permafrost", "Root_Zone_Soil_Moisture", "Snow_Depth",
        "Snow_Water_Equivalent", "Soil_Evaporation",
        "Surface_Snow_Cover_In_Fraction", "Surface_Soil_Moisture",
        "Terrestrial_Water_Storage_Change", "Total_Runoff", "Water_Evaporation"
    ],
    "Energy Cycle": [
        "Surface_Albedo", "Ground_Heat", "Latent_Heat", "Net_Radiation",
        "Root_Zone_Soil_Temperature", "Sensible_Heat",
        "Surface_Net_LW_Radiation", "Surface_Net_SW_Radiation",
        "Surface_Soil_Temperature", "Surface_Upward_LW_Radiation",
        "Surface_Upward_SW_Radiation"
    ],
}

METRICS = [
    "RMSE", "Correlation", "Bias", "MSE", "NSE", "KGE",
    "Percent_Bias", "Index_Agreement", "Standard_Deviation"
]

SCORES = [
    "Overall_Score", "Bias_Score", "RMSE_Score",
    "Seasonality_Score", "Interannual_Score"
]


def print_header():
    """Print program header."""
    print("=" * 60)
    print("  OpenBench NML Wizard - Command Line Interface")
    print("=" * 60)
    print()


def print_section(title):
    """Print section title."""
    print()
    print(f"--- {title} ---")
    print()


def get_input(prompt, default=None, required=True):
    """Get user input."""
    if default is not None:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if value or not required:
            return value
        print("  This field is required, please enter a value.")


def get_number(prompt, default=None, min_val=None, max_val=None):
    """Get numeric input."""
    while True:
        value = get_input(prompt, default)
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                print(f"  Value must be >= {min_val}")
                continue
            if max_val is not None and num > max_val:
                print(f"  Value must be <= {max_val}")
                continue
            return num
        except ValueError:
            print("  Please enter a valid number.")


def get_yes_no(prompt, default=True):
    """Get yes/no input."""
    default_str = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not value:
            return default
        if value in ('y', 'yes'):
            return True
        if value in ('n', 'no'):
            return False
        print("  Please enter y or n")


def select_items(items, title):
    """Interactive item selection."""
    print(f"\n{title}")
    print("-" * 40)

    # Display all items
    all_items = []
    for category, category_items in items.items():
        print(f"\n  [{category}]")
        for item in category_items:
            idx = len(all_items)
            print(f"    {idx:2d}. {item}")
            all_items.append(item)

    print("\nInput options:")
    print("  - Enter numbers (comma-separated) to select items, e.g.: 0,1,5,10")
    print("  - Enter 'all' to select all")
    print("  - Enter 'none' or press Enter to skip")

    while True:
        selection = input("\nYour selection: ").strip().lower()

        if not selection or selection == 'none':
            return []

        if selection == 'all':
            return all_items

        try:
            indices = [int(x.strip()) for x in selection.split(',')]
            selected = []
            for idx in indices:
                if 0 <= idx < len(all_items):
                    selected.append(all_items[idx])
                else:
                    print(f"  Invalid index: {idx}")
                    break
            else:
                return selected
        except ValueError:
            print("  Please enter valid numbers, separated by commas.")


def select_from_list(items, title):
    """Select from list."""
    print(f"\n{title}")
    print("-" * 40)

    for i, item in enumerate(items):
        print(f"  {i:2d}. {item}")

    print("\nEnter 'all' to select all, numbers for specific items, Enter to skip")

    while True:
        selection = input("\nYour selection: ").strip().lower()

        if not selection:
            return []

        if selection == 'all':
            return items

        try:
            indices = [int(x.strip()) for x in selection.split(',')]
            selected = []
            for idx in indices:
                if 0 <= idx < len(items):
                    selected.append(items[idx])
            return selected
        except ValueError:
            print("  Please enter valid numbers.")


def configure_data_source(source_type):
    """Configure data source."""
    print(f"\nConfigure {source_type} data source")
    print("-" * 40)

    sources = {}

    while True:
        name = get_input("Source name (empty to finish)", required=False)
        if not name:
            break

        print(f"\n  Configure '{name}':")
        source = {
            "dir": get_input("    Data directory"),
            "suffix": get_input("    File suffix", ".nc"),
            "varname": get_input("    Variable name"),
            "syear": int(get_number("    Start year", 2000)),
            "eyear": int(get_number("    End year", 2020)),
            "tim_res": get_input("    Time resolution", "monthly"),
            "nlon": int(get_number("    Number of longitude points", 720)),
            "nlat": int(get_number("    Number of latitude points", 360)),
            "geo_res": get_number("    Spatial resolution (degrees)", 0.5),
            "data_type": get_input("    Data type", "flux"),
        }
        sources[name] = source
        print(f"  ✓ Added data source: {name}")

    return sources


def interactive_mode():
    """Interactive configuration mode."""
    print_header()

    config = ConfigManager()

    # === General Settings ===
    print_section("1. General Settings")

    general = {
        "casename": get_input("Case name", "my_evaluation"),
        "basedir": get_input("Output base directory", os.path.expanduser("~/openbench_output")),
        "start_year": int(get_number("Start year", 2000)),
        "end_year": int(get_number("End year", 2020)),
        "min_lat": get_number("Minimum latitude", -90, -90, 90),
        "max_lat": get_number("Maximum latitude", 90, -90, 90),
        "min_lon": get_number("Minimum longitude", -180, -180, 180),
        "max_lon": get_number("Maximum longitude", 180, -180, 180),
        "comparison": get_yes_no("Enable comparison?", False),
        "statistics": get_yes_no("Enable statistics?", False),
    }
    config.update_section("general", general)

    # === Evaluation Items ===
    print_section("2. Select Evaluation Items")

    selected_items = select_items(EVALUATION_ITEMS, "Available evaluation items:")
    eval_items = {item: True for item in selected_items}
    config.update_section("evaluation_items", eval_items)
    print(f"\n✓ Selected {len(selected_items)} evaluation items")

    # === Metrics ===
    print_section("3. Select Evaluation Metrics")

    selected_metrics = select_from_list(METRICS, "Available metrics:")
    metrics = {m: True for m in selected_metrics}
    config.update_section("metrics", metrics)
    print(f"\n✓ Selected {len(selected_metrics)} metrics")

    # === Scores ===
    print_section("4. Select Score Items")

    selected_scores = select_from_list(SCORES, "Available scores:")
    scores = {s: True for s in selected_scores}
    config.update_section("scores", scores)
    print(f"\n✓ Selected {len(selected_scores)} score items")

    # === Reference Data ===
    print_section("5. Configure Reference Data")

    if get_yes_no("Configure reference data?", True):
        ref_data = configure_data_source("reference")
        config.update_section("ref_data", ref_data)

    # === Simulation Data ===
    print_section("6. Configure Simulation Data")

    if get_yes_no("Configure simulation data?", True):
        sim_data = configure_data_source("simulation")
        config.update_section("sim_data", sim_data)

    # === Generate Configuration Files ===
    print_section("7. Generate Configuration Files")

    output_dir = get_input("Configuration output directory", general["basedir"])
    os.makedirs(output_dir, exist_ok=True)

    # Generate and save
    main_nml = config.generate_main_nml()
    ref_nml = config.generate_ref_nml()
    sim_nml = config.generate_sim_nml()

    main_path = Path(output_dir) / "main_nml.yaml"
    ref_path = Path(output_dir) / "ref_nml.yaml"
    sim_path = Path(output_dir) / "sim_nml.yaml"

    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(main_nml)
    with open(ref_path, 'w', encoding='utf-8') as f:
        f.write(ref_nml)
    with open(sim_path, 'w', encoding='utf-8') as f:
        f.write(sim_nml)

    print()
    print("=" * 60)
    print("  Configuration files generated successfully!")
    print("=" * 60)
    print()
    print(f"  Main config file: {main_path}")
    print(f"  Reference data config: {ref_path}")
    print(f"  Simulation data config: {sim_path}")
    print()

    # Preview
    if get_yes_no("Preview main config file?", True):
        print("\n--- main_nml.yaml ---")
        print(main_nml)

    return str(main_path)


def generate_template(output_path):
    """Generate configuration template file."""
    template = """# OpenBench NML Wizard Configuration Template
# Usage: python cli.py --config this_file.yaml

general:
  casename: my_evaluation
  basedir: /path/to/output
  start_year: 2000
  end_year: 2020
  min_lat: -90
  max_lat: 90
  min_lon: -180
  max_lon: 180
  comparison: false
  statistics: false

evaluation_items:
  Gross_Primary_Productivity: true
  Evapotranspiration: true
  Latent_Heat: true
  # Add more evaluation items...

metrics:
  RMSE: true
  Correlation: true
  Bias: true
  # Add more metrics...

scores:
  Overall_Score: true
  Bias_Score: true
  # Add more score items...

ref_data:
  FLUXNET:
    dir: /data/reference/gpp
    suffix: .nc
    varname: GPP
    syear: 2000
    eyear: 2020
    tim_res: monthly
    nlon: 720
    nlat: 360
    geo_res: 0.5
    data_type: flux

sim_data:
  CLM5:
    dir: /data/simulation/clm5
    suffix: .nc
    varname: GPP
    syear: 2000
    eyear: 2020
    tim_res: monthly
    nlon: 720
    nlat: 360
    geo_res: 0.5
    data_type: flux
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"✓ Configuration template generated: {output_path}")
    print("\nAfter editing this file, use the following command to generate NML config:")
    print(f"  python cli.py --config {output_path}")


def from_config_file(config_path, output_dir=None):
    """Generate NML from configuration file."""
    import yaml

    print(f"Reading configuration file: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        user_config = yaml.safe_load(f)

    config = ConfigManager()

    # Load section configurations
    for section in ['general', 'evaluation_items', 'metrics', 'scores',
                    'comparisons', 'statistics', 'ref_data', 'sim_data']:
        if section in user_config:
            config.update_section(section, user_config[section])

    # Determine output directory
    if output_dir is None:
        output_dir = user_config.get('general', {}).get('basedir', '.')

    os.makedirs(output_dir, exist_ok=True)

    # Generate and save
    main_nml = config.generate_main_nml()
    ref_nml = config.generate_ref_nml()
    sim_nml = config.generate_sim_nml()

    main_path = Path(output_dir) / "main_nml.yaml"
    ref_path = Path(output_dir) / "ref_nml.yaml"
    sim_path = Path(output_dir) / "sim_nml.yaml"

    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(main_nml)
    with open(ref_path, 'w', encoding='utf-8') as f:
        f.write(ref_nml)
    with open(sim_path, 'w', encoding='utf-8') as f:
        f.write(sim_nml)

    print()
    print("✓ Configuration files generated successfully!")
    print(f"  Main config file: {main_path}")
    print(f"  Reference data config: {ref_path}")
    print(f"  Simulation data config: {sim_path}")

    return str(main_path)


def main():
    parser = argparse.ArgumentParser(
        description="OpenBench NML Wizard - Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --interactive              # Interactive configuration
  python cli.py --template                 # Generate config template
  python cli.py --config my_config.yaml    # Generate from config file
  python cli.py --config my_config.yaml --output /path/to/output
        """
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Interactive configuration mode'
    )

    parser.add_argument(
        '-c', '--config',
        type=str,
        help='Generate NML from specified config file'
    )

    parser.add_argument(
        '-t', '--template',
        type=str,
        nargs='?',
        const='wizard_config_template.yaml',
        help='Generate configuration template file'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output directory'
    )

    args = parser.parse_args()

    # Show help when no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        print("\nTip: Use --interactive to enter interactive configuration mode")
        return

    if args.template:
        generate_template(args.template)
    elif args.config:
        from_config_file(args.config, args.output)
    elif args.interactive:
        interactive_mode()


if __name__ == "__main__":
    main()
