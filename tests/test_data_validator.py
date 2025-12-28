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
            message="File exists"
        )
        assert check.name == "file_exists"
        assert check.passed is True
        assert check.message == "File exists"

    def test_validation_check_fail(self):
        """Test creating a failing validation check."""
        check = ValidationCheck(
            name="variable_exists",
            passed=False,
            message="Variable 'LE' not found, available: ['E', 'Ep']"
        )
        assert check.passed is False

    def test_source_validation_result(self):
        """Test source validation result."""
        checks = [
            ValidationCheck("file_exists", True, "OK"),
            ValidationCheck("variable_exists", False, "Variable not found")
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
                ValidationCheck("file", False, "Not found")
            ])
        ]
        report = DataValidationReport(results=results)
        assert report.total_count == 2
        assert report.passed_count == 1
        assert report.failed_count == 1


from unittest.mock import patch
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
        """Test Year groupby - uses glob to find files."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="ET",
            prefix="gleam_",
            suffix="",
            data_groupby="Year",
            syear=2000,
            eyear=2020
        )
        # Mock glob to return matching files
        mock_files = [
            "/data/ET/gleam_2000.nc",
            "/data/ET/gleam_2010.nc",
            "/data/ET/gleam_2020.nc"
        ]
        with patch('glob.glob', return_value=mock_files):
            paths = gen.get_sample_paths()
        # Should return first, middle, last file
        assert len(paths) == 3
        assert "/data/ET/gleam_2000.nc" in paths
        assert "/data/ET/gleam_2010.nc" in paths
        assert "/data/ET/gleam_2020.nc" in paths

    def test_month_groupby(self):
        """Test Month groupby - uses glob to find files."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="",
            prefix="data_",
            suffix="",
            data_groupby="Month",
            syear=2000,
            eyear=2001
        )
        # Mock glob to return matching files
        mock_files = [
            "/data/data_200001.nc",
            "/data/data_200006.nc",
            "/data/data_200012.nc"
        ]
        with patch('glob.glob', return_value=mock_files):
            paths = gen.get_sample_paths()
        # Should sample a few months
        assert len(paths) == 3
        assert any("200001" in p for p in paths)

    def test_day_groupby(self):
        """Test Day groupby - uses glob to find files."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="daily",
            prefix="obs_",
            suffix="",
            data_groupby="Day",
            syear=2000,
            eyear=2001
        )
        # Mock glob to return matching files
        mock_files = [
            "/data/daily/obs_20000101.nc",
            "/data/daily/obs_20010101.nc"
        ]
        with patch('glob.glob', return_value=mock_files):
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

    def test_glob_no_matches(self):
        """Test that empty list returned when no files match glob."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="",
            prefix="missing_",
            suffix="",
            data_groupby="Year",
            syear=2000,
            eyear=2020
        )
        with patch('glob.glob', return_value=[]):
            paths = gen.get_sample_paths()
        assert len(paths) == 0

    def test_glob_single_match(self):
        """Test glob returns single file."""
        gen = FilePathGenerator(
            root_dir="/data",
            sub_dir="",
            prefix="data_",
            suffix="",
            data_groupby="Year",
            syear=2000,
            eyear=2020
        )
        mock_files = ["/data/data_2000.nc"]
        with patch('glob.glob', return_value=mock_files):
            paths = gen.get_sample_paths()
        assert len(paths) == 1
        assert paths[0] == "/data/data_2000.nc"


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
        assert "not found" in check.message.lower() or "File not found" in check.message

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
            assert "Time range OK" in check.message

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
            assert "Time range insufficient" in check.message or "insufficient" in check.message.lower()

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
            assert "Time dimension not found" in check.message or "not found" in check.message.lower()

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
            assert "Spatial range OK" in check.message or "OK" in check.message

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
            assert "Spatial range insufficient" in check.message or "insufficient" in check.message.lower()

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
            assert "Lat/lon dimensions not found" in check.message or "not found" in check.message.lower()

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
        assert "Remote check failed" in check.message

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
        assert "not found" in check.message.lower()

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
        assert "Remote error" in check.message or "error" in check.message.lower()

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
        assert "Time range insufficient" in check.message or "insufficient" in check.message.lower()

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
        assert "Time dimension not found" in check.message or "not found" in check.message.lower()

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
        assert "Spatial range insufficient" in check.message or "insufficient" in check.message.lower()

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
        assert "Lat/lon dimensions not found" in check.message or "not found" in check.message.lower()

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


from core.data_validator import DataValidator


