# -*- coding: utf-8 -*-
"""
Data validation for NetCDF files.

Validates file existence, variable names, time range, and spatial range.
Supports both local and remote (SSH) validation.
"""

import json
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
            path = os.path.join(self.root_dir, self.sub_dir, filename)
        else:
            path = os.path.join(self.root_dir, filename)
        # Convert to absolute path
        return os.path.abspath(path)

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
            return ValidationCheck("file_exists", True, f"File exists: {path}")
        return ValidationCheck("file_exists", False, f"File not found: {path}")

    def check_variable(self, path: str, varname: str) -> ValidationCheck:
        """Check if variable exists in NetCDF file."""
        try:
            import xarray as xr
        except ImportError:
            return ValidationCheck(
                "variable_exists", False,
                "xarray required: pip install xarray netCDF4"
            )

        try:
            ds = xr.open_dataset(path)
            available_vars = list(ds.data_vars)
            ds.close()

            if varname in available_vars:
                return ValidationCheck("variable_exists", True, f"Variable '{varname}' exists")
            return ValidationCheck(
                "variable_exists", False,
                f"Variable '{varname}' not found, available: {available_vars}"
            )
        except Exception as e:
            return ValidationCheck("variable_exists", False, f"Cannot read file: {e}")

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
                "xarray required: pip install xarray netCDF4"
            )

        try:
            ds = xr.open_dataset(path)
            time_dim = self._find_dim(ds, self.TIME_DIMS)

            if time_dim is None:
                ds.close()
                return ValidationCheck(
                    "time_range", False,
                    f"Time dimension not found, tried: {self.TIME_DIMS}"
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
                    f"Time range OK: data {data_syear}-{data_eyear}, required {syear}-{eyear}"
                )
            return ValidationCheck(
                "time_range", False,
                f"Time range insufficient: data {data_syear}-{data_eyear}, required {syear}-{eyear}"
            )
        except Exception as e:
            return ValidationCheck("time_range", False, f"Time check failed: {e}")

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
                "xarray required: pip install xarray netCDF4"
            )

        try:
            ds = xr.open_dataset(path)
            lat_dim = self._find_dim(ds, self.LAT_DIMS)
            lon_dim = self._find_dim(ds, self.LON_DIMS)

            if lat_dim is None or lon_dim is None:
                ds.close()
                return ValidationCheck(
                    "spatial_range", False,
                    "Lat/lon dimensions not found"
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
                    "Spatial range OK"
                )

            msg_parts = []
            if not lat_ok:
                msg_parts.append(f"Lat: data {data_min_lat:.1f}~{data_max_lat:.1f}, required {min_lat:.1f}~{max_lat:.1f}")
            if not lon_ok:
                msg_parts.append(f"Lon: data {data_min_lon:.1f}~{data_max_lon:.1f}, required {min_lon:.1f}~{max_lon:.1f}")

            return ValidationCheck("spatial_range", False, "Spatial range insufficient: " + "; ".join(msg_parts))
        except Exception as e:
            return ValidationCheck("spatial_range", False, f"Spatial check failed: {e}")


