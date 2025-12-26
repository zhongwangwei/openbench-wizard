# tests/test_validation.py
# -*- coding: utf-8 -*-
"""Tests for validation module."""

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
