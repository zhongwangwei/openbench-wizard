# Validation System Design

## Overview

Add real-time validation functionality to OpenBench Wizard that checks all configuration items during user input, save operations, and page navigation. When errors are detected, display popup dialogs one by one to guide users through fixing each issue.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                   ValidationManager                      │
│  - Manages all validation rules                          │
│  - Coordinates validation flow                           │
│  - Handles error queue and blocking popups               │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │FieldValidator│ │PageValidator │ │ConfigValidator│
   │ Single field │ │ Page-level   │ │ Global config │
   │ real-time    │ │ validation   │ │ validation    │
   └─────────────┘ └─────────────┘ └─────────────┘
```

### Validation Triggers

| Trigger | Validator | Behavior |
|---------|-----------|----------|
| Field loses focus | FieldValidator | Validate single field, popup on error and focus |
| DataSourceEditor OK click | PageValidator | Validate all fields, popup one by one |
| Page navigation (Next/sidebar) | PageValidator + ConfigValidator | Validate current page + related data |

### Error Handling Flow

1. Detect first error → Show QMessageBox
2. User clicks "OK" → Auto-focus on error field (or open editor)
3. User fixes → Re-trigger validation
4. All errors fixed → Allow to continue

## Validation Rules

### 1. General Settings Page

| Field | Rule | Error Message |
|-------|------|---------------|
| Project Name | Not empty | "项目名称不能为空" |
| Output Directory | Not empty + path exists | "输出目录不能为空" / "输出目录不存在" |
| Start Year | ≤ End Year | "起始年份不能大于结束年份" |
| Min Latitude | -90 ~ 90, ≤ Max | "纬度范围无效（-90 到 90）" |
| Max Latitude | -90 ~ 90 | Same as above |
| Min Longitude | -180 ~ 180, ≤ Max | "经度范围无效（-180 到 180）" |
| Max Longitude | -180 ~ 180 | Same as above |

### 2. Evaluation Items Page

| Rule | Error Message |
|------|---------------|
| At least one item selected | "请至少选择一个评估项目" |

### 3. Metrics + Scores Pages

| Rule | Error Message |
|------|---------------|
| At least one selected across both | "请至少选择一个指标或评分项" |

### 4. Reference Data / Simulation Data Pages

| Rule | Error Message |
|------|---------------|
| Each selected evaluation item must have a data source | "{变量名} 缺少数据源配置" |

### 5. Data Source Fields (DataSourceEditor)

| Field | Condition | Rule | Error Message |
|-------|-----------|------|---------------|
| Source Name | When creating new | Not empty | "数据源名称不能为空" |
| Root Directory | Always | Not empty + path exists | "根目录不能为空" / "根目录路径不存在: {path}" |
| Variable Name | Always | Not empty | "变量名不能为空" |
| Prefix / Suffix | Always | At least one | "文件前缀和后缀至少填写一个" |
| Grid Resolution | Grid type | Not empty + numeric | "Grid 类型数据必须填写网格分辨率" |
| Year Range | Grid type | Not empty + syear ≤ eyear | "Grid 类型数据必须填写年份范围" / "起始年份不能大于结束年份" |

## Validation Flow Details

### 1. Field-Level Real-Time Validation (On Focus Lost)

```
User edits field → Loses focus
       │
       ▼
  FieldValidator.validate(field)
       │
       ├─ Pass → No action
       │
       └─ Fail → QMessageBox.warning()
                      │
                      ▼
                 User clicks "OK"
                      │
                      ▼
                 field.setFocus() ← Auto-focus back to error field
