# -*- coding: utf-8 -*-
"""
Data validation for NetCDF files.

Validates file existence, variable names, time range, and spatial range.
Supports both local and remote (SSH) validation.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ValidationCheck:
    """Single validation check result."""
    name: str
    passed: bool
    message: str


@dataclass
class SourceValidationResult:
    """Validation result for a single data source."""
    var_name: str
    source_name: str
    checks: List[ValidationCheck] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return True if all checks passed."""
        return all(check.passed for check in self.checks)

    @property
    def failed_checks(self) -> List[ValidationCheck]:
        """Return list of failed checks."""
        return [check for check in self.checks if not check.passed]


@dataclass
class DataValidationReport:
    """Complete validation report for all sources."""
    results: List[SourceValidationResult] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        """Total number of sources validated."""
        return len(self.results)

    @property
    def passed_count(self) -> int:
        """Number of sources that passed all checks."""
        return sum(1 for r in self.results if r.is_valid)

    @property
    def failed_count(self) -> int:
        """Number of sources with failed checks."""
        return sum(1 for r in self.results if not r.is_valid)


class FilePathGenerator:
    """Generate file paths based on data_groupby setting."""

    def __init__(
        self,
        root_dir: str,
        sub_dir: str,
        prefix: str,
        suffix: str,
        data_groupby: str,
        syear: int,
        eyear: int
    ):
        self.root_dir = root_dir
        self.sub_dir = sub_dir
        self.prefix = prefix or ""
        self.suffix = suffix or ""
        self.data_groupby = data_groupby
        self.syear = syear
        self.eyear = eyear

    def _build_path(self, filename: str) -> str:
        """Build full path with root_dir and sub_dir."""
        if self.sub_dir:
            return os.path.join(self.root_dir, self.sub_dir, filename)
        return os.path.join(self.root_dir, filename)

    def get_sample_paths(self) -> List[str]:
        """Get sample file paths for validation.

        Returns a small set of representative paths to check.
        """
        if self.data_groupby == "Single":
            filename = f"{self.prefix}{self.suffix}.nc"
            return [self._build_path(filename)]

        elif self.data_groupby == "Year":
            # Sample: first, middle, last year
            years = [self.syear, (self.syear + self.eyear) // 2, self.eyear]
            paths = []
            for year in years:
                filename = f"{self.prefix}{year}{self.suffix}.nc"
                paths.append(self._build_path(filename))
            return paths

        elif self.data_groupby == "Month":
            # Sample: first month of first and last year
            paths = []
            for year in [self.syear, self.eyear]:
                for month in [1]:
                    filename = f"{self.prefix}{year}{month:02d}{self.suffix}.nc"
                    paths.append(self._build_path(filename))
            return paths

        elif self.data_groupby == "Day":
            # Sample: first day of first and last year
            paths = []
            for year in [self.syear, self.eyear]:
                filename = f"{self.prefix}{year}0101{self.suffix}.nc"
                paths.append(self._build_path(filename))
            return paths

        return []


class LocalNetCDFValidator:
    """Validate NetCDF files locally using xarray."""

    # Common dimension names
    TIME_DIMS = ['time', 'Time', 'TIME', 't', 'date']
    LAT_DIMS = ['lat', 'latitude', 'Lat', 'LAT', 'y']
    LON_DIMS = ['lon', 'longitude', 'Lon', 'LON', 'x']

    def check_file_exists(self, path: str) -> ValidationCheck:
        """Check if file exists."""
        exists = os.path.exists(path)
        if exists:
            return ValidationCheck("file_exists", True, f"文件存在: {path}")
        return ValidationCheck("file_exists", False, f"文件不存在: {path}")

    def check_variable(self, path: str, varname: str) -> ValidationCheck:
        """Check if variable exists in NetCDF file."""
        try:
            import xarray as xr
        except ImportError:
            return ValidationCheck(
                "variable_exists", False,
                "需要安装 xarray: pip install xarray netCDF4"
            )

        try:
            ds = xr.open_dataset(path)
            available_vars = list(ds.data_vars)
            ds.close()

            if varname in available_vars:
                return ValidationCheck("variable_exists", True, f"变量 '{varname}' 存在")
            return ValidationCheck(
                "variable_exists", False,
                f"变量 '{varname}' 不存在，可用变量: {available_vars}"
            )
        except Exception as e:
            return ValidationCheck("variable_exists", False, f"无法读取文件: {e}")

    def _find_dim(self, ds, candidates: List[str]) -> Optional[str]:
        """Find a dimension by trying common names."""
        for name in candidates:
            if name in ds.dims or name in ds.coords:
                return name
        return None

    def check_time_range(
        self, path: str, syear: int, eyear: int
    ) -> ValidationCheck:
        """Check if data time range covers required period."""
        try:
            import xarray as xr
            import pandas as pd
        except ImportError:
            return ValidationCheck(
                "time_range", False,
                "需要安装 xarray: pip install xarray netCDF4"
            )

        try:
            ds = xr.open_dataset(path)
            time_dim = self._find_dim(ds, self.TIME_DIMS)

            if time_dim is None:
                ds.close()
                return ValidationCheck(
                    "time_range", False,
                    f"未找到时间维度，尝试了: {self.TIME_DIMS}"
                )

            time_vals = ds[time_dim].values
            ds.close()

            # Convert to years
            time_years = pd.to_datetime(time_vals).year
            data_syear = int(time_years.min())
            data_eyear = int(time_years.max())

            if data_syear <= syear and data_eyear >= eyear:
                return ValidationCheck(
                    "time_range", True,
                    f"时间范围满足: 数据 {data_syear}-{data_eyear}, 需要 {syear}-{eyear}"
                )
            return ValidationCheck(
                "time_range", False,
                f"时间范围不足: 数据 {data_syear}-{data_eyear}, 需要 {syear}-{eyear}"
            )
        except Exception as e:
            return ValidationCheck("time_range", False, f"时间检查失败: {e}")

    def check_spatial_range(
        self, path: str,
        min_lat: float, max_lat: float,
        min_lon: float, max_lon: float
    ) -> ValidationCheck:
        """Check if data spatial range covers required area."""
        try:
            import xarray as xr
        except ImportError:
            return ValidationCheck(
                "spatial_range", False,
                "需要安装 xarray: pip install xarray netCDF4"
            )

        try:
            ds = xr.open_dataset(path)
            lat_dim = self._find_dim(ds, self.LAT_DIMS)
            lon_dim = self._find_dim(ds, self.LON_DIMS)

            if lat_dim is None or lon_dim is None:
                ds.close()
                return ValidationCheck(
                    "spatial_range", False,
                    f"未找到经纬度维度"
                )

            lat_vals = ds[lat_dim].values
            lon_vals = ds[lon_dim].values
            ds.close()

            data_min_lat, data_max_lat = float(lat_vals.min()), float(lat_vals.max())
            data_min_lon, data_max_lon = float(lon_vals.min()), float(lon_vals.max())

            lat_ok = data_min_lat <= min_lat and data_max_lat >= max_lat
            lon_ok = data_min_lon <= min_lon and data_max_lon >= max_lon

            if lat_ok and lon_ok:
                return ValidationCheck(
                    "spatial_range", True,
                    f"空间范围满足"
                )

            msg_parts = []
            if not lat_ok:
                msg_parts.append(f"纬度: 数据 {data_min_lat:.1f}~{data_max_lat:.1f}, 需要 {min_lat:.1f}~{max_lat:.1f}")
            if not lon_ok:
                msg_parts.append(f"经度: 数据 {data_min_lon:.1f}~{data_max_lon:.1f}, 需要 {min_lon:.1f}~{max_lon:.1f}")

            return ValidationCheck("spatial_range", False, "空间范围不足: " + "; ".join(msg_parts))
        except Exception as e:
            return ValidationCheck("spatial_range", False, f"空间检查失败: {e}")
