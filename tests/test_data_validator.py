# -*- coding: utf-8 -*-
"""Tests for data validator module."""

import pytest
from core.data_validator import (
    ValidationCheck,
    SourceValidationResult,
    DataValidationReport
)


class TestValidationDataClasses:
    """Test validation data classes."""

    def test_validation_check_pass(self):
        """Test creating a passing validation check."""
        check = ValidationCheck(
            name="file_exists",
            passed=True,
            message="文件存在"
        )
        assert check.name == "file_exists"
        assert check.passed is True
        assert check.message == "文件存在"

    def test_validation_check_fail(self):
        """Test creating a failing validation check."""
        check = ValidationCheck(
            name="variable_exists",
            passed=False,
            message="变量 'LE' 不存在，可用变量: ['E', 'Ep']"
        )
        assert check.passed is False

    def test_source_validation_result(self):
        """Test source validation result."""
        checks = [
            ValidationCheck("file_exists", True, "OK"),
            ValidationCheck("variable_exists", False, "变量不存在")
        ]
        result = SourceValidationResult(
            var_name="Evapotranspiration",
            source_name="GLEAM_v4.2a",
            checks=checks
        )
        assert result.var_name == "Evapotranspiration"
        assert result.is_valid is False  # One check failed
        assert len(result.failed_checks) == 1

    def test_data_validation_report(self):
        """Test complete validation report."""
        results = [
            SourceValidationResult("ET", "GLEAM", [
                ValidationCheck("file", True, "OK")
            ]),
            SourceValidationResult("GPP", "MODIS", [
                ValidationCheck("file", False, "不存在")
            ])
        ]
        report = DataValidationReport(results=results)
        assert report.total_count == 2
        assert report.passed_count == 1
        assert report.failed_count == 1


from core.data_validator import FilePathGenerator


class TestFilePathGenerator:
    """Test file path generation based on data_groupby."""

    def test_single_groupby(self):
        """Test Single groupby - one file."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="ET",
            prefix="gleam_",
            suffix="_v4",
            data_groupby="Single",
            syear=2000,
            eyear=2020
        )
        paths = gen.get_sample_paths()
        assert len(paths) == 1
        assert paths[0] == "/data/ET/gleam__v4.nc"

    def test_year_groupby(self):
        """Test Year groupby - sample years."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="ET",
            prefix="gleam_",
            suffix="",
            data_groupby="Year",
            syear=2000,
            eyear=2020
        )
        paths = gen.get_sample_paths()
        # Should return first, middle, last year
        assert len(paths) == 3
        assert "/data/ET/gleam_2000.nc" in paths
        assert "/data/ET/gleam_2010.nc" in paths
        assert "/data/ET/gleam_2020.nc" in paths

    def test_month_groupby(self):
        """Test Month groupby - sample months."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="",
            prefix="data_",
            suffix="",
            data_groupby="Month",
            syear=2000,
            eyear=2001
        )
        paths = gen.get_sample_paths()
        # Should sample a few months
        assert len(paths) >= 2
        assert any("200001" in p for p in paths)

    def test_no_sub_dir(self):
        """Test path generation without sub_dir."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="",
            prefix="file_",
            suffix="",
            data_groupby="Single",
            syear=2000,
            eyear=2020
        )
        paths = gen.get_sample_paths()
        assert paths[0] == "/data/file_.nc"