```

### 2. DataSourceEditor Save Validation

```
User clicks "OK"
       │
       ▼
  Collect all errors = []
       │
       ▼
  Validate each field
       │
       ├─ All pass → accept() close dialog
       │
       └─ Has errors → Popup first error
                      │
                      ▼
                 User clicks "OK"
                      │
                      ▼
                 Focus on corresponding field
                      │
                      ▼
                 Block close (return, don't call accept)
```

### 3. Page Navigation Validation

```
User clicks "Next" or sidebar navigation
       │
       ▼
  PageValidator.validate(current_page)
       │
       ├─ Pass → Allow navigation
       │
       └─ Fail → Popup error
                    │
                    ▼
              User clicks "OK"
                    │
                    ├─ If data source error → Auto-open DataSourceEditor
                    │
                    └─ If page field error → Focus on that field
                    │
                    ▼
              Block page navigation
```

### 4. Special Handling for Missing Data Source

When validation finds an evaluation item missing data source:
1. Popup: "{变量名} 缺少数据源配置"
2. After user clicks OK, auto-open "Add Source" dialog for that variable

## Implementation Components

### New Files

```
core/
└── validation.py          # Validation framework core module
```

### Core Classes

```python
# core/validation.py

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from PySide6.QtWidgets import QWidget, QMessageBox

@dataclass
class ValidationError:
    """Single validation error"""
    field_name: str          # Field name
    message: str             # Error message
    widget: QWidget          # Associated input widget (for focusing)
    page_id: str             # Page ID
    context: dict            # Extra context (e.g., variable name, source name)

@dataclass
class ValidationResult:
    """Validation result"""
    is_valid: bool
    errors: List[ValidationError]

class FieldValidator:
    """Field validator - single field validation rules"""
    @staticmethod
    def required(value: str, field_name: str, widget: QWidget = None) -> Optional[ValidationError]:
        """Validate required field"""
        pass

    @staticmethod
    def path_exists(path: str, field_name: str, widget: QWidget = None) -> Optional[ValidationError]:
        """Validate path exists"""
        pass

    @staticmethod
    def number_range(value: float, min_val: float, max_val: float,
                     field_name: str, widget: QWidget = None) -> Optional[ValidationError]:
        """Validate number in range"""
        pass

    @staticmethod
    def year_range(syear: int, eyear: int,
                   syear_widget: QWidget = None) -> Optional[ValidationError]:
        """Validate year range"""
        pass

class PageValidator:
    """Page validator - whole page validation"""
    def validate_general(self, page) -> ValidationResult:
        pass

    def validate_evaluation(self, page) -> ValidationResult:
        pass

    def validate_metrics_scores(self, metrics_page, scores_page) -> ValidationResult:
        pass

    def validate_ref_data(self, page) -> ValidationResult:
        pass

    def validate_sim_data(self, page) -> ValidationResult:
        pass

class ValidationManager:
    """Validation manager - coordinates validation flow"""
    def __init__(self, controller):
        self.controller = controller
        self.page_validator = PageValidator()

    def validate_field(self, widget: QWidget, rules: List) -> bool:
        """Validate single field with rules"""
        pass

    def validate_page(self, page) -> bool:
        """Validate entire page"""
        pass

    def show_error_and_focus(self, error: ValidationError) -> None:
        """Show error popup and focus on widget"""
        pass

    def process_errors_sequentially(self, errors: List[ValidationError]) -> bool:
        """Process errors one by one, return True if all resolved"""
        pass
```

### Files to Modify

| File | Modification |
|------|--------------|
| `ui/pages/base_page.py` | Add validation hook methods |
| `ui/pages/page_general.py` | Integrate field-level validation |
| `ui/pages/page_evaluation.py` | Add selection validation |
| `ui/pages/page_metrics.py` | Add joint validation logic |
| `ui/pages/page_scores.py` | Add joint validation logic |
| `ui/pages/page_ref_data.py` | Add data source validation |
| `ui/pages/page_sim_data.py` | Add data source validation |
| `ui/widgets/data_source_editor.py` | Enhance validation logic |
| `ui/wizard_controller.py` | Integrate ValidationManager |

## Error UI Design

### Error Popup Style

Use `QMessageBox.warning()` for consistency:

```
┌─────────────────────────────────────────┐
│  ⚠ Validation Error                     │
├─────────────────────────────────────────┤
│                                         │
│  根目录路径不存在:                        │
│  /path/to/invalid/dir                   │
│                                         │
│                          [ 确定 ]        │
└─────────────────────────────────────────┘
```

### Visual Feedback for Invalid Fields (Optional Enhancement)

Add red border to invalid input fields:

```css
/* Add to theme.qss */
QLineEdit[invalid="true"],
QSpinBox[invalid="true"] {
    border: 2px solid #e74c3c;
}
```

### Interaction Example

**Scenario: User clicks Next on Reference Data page**

1. System detects `Evapotranspiration` data source `GLEAM_v4.2a` missing `varname`
2. Popup: "变量名不能为空\n\n数据源: GLEAM_v4.2a\n变量: Evapotranspiration"
3. User clicks "OK"
4. Auto-open `DataSourceEditor` to edit `GLEAM_v4.2a`
5. `varname` input field auto-focused
6. User fills in and clicks OK
7. System continues checking next error (if any)
8. All errors fixed → Allow navigation to next page

---

*Document Version: 1.0*
*Created: 2025-12-26*
