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

    def test_day_groupby(self):
        """Test Day groupby - sample days."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="daily",
            prefix="obs_",
            suffix="",
            data_groupby="Day",
            syear=2000,
            eyear=2001
        )
        paths = gen.get_sample_paths()
        assert len(paths) == 2
        assert "/data/daily/obs_20000101.nc" in paths
        assert "/data/daily/obs_20010101.nc" in paths

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


import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from core.data_validator import LocalNetCDFValidator


class TestLocalNetCDFValidator:
    """Test local NetCDF file validation."""

    def test_check_file_exists_true(self):
        """Test file exists check when file exists."""
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
            try:
                validator = LocalNetCDFValidator()
                check = validator.check_file_exists(f.name)
                assert check.passed is True
                assert check.name == "file_exists"
            finally:
                os.unlink(f.name)

    def test_check_file_exists_false(self):
        """Test file exists check when file missing."""
        validator = LocalNetCDFValidator()
        check = validator.check_file_exists("/nonexistent/path/file.nc")
        assert check.passed is False
        assert "不存在" in check.message

    def test_check_variable_exists(self):
        """Test variable check with mocked xarray."""
        validator = LocalNetCDFValidator()

        # Mock xarray dataset
        mock_ds = Mock()
        mock_ds.data_vars = ["temperature", "precipitation", "ET"]
        mock_ds.close = Mock()

        with patch('xarray.open_dataset', return_value=mock_ds):
            check = validator.check_variable("/data/file.nc", "ET")
            assert check.passed is True

            check = validator.check_variable("/data/file.nc", "LE")
            assert check.passed is False
            assert "temperature" in check.message  # Shows available vars

    def test_check_variable_xarray_not_installed(self):
        """Test graceful handling when xarray not installed."""
        validator = LocalNetCDFValidator()

        with patch.dict('sys.modules', {'xarray': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'xarray'")):
                check = validator.check_variable("/data/file.nc", "ET")
                assert check.passed is False
                assert "xarray" in check.message.lower()

    def test_check_time_range_pass(self):
        """Test time range check when data covers required period."""
        validator = LocalNetCDFValidator()

        # Mock xarray dataset with time dimension
        mock_ds = MagicMock()
        mock_ds.dims = {'time': 100, 'lat': 180, 'lon': 360}
        mock_ds.coords = {'time': Mock(), 'lat': Mock(), 'lon': Mock()}

        # Create mock time values that span 2000-2020
        import pandas as pd
        time_values = pd.date_range('2000-01-01', '2020-12-31', freq='M').values
        mock_ds.__getitem__ = Mock(return_value=Mock(values=time_values))
        mock_ds.close = Mock()

        with patch('xarray.open_dataset', return_value=mock_ds):
            check = validator.check_time_range("/data/file.nc", 2005, 2015)
            assert check.passed is True
            assert "时间范围满足" in check.message

    def test_check_time_range_fail(self):
        """Test time range check when data doesn't cover required period."""
        validator = LocalNetCDFValidator()

        mock_ds = MagicMock()
        mock_ds.dims = {'time': 50, 'lat': 180, 'lon': 360}
        mock_ds.coords = {'time': Mock()}

        # Create mock time values that only span 2010-2015
        import pandas as pd
        time_values = pd.date_range('2010-01-01', '2015-12-31', freq='M').values
        mock_ds.__getitem__ = Mock(return_value=Mock(values=time_values))
        mock_ds.close = Mock()

        with patch('xarray.open_dataset', return_value=mock_ds):
            check = validator.check_time_range("/data/file.nc", 2000, 2020)
            assert check.passed is False
            assert "时间范围不足" in check.message

    def test_check_time_range_no_time_dim(self):
        """Test time range check when no time dimension found."""
        validator = LocalNetCDFValidator()

        mock_ds = MagicMock()
        mock_ds.dims = {'lat': 180, 'lon': 360}  # No time dimension
        mock_ds.coords = {'lat': Mock(), 'lon': Mock()}
        mock_ds.close = Mock()

        with patch('xarray.open_dataset', return_value=mock_ds):
            check = validator.check_time_range("/data/file.nc", 2000, 2020)
            assert check.passed is False
            assert "未找到时间维度" in check.message

    def test_check_spatial_range_pass(self):
        """Test spatial range check when data covers required area."""
        validator = LocalNetCDFValidator()

        mock_ds = MagicMock()
        mock_ds.dims = {'lat': 180, 'lon': 360}
        mock_ds.coords = {'lat': Mock(), 'lon': Mock()}

        # Mock lat/lon values covering global range
        lat_values = np.linspace(-90, 90, 180)
        lon_values = np.linspace(-180, 180, 360)

        mock_lat = Mock()
        mock_lat.values = lat_values
        mock_lon = Mock()
        mock_lon.values = lon_values

        mock_ds.__getitem__.side_effect = lambda key: mock_lat if key == 'lat' else mock_lon
        mock_ds.close = Mock()

        with patch('xarray.open_dataset', return_value=mock_ds):
            check = validator.check_spatial_range("/data/file.nc", -45, 45, -90, 90)
            assert check.passed is True
            assert "空间范围满足" in check.message

    def test_check_spatial_range_fail(self):
        """Test spatial range check when data doesn't cover required area."""
        validator = LocalNetCDFValidator()

        mock_ds = MagicMock()
        mock_ds.dims = {'lat': 90, 'lon': 180}
        mock_ds.coords = {'lat': Mock(), 'lon': Mock()}

        # Mock lat/lon values covering only northern hemisphere
        lat_values = np.linspace(0, 90, 90)
        lon_values = np.linspace(0, 180, 180)

        mock_lat = Mock()
        mock_lat.values = lat_values
        mock_lon = Mock()
        mock_lon.values = lon_values

        mock_ds.__getitem__.side_effect = lambda key: mock_lat if key == 'lat' else mock_lon
        mock_ds.close = Mock()

        with patch('xarray.open_dataset', return_value=mock_ds):
            check = validator.check_spatial_range("/data/file.nc", -45, 45, -90, 90)
            assert check.passed is False
            assert "空间范围不足" in check.message

    def test_check_spatial_range_no_lat_lon(self):
        """Test spatial range check when no lat/lon dimensions found."""
        validator = LocalNetCDFValidator()

        mock_ds = MagicMock()
        # Use dimension names that won't match LAT_DIMS or LON_DIMS
        mock_ds.dims = {'row': 100, 'col': 100}
        mock_ds.coords = {'row': Mock(), 'col': Mock()}
        mock_ds.close = Mock()

        with patch('xarray.open_dataset', return_value=mock_ds):
            check = validator.check_spatial_range("/data/file.nc", -45, 45, -90, 90)
            assert check.passed is False
            assert "未找到经纬度维度" in check.message

    def test_time_dims_list_exists(self):
        """Test that TIME_DIMS list is defined."""
        assert hasattr(LocalNetCDFValidator, 'TIME_DIMS')
        assert 'time' in LocalNetCDFValidator.TIME_DIMS
        assert 'Time' in LocalNetCDFValidator.TIME_DIMS

    def test_lat_dims_list_exists(self):
        """Test that LAT_DIMS list is defined."""
        assert hasattr(LocalNetCDFValidator, 'LAT_DIMS')
        assert 'lat' in LocalNetCDFValidator.LAT_DIMS
        assert 'latitude' in LocalNetCDFValidator.LAT_DIMS

    def test_lon_dims_list_exists(self):
        """Test that LON_DIMS list is defined."""
        assert hasattr(LocalNetCDFValidator, 'LON_DIMS')
        assert 'lon' in LocalNetCDFValidator.LON_DIMS
        assert 'longitude' in LocalNetCDFValidator.LON_DIMS


