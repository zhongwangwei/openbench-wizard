# Validation System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add real-time validation with blocking error popups and auto-focus to error fields.

**Architecture:** Create a ValidationManager that coordinates FieldValidator (single field validation) and PageValidator (page-level validation). Validation triggers on field blur, dialog save, and page navigation. Errors are shown one-by-one with auto-focus.

**Tech Stack:** Python 3.10+, PySide6, pytest

---

## Task 1: Create Core Validation Module - Data Classes

**Files:**
- Create: `core/validation.py`
- Test: `tests/test_validation.py`

**Step 1: Write the failing test for ValidationError dataclass**

```python
# tests/test_validation.py
# -*- coding: utf-8 -*-
"""Tests for validation module."""

import pytest
from core.validation import ValidationError, ValidationResult


class TestValidationError:
    """Test ValidationError dataclass."""

    def test_create_validation_error(self):
        """Test creating a validation error."""
        error = ValidationError(
            field_name="project_name",
            message="项目名称不能为空",
            page_id="general",
        )
        assert error.field_name == "project_name"
        assert error.message == "项目名称不能为空"
        assert error.page_id == "general"
        assert error.widget is None
        assert error.context == {}

    def test_validation_error_with_context(self):
        """Test validation error with context."""
        error = ValidationError(
            field_name="varname",
            message="变量名不能为空",
            page_id="ref_data",
            context={"var_name": "Evapotranspiration", "source_name": "GLEAM"}
        )
        assert error.context["var_name"] == "Evapotranspiration"
        assert error.context["source_name"] == "GLEAM"


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_valid_result(self):
        """Test valid result."""
        result = ValidationResult(is_valid=True, errors=[])
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_result(self):
        """Test invalid result with errors."""
        error = ValidationError(
            field_name="test",
            message="test error",
            page_id="general"
        )
        result = ValidationResult(is_valid=False, errors=[error])
        assert result.is_valid is False
        assert len(result.errors) == 1
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'core.validation'"

**Step 3: Write minimal implementation**

```python
# core/validation.py
# -*- coding: utf-8 -*-
"""
Validation framework for OpenBench Wizard.

Provides real-time validation with blocking error popups and auto-focus.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import QWidget


@dataclass
class ValidationError:
    """Single validation error."""
    field_name: str
    message: str
    page_id: str
    widget: Optional[QWidget] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Validation result containing validity status and errors."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/validation.py tests/test_validation.py
git commit -m "feat(validation): add ValidationError and ValidationResult dataclasses"
```

---

## Task 2: Add FieldValidator - Required Field Validation

**Files:**
- Modify: `core/validation.py`
- Modify: `tests/test_validation.py`

**Step 1: Write the failing test for required field validation**

Add to `tests/test_validation.py`:

```python
from core.validation import ValidationError, ValidationResult, FieldValidator


class TestFieldValidator:
    """Test FieldValidator static methods."""

    def test_required_with_empty_string(self):
        """Test required validation fails for empty string."""
        error = FieldValidator.required("", "project_name", "项目名称不能为空")
        assert error is not None
        assert error.field_name == "project_name"
        assert error.message == "项目名称不能为空"

    def test_required_with_whitespace_only(self):
        """Test required validation fails for whitespace only."""
        error = FieldValidator.required("   ", "project_name", "项目名称不能为空")
        assert error is not None

    def test_required_with_valid_value(self):
        """Test required validation passes for valid value."""
        error = FieldValidator.required("my_project", "project_name", "项目名称不能为空")
        assert error is None

    def test_required_with_none(self):
        """Test required validation fails for None."""
        error = FieldValidator.required(None, "project_name", "项目名称不能为空")
        assert error is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidator -v`
Expected: FAIL with "cannot import name 'FieldValidator'"

**Step 3: Write minimal implementation**

Add to `core/validation.py`:

```python
class FieldValidator:
    """Field validator with static methods for common validation rules."""

    @staticmethod
    def required(
        value: Any,
        field_name: str,
        message: str,
        page_id: str = "",
        widget: QWidget = None
    ) -> Optional[ValidationError]:
        """
        Validate that a field is not empty.

        Args:
            value: The value to validate
            field_name: Name of the field for error reporting
            message: Error message if validation fails
            page_id: Page ID for error context
            widget: Widget to focus on error

        Returns:
            ValidationError if invalid, None if valid
        """
        if value is None:
            return ValidationError(field_name, message, page_id, widget)

        if isinstance(value, str) and not value.strip():
            return ValidationError(field_name, message, page_id, widget)

        return None
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidator -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/validation.py tests/test_validation.py
git commit -m "feat(validation): add FieldValidator.required method"
```

---

## Task 3: Add FieldValidator - Path Exists Validation

**Files:**
- Modify: `core/validation.py`
- Modify: `tests/test_validation.py`

**Step 1: Write the failing test for path exists validation**

Add to `tests/test_validation.py`:

```python
import tempfile
import os


class TestFieldValidatorPathExists:
    """Test FieldValidator.path_exists method."""

    def test_path_exists_with_valid_directory(self):
        """Test path exists passes for valid directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            error = FieldValidator.path_exists(tmpdir, "root_dir", "目录不存在")
            assert error is None

    def test_path_exists_with_invalid_path(self):
        """Test path exists fails for non-existent path."""
        error = FieldValidator.path_exists(
            "/non/existent/path/12345",
            "root_dir",
            "目录不存在"
        )
        assert error is not None
        assert "目录不存在" in error.message

    def test_path_exists_with_empty_path(self):
        """Test path exists passes for empty path (optional field)."""
        error = FieldValidator.path_exists("", "root_dir", "目录不存在")
        assert error is None

    def test_path_exists_with_file(self):
        """Test path exists passes for valid file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                error = FieldValidator.path_exists(f.name, "file_path", "文件不存在")
                assert error is None
            finally:
                os.unlink(f.name)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorPathExists -v`
Expected: FAIL with "AttributeError: type object 'FieldValidator' has no attribute 'path_exists'"

**Step 3: Write minimal implementation**

Add to `FieldValidator` class in `core/validation.py`:

```python
    @staticmethod
    def path_exists(
        path: str,
        field_name: str,
        message: str,
        page_id: str = "",
        widget: QWidget = None
    ) -> Optional[ValidationError]:
        """
        Validate that a path exists.

        Args:
            path: Path to validate
            field_name: Name of the field for error reporting
            message: Error message if validation fails
            page_id: Page ID for error context
            widget: Widget to focus on error

        Returns:
            ValidationError if invalid, None if valid
        """
        import os

        # Empty path is OK (optional field)
        if not path or not path.strip():
            return None

        if not os.path.exists(path):
            full_message = f"{message}: {path}"
            return ValidationError(field_name, full_message, page_id, widget)

        return None
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorPathExists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/validation.py tests/test_validation.py
git commit -m "feat(validation): add FieldValidator.path_exists method"
```

---

## Task 4: Add FieldValidator - Number Range Validation

**Files:**
- Modify: `core/validation.py`
- Modify: `tests/test_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_validation.py`:

```python
class TestFieldValidatorNumberRange:
    """Test FieldValidator.number_range method."""

    def test_number_in_range(self):
        """Test number in valid range."""
        error = FieldValidator.number_range(45.0, -90.0, 90.0, "latitude", "纬度范围无效")
        assert error is None

    def test_number_at_min_boundary(self):
        """Test number at minimum boundary."""
        error = FieldValidator.number_range(-90.0, -90.0, 90.0, "latitude", "纬度范围无效")
        assert error is None

    def test_number_at_max_boundary(self):
        """Test number at maximum boundary."""
        error = FieldValidator.number_range(90.0, -90.0, 90.0, "latitude", "纬度范围无效")
        assert error is None

    def test_number_below_min(self):
        """Test number below minimum fails."""
        error = FieldValidator.number_range(-100.0, -90.0, 90.0, "latitude", "纬度范围无效（-90 到 90）")
        assert error is not None
        assert "纬度范围无效" in error.message

    def test_number_above_max(self):
        """Test number above maximum fails."""
        error = FieldValidator.number_range(100.0, -90.0, 90.0, "latitude", "纬度范围无效（-90 到 90）")
        assert error is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorNumberRange -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Add to `FieldValidator` class:

```python
    @staticmethod
    def number_range(
        value: float,
        min_val: float,
        max_val: float,
        field_name: str,
        message: str,
        page_id: str = "",
        widget: QWidget = None
    ) -> Optional[ValidationError]:
        """
        Validate that a number is within a range.

        Args:
            value: Number to validate
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)
            field_name: Name of the field
            message: Error message if validation fails
            page_id: Page ID for error context
            widget: Widget to focus on error

        Returns:
            ValidationError if invalid, None if valid
        """
        if value < min_val or value > max_val:
            return ValidationError(field_name, message, page_id, widget)
        return None
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorNumberRange -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/validation.py tests/test_validation.py
git commit -m "feat(validation): add FieldValidator.number_range method"
```

---

## Task 5: Add FieldValidator - Year Range and Min/Max Comparison

**Files:**
- Modify: `core/validation.py`
- Modify: `tests/test_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_validation.py`:

```python
class TestFieldValidatorComparison:
    """Test FieldValidator comparison methods."""

    def test_min_max_valid(self):
        """Test min <= max passes."""
        error = FieldValidator.min_max(2000, 2020, "year", "起始年份不能大于结束年份")
        assert error is None

    def test_min_max_equal(self):
        """Test min == max passes."""
        error = FieldValidator.min_max(2010, 2010, "year", "起始年份不能大于结束年份")
        assert error is None

    def test_min_max_invalid(self):
        """Test min > max fails."""
        error = FieldValidator.min_max(2020, 2000, "year", "起始年份不能大于结束年份")
        assert error is not None
        assert "起始年份不能大于结束年份" in error.message

    def test_min_max_with_floats(self):
        """Test min/max with float values."""
        error = FieldValidator.min_max(-90.0, 90.0, "latitude", "最小值不能大于最大值")
        assert error is None

        error = FieldValidator.min_max(90.0, -90.0, "latitude", "最小值不能大于最大值")
        assert error is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorComparison -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Add to `FieldValidator` class:

```python
    @staticmethod
    def min_max(
        min_value: float,
        max_value: float,
        field_name: str,
        message: str,
        page_id: str = "",
        widget: QWidget = None
    ) -> Optional[ValidationError]:
        """
        Validate that min value is less than or equal to max value.

        Args:
            min_value: Minimum value
            max_value: Maximum value
            field_name: Name of the field
            message: Error message if validation fails
            page_id: Page ID for error context
            widget: Widget to focus on error (usually the min field)

        Returns:
            ValidationError if min > max, None if valid
        """
        if min_value > max_value:
            return ValidationError(field_name, message, page_id, widget)
        return None
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorComparison -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/validation.py tests/test_validation.py
git commit -m "feat(validation): add FieldValidator.min_max method"
```

---

## Task 6: Add FieldValidator - At Least One Required

**Files:**
- Modify: `core/validation.py`
- Modify: `tests/test_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_validation.py`:

```python
class TestFieldValidatorAtLeastOne:
    """Test FieldValidator.at_least_one method."""

    def test_at_least_one_with_values(self):
        """Test passes when at least one value is provided."""
        error = FieldValidator.at_least_one(
            ["prefix_value", ""],
            ["prefix", "suffix"],
            "文件前缀和后缀至少填写一个"
        )
        assert error is None

    def test_at_least_one_both_filled(self):
        """Test passes when both values provided."""
        error = FieldValidator.at_least_one(
            ["prefix_value", "suffix_value"],
            ["prefix", "suffix"],
            "文件前缀和后缀至少填写一个"
        )
        assert error is None

    def test_at_least_one_all_empty(self):
        """Test fails when all values are empty."""
        error = FieldValidator.at_least_one(
            ["", ""],
            ["prefix", "suffix"],
            "文件前缀和后缀至少填写一个"
        )
        assert error is not None
        assert "至少填写一个" in error.message

    def test_at_least_one_all_whitespace(self):
        """Test fails when all values are whitespace."""
        error = FieldValidator.at_least_one(
            ["  ", "   "],
            ["prefix", "suffix"],
            "文件前缀和后缀至少填写一个"
        )
        assert error is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorAtLeastOne -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Add to `FieldValidator` class:

```python
    @staticmethod
    def at_least_one(
        values: List[Any],
        field_names: List[str],
        message: str,
        page_id: str = "",
        widget: QWidget = None
    ) -> Optional[ValidationError]:
        """
        Validate that at least one of the values is non-empty.

        Args:
            values: List of values to check
            field_names: Names of the fields
            message: Error message if validation fails
            page_id: Page ID for error context
            widget: Widget to focus on error

        Returns:
            ValidationError if all empty, None if at least one is valid
        """
        for value in values:
            if value is not None:
                if isinstance(value, str) and value.strip():
                    return None
                elif not isinstance(value, str) and value:
                    return None

        combined_name = "/".join(field_names)
        return ValidationError(combined_name, message, page_id, widget)
```

Also add `List` to imports at top of file:

```python
from typing import List, Optional, Dict, Any
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorAtLeastOne -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/validation.py tests/test_validation.py
git commit -m "feat(validation): add FieldValidator.at_least_one method"
```

---

## Task 7: Add FieldValidator - Selection Required

**Files:**
- Modify: `core/validation.py`
- Modify: `tests/test_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_validation.py`:

```python
class TestFieldValidatorSelectionRequired:
    """Test FieldValidator.selection_required method."""

    def test_selection_with_items(self):
        """Test passes when items are selected."""
        selection = {"item1": True, "item2": False, "item3": True}
        error = FieldValidator.selection_required(selection, "evaluation", "请至少选择一个评估项目")
        assert error is None

    def test_selection_all_false(self):
        """Test fails when no items selected."""
        selection = {"item1": False, "item2": False}
        error = FieldValidator.selection_required(selection, "evaluation", "请至少选择一个评估项目")
        assert error is not None
        assert "至少选择一个" in error.message

    def test_selection_empty_dict(self):
        """Test fails for empty dict."""
        error = FieldValidator.selection_required({}, "evaluation", "请至少选择一个评估项目")
        assert error is not None

    def test_combined_selection(self):
        """Test combined selection from multiple dicts."""
        metrics = {"rmse": False}
        scores = {"overall": True}
        combined = {**metrics, **scores}
        error = FieldValidator.selection_required(combined, "metrics_scores", "请至少选择一个指标或评分项")
        assert error is None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorSelectionRequired -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Add to `FieldValidator` class:

```python
    @staticmethod
    def selection_required(
        selection: Dict[str, bool],
        field_name: str,
        message: str,
        page_id: str = "",
        widget: QWidget = None
    ) -> Optional[ValidationError]:
        """
        Validate that at least one item is selected (True).

        Args:
            selection: Dict mapping item names to selected status
            field_name: Name of the field
            message: Error message if validation fails
            page_id: Page ID for error context
            widget: Widget to focus on error

        Returns:
            ValidationError if none selected, None if at least one selected
        """
        if not selection:
            return ValidationError(field_name, message, page_id, widget)

        has_selection = any(v for v in selection.values())
        if not has_selection:
            return ValidationError(field_name, message, page_id, widget)

        return None
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestFieldValidatorSelectionRequired -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/validation.py tests/test_validation.py
git commit -m "feat(validation): add FieldValidator.selection_required method"
```

---

## Task 8: Add ValidationManager - Show Error and Focus

**Files:**
- Modify: `core/validation.py`
- Modify: `tests/test_validation.py`

**Step 1: Write the failing test**

Add to `tests/test_validation.py`:

```python
from unittest.mock import Mock, patch
from core.validation import ValidationManager


class TestValidationManager:
    """Test ValidationManager class."""

    def test_show_error_and_focus_with_widget(self):
        """Test showing error and focusing widget."""
        manager = ValidationManager()
        mock_widget = Mock()
        error = ValidationError(
            field_name="test",
            message="Test error",
            page_id="general",
            widget=mock_widget
        )

        with patch('core.validation.QMessageBox') as mock_msgbox:
            manager.show_error_and_focus(error)
            mock_msgbox.warning.assert_called_once()
            mock_widget.setFocus.assert_called_once()

    def test_show_error_without_widget(self):
        """Test showing error without widget (no focus)."""
        manager = ValidationManager()
        error = ValidationError(
            field_name="test",
            message="Test error",
            page_id="general",
            widget=None
        )

        with patch('core.validation.QMessageBox') as mock_msgbox:
            manager.show_error_and_focus(error)
            mock_msgbox.warning.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestValidationManager -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Add to `core/validation.py`:

```python
from PySide6.QtWidgets import QWidget, QMessageBox


class ValidationManager:
    """
    Validation manager that coordinates validation flow.

    Handles showing errors sequentially and focusing on error widgets.
    """

    def __init__(self, parent_widget: QWidget = None):
        """
        Initialize validation manager.

        Args:
            parent_widget: Parent widget for message boxes
        """
        self._parent = parent_widget

    def show_error_and_focus(self, error: ValidationError) -> None:
        """
        Show error message and focus on the error widget.

        Args:
            error: ValidationError to display
        """
        QMessageBox.warning(
            self._parent,
            "Validation Error",
            error.message
        )

        if error.widget is not None:
            error.widget.setFocus()

    def validate_and_show_errors(self, errors: List[ValidationError]) -> bool:
        """
        Process errors one by one, showing each and focusing.

        Args:
            errors: List of validation errors

        Returns:
            True if no errors, False if there were errors
        """
        if not errors:
            return True

        # Show first error only (blocking approach)
        self.show_error_and_focus(errors[0])
        return False
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py::TestValidationManager -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/validation.py tests/test_validation.py
git commit -m "feat(validation): add ValidationManager with show_error_and_focus"
```

---

## Task 9: Integrate Validation into DataSourceEditor - Required Fields

**Files:**
- Modify: `ui/widgets/data_source_editor.py:931-991` (the accept method)

**Step 1: Read current implementation**

Review the existing `accept()` method in DataSourceEditor to understand current validation.

**Step 2: Update accept() method to use FieldValidator**

Replace the `accept` method in `ui/widgets/data_source_editor.py`:

```python
    def accept(self):
        """Override accept to validate required fields and paths before closing."""
        from core.validation import FieldValidator, ValidationManager

        errors = []
        manager = ValidationManager(self)

        # Validate source name (required for new sources)
        if hasattr(self, 'name_input'):
            error = FieldValidator.required(
                self.name_input.text().strip(),
                "source_name",
                "数据源名称不能为空",
                widget=self.name_input
            )
            if error:
                errors.append(error)

        # Validate root_dir (required)
        root_dir = self.root_dir.path()
        error = FieldValidator.required(
            root_dir,
            "root_dir",
            "根目录不能为空",
            widget=self.root_dir
        )
        if error:
            errors.append(error)

        # Validate varname (required)
        error = FieldValidator.required(
            self.varname_input.text().strip(),
            "varname",
            "变量名不能为空",
            widget=self.varname_input
        )
        if error:
            errors.append(error)

        # Validate prefix/suffix (at least one required)
        error = FieldValidator.at_least_one(
            [self.prefix_input.text().strip(), self.suffix_input.text().strip()],
            ["prefix", "suffix"],
            "文件前缀和后缀至少填写一个",
            widget=self.prefix_input
        )
        if error:
            errors.append(error)

        # Grid type specific validations
        if self.radio_grid.isChecked():
            # Grid resolution required
            grid_res = self.grid_res_input.text().strip()
            error = FieldValidator.required(
                grid_res,
                "grid_res",
                "Grid 类型数据必须填写网格分辨率",
                widget=self.grid_res_input
            )
            if error:
                errors.append(error)

            # Year range required for grid type
            syear = self.syear_input.text().strip()
            eyear = self.eyear_input.text().strip()

            error = FieldValidator.required(
                syear,
                "syear",
                "Grid 类型数据必须填写起始年份",
                widget=self.syear_input
            )
            if error:
                errors.append(error)

            error = FieldValidator.required(
                eyear,
                "eyear",
                "Grid 类型数据必须填写结束年份",
                widget=self.eyear_input
            )
            if error:
                errors.append(error)

            # Validate year range if both provided
            if syear and eyear:
                try:
                    syear_int = int(syear)
                    eyear_int = int(eyear)
                    error = FieldValidator.min_max(
                        syear_int,
                        eyear_int,
                        "year_range",
                        "起始年份不能大于结束年份",
                        widget=self.syear_input
                    )
                    if error:
                        errors.append(error)
                except ValueError:
                    pass  # Invalid number format handled elsewhere

        # Show first error if any
        if errors:
            manager.show_error_and_focus(errors[0])
            return

        # Path validation (skip in remote mode)
        if not self._is_remote_mode():
            if root_dir:
                root_dir = to_absolute_path(root_dir, get_openbench_root())
                is_valid, error_msg = validate_path(root_dir, "directory")
                if not is_valid:
                    error = ValidationError(
                        "root_dir",
                        f"根目录路径不存在: {root_dir}",
                        "",
                        self.root_dir
                    )
                    manager.show_error_and_focus(error)
                    return

            # Validate fulllist if station data
            if self.radio_station.isChecked():
                fulllist_path = self.fulllist.path()
                if fulllist_path:
                    fulllist_path = to_absolute_path(fulllist_path, get_openbench_root())
                    is_valid, error_msg = validate_path(fulllist_path, "file")
                    if not is_valid:
                        error = ValidationError(
                            "fulllist",
                            f"站点列表文件不存在: {fulllist_path}",
                            "",
                            self.fulllist
                        )
                        manager.show_error_and_focus(error)
                        return

            # Validate model_namelist for sim data
            if self.source_type == "sim":
                model_path = self.model_nml.path()
                if model_path:
                    model_path = to_absolute_path(model_path, get_openbench_root())
                    is_valid, error_msg = validate_path(model_path, "file")
                    if not is_valid:
                        error = ValidationError(
                            "model_nml",
                            f"模型定义文件不存在: {model_path}",
                            "",
                            self.model_nml
                        )
                        manager.show_error_and_focus(error)
                        return

        super().accept()
```

**Step 3: Add import for ValidationError**

At the top of `ui/widgets/data_source_editor.py`, after the existing imports:

```python
from core.validation import ValidationError
```

**Step 4: Test manually**

Run the application and test DataSourceEditor validation:
```bash
cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python main.py
```

**Step 5: Commit**

```bash
git add ui/widgets/data_source_editor.py
git commit -m "feat(validation): integrate FieldValidator into DataSourceEditor"
```

---

## Task 10: Integrate Validation into PageGeneral

**Files:**
- Modify: `ui/pages/page_general.py:583-611` (the validate method)

**Step 1: Update validate() method**

Replace the `validate` method in `ui/pages/page_general.py`:

```python
    def validate(self) -> bool:
        """Validate page input."""
        from core.validation import FieldValidator, ValidationManager

        errors = []
        manager = ValidationManager(self)

        # Project name required
        error = FieldValidator.required(
            self.basename_input.text().strip(),
            "basename",
            "项目名称不能为空",
            page_id=self.PAGE_ID,
            widget=self.basename_input
        )
        if error:
            errors.append(error)

        # Output directory required
        error = FieldValidator.required(
            self.basedir_input.path().strip(),
            "basedir",
            "输出目录不能为空",
            page_id=self.PAGE_ID,
            widget=self.basedir_input
        )
        if error:
            errors.append(error)

        # Year range validation
        error = FieldValidator.min_max(
            self.syear_spin.value(),
            self.eyear_spin.value(),
            "year_range",
            "起始年份不能大于结束年份",
            page_id=self.PAGE_ID,
            widget=self.syear_spin
        )
        if error:
            errors.append(error)

        # Latitude range validation
        error = FieldValidator.number_range(
            self.min_lat_spin.value(),
            -90.0, 90.0,
            "min_lat",
            "最小纬度范围无效（-90 到 90）",
            page_id=self.PAGE_ID,
            widget=self.min_lat_spin
        )
        if error:
            errors.append(error)

        error = FieldValidator.number_range(
            self.max_lat_spin.value(),
            -90.0, 90.0,
            "max_lat",
            "最大纬度范围无效（-90 到 90）",
            page_id=self.PAGE_ID,
            widget=self.max_lat_spin
        )
        if error:
            errors.append(error)

        error = FieldValidator.min_max(
            self.min_lat_spin.value(),
            self.max_lat_spin.value(),
            "lat_range",
            "最小纬度不能大于最大纬度",
            page_id=self.PAGE_ID,
            widget=self.min_lat_spin
        )
        if error:
            errors.append(error)

        # Longitude range validation
        error = FieldValidator.number_range(
            self.min_lon_spin.value(),
            -180.0, 180.0,
            "min_lon",
            "最小经度范围无效（-180 到 180）",
            page_id=self.PAGE_ID,
            widget=self.min_lon_spin
        )
        if error:
            errors.append(error)

        error = FieldValidator.number_range(
            self.max_lon_spin.value(),
            -180.0, 180.0,
            "max_lon",
            "最大经度范围无效（-180 到 180）",
            page_id=self.PAGE_ID,
            widget=self.max_lon_spin
        )
        if error:
            errors.append(error)

        error = FieldValidator.min_max(
            self.min_lon_spin.value(),
            self.max_lon_spin.value(),
            "lon_range",
            "最小经度不能大于最大经度",
            page_id=self.PAGE_ID,
            widget=self.min_lon_spin
        )
        if error:
            errors.append(error)

        # Show first error if any
        if errors:
            manager.show_error_and_focus(errors[0])
            return False

        self.save_to_config()
        return True
```

**Step 2: Test manually**

Run the application and test General page validation.

**Step 3: Commit**

```bash
git add ui/pages/page_general.py
git commit -m "feat(validation): integrate FieldValidator into PageGeneral"
```

---

## Task 11: Add Validation to PageEvaluation

**Files:**
- Modify: `ui/pages/page_evaluation.py`

**Step 1: Read current implementation**

```bash
cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && head -80 ui/pages/page_evaluation.py
```

**Step 2: Add validate method to PageEvaluation**

Add the following method to `PageEvaluation` class:

```python
    def validate(self) -> bool:
        """Validate page input."""
        from core.validation import FieldValidator, ValidationManager

        selection = self.checkbox_group.get_selection()
        error = FieldValidator.selection_required(
            selection,
            "evaluation_items",
            "请至少选择一个评估项目",
            page_id=self.PAGE_ID
        )

        if error:
            manager = ValidationManager(self)
            manager.show_error_and_focus(error)
            return False

        self.save_to_config()
        return True
```

**Step 3: Commit**

```bash
git add ui/pages/page_evaluation.py
git commit -m "feat(validation): add validation to PageEvaluation"
```

---

## Task 12: Add Combined Validation to PageMetrics and PageScores

**Files:**
- Modify: `ui/pages/page_metrics.py`
- Modify: `ui/pages/page_scores.py`
- Modify: `ui/wizard_controller.py`

**Step 1: Add helper method to WizardController**

Add to `WizardController` class in `ui/wizard_controller.py`:

```python
    def get_combined_metrics_scores_selection(self) -> Dict[str, bool]:
        """Get combined selection from metrics and scores pages."""
        metrics = self._config.get("metrics", {})
        scores = self._config.get("scores", {})
        return {**metrics, **scores}
```

**Step 2: Add validate to PageMetrics**

Add to `PageMetrics` class in `ui/pages/page_metrics.py`:

```python
    def validate(self) -> bool:
        """Validate page input - check combined metrics + scores selection."""
        from core.validation import FieldValidator, ValidationManager

        # Save current selection first
        self.save_to_config()

        # Get combined selection
        combined = self.controller.get_combined_metrics_scores_selection()

        error = FieldValidator.selection_required(
            combined,
            "metrics_scores",
            "请至少选择一个指标或评分项",
            page_id=self.PAGE_ID
        )

        if error:
            manager = ValidationManager(self)
            manager.show_error_and_focus(error)
            return False

        return True
```

**Step 3: Add validate to PageScores**

Add to `PageScores` class (similar to PageMetrics):

```python
    def validate(self) -> bool:
        """Validate page input - check combined metrics + scores selection."""
        from core.validation import FieldValidator, ValidationManager

        # Save current selection first
        self.save_to_config()

        # Get combined selection
        combined = self.controller.get_combined_metrics_scores_selection()

        error = FieldValidator.selection_required(
            combined,
            "metrics_scores",
            "请至少选择一个指标或评分项",
            page_id=self.PAGE_ID
        )

        if error:
            manager = ValidationManager(self)
            manager.show_error_and_focus(error)
            return False

        return True
```

**Step 4: Commit**

```bash
git add ui/pages/page_metrics.py ui/pages/page_scores.py ui/wizard_controller.py
git commit -m "feat(validation): add combined metrics/scores validation"
```

---

## Task 13: Add Validation to PageRefData - Data Source Required

**Files:**
- Modify: `ui/pages/page_ref_data.py`

**Step 1: Add validate method to PageRefData**

Add the following method to `PageRefData` class:

```python
    def validate(self) -> bool:
        """Validate page input - ensure all evaluation items have data sources."""
        from core.validation import ValidationError, ValidationManager

        eval_items = self.controller.config.get("evaluation_items", {})
        selected = [k for k, v in eval_items.items() if v]

        manager = ValidationManager(self)

        for var_name in selected:
            sources = self._source_configs.get(var_name, {})
            if not sources:
                error = ValidationError(
                    field_name="data_source",
                    message=f"{var_name.replace('_', ' ')} 缺少参考数据源配置",
                    page_id=self.PAGE_ID,
                    context={"var_name": var_name}
                )
                manager.show_error_and_focus(error)
                # Auto-open add source dialog
                self._add_source(var_name)
                return False

            # Validate each source has required fields
            for source_name, source_data in sources.items():
                # Check varname
                varname = source_data.get("varname", "")
                if not varname:
                    error = ValidationError(
                        field_name="varname",
                        message=f"变量名不能为空\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    # Auto-open edit source dialog
                    self._select_and_edit_source(var_name, source_name)
                    return False

                # Check prefix/suffix
                prefix = source_data.get("prefix", "")
                suffix = source_data.get("suffix", "")
                if not prefix and not suffix:
                    error = ValidationError(
                        field_name="prefix/suffix",
                        message=f"文件前缀和后缀至少填写一个\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    self._select_and_edit_source(var_name, source_name)
                    return False

                # Check root_dir
                general = source_data.get("general", {})
                root_dir = general.get("root_dir", "") or general.get("dir", "")
                if not root_dir:
                    error = ValidationError(
                        field_name="root_dir",
                        message=f"根目录不能为空\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    self._select_and_edit_source(var_name, source_name)
                    return False

        self.save_to_config()
        return True

    def _select_and_edit_source(self, var_name: str, source_name: str):
        """Select source in list and open edit dialog."""
        source_list = self._source_lists.get(var_name)
        if source_list:
            # Find and select the item
            for i in range(source_list.count()):
                if source_list.item(i).text() == source_name:
                    source_list.setCurrentRow(i)
                    break
            # Open edit dialog
            self._edit_source(var_name)
```

**Step 2: Commit**

```bash
git add ui/pages/page_ref_data.py
git commit -m "feat(validation): add data source validation to PageRefData"
```

---

## Task 14: Add Validation to PageSimData

**Files:**
- Modify: `ui/pages/page_sim_data.py`

**Step 1: Add validate method to PageSimData**

Add similar validation method to `PageSimData` class (same pattern as PageRefData):

```python
    def validate(self) -> bool:
        """Validate page input - ensure all evaluation items have data sources."""
        from core.validation import ValidationError, ValidationManager

        eval_items = self.controller.config.get("evaluation_items", {})
        selected = [k for k, v in eval_items.items() if v]

        manager = ValidationManager(self)

        for var_name in selected:
            sources = self._source_configs.get(var_name, {})
            if not sources:
                error = ValidationError(
                    field_name="data_source",
                    message=f"{var_name.replace('_', ' ')} 缺少模拟数据源配置",
                    page_id=self.PAGE_ID,
                    context={"var_name": var_name}
                )
                manager.show_error_and_focus(error)
                # Auto-open add source dialog
                self._add_source(var_name)
                return False

            # Validate each source has required fields
            for source_name, source_data in sources.items():
                # Check varname
                varname = source_data.get("varname", "")
                if not varname:
                    error = ValidationError(
                        field_name="varname",
                        message=f"变量名不能为空\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    self._select_and_edit_source(var_name, source_name)
                    return False

                # Check prefix/suffix
                prefix = source_data.get("prefix", "")
                suffix = source_data.get("suffix", "")
                if not prefix and not suffix:
                    error = ValidationError(
                        field_name="prefix/suffix",
                        message=f"文件前缀和后缀至少填写一个\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    self._select_and_edit_source(var_name, source_name)
                    return False

                # Check root_dir
                general = source_data.get("general", {})
                root_dir = general.get("root_dir", "") or general.get("dir", "")
                if not root_dir:
                    error = ValidationError(
                        field_name="root_dir",
                        message=f"根目录不能为空\n\n数据源: {source_name}\n变量: {var_name.replace('_', ' ')}",
                        page_id=self.PAGE_ID,
                        context={"var_name": var_name, "source_name": source_name}
                    )
                    manager.show_error_and_focus(error)
                    self._select_and_edit_source(var_name, source_name)
                    return False

        self.save_to_config()
        return True

    def _select_and_edit_source(self, var_name: str, source_name: str):
        """Select source in list and open edit dialog."""
        source_list = self._source_lists.get(var_name)
        if source_list:
            # Find and select the item
            for i in range(source_list.count()):
                if source_list.item(i).text() == source_name:
                    source_list.setCurrentRow(i)
                    break
            # Open edit dialog
            self._edit_source(var_name)
```

**Step 2: Commit**

```bash
git add ui/pages/page_sim_data.py
git commit -m "feat(validation): add data source validation to PageSimData"
```

---

## Task 15: Integrate Page Validation with Navigation

**Files:**
- Modify: `ui/main_window.py`

**Step 1: Read current navigation implementation**

Review how navigation works in MainWindow.

**Step 2: Add validation before navigation**

Find the navigation methods in `MainWindow` and add validation calls. Look for methods like `_on_next_clicked` or sidebar click handlers.

Update the next button click handler:

```python
    def _on_next_clicked(self):
        """Handle Next button click."""
        # Get current page and validate
        current_page_id = self.controller.current_page
        current_page = self.pages.get(current_page_id)

        if current_page and hasattr(current_page, 'validate'):
            if not current_page.validate():
                return  # Validation failed, don't navigate

        # Proceed with navigation
        self.controller.go_next()
```

Update sidebar navigation:

```python
    def _on_nav_item_clicked(self, item):
        """Handle navigation sidebar item click."""
        page_id = item.data(Qt.UserRole)

        # Validate current page before navigating away
        current_page_id = self.controller.current_page
        current_page = self.pages.get(current_page_id)

        if current_page and hasattr(current_page, 'validate'):
            if not current_page.validate():
                return  # Validation failed, don't navigate

        self.controller.go_to_page(page_id)
```

**Step 3: Commit**

```bash
git add ui/main_window.py
git commit -m "feat(validation): integrate page validation with navigation"
```

---

## Task 16: Run All Tests and Final Verification

**Step 1: Run all validation tests**

```bash
cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/test_validation.py -v
```
Expected: All tests PASS

**Step 2: Run all project tests**

```bash
cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python -m pytest tests/ -v
```
Expected: All tests PASS

**Step 3: Manual testing**

Run the application and test:
1. Leave project name empty → should show error and focus
2. Set start year > end year → should show error
3. Don't select any evaluation items → should show error
4. Don't add data sources → should show error and open dialog
5. Leave varname empty in data source → should show error

```bash
cd /Users/zhongwangwei/Desktop/Github/openbench-wizard && python main.py
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(validation): complete validation system implementation"
```

---

## Summary

This implementation plan covers:

1. **Tasks 1-8**: Core validation module with FieldValidator and ValidationManager
2. **Task 9**: DataSourceEditor validation integration
3. **Tasks 10-14**: Page-level validation for all pages
4. **Task 15**: Navigation integration
5. **Task 16**: Testing and verification

Total: 16 tasks, each following TDD approach with failing tests first.

---

*Document Version: 1.0*
*Created: 2025-12-26*
