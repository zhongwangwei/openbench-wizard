# OpenBench NML Wizard Technical Manual

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Directory Structure](#3-directory-structure)
4. [Core Modules](#4-core-modules)
5. [UI Components](#5-ui-components)
6. [Page Descriptions](#6-page-descriptions)
7. [Configuration Management](#7-configuration-management)
8. [Running and Monitoring](#8-running-and-monitoring)
9. [Themes and Styles](#9-themes-and-styles)
10. [Building and Packaging](#10-building-and-packaging)
11. [Server Deployment and Remote Usage](#11-server-deployment-and-remote-usage)
12. [Development Guide](#12-development-guide)
13. [FAQ](#13-faq)

---

## 1. Overview

### 1.1 Introduction

OpenBench NML Wizard is a desktop wizard application developed using PySide6, designed to generate NML (Namelist) configuration files required by the OpenBench evaluation system. This application provides an intuitive graphical interface to help users configure evaluation parameters, select evaluation metrics, set data sources, and ultimately generate YAML configuration files suitable for OpenBench evaluation.

### 1.2 Main Features

- **Wizard-style configuration flow**: Step-by-step guidance through configuration
- **Multi-category evaluation item selection**: Supports carbon cycle, water cycle, energy cycle, and more
- **Flexible data source configuration**: Supports reference and simulation data configuration
- **Real-time configuration preview**: YAML format preview with syntax highlighting
- **Evaluation task execution**: Integrated OpenBench run functionality
- **Progress monitoring**: Real-time display of evaluation progress and resource usage

### 1.3 Technology Stack

| Component | Technology |
|-----------|------------|
| GUI Framework | PySide6 (Qt 6) |
| Configuration Format | YAML |
| Packaging Tool | PyInstaller |
| Python Version | >= 3.10 |

---

## 2. System Architecture

### 2.1 Overall Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenBench Wizard                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   main.py   │  │  MainWindow │  │  WizardController   │  │
│  │ (Entry Point)│──▶│  (Main Win) │──▶│  (Flow Controller)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                         UI Layer                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                      Pages                            │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │   │
│  │  │ General │ │Evaluation│ │ Metrics │ │ Scores  │    │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │   │
│  │  │Compare  │ │Statistics│ │ RefData │ │ SimData │    │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │   │
│  │  ┌─────────┐ ┌──────────┐                           │   │
│  │  │ Preview │ │RunMonitor│                           │   │
│  │  └─────────┘ └──────────┘                           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                      Widgets                          │   │
│  │  PathSelector │ CheckboxGroup │ YamlPreview          │   │
│  │  ProgressDashboard │ DataSourceEditor                │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                        Core Layer                            │
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │   ConfigManager     │  │    EvaluationRunner         │   │
│  │ (Config generation) │  │   (Task execution)          │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
User Input ──▶ Pages ──▶ WizardController ──▶ ConfigManager ──▶ YAML Files
                               │
                               ▼
                       EvaluationRunner ──▶ OpenBench
```

### 2.3 Signal and Slot Mechanism

The application extensively uses Qt's signal and slot mechanism for inter-component communication:

| Signal Source | Signal Name | Receiver | Description |
|---------------|-------------|----------|-------------|
| WizardController | page_changed | MainWindow | Page switch notification |
| WizardController | config_updated | Pages | Configuration update notification |
| EvaluationRunner | progress_updated | ProgressDashboard | Progress update |
| EvaluationRunner | log_message | ProgressDashboard | Log message |
| CheckboxGroup | selection_changed | Pages | Selection change |

---

## 3. Directory Structure

```
openbench_wizard/
├── main.py                    # Application entry
├── build.py                   # Packaging script
├── pyproject.toml             # Project configuration
├── requirements.txt           # Dependencies list
├── .gitignore                 # Git ignore configuration
│
├── core/                      # Core modules
│   ├── __init__.py
│   ├── config_manager.py      # Configuration manager
│   └── runner.py              # Evaluation runner
│
├── ui/                        # UI modules
│   ├── __init__.py
│   ├── main_window.py         # Main window
│   ├── wizard_controller.py   # Wizard controller
│   │
│   ├── pages/                 # Page components
│   │   ├── __init__.py
│   │   ├── base_page.py       # Base page class
│   │   ├── page_general.py    # General settings page
│   │   ├── page_evaluation.py # Evaluation items page
│   │   ├── page_metrics.py    # Metrics selection page
│   │   ├── page_scores.py     # Scores selection page
│   │   ├── page_comparisons.py# Comparisons page
│   │   ├── page_statistics.py # Statistics page
│   │   ├── page_ref_data.py   # Reference data page
│   │   ├── page_sim_data.py   # Simulation data page
│   │   ├── page_preview.py    # Preview export page
│   │   └── page_run_monitor.py# Run monitor page
│   │
│   ├── widgets/               # Custom widgets
│   │   ├── __init__.py
│   │   ├── path_selector.py   # Path selector
│   │   ├── checkbox_group.py  # Checkbox group
│   │   ├── yaml_preview.py    # YAML preview
│   │   ├── progress_dashboard.py # Progress dashboard
│   │   └── data_source_editor.py # Data source editor
│   │
│   └── styles/                # Style files
│       ├── theme.qss          # Theme stylesheet
│       ├── checkmark.png      # Checkmark icon
│       └── checkmark.svg      # Checkmark vector
│
├── resources/                 # Resource files
│   ├── icons/                 # Icons
│   └── templates/             # Templates
│
└── docs/                      # Documentation
    └── technical_manual.md    # Technical manual
```

---

## 4. Core Modules

### 4.1 ConfigManager (config_manager.py)

The configuration manager is responsible for managing evaluation configuration data and generating YAML configuration files.

#### Class Definition

```python
class ConfigManager:
    """Manage evaluation configuration and generate NML config files"""

    def __init__(self):
        self._config: Dict[str, Any] = {}
```

#### Main Methods

| Method | Parameters | Return Value | Description |
|--------|------------|--------------|-------------|
| `get(key, default)` | key: str, default: Any | Any | Get configuration value |
| `set(key, value)` | key: str, value: Any | None | Set configuration value |
| `update_section(section, data)` | section: str, data: dict | None | Update configuration section |
| `generate_main_nml()` | - | str | Generate main configuration YAML |
| `generate_ref_nml()` | - | str | Generate reference data YAML |
| `generate_sim_nml()` | - | str | Generate simulation data YAML |
| `validate()` | - | Tuple[bool, List[str]] | Validate configuration completeness |
| `save_to_yaml(path)` | path: str | None | Save configuration to file |
| `load_from_yaml(path)` | path: str | None | Load configuration from file |

#### Configuration Structure

```python
{
    "general": {
        "casename": str,          # Case name
        "basedir": str,           # Base directory
        "start_year": int,        # Start year
        "end_year": int,          # End year
        "min_lat": float,         # Minimum latitude
        "max_lat": float,         # Maximum latitude
        "min_lon": float,         # Minimum longitude
        "max_lon": float,         # Maximum longitude
        "comparison": bool,       # Enable comparison
        "statistics": bool,       # Enable statistics
    },
    "evaluation_items": {
        "Biomass": bool,
        "Gross_Primary_Productivity": bool,
        # ... other evaluation items
    },
    "metrics": {
        "RMSE": bool,
        "Correlation": bool,
        # ... other metrics
    },
    "scores": {...},
    "comparisons": {...},
    "statistics": {...},
    "ref_data": {
        "source_name": {
            "dir": str,
            "suffix": str,
            "varname": str,
            # ... other parameters
        }
    },
    "sim_data": {...}
}
```

### 4.2 EvaluationRunner (runner.py)

The evaluation runner is responsible for executing OpenBench evaluation tasks in a background thread.

#### Class Definition

```python
class RunnerStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

@dataclass
class RunnerProgress:
    current_task: str
    current_variable: str
    current_stage: str
    progress_percent: int
    eta_seconds: Optional[int]

class EvaluationRunner(QThread):
    """Run OpenBench evaluation in background thread"""

    # Signals
    progress_updated = Signal(RunnerProgress)
    log_message = Signal(str)
    finished_signal = Signal(RunnerStatus, str)
```

#### Main Methods

| Method | Description |
|--------|-------------|
| `run()` | Thread main function, execute evaluation |
| `stop()` | Stop evaluation |

---

## 5. UI Components

### 5.1 PathSelector (path_selector.py)

Path selection component, supports file or directory selection with drag-and-drop functionality.

```python
class PathSelector(QWidget):
    path_changed = Signal(str)

    def __init__(
        self,
        mode: str = "directory",  # "directory" or "file"
        filter: str = "",          # File filter
        placeholder: str = "",     # Placeholder text
        parent=None
    )
```

**Features:**
- Supports drag-and-drop files/folders
- Real-time path validity validation
- Automatically remembers last browsed directory

### 5.2 CheckboxGroup (checkbox_group.py)

Grouped checkbox component with search and batch selection support.

```python
class CheckboxGroup(QWidget):
    selection_changed = Signal(dict)

    def __init__(
        self,
        items: Dict[str, List[str]],  # {group_name: [item_list]}
        parent=None
    )
```

**Features:**
- Grouped display (3-column grid layout)
- Real-time search filtering
- Select all/deselect all buttons
- Selection count display
- Green checkmark style

### 5.3 YamlPreview (yaml_preview.py)

YAML preview component with syntax highlighting.

```python
class YamlHighlighter(QSyntaxHighlighter):
    """YAML syntax highlighter"""

class YamlPreview(QWidget):
    def set_content(self, content: str)
    def get_content(self) -> str
```

**Syntax Highlighting Rules:**
| Element | Color |
|---------|-------|
| Key names | #569cd6 (blue) |
| String values | #ce9178 (orange) |
| Numbers | #b5cea8 (green) |
| Boolean values | #569cd6 (blue) |
| Comments | #6a9955 (green italic) |

### 5.4 ProgressDashboard (progress_dashboard.py)

Progress dashboard, displays evaluation progress and system resources.

```python
class ProgressDashboard(QWidget):
    stop_requested = Signal()
    open_output_requested = Signal()
```

**Display Content:**
- Overall progress bar
- Current task info (variable, stage, data source)
- CPU/memory usage
- Task queue list
- Real-time log output

### 5.5 DataSourceEditor (data_source_editor.py)

Data source configuration dialog.

```python
class DataSourceEditor(QDialog):
    def __init__(
        self,
        source_name: str = "",
        source_type: str = "ref",  # "ref" or "sim"
        initial_data: Optional[Dict] = None,
        parent=None
    )

    def get_data(self) -> Dict[str, Any]
```

**Configuration Fields:**
- Data path (dir)
- File suffix (suffix)
- Variable name (varname)
- Time info (syear, eyear, tim_res)
- Spatial info (nlon, nlat, geo_res)
- Data units (data_type)

---

## 6. Page Descriptions

### 6.1 BasePage (base_page.py)

Base class for all pages, defines unified page structure.

```python
class BasePage(QWidget):
    PAGE_ID: str = ""         # Page identifier
    PAGE_TITLE: str = ""      # Page title
    PAGE_SUBTITLE: str = ""   # Page subtitle

    def _setup_content(self):
        """Subclass implements: setup page content"""
        raise NotImplementedError

    def load_from_config(self):
        """Load data from configuration"""
        pass

    def save_to_config(self):
        """Save data to configuration"""
        pass

    def validate(self) -> Tuple[bool, str]:
        """Validate page data"""
        return True, ""
```

### 6.2 Page List

| Page Class | PAGE_ID | Description | Conditional Display |
|------------|---------|-------------|---------------------|
| PageGeneral | general | General settings | No |
| PageEvaluation | evaluation_items | Evaluation items selection | No |
| PageMetrics | metrics | Metrics selection | No |
| PageScores | scores | Scores selection | No |
| PageComparisons | comparisons | Comparisons selection | comparison=True |
| PageStatistics | statistics | Statistics selection | statistics=True |
| PageRefData | ref_data | Reference data config | No |
| PageSimData | sim_data | Simulation data config | No |
| PagePreview | preview | Preview and export | No |
| PageRunMonitor | run_monitor | Run monitoring | No |

### 6.3 Evaluation Item Categories

```python
EVALUATION_ITEMS = {
    "Carbon Cycle": [
        "Biomass", "Ecosystem_Respiration", "Gross_Primary_Productivity",
        "Leaf_Area_Index", "Methane", "Net_Ecosystem_Exchange",
        "Nitrogen_Fixation", "Soil_Carbon"
    ],
    "Water Cycle": [
        "Canopy_Interception", "Canopy_Transpiration", "Evapotranspiration",
        "Permafrost", "Root_Zone_Soil_Moisture", "Snow_Depth",
        "Snow_Water_Equivalent", "Soil_Evaporation", ...
    ],
    "Energy Cycle": [
        "Surface_Albedo", "Ground_Heat", "Latent_Heat", "Net_Radiation", ...
    ],
    "Atmospheric": [
        "Diurnal_Max_Temperature", "Precipitation", "Surface_Air_Temperature", ...
    ],
    "Agriculture": [
        "Crop_Yield_Corn", "Crop_Yield_Wheat", "Total_Irrigation_Amount", ...
    ],
    "Water Bodies": [
        "Dam_Inflow", "Lake_Temperature", "Streamflow", ...
    ],
    "Urban": [
        "Urban_Air_Temperature_Max", "Urban_Latent_Heat_Flux", ...
    ]
}
```

---

## 7. Configuration Management

### 7.1 WizardController (wizard_controller.py)

The wizard controller manages page flow and configuration state.

```python
class WizardController(QObject):
    page_changed = Signal(str)           # Page switch signal
    config_updated = Signal(str, dict)   # Configuration update signal
    pages_visibility_changed = Signal()  # Page visibility change

    def __init__(self):
        self.config = {}                 # Current configuration
        self._pages: List[str] = []      # Page order
        self._current_index: int = 0     # Current page index
        self._conditional_pages = {      # Conditional pages
            "comparisons": "comparison",
            "statistics": "statistics"
        }
```

**Main Methods:**

| Method | Description |
|--------|-------------|
| `register_pages(page_ids)` | Register page order |
| `goto_page(page_id)` | Jump to specified page |
| `next_page()` | Next page |
| `prev_page()` | Previous page |
| `update_section(section, data)` | Update configuration section |
| `is_page_visible(page_id)` | Check if page is visible |
| `get_visible_pages()` | Get all visible pages |

### 7.2 Configuration File Format

#### main_nml.yaml

```yaml
General:
  casename: my_evaluation
  basedir: /path/to/output
  start_year: 2000
  end_year: 2020
  min_lat: -90
  max_lat: 90
  min_lon: -180
  max_lon: 180

Evaluation_Items:
  Gross_Primary_Productivity: true
  Evapotranspiration: true
  Latent_Heat: true

Metrics:
  RMSE: true
  Correlation: true
  Bias: true

Scores:
  Overall_Score: true
```

#### ref_nml.yaml

```yaml
Gross_Primary_Productivity:
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
```

---

## 8. Running and Monitoring

### 8.1 Execution Flow

```
1. User clicks "Run" button
       │
       ▼
2. PageRunMonitor.start_evaluation()
       │
       ▼
3. Create EvaluationRunner thread
       │
       ▼
4. runner.set_config(config_path, output_dir)
       │
       ▼
5. runner.start() ──▶ Background execution
       │
       ├──▶ progress_updated signal ──▶ Update progress bar
       ├──▶ log_message signal ──▶ Update logs
       │
       ▼
6. finished_signal ──▶ Show completion status
```

### 8.2 Task Status

```python
class TaskStatus(Enum):
    PENDING = "pending"      # Waiting ○
    RUNNING = "running"      # Running ●
    COMPLETED = "completed"  # Completed ✓
    FAILED = "failed"        # Failed ✗
```

### 8.3 Resource Monitoring

Using `psutil` library to monitor system resources:

```python
def _update_resource_usage(self):
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    mem_percent = mem.percent
```

---

## 9. Themes and Styles

### 9.1 Stylesheet Structure (theme.qss)

```css
/* Global styles */
QWidget {
    font-family: "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 14px;
    color: #333333;
    background-color: #f5f5f5;
}

/* Button styles */
QPushButton {
    background-color: #0078d4;  /* Primary color */
    color: white;
    border-radius: 6px;
    padding: 8px 16px;
}

/* Checkbox styles */
QCheckBox::indicator:checked {
    background-color: #e8f5e9;  /* Light green background */
    border-color: #27ae60;      /* Green border */
    image: url(CHECKMARK_PATH); /* Green checkmark */
}

/* Sidebar styles */
QListWidget#nav_sidebar {
    background-color: #2d2d2d;  /* Dark background */
    min-width: 220px;
}
```

### 9.2 Color Scheme

| Usage | Color | Value |
|-------|-------|-------|
| Primary | Blue | #0078d4 |
| Success | Green | #27ae60 |
| Error | Red | #e74c3c |
| Background | Light gray | #f5f5f5 |
| Sidebar | Dark gray | #2d2d2d |
| Text | Dark gray | #333333 |

---

## 10. Building and Packaging

### 10.1 Dependency Installation

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
PySide6>=6.5.0
PyYAML>=6.0
psutil>=5.9.0
```

### 10.2 Development Run

```bash
cd openbench_wizard
python main.py
```

### 10.3 Packaging Build

```bash
cd openbench_wizard
python build.py
```

**Build Output:**
- macOS: `dist/OpenBench-Wizard.app`
- Windows: `dist/OpenBench-Wizard.exe`
- Linux: `dist/OpenBench-Wizard`

### 10.4 PyInstaller Configuration

```python
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name", "OpenBench-Wizard",
    "--windowed",
    "--onedir",  # macOS uses onedir
    "--add-data", f"{styles_dir}:ui/styles/",
    "--add-data", f"{resources_path}:resources",
    main_path
]
```

---

## 11. Server Deployment and Remote Usage

### 11.1 Usage Overview

OpenBench Wizard provides two ways to use on servers:

| Method | Use Case | Dependencies |
|--------|----------|--------------|
| SSH X11 Forwarding | Full GUI functionality needed | X11 Server |
| CLI Command Line | No GUI environment | No extra dependencies |

### 11.2 SSH X11 Forwarding

#### 11.2.1 Prerequisites

**Server Side (Linux):**
```bash
# Ensure sshd configuration allows X11 forwarding
sudo grep -q "^X11Forwarding yes" /etc/ssh/sshd_config || \
    echo "X11Forwarding yes" | sudo tee -a /etc/ssh/sshd_config

# Install necessary X11 packages
sudo apt-get install xauth x11-apps  # Ubuntu/Debian
sudo yum install xorg-x11-xauth xorg-x11-apps  # CentOS/RHEL
```

**Client Side:**
- **macOS**: Install XQuartz
  ```bash
  brew install --cask xquartz
  # Log out and log in again after installation
  ```
- **Windows**: Install VcXsrv or Xming
- **Linux**: Usually X11 is built-in

#### 11.2.2 Connection Method

```bash
# Basic X11 forwarding
ssh -X user@server

# Trusted X11 forwarding (resolves some permission issues)
ssh -Y user@server

# Enable compression (improves slow network performance)
ssh -XC user@server

# Full recommended command
ssh -YC user@server
```

#### 11.2.3 Using X11 Launcher

The application provides a dedicated X11 launch script `x11_launcher.sh`:

```bash
# After connecting to server
cd /path/to/openbench_wizard

# Check X11 environment
./x11_launcher.sh --check

# Launch GUI application
./x11_launcher.sh

# If X11 is unavailable, use CLI mode
./x11_launcher.sh --cli
```

#### 11.2.4 Automatic Environment Optimization

The program automatically detects SSH sessions and sets the following optimizations:

```python
# Automatically set environment variables
QT_QUICK_BACKEND=software      # Use software rendering
LIBGL_ALWAYS_INDIRECT=1        # Indirect OpenGL
QT_GRAPHICSSYSTEM=native       # Native graphics system
```

#### 11.2.5 Common Troubleshooting

**Issue: "cannot open display"**
```bash
# Check DISPLAY variable
echo $DISPLAY

# Should show something like localhost:10.0

# If empty, check SSH connection
ssh -v -X user@server  # View detailed connection log
```

**Issue: Graphics display is very slow**
```bash
# Use compression
ssh -XC user@server

# Or set environment variables
export QT_QUICK_BACKEND=software
export LIBGL_ALWAYS_INDIRECT=1
```

**Issue: "Invalid MIT-MAGIC-COOKIE-1 key"**
```bash
# Regenerate xauth
xauth generate :0 . trusted
```

### 11.3 CLI Command Line Mode

For environments where X11 cannot be used, a complete command line interface is provided:

#### 11.3.1 Interactive Mode

```bash
python cli.py --interactive
# or
python cli.py -i
```

Follow the prompts step by step:
1. Enter general settings (case name, output directory, time range, etc.)
2. Select evaluation items
3. Select evaluation metrics
4. Configure reference data and simulation data
5. Generate configuration files

#### 11.3.2 Configuration File Mode

```bash
# Generate configuration template
python cli.py --template my_config.yaml

# Generate NML after editing template
python cli.py --config my_config.yaml

# Specify output directory
python cli.py --config my_config.yaml --output /path/to/output
```

#### 11.3.3 Configuration Template Example

```yaml
# wizard_config_template.yaml
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

metrics:
  RMSE: true
  Correlation: true
  Bias: true

scores:
  Overall_Score: true
  Bias_Score: true

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
```

### 11.4 Batch Script Example

```bash
#!/bin/bash
# batch_generate.sh - Batch generate multiple configurations

CONFIGS=("config1.yaml" "config2.yaml" "config3.yaml")
OUTPUT_BASE="/path/to/outputs"

for config in "${CONFIGS[@]}"; do
    name="${config%.yaml}"
    python cli.py --config "$config" --output "$OUTPUT_BASE/$name"
    echo "Generated: $name"
done
```

---

## 12. Development Guide

### 12.1 Adding New Pages

1. Create new page file in `ui/pages/`:

```python
# page_new_feature.py
from ui.pages.base_page import BasePage

class PageNewFeature(BasePage):
    PAGE_ID = "new_feature"
    PAGE_TITLE = "New Feature"
    PAGE_SUBTITLE = "Configure new feature options"

    def _setup_content(self):
        # Add UI components to self.content_layout
        pass

    def load_from_config(self):
        data = self.controller.config.get("new_feature", {})
        # Load data to UI

    def save_to_config(self):
        data = {...}  # Collect data from UI
        self.controller.update_section("new_feature", data)
```

2. Register in `ui/pages/__init__.py`:

```python
from ui.pages.page_new_feature import PageNewFeature
```

3. Add page in `ui/main_window.py`:

```python
self.pages["new_feature"] = PageNewFeature(self.controller)
```

### 12.2 Adding New Components

1. Create component file in `ui/widgets/`
2. Export in `ui/widgets/__init__.py`
3. Use in pages

### 12.3 Modifying Styles

Edit `ui/styles/theme.qss`, using Qt stylesheet syntax.

### 12.4 Code Standards

- Use absolute imports (`from ui.widgets import ...`)
- Follow PEP 8 style
- Add type annotations
- Write docstrings

---

## 13. FAQ

### Q1: Application won't start

**Possible causes:**
- PySide6 not properly installed
- Import path errors

**Solution:**
```bash
pip install --upgrade PySide6
python -c "from PySide6.QtWidgets import QApplication; print('OK')"
```

### Q2: PyInstaller build fails

**Possible causes:**
- Corrupt conda environment metadata

**Solution:**
```python
# Fix packages missing 'depends' field in conda-meta
import json
files = ["path/to/broken/package.json"]
for f in files:
    with open(f, 'r+') as fp:
        data = json.load(fp)
        if 'depends' not in data:
            data['depends'] = []
            fp.seek(0)
            json.dump(data, fp, indent=4)
```

### Q3: Checkbox style not displaying

**Possible causes:**
- Image path not correctly replaced

**Solution:**
Ensure `CHECKMARK_PATH` is correctly replaced in `main.py`:
```python
stylesheet = stylesheet.replace(
    "CHECKMARK_PATH",
    str(checkmark_path).replace("\\", "/")
)
```

### Q4: Files missing after packaging

**Solution:**
Add `--add-data` option in `build.py`:
```python
"--add-data", f"{missing_file_path}:destination/"
```

---

## Appendix

### A. Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| Ctrl+N | New configuration |
| Ctrl+O | Open configuration |
| Ctrl+S | Save configuration |
| Ctrl+Q | Exit application |

### B. Configuration File Examples

For complete configuration file examples, please refer to the `resources/templates/` directory.

### C. API Reference

For detailed API documentation, please use `pydoc` or refer to source code comments.

---

*Document Version: 1.0.0*
*Last Updated: 2025-12-28*