import json
from core.data_validator import RemoteNetCDFValidator


class TestRemoteNetCDFValidator:
    """Test remote NetCDF validation via SSH."""

    def test_check_file_exists_remote(self):
        """Test remote file exists check."""
        mock_ssh = Mock()
        mock_ssh.execute.return_value = ("", "", 0)  # exit code 0 = exists

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_file_exists("/remote/data/file.nc")

        assert check.passed is True
        mock_ssh.execute.assert_called_once()

    def test_check_file_not_exists_remote(self):
        """Test remote file not exists."""
        mock_ssh = Mock()
        mock_ssh.execute.return_value = ("", "", 1)  # exit code 1 = not exists

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_file_exists("/remote/data/file.nc")

        assert check.passed is False

    def test_check_file_exists_ssh_error(self):
        """Test remote file check when SSH fails."""
        mock_ssh = Mock()
        mock_ssh.execute.side_effect = Exception("SSH connection failed")

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_file_exists("/remote/data/file.nc")

        assert check.passed is False
        assert "远程检查失败" in check.message

    def test_check_variable_remote(self):
        """Test remote variable check."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "variables": ["ET", "precipitation", "temperature"]
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_variable("/remote/file.nc", "ET")

        assert check.passed is True

    def test_check_variable_not_exists_remote(self):
        """Test remote variable check when variable not found."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "variables": ["precipitation", "temperature"]
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_variable("/remote/file.nc", "ET")

        assert check.passed is False
        assert "ET" in check.message
        assert "不存在" in check.message

    def test_check_variable_remote_error(self):
        """Test remote variable check when script fails."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": False,
            "error": "xarray not installed"
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_variable("/remote/file.nc", "ET")

        assert check.passed is False
        assert "远程错误" in check.message

    def test_check_time_range_remote(self):
        """Test remote time range check."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "time_range": [2000, 2020]
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_time_range("/remote/file.nc", 2005, 2015)

        assert check.passed is True

    def test_check_time_range_remote_insufficient(self):
        """Test remote time range check when data doesn't cover required period."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "time_range": [2010, 2015]
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_time_range("/remote/file.nc", 2000, 2020)

        assert check.passed is False
        assert "时间范围不足" in check.message

    def test_check_time_range_remote_no_time_dim(self):
        """Test remote time range check when no time dimension found."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "variables": ["ET"]
            # No time_range key
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_time_range("/remote/file.nc", 2000, 2020)

        assert check.passed is False
        assert "未找到时间维度" in check.message

    def test_check_spatial_range_remote(self):
        """Test remote spatial range check."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "lat_range": [-90.0, 90.0],
            "lon_range": [-180.0, 180.0]
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_spatial_range("/remote/file.nc", -45, 45, -90, 90)

        assert check.passed is True

    def test_check_spatial_range_remote_insufficient(self):
        """Test remote spatial range check when data doesn't cover required area."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "lat_range": [0.0, 90.0],  # Only northern hemisphere
            "lon_range": [0.0, 180.0]  # Only eastern hemisphere
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_spatial_range("/remote/file.nc", -45, 45, -90, 90)

        assert check.passed is False
        assert "空间范围不足" in check.message

    def test_check_spatial_range_remote_no_lat_lon(self):
        """Test remote spatial range check when no lat/lon dimensions found."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "variables": ["ET"]
            # No lat_range or lon_range keys
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        check = validator.check_spatial_range("/remote/file.nc", -45, 45, -90, 90)

        assert check.passed is False
        assert "未找到经纬度维度" in check.message

    def test_inspect_script_exists(self):
        """Test that INSPECT_SCRIPT attribute is defined."""
        mock_ssh = Mock()
        validator = RemoteNetCDFValidator(mock_ssh)
        assert hasattr(validator, 'INSPECT_SCRIPT')
        assert isinstance(validator.INSPECT_SCRIPT, str)
        assert "xarray" in validator.INSPECT_SCRIPT

    def test_run_inspect_script_returns_dict(self):
        """Test _run_inspect_script helper method returns dict or None."""
        mock_ssh = Mock()
        result_json = json.dumps({
            "success": True,
            "variables": ["ET"]
        })
        mock_ssh.execute.return_value = (result_json, "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        result = validator._run_inspect_script("/remote/file.nc")

        assert isinstance(result, dict)
        assert result["success"] is True

    def test_run_inspect_script_handles_invalid_json(self):
        """Test _run_inspect_script returns None for invalid JSON."""
        mock_ssh = Mock()
        mock_ssh.execute.return_value = ("not valid json", "", 0)

        validator = RemoteNetCDFValidator(mock_ssh)
        result = validator._run_inspect_script("/remote/file.nc")

        assert result is None

    def test_run_inspect_script_handles_ssh_failure(self):
        """Test _run_inspect_script returns None on SSH failure."""
        mock_ssh = Mock()
        mock_ssh.execute.return_value = ("", "error", 1)

        validator = RemoteNetCDFValidator(mock_ssh)
        result = validator._run_inspect_script("/remote/file.nc")

        assert result is None
