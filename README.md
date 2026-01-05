# OpenBench Wizard

A desktop wizard application for generating NML (Namelist) configuration files for [OpenBench](https://github.com/CoLM-SYSU/OpenBench) - a land surface model benchmarking and evaluation framework.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

## Overview

OpenBench Wizard simplifies the process of configuring land surface model evaluations by providing an intuitive interface for:

- **Selecting evaluation variables** across Carbon, Water, and Energy cycles
- **Configuring metrics and scores** for model performance assessment
- **Managing reference and simulation data sources** with NetCDF support
- **Generating NML configuration files** compatible with OpenBench
- **Running evaluations** locally or on remote HPC clusters

### Key Features

- Graphical wizard interface (PySide6/Qt6)
- Command-line interface for headless servers
- Remote execution via SSH with X11 forwarding
- Real-time file synchronization for remote mode
- Data validation with NetCDF inspection
- Cross-platform support (Windows, macOS, Linux)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      OpenBench Wizard                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   GUI Mode  │  │  CLI Mode   │  │    Remote Mode (SSH)    │  │
│  │  (PySide6)  │  │ (Terminal)  │  │  X11 Forwarding/Sync    │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
│         │                │                      │               │
│         └────────────────┼──────────────────────┘               │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Core Engine                              ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐ ││
│  │  │   Config    │ │    Data     │ │   Evaluation Runner   │ ││
│  │  │   Manager   │ │  Validator  │ │   (Local/Remote)      │ ││
│  │  └─────────────┘ └─────────────┘ └───────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Output: NML Configuration Files                ││
│  │         (main.yaml, ref.yaml, sim.yaml)                     ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │       OpenBench         │
              │  (Evaluation Framework) │
              └─────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager
- For remote mode: SSH client with X11 support

### Install from Source

```bash
# Clone the repository
git clone https://github.com/your-org/openbench-wizard.git
cd openbench-wizard

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PySide6 | >=6.5.0 | GUI framework |
| PyYAML | >=6.0 | Configuration files |
| paramiko | >=3.0.0 | SSH connectivity |
| xarray | >=2023.0.0 | NetCDF data handling |
| pandas | >=2.0.0 | Data manipulation |
| numpy | >=1.24.0 | Numerical operations |
| netCDF4 | >=1.6.0 | NetCDF file support |
| psutil | >=5.9.0 | System monitoring |

### Building Standalone Application

Build a standalone executable using PyInstaller:

```bash
# Install PyInstaller
pip install pyinstaller

# Method 1: Using the spec file (recommended)
pyinstaller --clean openbench_wizard.spec

# Method 2: Using the build script
python build.py

# Method 3: On Windows
build_windows.bat
```

The `--clean` flag removes temporary files from previous builds before rebuilding.

The built application will be available in the `dist/` directory:
- **macOS**: `dist/OpenBench_Wizard.app`
- **Windows**: `dist/OpenBench_Wizard/OpenBench_Wizard.exe`
- **Linux**: `dist/OpenBench_Wizard/OpenBench_Wizard`

## Quick Start

### GUI Mode

```bash
# Launch the wizard
python main.py
```

The wizard guides you through these steps:

1. **Runtime Environment** - Configure local or remote execution
2. **General Settings** - Set case name, output directory, time range
3. **Evaluation Items** - Select variables to evaluate
4. **Metrics & Scores** - Choose performance metrics
5. **Reference Data** - Configure observation/reference datasets
6. **Simulation Data** - Configure model output datasets
7. **Preview & Run** - Review configuration and execute

### CLI Mode

```bash
# Interactive mode
python cli.py --interactive

# Generate from config file
python cli.py --config my_config.yaml

# Generate a config template
python cli.py --template my_template.yaml

# Specify output directory
python cli.py --config my_config.yaml --output /path/to/output
```

### Basic Workflow

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│  1. Configure  │────▶│  2. Generate   │────▶│   3. Run       │
│   Evaluation   │     │  NML Files     │     │  OpenBench     │
└────────────────┘     └────────────────┘     └────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
  Select variables,      main.yaml            Execute evaluation
  metrics, data         ref.yaml              and generate
  sources               sim.yaml              results
```

## Usage Guide

### GUI Wizard Pages

#### 1. Runtime Environment

Configure where the evaluation will run:

- **Local Mode**: Run on your local machine
  - Set the local OpenBench installation path
  - Configure Python interpreter or Conda environment

- **Remote Mode**: Run on a remote server via SSH
  - Enter SSH credentials (host, username, key/password)
  - Set remote OpenBench path
  - Configure remote Conda environment

#### 2. General Settings

| Setting | Description |
|---------|-------------|
| Case Name | Identifier for this evaluation run |
| Base Directory | Output directory for results |
| Start/End Year | Temporal range for evaluation |
| Lat/Lon Bounds | Spatial domain (-90 to 90, -180 to 180) |
| Enable Comparison | Compare multiple simulations |
| Enable Statistics | Generate statistical summaries |

#### 3. Evaluation Items

Select variables organized by cycle:

- **Carbon Cycle**: GPP, NEE, Biomass, Respiration, LAI, etc.
- **Water Cycle**: ET, Runoff, Soil Moisture, Snow, etc.
- **Energy Cycle**: Radiation, Heat Fluxes, Temperature, etc.

#### 4. Metrics and Scores

**Metrics** - Statistical measures:
- RMSE, Correlation, Bias, MSE
- NSE (Nash-Sutcliffe Efficiency)
- KGE (Kling-Gupta Efficiency)
- Percent Bias, Index of Agreement

**Scores** - Composite performance scores:
- Overall Score, Bias Score, RMSE Score
- Seasonality Score, Interannual Score

#### 5. Reference & Simulation Data

Configure data sources with:
- Directory path containing NetCDF files
- Variable name in files
- Time range (start/end year)
- Spatial resolution (nlon, nlat, geo_res)
- Time resolution (monthly, daily, etc.)

#### 6. Preview and Run

- Review generated YAML configuration
- Export configuration files
- Execute OpenBench evaluation
- Monitor run progress

### Loading and Saving Configurations

**Load existing config:**
- Click "Load Config..." in the sidebar
- Select a YAML file (main, ref, or sim config)
- The wizard will auto-detect config type and load related files

**Save/Export config:**
- Navigate to the Preview page
- Click "Export" to save configuration files
- Files are saved to the configured output directory

## Remote Server Setup

### SSH X11 Forwarding

Run the GUI wizard on a remote server with display forwarding:

```bash
# Basic X11 forwarding
ssh -X user@server

# Trusted X11 forwarding (if -X doesn't work)
ssh -Y user@server

# With compression for slow connections
ssh -X -C user@server

# Navigate to wizard directory and run
cd /path/to/openbench-wizard
python main.py
```

### X11 Prerequisites

**On your local machine:**

- **macOS**: Install [XQuartz](https://www.xquartz.org/)
  ```bash
  brew install --cask xquartz
  # Log out and back in after installation
  ```

- **Windows**: Install [VcXsrv](https://sourceforge.net/projects/vcxsrv/) or [Xming](http://www.straightrunning.com/XmingNotes/)

- **Linux**: X11 is typically pre-installed

**On the remote server:**

Ensure `xauth` is installed and X11 forwarding is enabled in `/etc/ssh/sshd_config`:
```
X11Forwarding yes
X11DisplayOffset 10
```

### HPC Cluster Deployment

For HPC environments, use the provided launcher script:

```bash
# Make the launcher executable
chmod +x x11_launcher.sh

# Run with X11 optimization
./x11_launcher.sh
```

The launcher script:
- Detects SSH sessions and optimizes for X11 forwarding
- Sets appropriate Qt environment variables
- Disables OpenGL for better remote performance

### Conda Environment Setup

If using Conda on a remote server:

```bash
# Create environment
conda create -n openbench python=3.10
conda activate openbench

# Install dependencies
pip install -r requirements.txt

# For headless servers (CLI only)
pip install PyYAML paramiko xarray pandas numpy netCDF4
```

### Troubleshooting X11

**"Cannot open display" error:**
```bash
# Check DISPLAY variable
echo $DISPLAY

# Should show something like "localhost:10.0"
# If empty, reconnect with ssh -X
```

**Slow or laggy GUI:**
```bash
# Use compression
ssh -X -C user@server

# Or set software rendering
export QT_QUICK_BACKEND=software
export LIBGL_ALWAYS_INDIRECT=1
python main.py
```

**Authentication errors:**
```bash
# Generate new Xauthority
xauth generate :0 . trusted

# Or use trusted forwarding
ssh -Y user@server
```

**Fallback to CLI:**

If X11 is unavailable, use the command-line interface:
```bash
python cli.py --interactive
```

## Configuration Reference

### Evaluation Items

#### Carbon Cycle Variables

| Variable | Description |
|----------|-------------|
| `Gross_Primary_Productivity` | GPP - Carbon uptake by photosynthesis |
| `Net_Ecosystem_Exchange` | NEE - Net CO2 flux |
| `Ecosystem_Respiration` | Total ecosystem respiration |
| `Biomass` | Total vegetation biomass |
| `Leaf_Area_Index` | LAI - Leaf area per ground area |
| `Soil_Carbon` | Soil organic carbon content |
| `Methane` | CH4 emissions |
| `Nitrogen_Fixation` | Biological N fixation |

#### Water Cycle Variables

| Variable | Description |
|----------|-------------|
| `Evapotranspiration` | ET - Total water vapor flux |
| `Canopy_Transpiration` | Plant transpiration |
| `Soil_Evaporation` | Evaporation from soil |
| `Total_Runoff` | Surface + subsurface runoff |
| `Snow_Water_Equivalent` | SWE - Water content of snow |
| `Snow_Depth` | Snow depth |
| `Surface_Soil_Moisture` | Top layer soil moisture |
| `Root_Zone_Soil_Moisture` | Root zone soil moisture |
| `Terrestrial_Water_Storage_Change` | TWSC - Total water storage |
| `Permafrost` | Permafrost extent/depth |

#### Energy Cycle Variables

| Variable | Description |
|----------|-------------|
| `Net_Radiation` | Rnet - Net radiative flux |
| `Latent_Heat` | LE - Latent heat flux |
| `Sensible_Heat` | H - Sensible heat flux |
| `Ground_Heat` | G - Ground heat flux |
| `Surface_Albedo` | Surface reflectivity |
| `Surface_Soil_Temperature` | Top layer soil temperature |
| `Surface_Net_SW_Radiation` | Net shortwave radiation |
| `Surface_Net_LW_Radiation` | Net longwave radiation |

### Metrics Reference

| Metric | Formula | Range | Optimal |
|--------|---------|-------|---------|
| RMSE | √(Σ(sim-obs)²/n) | [0, ∞) | 0 |
| Correlation | Pearson r | [-1, 1] | 1 |
| Bias | mean(sim-obs) | (-∞, ∞) | 0 |
| NSE | 1 - Σ(sim-obs)²/Σ(obs-mean)² | (-∞, 1] | 1 |
| KGE | 1 - √((r-1)² + (α-1)² + (β-1)²) | (-∞, 1] | 1 |
| Percent_Bias | 100 × Σ(sim-obs)/Σ(obs) | (-∞, ∞) | 0 |

### Data Source Configuration

Example YAML structure for data sources:

```yaml
# Reference data configuration
general:
  GPP_ref_source:
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

# Simulation data configuration
general:
  GPP_sim_source:
    dir: /data/simulation/model_output
    suffix: .nc
    varname: gpp
    syear: 2000
    eyear: 2020
    tim_res: monthly
    nlon: 720
    nlat: 360
    geo_res: 0.5
    data_type: flux
```

### Configuration File Format

**Main configuration (main-{casename}.yaml):**

```yaml
general:
  casename: my_evaluation
  basedir: ./output
  basename: my_evaluation
  start_year: 2000
  end_year: 2020
  min_lat: -60
  max_lat: 90
  min_lon: -180
  max_lon: 180
  reference_nml: ./nml/ref-my_evaluation.yaml
  simulation_nml: ./nml/sim-my_evaluation.yaml
  comparison: false
  statistics: true

evaluation_items:
  Gross_Primary_Productivity: true
  Evapotranspiration: true
  Latent_Heat: true

metrics:
  RMSE: true
  Correlation: true
  Bias: true

scores:
  Overall_Score: true
  Bias_Score: true
```

## Development

### Project Structure

```
openbench-wizard/
├── main.py                 # GUI application entry point
├── cli.py                  # Command-line interface
├── build.py                # PyInstaller build script
├── pyproject.toml          # Package configuration
├── requirements.txt        # Python dependencies
├── core/                   # Core business logic
│   ├── config_manager.py   # Configuration handling
│   ├── runner.py           # Local evaluation runner
│   ├── remote_runner.py    # Remote execution
│   ├── ssh_manager.py      # SSH connection management
│   ├── sync_engine.py      # File synchronization
│   ├── storage.py          # Local/remote storage abstraction
│   ├── validation.py       # Input validation
│   └── data_validator.py   # NetCDF data validation
├── ui/                     # User interface
│   ├── main_window.py      # Main application window
│   ├── wizard_controller.py # Wizard state management
│   ├── pages/              # Wizard pages
│   │   ├── page_runtime.py
│   │   ├── page_general.py
│   │   ├── page_evaluation.py
│   │   └── ...
│   ├── widgets/            # Reusable UI components
│   └── styles/             # QSS stylesheets
├── tests/                  # Unit tests
└── docs/                   # Documentation
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=ui

# Run specific test file
pytest tests/test_config_manager.py
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Add docstrings for public functions and classes
- Keep functions focused and under 50 lines when possible

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OpenBench](https://github.com/CoLM-SYSU/OpenBench) - The land surface model benchmarking framework
- [PySide6](https://doc.qt.io/qtforpython/) - Qt for Python GUI framework
- [Paramiko](https://www.paramiko.org/) - SSH library for Python

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/openbench-wizard/issues)
- **Documentation**: See the `docs/` directory for additional guides