class RemoteNetCDFValidator:
    """Validate NetCDF files on remote server via SSH."""

    # Python script template for remote execution
    INSPECT_SCRIPT = '''
import json
import sys
try:
    import xarray as xr
    import pandas as pd
    ds = xr.open_dataset("{path}")
    result = {{"success": True}}
    result["variables"] = list(ds.data_vars)

    # Find time dimension
    time_dims = ['time', 'Time', 'TIME', 't', 'date']
    for td in time_dims:
        if td in ds.dims or td in ds.coords:
            time_vals = pd.to_datetime(ds[td].values)
            result["time_range"] = [int(time_vals.year.min()), int(time_vals.year.max())]
            break

    # Find lat/lon dimensions
    lat_dims = ['lat', 'latitude', 'Lat', 'LAT', 'y']
    lon_dims = ['lon', 'longitude', 'Lon', 'LON', 'x']
    for ld in lat_dims:
        if ld in ds.dims or ld in ds.coords:
            result["lat_range"] = [float(ds[ld].values.min()), float(ds[ld].values.max())]
            break
    for ld in lon_dims:
        if ld in ds.dims or ld in ds.coords:
            result["lon_range"] = [float(ds[ld].values.min()), float(ds[ld].values.max())]
            break

    ds.close()
    print(json.dumps(result))
except ImportError as e:
    print(json.dumps({{"success": False, "error": "xarray not installed"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''

    def __init__(self, ssh_manager):
        """Initialize with SSH manager.

        Args:
            ssh_manager: SSHManager instance for remote execution
        """
        self._ssh = ssh_manager

    def check_file_exists(self, path: str) -> ValidationCheck:
        """Check if file exists on remote server."""
        try:
            stdout, stderr, exit_code = self._ssh.execute(f"test -f '{path}'", timeout=10)
            if exit_code == 0:
                return ValidationCheck("file_exists", True, f"File exists: {path}")
            return ValidationCheck("file_exists", False, f"File not found: {path}")
        except Exception as e:
            return ValidationCheck("file_exists", False, f"Remote check failed: {e}")

    def _run_inspect_script(self, path: str) -> Optional[Dict[str, Any]]:
        """Run inspection script on remote server."""
        script = self.INSPECT_SCRIPT.format(path=path)
        cmd = f"python3 -c '{script}'"

        try:
            stdout, stderr, exit_code = self._ssh.execute(cmd, timeout=30)
            if exit_code == 0 and stdout.strip():
                return json.loads(stdout.strip())
        except Exception:
            pass
        return None

    def check_variable(self, path: str, varname: str) -> ValidationCheck:
        """Check if variable exists in remote NetCDF file."""
        result = self._run_inspect_script(path)

        if result is None:
            return ValidationCheck("variable_exists", False, "Remote check failed")

        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return ValidationCheck("variable_exists", False, f"Remote error: {error}")

        variables = result.get("variables", [])
        if varname in variables:
            return ValidationCheck("variable_exists", True, f"Variable '{varname}' exists")
        return ValidationCheck(
            "variable_exists", False,
            f"Variable '{varname}' not found, available: {variables}"
        )

    def check_time_range(self, path: str, syear: int, eyear: int) -> ValidationCheck:
        """Check time range on remote file."""
        result = self._run_inspect_script(path)

        if result is None or not result.get("success"):
            return ValidationCheck("time_range", False, "Remote time check failed")

        time_range = result.get("time_range")
        if time_range is None:
            return ValidationCheck("time_range", False, "Time dimension not found")

        data_syear, data_eyear = time_range
        if data_syear <= syear and data_eyear >= eyear:
            return ValidationCheck(
                "time_range", True,
                f"Time range OK: data {data_syear}-{data_eyear}"
            )
        return ValidationCheck(
            "time_range", False,
            f"Time range insufficient: data {data_syear}-{data_eyear}, required {syear}-{eyear}"
        )

    def check_spatial_range(
        self, path: str,
        min_lat: float, max_lat: float,
        min_lon: float, max_lon: float
    ) -> ValidationCheck:
        """Check spatial range on remote file."""
        result = self._run_inspect_script(path)

        if result is None or not result.get("success"):
            return ValidationCheck("spatial_range", False, "Remote spatial check failed")

        lat_range = result.get("lat_range")
        lon_range = result.get("lon_range")

        if lat_range is None or lon_range is None:
            return ValidationCheck("spatial_range", False, "Lat/lon dimensions not found")

        data_min_lat, data_max_lat = lat_range
        data_min_lon, data_max_lon = lon_range

        lat_ok = data_min_lat <= min_lat and data_max_lat >= max_lat
        lon_ok = data_min_lon <= min_lon and data_max_lon >= max_lon

        if lat_ok and lon_ok:
            return ValidationCheck("spatial_range", True, "Spatial range OK")

        return ValidationCheck(
            "spatial_range", False,
            "Spatial range insufficient"
        )


class DataValidator:
    """Main validator that orchestrates validation checks."""

    def __init__(self, is_remote: bool = False, ssh_manager=None):
        """Initialize validator.

        Args:
            is_remote: If True, use remote validation via SSH
            ssh_manager: SSHManager instance (required if is_remote=True)
        """
        self._is_remote = is_remote
        self._ssh_manager = ssh_manager

        if is_remote and ssh_manager:
            self._validator = RemoteNetCDFValidator(ssh_manager)
        else:
            self._validator = LocalNetCDFValidator()

    def validate_source(
        self,
        var_name: str,
        source_name: str,
        source_config: Dict[str, Any],
        general_config: Dict[str, Any]
    ) -> SourceValidationResult:
        """Validate a single data source.

        Args:
            var_name: Variable name (e.g., "Evapotranspiration")
            source_name: Source name (e.g., "GLEAM_v4.2a")
            source_config: Source configuration dict
            general_config: General settings (syear, eyear, lat/lon range)

        Returns:
            SourceValidationResult with all checks
        """
        checks = []

        # Extract config values
        general = source_config.get("general", source_config)
        var_config = source_config.get("var_config", source_config)

        root_dir = general.get("root_dir") or general.get("dir", "")
        # sub_dir, prefix, suffix, varname can be in var_config or top level
        sub_dir = var_config.get("sub_dir") or source_config.get("sub_dir", "")
        prefix = var_config.get("prefix") or source_config.get("prefix", "")
        suffix = var_config.get("suffix") or source_config.get("suffix", "")
        varname = var_config.get("varname") or source_config.get("varname", "")
        data_groupby = general.get("data_groupby", "Year")
        data_type = general.get("data_type", "grid")

        # Use source-specific years if available, otherwise general config
        syear = source_config.get("syear") or general.get("syear") or general_config.get("syear", 2000)
        eyear = source_config.get("eyear") or general.get("eyear") or general_config.get("eyear", 2020)

        # Generate file paths
        path_gen = FilePathGenerator(
            root_dir=root_dir,
            sub_dir=sub_dir,
            prefix=prefix,
            suffix=suffix,
            data_groupby=data_groupby,
            syear=syear,
            eyear=eyear
        )
        sample_paths = path_gen.get_sample_paths()

        # Check file existence
        first_existing_path = None
        for path in sample_paths:
            check = self._validator.check_file_exists(path)
            checks.append(check)
            if check.passed and first_existing_path is None:
                first_existing_path = path

        # If no files found, skip other checks
        if first_existing_path is None:
            return SourceValidationResult(var_name, source_name, checks)

        # Check variable name
        if varname:
            check = self._validator.check_variable(first_existing_path, varname)
            checks.append(check)

        # Check time range (only for grid data)
        if data_type == "grid":
            check = self._validator.check_time_range(
                first_existing_path,
                int(syear), int(eyear)
            )
            checks.append(check)

        return SourceValidationResult(var_name, source_name, checks)

    def validate_all(
        self,
        sources: Dict[str, Dict[str, Dict]],
        general_config: Dict[str, Any],
        progress_callback=None
    ) -> DataValidationReport:
        """Validate all data sources.

        Args:
            sources: Dict of {var_name: {source_name: source_config}}
            general_config: General settings
            progress_callback: Optional callback(current, total, var_name, source_name)

        Returns:
            DataValidationReport with all results
        """
        results = []
        total = sum(len(s) for s in sources.values())
        current = 0

        for var_name, var_sources in sources.items():
            for source_name, source_config in var_sources.items():
                if progress_callback:
                    progress_callback(current, total, var_name, source_name)

                result = self.validate_source(
                    var_name, source_name, source_config, general_config
                )
                results.append(result)
                current += 1

        if progress_callback:
            progress_callback(total, total, "", "")

        return DataValidationReport(results=results)
