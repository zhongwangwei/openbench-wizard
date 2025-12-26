# tests/test_validation.py
# -*- coding: utf-8 -*-
"""Tests for validation module."""

import tempfile
import os

import pytest
from core.validation import ValidationError, ValidationResult, FieldValidator


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