class TestDataValidator:
    """Test main DataValidator class."""

    def test_init_local_mode(self):
        """Test initializing validator in local mode."""
        validator = DataValidator(is_remote=False)
        assert validator._is_remote is False
        assert isinstance(validator._validator, LocalNetCDFValidator)

    def test_init_remote_mode(self):
        """Test initializing validator in remote mode."""
        mock_ssh = Mock()
        validator = DataValidator(is_remote=True, ssh_manager=mock_ssh)
        assert validator._is_remote is True
        assert isinstance(validator._validator, RemoteNetCDFValidator)

    def test_init_remote_mode_no_ssh(self):
        """Test that remote mode without ssh_manager falls back to local."""
        validator = DataValidator(is_remote=True, ssh_manager=None)
        # Should fall back to local validator when no ssh_manager
        assert isinstance(validator._validator, LocalNetCDFValidator)

    def test_validate_source_local(self):
        """Test validating a source in local mode."""
        validator = DataValidator(is_remote=False)

        source_config = {
            "general": {
                "root_dir": "/data",
                "data_groupby": "Year",
                "data_type": "grid"
            },
            "sub_dir": "ET",
            "prefix": "gleam_",
            "suffix": "",
            "varname": "E",
            "syear": 2000,
            "eyear": 2020
        }
        general_config = {
            "syear": 2000,
            "eyear": 2020,
            "min_lat": -90,
            "max_lat": 90,
            "min_lon": -180,
            "max_lon": 180
        }

        # This will fail because files don't exist, but structure should work
        result = validator.validate_source(
            var_name="Evapotranspiration",
            source_name="GLEAM",
            source_config=source_config,
            general_config=general_config
        )

        assert result.var_name == "Evapotranspiration"
        assert result.source_name == "GLEAM"
        assert len(result.checks) > 0  # Should have file_exists check at minimum

    def test_validate_source_with_existing_file(self):
        """Test validating a source when file exists."""
        validator = DataValidator(is_remote=False)

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
            temp_path = f.name
            temp_dir = os.path.dirname(temp_path)
            temp_basename = os.path.basename(temp_path)
            # Extract prefix and suffix from filename
            prefix = temp_basename.replace(".nc", "")

        try:
            source_config = {
                "general": {
                    "root_dir": temp_dir,
                    "data_groupby": "Single",
                    "data_type": "grid"
                },
                "sub_dir": "",
                "prefix": prefix,
                "suffix": "",
                "varname": "ET",
                "syear": 2000,
                "eyear": 2020
            }
            general_config = {
                "syear": 2000,
                "eyear": 2020,
                "min_lat": -90,
                "max_lat": 90,
                "min_lon": -180,
                "max_lon": 180
            }

            result = validator.validate_source(
                var_name="ET",
                source_name="TestSource",
                source_config=source_config,
                general_config=general_config
            )

            # File should exist
            file_check = next((c for c in result.checks if c.name == "file_exists"), None)
            assert file_check is not None
            assert file_check.passed is True
        finally:
            os.unlink(temp_path)

    def test_validate_source_non_grid_type(self):
        """Test that spatial range check is skipped for non-grid data types."""
        validator = DataValidator(is_remote=False)

        source_config = {
            "general": {
                "root_dir": "/data",
                "data_groupby": "Single",
                "data_type": "stn"  # Station data - should skip spatial check
            },
            "sub_dir": "",
            "prefix": "station_data",
            "suffix": "",
            "varname": "ET",
            "syear": 2000,
            "eyear": 2020
        }
        general_config = {
            "syear": 2000,
            "eyear": 2020
        }

        result = validator.validate_source(
            var_name="ET",
            source_name="StationData",
            source_config=source_config,
            general_config=general_config
        )

        # Should have file_exists check but no spatial_range check
        check_names = [c.name for c in result.checks]
        assert "file_exists" in check_names
        # Since file doesn't exist, no other checks are performed
        # But if file existed, spatial_range should NOT be checked for non-grid data

    def test_validate_source_extracts_config_from_general(self):
        """Test that config values are correctly extracted from nested general section."""
        validator = DataValidator(is_remote=False)

        source_config = {
            "general": {
                "root_dir": "/test/path",
                "data_groupby": "Month",
                "data_type": "grid",
                "syear": 2010,
                "eyear": 2015
            },
            "sub_dir": "subdir",
            "prefix": "pre_",
            "suffix": "_suf",
            "varname": "precip"
        }
        general_config = {
            "syear": 2000,
            "eyear": 2020
        }

        result = validator.validate_source(
            var_name="Precipitation",
            source_name="GPM",
            source_config=source_config,
            general_config=general_config
        )

        # Check that paths were generated correctly
        # File exists checks should reference the correct paths
        file_checks = [c for c in result.checks if c.name == "file_exists"]
        assert len(file_checks) >= 1
        # Check that the path includes our configured values
        assert any("/test/path" in c.message for c in file_checks)

    def test_validate_source_uses_dir_fallback(self):
        """Test that 'dir' key is used as fallback for 'root_dir'."""
        validator = DataValidator(is_remote=False)

        source_config = {
            "general": {
                "dir": "/fallback/path",  # Using 'dir' instead of 'root_dir'
                "data_groupby": "Single",
                "data_type": "grid"
            },
            "sub_dir": "",
            "prefix": "data",
            "suffix": "",
            "varname": "ET"
        }
        general_config = {
            "syear": 2000,
            "eyear": 2020
        }

        result = validator.validate_source(
            var_name="ET",
            source_name="TestSource",
            source_config=source_config,
            general_config=general_config
        )

        file_checks = [c for c in result.checks if c.name == "file_exists"]
        assert len(file_checks) >= 1
        assert any("/fallback/path" in c.message for c in file_checks)

    def test_validate_all_empty_sources(self):
        """Test validate_all with empty sources dict."""
        validator = DataValidator(is_remote=False)

        report = validator.validate_all(
            sources={},
            general_config={"syear": 2000, "eyear": 2020}
        )

        assert report.total_count == 0
        assert report.passed_count == 0
        assert report.failed_count == 0

    def test_validate_all_single_source(self):
        """Test validate_all with a single source."""
        validator = DataValidator(is_remote=False)

        sources = {
            "Evapotranspiration": {
                "GLEAM": {
                    "general": {
                        "root_dir": "/data",
                        "data_groupby": "Year",
                        "data_type": "grid"
                    },
                    "sub_dir": "ET",
                    "prefix": "gleam_",
                    "suffix": "",
                    "varname": "E",
                    "syear": 2000,
                    "eyear": 2020
                }
            }
        }
        general_config = {
            "syear": 2000,
            "eyear": 2020
        }

        report = validator.validate_all(sources, general_config)

        assert report.total_count == 1
        assert len(report.results) == 1
        assert report.results[0].var_name == "Evapotranspiration"
        assert report.results[0].source_name == "GLEAM"

    def test_validate_all_multiple_sources(self):
        """Test validate_all with multiple sources."""
        validator = DataValidator(is_remote=False)

        sources = {
            "ET": {
                "GLEAM": {
                    "general": {"root_dir": "/data1", "data_groupby": "Year", "data_type": "grid"},
                    "prefix": "gleam_", "suffix": "", "varname": "E"
                },
                "FLUXCOM": {
                    "general": {"root_dir": "/data2", "data_groupby": "Year", "data_type": "grid"},
                    "prefix": "flux_", "suffix": "", "varname": "ET"
                }
            },
            "GPP": {
                "MODIS": {
                    "general": {"root_dir": "/data3", "data_groupby": "Single", "data_type": "grid"},
                    "prefix": "modis_gpp", "suffix": "", "varname": "GPP"
                }
            }
        }
        general_config = {"syear": 2000, "eyear": 2020}

        report = validator.validate_all(sources, general_config)

        assert report.total_count == 3
        var_names = [r.var_name for r in report.results]
        assert "ET" in var_names
        assert "GPP" in var_names

    def test_validate_all_with_progress_callback(self):
        """Test validate_all calls progress callback correctly."""
        validator = DataValidator(is_remote=False)

        progress_calls = []

        def progress_callback(current, total, var_name, source_name):
            progress_calls.append((current, total, var_name, source_name))

        sources = {
            "ET": {
                "Source1": {
                    "general": {"root_dir": "/d", "data_groupby": "Single", "data_type": "grid"},
                    "prefix": "f", "suffix": "", "varname": "E"
                }
            },
            "GPP": {
                "Source2": {
                    "general": {"root_dir": "/d", "data_groupby": "Single", "data_type": "grid"},
                    "prefix": "g", "suffix": "", "varname": "G"
                }
            }
        }

        report = validator.validate_all(sources, {"syear": 2000, "eyear": 2020}, progress_callback)

        # Should have progress calls for each source plus final call
        assert len(progress_calls) >= 2
        # First call should be (0, 2, var_name, source_name)
        assert progress_calls[0][0] == 0
        assert progress_calls[0][1] == 2
        # Final call should indicate completion (total, total, "", "")
        assert progress_calls[-1][0] == progress_calls[-1][1]

    def test_validate_all_remote_mode(self):
        """Test validate_all works in remote mode."""
        mock_ssh = Mock()
        mock_ssh.execute.return_value = ("", "", 1)  # Files don't exist

        validator = DataValidator(is_remote=True, ssh_manager=mock_ssh)

        sources = {
            "ET": {
                "GLEAM": {
                    "general": {"root_dir": "/remote/data", "data_groupby": "Single", "data_type": "grid"},
                    "prefix": "gleam", "suffix": "", "varname": "E"
                }
            }
        }

        report = validator.validate_all(sources, {"syear": 2000, "eyear": 2020})

        assert report.total_count == 1
        # SSH execute should have been called for file existence check
        assert mock_ssh.execute.called
