# OpenBench NML Wizard 技术手册

## 目录

1. [概述](#1-概述)
2. [系统架构](#2-系统架构)
3. [目录结构](#3-目录结构)
4. [核心模块](#4-核心模块)
5. [UI组件](#5-ui组件)
6. [页面说明](#6-页面说明)
7. [配置管理](#7-配置管理)
8. [运行与监控](#8-运行与监控)
9. [主题与样式](#9-主题与样式)
10. [构建与打包](#10-构建与打包)
11. [服务器部署与远程使用](#11-服务器部署与远程使用)
12. [开发指南](#12-开发指南)
13. [常见问题](#13-常见问题)

---

## 1. 概述

### 1.1 简介

OpenBench NML Wizard 是一个基于 PySide6 开发的桌面向导应用程序，用于生成 OpenBench 评估系统所需的 NML (Namelist) 配置文件。该应用提供了直观的图形界面，帮助用户配置评估参数、选择评估指标、设置数据源，并最终生成可用于 OpenBench 评估的 YAML 配置文件。

### 1.2 主要功能

- **向导式配置流程**: 分步骤引导用户完成配置
- **多类别评估项选择**: 支持碳循环、水循环、能量循环等多个类别
- **灵活的数据源配置**: 支持参考数据和模拟数据的配置
- **实时配置预览**: YAML 格式预览，支持语法高亮
- **评估任务运行**: 集成 OpenBench 运行功能
- **进度监控**: 实时显示评估进度和资源使用情况

### 1.3 技术栈

| 组件 | 技术 |
|------|------|
| GUI框架 | PySide6 (Qt 6) |
| 配置格式 | YAML |
| 打包工具 | PyInstaller |
| Python版本 | >= 3.10 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenBench Wizard                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   main.py   │  │  MainWindow │  │  WizardController   │  │
│  │  (入口点)    │──▶│  (主窗口)   │──▶│  (流程控制器)       │  │
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
│  │  (配置生成与管理)    │  │    (评估任务执行)           │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入 ──▶ Pages ──▶ WizardController ──▶ ConfigManager ──▶ YAML文件
                              │
                              ▼
                      EvaluationRunner ──▶ OpenBench
```

### 2.3 信号与槽机制

应用广泛使用 Qt 的信号与槽机制进行组件间通信：

| 信号源 | 信号名 | 接收者 | 说明 |
|--------|--------|--------|------|
| WizardController | page_changed | MainWindow | 页面切换通知 |
| WizardController | config_updated | Pages | 配置更新通知 |
| EvaluationRunner | progress_updated | ProgressDashboard | 进度更新 |
| EvaluationRunner | log_message | ProgressDashboard | 日志消息 |
| CheckboxGroup | selection_changed | Pages | 选择变更 |

---

## 3. 目录结构

```
openbench_wizard/
├── main.py                    # 应用入口
├── build.py                   # 打包脚本
├── pyproject.toml             # 项目配置
├── requirements.txt           # 依赖列表
├── .gitignore                 # Git忽略配置
│
├── core/                      # 核心模块
│   ├── __init__.py
│   ├── config_manager.py      # 配置管理器
│   └── runner.py              # 评估运行器
│
├── ui/                        # UI模块
│   ├── __init__.py
│   ├── main_window.py         # 主窗口
│   ├── wizard_controller.py   # 向导控制器
│   │
│   ├── pages/                 # 页面组件
│   │   ├── __init__.py
│   │   ├── base_page.py       # 基础页面类
│   │   ├── page_general.py    # 通用设置页
│   │   ├── page_evaluation.py # 评估项选择页
│   │   ├── page_metrics.py    # 指标选择页
│   │   ├── page_scores.py     # 评分选择页
│   │   ├── page_comparisons.py# 比较项选择页
│   │   ├── page_statistics.py # 统计项选择页
│   │   ├── page_ref_data.py   # 参考数据页
│   │   ├── page_sim_data.py   # 模拟数据页
│   │   ├── page_preview.py    # 预览导出页
│   │   └── page_run_monitor.py# 运行监控页
│   │
│   ├── widgets/               # 自定义组件
│   │   ├── __init__.py
│   │   ├── path_selector.py   # 路径选择器
│   │   ├── checkbox_group.py  # 复选框组
│   │   ├── yaml_preview.py    # YAML预览
│   │   ├── progress_dashboard.py # 进度仪表板
│   │   └── data_source_editor.py # 数据源编辑器
│   │
│   └── styles/                # 样式文件
│       ├── theme.qss          # 主题样式表
│       ├── checkmark.png      # 复选标记图标
│       └── checkmark.svg      # 复选标记矢量图
│
├── resources/                 # 资源文件
│   ├── icons/                 # 图标
│   └── templates/             # 模板
│
└── docs/                      # 文档
    └── technical_manual.md    # 技术手册
```

---

## 4. 核心模块

### 4.1 ConfigManager (config_manager.py)

配置管理器负责管理评估配置数据并生成 YAML 配置文件。

#### 类定义

```python
class ConfigManager:
    """管理评估配置并生成NML配置文件"""

    def __init__(self):
        self._config: Dict[str, Any] = {}
```

#### 主要方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get(key, default)` | key: str, default: Any | Any | 获取配置值 |
| `set(key, value)` | key: str, value: Any | None | 设置配置值 |
| `update_section(section, data)` | section: str, data: dict | None | 更新配置节 |
| `generate_main_nml()` | - | str | 生成主配置YAML |
| `generate_ref_nml()` | - | str | 生成参考数据YAML |
| `generate_sim_nml()` | - | str | 生成模拟数据YAML |
| `validate()` | - | Tuple[bool, List[str]] | 验证配置完整性 |
| `save_to_yaml(path)` | path: str | None | 保存配置到文件 |
| `load_from_yaml(path)` | path: str | None | 从文件加载配置 |

#### 配置结构

```python
{
    "general": {
        "casename": str,          # 案例名称
        "basedir": str,           # 基础目录
        "start_year": int,        # 起始年份
        "end_year": int,          # 结束年份
        "min_lat": float,         # 最小纬度
        "max_lat": float,         # 最大纬度
        "min_lon": float,         # 最小经度
        "max_lon": float,         # 最大经度
        "comparison": bool,       # 启用比较
        "statistics": bool,       # 启用统计
    },
    "evaluation_items": {
        "Biomass": bool,
        "Gross_Primary_Productivity": bool,
        # ... 其他评估项
    },
    "metrics": {
        "RMSE": bool,
        "Correlation": bool,
        # ... 其他指标
    },
    "scores": {...},
    "comparisons": {...},
    "statistics": {...},
    "ref_data": {
        "source_name": {
            "dir": str,
            "suffix": str,
            "varname": str,
            # ... 其他参数
        }
    },
    "sim_data": {...}
}
```

### 4.2 EvaluationRunner (runner.py)

评估运行器负责在后台线程中执行 OpenBench 评估任务。

#### 类定义

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
    """在后台线程运行OpenBench评估"""

    # 信号
    progress_updated = Signal(RunnerProgress)
    log_message = Signal(str)
    finished_signal = Signal(RunnerStatus, str)
```

#### 主要方法

| 方法 | 说明 |
|------|------|
| `run()` | 线程主函数，执行评估 |
| `stop()` | 停止评估 |

---

## 5. UI组件

### 5.1 PathSelector (path_selector.py)

路径选择组件，支持文件或目录选择，带拖放功能。

```python
class PathSelector(QWidget):
    path_changed = Signal(str)

    def __init__(
        self,
        mode: str = "directory",  # "directory" 或 "file"
        filter: str = "",          # 文件过滤器
        placeholder: str = "",     # 占位符文本
        parent=None
    )
```

**特性:**
- 支持拖放文件/文件夹
- 路径有效性实时验证
- 自动记住上次浏览目录

### 5.2 CheckboxGroup (checkbox_group.py)

分组复选框组件，支持搜索和批量选择。

```python
class CheckboxGroup(QWidget):
    selection_changed = Signal(dict)

    def __init__(
        self,
        items: Dict[str, List[str]],  # {组名: [项目列表]}
        parent=None
    )
```

**特性:**
- 分组显示（3列网格布局）
- 实时搜索过滤
- 全选/全不选按钮
- 选择计数显示
- 绿色复选标记样式

### 5.3 YamlPreview (yaml_preview.py)

YAML 预览组件，带语法高亮。

```python
class YamlHighlighter(QSyntaxHighlighter):
    """YAML语法高亮器"""

class YamlPreview(QWidget):
    def set_content(self, content: str)
    def get_content(self) -> str
```

**语法高亮规则:**
| 元素 | 颜色 |
|------|------|
| 键名 | #569cd6 (蓝色) |
| 字符串值 | #ce9178 (橙色) |
| 数字 | #b5cea8 (绿色) |
| 布尔值 | #569cd6 (蓝色) |
| 注释 | #6a9955 (绿色斜体) |

### 5.4 ProgressDashboard (progress_dashboard.py)

进度仪表板，显示评估进度和系统资源。

```python
class ProgressDashboard(QWidget):
    stop_requested = Signal()
    open_output_requested = Signal()
```

**显示内容:**
- 总体进度条
- 当前任务信息（变量、阶段、数据源）
- CPU/内存使用率
- 任务队列列表
- 实时日志输出

### 5.5 DataSourceEditor (data_source_editor.py)

数据源配置对话框。

```python
class DataSourceEditor(QDialog):
    def __init__(
        self,
        source_name: str = "",
        source_type: str = "ref",  # "ref" 或 "sim"
        initial_data: Optional[Dict] = None,
        parent=None
    )

    def get_data(self) -> Dict[str, Any]
```

**配置字段:**
- 数据路径 (dir)
- 文件后缀 (suffix)
- 变量名 (varname)
- 时间信息 (syear, eyear, tim_res)
- 空间信息 (nlon, nlat, geo_res)
- 数据单位 (data_type)

---

## 6. 页面说明

### 6.1 BasePage (base_page.py)

所有页面的基类，定义统一的页面结构。

```python
class BasePage(QWidget):
    PAGE_ID: str = ""         # 页面标识符
    PAGE_TITLE: str = ""      # 页面标题
    PAGE_SUBTITLE: str = ""   # 页面副标题

    def _setup_content(self):
        """子类实现：设置页面内容"""
        raise NotImplementedError

    def load_from_config(self):
        """从配置加载数据"""
        pass

    def save_to_config(self):
        """保存数据到配置"""
        pass

    def validate(self) -> Tuple[bool, str]:
        """验证页面数据"""
        return True, ""
```

### 6.2 页面列表

| 页面类 | PAGE_ID | 说明 | 条件显示 |
|--------|---------|------|----------|
| PageGeneral | general | 通用设置 | 否 |
| PageEvaluation | evaluation_items | 评估项选择 | 否 |
| PageMetrics | metrics | 指标选择 | 否 |
| PageScores | scores | 评分选择 | 否 |
| PageComparisons | comparisons | 比较项选择 | comparison=True |
| PageStatistics | statistics | 统计项选择 | statistics=True |
| PageRefData | ref_data | 参考数据配置 | 否 |
| PageSimData | sim_data | 模拟数据配置 | 否 |
| PagePreview | preview | 预览与导出 | 否 |
| PageRunMonitor | run_monitor | 运行监控 | 否 |

### 6.3 评估项类别

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

## 7. 配置管理

### 7.1 WizardController (wizard_controller.py)

向导控制器管理页面流程和配置状态。

```python
class WizardController(QObject):
    page_changed = Signal(str)           # 页面切换信号
    config_updated = Signal(str, dict)   # 配置更新信号
    pages_visibility_changed = Signal()  # 页面可见性变更

    def __init__(self):
        self.config = {}                 # 当前配置
        self._pages: List[str] = []      # 页面顺序
        self._current_index: int = 0     # 当前页面索引
        self._conditional_pages = {      # 条件页面
            "comparisons": "comparison",
            "statistics": "statistics"
        }
```

**主要方法:**

| 方法 | 说明 |
|------|------|
| `register_pages(page_ids)` | 注册页面顺序 |
| `goto_page(page_id)` | 跳转到指定页面 |
| `next_page()` | 下一页 |
| `prev_page()` | 上一页 |
| `update_section(section, data)` | 更新配置节 |
| `is_page_visible(page_id)` | 检查页面是否可见 |
| `get_visible_pages()` | 获取所有可见页面 |

### 7.2 配置文件格式

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

## 8. 运行与监控

### 8.1 运行流程

```
1. 用户点击"Run"按钮
       │
       ▼
2. PageRunMonitor.start_evaluation()
       │
       ▼
3. 创建 EvaluationRunner 线程
       │
       ▼
4. runner.set_config(config_path, output_dir)
       │
       ▼
5. runner.start() ──▶ 后台执行
       │
       ├──▶ progress_updated 信号 ──▶ 更新进度条
       ├──▶ log_message 信号 ──▶ 更新日志
       │
       ▼
6. finished_signal ──▶ 显示完成状态
```

### 8.2 任务状态

```python
class TaskStatus(Enum):
    PENDING = "pending"      # 等待中 ○
    RUNNING = "running"      # 运行中 ●
    COMPLETED = "completed"  # 已完成 ✓
    FAILED = "failed"        # 失败 ✗
```

### 8.3 资源监控

使用 `psutil` 库监控系统资源：

```python
def _update_resource_usage(self):
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    mem_percent = mem.percent
```

---

## 9. 主题与样式

### 9.1 样式表结构 (theme.qss)

```css
/* 全局样式 */
QWidget {
    font-family: "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 14px;
    color: #333333;
    background-color: #f5f5f5;
}

/* 按钮样式 */
QPushButton {
    background-color: #0078d4;  /* 主色调 */
    color: white;
    border-radius: 6px;
    padding: 8px 16px;
}

/* 复选框样式 */
QCheckBox::indicator:checked {
    background-color: #e8f5e9;  /* 浅绿背景 */
    border-color: #27ae60;      /* 绿色边框 */
    image: url(CHECKMARK_PATH); /* 绿色复选标记 */
}

/* 侧边栏样式 */
QListWidget#nav_sidebar {
    background-color: #2d2d2d;  /* 深色背景 */
    min-width: 220px;
}
```

### 9.2 颜色方案

| 用途 | 颜色 | 色值 |
|------|------|------|
| 主色调 | 蓝色 | #0078d4 |
| 成功 | 绿色 | #27ae60 |
| 错误 | 红色 | #e74c3c |
| 背景 | 浅灰 | #f5f5f5 |
| 侧边栏 | 深灰 | #2d2d2d |
| 文字 | 深灰 | #333333 |

---

## 10. 构建与打包

### 10.1 依赖安装

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
PySide6>=6.5.0
PyYAML>=6.0
psutil>=5.9.0
```

### 10.2 开发运行

```bash
cd openbench_wizard
python main.py
```

### 10.3 打包构建

```bash
cd openbench_wizard
python build.py
```

**构建输出:**
- macOS: `dist/OpenBench-Wizard.app`
- Windows: `dist/OpenBench-Wizard.exe`
- Linux: `dist/OpenBench-Wizard`

### 10.4 PyInstaller 配置

```python
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name", "OpenBench-Wizard",
    "--windowed",
    "--onedir",  # macOS使用onedir
    "--add-data", f"{styles_dir}:ui/styles/",
    "--add-data", f"{resources_path}:resources",
    main_path
]
```

---

## 11. 服务器部署与远程使用

### 11.1 运行方式概述

OpenBench Wizard 提供两种在服务器上使用的方式：

| 方式 | 适用场景 | 依赖 |
|------|----------|------|
| SSH X11 转发 | 需要完整 GUI 功能 | X11 服务器 |
| CLI 命令行 | 无 GUI 环境 | 无额外依赖 |

### 11.2 SSH X11 转发

#### 11.2.1 前置条件

**服务器端 (Linux):**
```bash
# 确保 sshd 配置允许 X11 转发
sudo grep -q "^X11Forwarding yes" /etc/ssh/sshd_config || \
    echo "X11Forwarding yes" | sudo tee -a /etc/ssh/sshd_config

# 安装必要的 X11 包
sudo apt-get install xauth x11-apps  # Ubuntu/Debian
sudo yum install xorg-x11-xauth xorg-x11-apps  # CentOS/RHEL
```

**客户端:**
- **macOS**: 安装 XQuartz
  ```bash
  brew install --cask xquartz
  # 安装后需要注销并重新登录
  ```
- **Windows**: 安装 VcXsrv 或 Xming
- **Linux**: 通常已内置 X11

#### 11.2.2 连接方式

```bash
# 基本 X11 转发
ssh -X user@server

# 可信 X11 转发 (解决某些权限问题)
ssh -Y user@server

# 启用压缩 (提高慢速网络性能)
ssh -XC user@server

# 完整推荐命令
ssh -YC user@server
```

#### 11.2.3 使用 X11 启动器

应用提供了专用的 X11 启动脚本 `x11_launcher.sh`:

```bash
# 连接服务器后
cd /path/to/openbench_wizard

# 检查 X11 环境
./x11_launcher.sh --check

# 启动 GUI 应用
./x11_launcher.sh

# 如果 X11 不可用，使用 CLI 模式
./x11_launcher.sh --cli
```

#### 11.2.4 环境变量自动优化

程序会自动检测 SSH 会话并设置以下优化:

```python
# 自动设置的环境变量
QT_QUICK_BACKEND=software      # 使用软件渲染
LIBGL_ALWAYS_INDIRECT=1        # 间接 OpenGL
QT_GRAPHICSSYSTEM=native       # 原生图形系统
```

#### 11.2.5 常见问题排查

**问题: "cannot open display"**
```bash
# 检查 DISPLAY 变量
echo $DISPLAY

# 应该显示类似 localhost:10.0

# 如果为空，检查 SSH 连接
ssh -v -X user@server  # 查看详细连接日志
```

**问题: 图形显示非常慢**
```bash
# 使用压缩
ssh -XC user@server

# 或设置环境变量
export QT_QUICK_BACKEND=software
export LIBGL_ALWAYS_INDIRECT=1
```

**问题: "Invalid MIT-MAGIC-COOKIE-1 key"**
```bash
# 重新生成 xauth
xauth generate :0 . trusted
```

### 11.3 CLI 命令行模式

对于无法使用 X11 的环境，提供完整的命令行界面:

#### 11.3.1 交互式模式

```bash
python cli.py --interactive
# 或
python cli.py -i
```

按照提示逐步配置：
1. 输入通用设置（案例名、输出目录、时间范围等）
2. 选择评估项目
3. 选择评估指标
4. 配置参考数据和模拟数据
5. 生成配置文件

#### 11.3.2 配置文件模式

```bash
# 生成配置模板
python cli.py --template my_config.yaml

# 编辑模板后生成 NML
python cli.py --config my_config.yaml

# 指定输出目录
python cli.py --config my_config.yaml --output /path/to/output
```

#### 11.3.3 配置模板示例

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

### 11.4 批处理脚本示例

```bash
#!/bin/bash
# batch_generate.sh - 批量生成多个配置

CONFIGS=("config1.yaml" "config2.yaml" "config3.yaml")
OUTPUT_BASE="/path/to/outputs"

for config in "${CONFIGS[@]}"; do
    name="${config%.yaml}"
    python cli.py --config "$config" --output "$OUTPUT_BASE/$name"
    echo "Generated: $name"
done
```

---

## 12. 开发指南

### 12.1 添加新页面

1. 在 `ui/pages/` 创建新页面文件:

```python
# page_new_feature.py
from ui.pages.base_page import BasePage

class PageNewFeature(BasePage):
    PAGE_ID = "new_feature"
    PAGE_TITLE = "New Feature"
    PAGE_SUBTITLE = "Configure new feature options"

    def _setup_content(self):
        # 添加UI组件到 self.content_layout
        pass

    def load_from_config(self):
        data = self.controller.config.get("new_feature", {})
        # 加载数据到UI

    def save_to_config(self):
        data = {...}  # 从UI收集数据
        self.controller.update_section("new_feature", data)
```

2. 在 `ui/pages/__init__.py` 注册:

```python
from ui.pages.page_new_feature import PageNewFeature
```

3. 在 `ui/main_window.py` 添加页面:

```python
self.pages["new_feature"] = PageNewFeature(self.controller)
```

### 12.2 添加新组件

1. 在 `ui/widgets/` 创建组件文件
2. 在 `ui/widgets/__init__.py` 导出
3. 在页面中使用

### 12.3 修改样式

编辑 `ui/styles/theme.qss`，使用 Qt 样式表语法。

### 12.4 代码规范

- 使用绝对导入 (`from ui.widgets import ...`)
- 遵循 PEP 8 风格
- 添加类型注解
- 编写文档字符串

---

## 13. 常见问题

### Q1: 应用无法启动

**可能原因:**
- PySide6 未正确安装
- 导入路径错误

**解决方案:**
```bash
pip install --upgrade PySide6
python -c "from PySide6.QtWidgets import QApplication; print('OK')"
```

### Q2: PyInstaller 构建失败

**可能原因:**
- conda 环境元数据损坏

**解决方案:**
```python
# 修复 conda-meta 中缺少 depends 字段的包
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

### Q3: 复选框样式不显示

**可能原因:**
- 图像路径未正确替换

**解决方案:**
确保 `main.py` 中正确替换了 `CHECKMARK_PATH`:
```python
stylesheet = stylesheet.replace(
    "CHECKMARK_PATH",
    str(checkmark_path).replace("\\", "/")
)
```

### Q4: 打包后缺少文件

**解决方案:**
在 `build.py` 中添加 `--add-data` 选项:
```python
"--add-data", f"{missing_file_path}:destination/"
```

---

## 附录

### A. 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+N | 新建配置 |
| Ctrl+O | 打开配置 |
| Ctrl+S | 保存配置 |
| Ctrl+Q | 退出应用 |

### B. 配置文件示例

完整的配置文件示例请参考 `resources/templates/` 目录。

### C. API 参考

详细的 API 文档请使用 `pydoc` 或查看源代码注释。

---

*文档版本: 1.0.0*
*最后更新: 2025-12-17*
