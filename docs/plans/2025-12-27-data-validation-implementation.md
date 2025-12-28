# Data Validation Implementation Plan

## Overview

This document describes the technical design for integrating data validation into the OpenBench Wizard. The validation system checks NetCDF data files for:
- File existence (local and remote)
- Variable existence
- Time range coverage
- Spatial range coverage

## Architecture

### Data Structures

```python
@dataclass
class ValidationCheck:
    """Single validation check result."""
    name: str           # Check name (file_exists, variable_exists, etc.)
    passed: bool        # Whether check passed
    message: str        # Detailed message

@dataclass
class SourceValidationResult:
    """Validation result for one data source."""
    var_name: str       # Variable name (e.g., "Evapotranspiration")
    source_name: str    # Source name (e.g., "GLEAM")
    checks: List[ValidationCheck]

    @property
    def is_valid(self) -> bool:
        return all(c.passed for c in self.checks)

@dataclass
class DataValidationReport:
    """Complete validation report."""
    results: List[SourceValidationResult]
    timestamp: datetime

    @property
    def all_valid(self) -> bool:
        return all(r.is_valid for r in self.results)
```

### Validator Classes

#### LocalNetCDFValidator

For local file validation using xarray:

```python
class LocalNetCDFValidator:
    """Validate NetCDF files locally using xarray."""

    TIME_DIMS = ["time", "t", "TIME"]
    LAT_DIMS = ["lat", "latitude", "LAT"]
    LON_DIMS = ["lon", "longitude", "LON"]

    def check_file_exists(self, path: str) -> ValidationCheck
    def check_variable(self, path: str, varname: str) -> ValidationCheck
    def check_time_range(self, path: str, syear: int, eyear: int) -> ValidationCheck
    def check_spatial_range(self, path: str,
                           min_lat: float, max_lat: float,
                           min_lon: float, max_lon: float) -> ValidationCheck
```

#### RemoteNetCDFValidator

For remote file validation via SSH:

```python
class RemoteNetCDFValidator:
    """Validate NetCDF files on remote server via SSH."""

    def __init__(self, host: str, username: str, password: str = None, key_path: str = None)
    def check_file_exists(self, path: str) -> ValidationCheck
    def check_variable(self, path: str, varname: str) -> ValidationCheck
    def check_time_range(self, path: str, syear: int, eyear: int) -> ValidationCheck
    def check_spatial_range(self, path: str,
                           min_lat: float, max_lat: float,
                           min_lon: float, max_lon: float) -> ValidationCheck
```

## Implementation Order

### Phase 1: Core Classes
1. Create `ValidationCheck` dataclass
2. Create `SourceValidationResult` dataclass
3. Create `DataValidationReport` dataclass

### Phase 2: Local Validation
1. Implement `LocalNetCDFValidator.check_file_exists()`
2. Implement `LocalNetCDFValidator.check_variable()`
3. Implement `LocalNetCDFValidator.check_time_range()`
4. Implement `LocalNetCDFValidator.check_spatial_range()`

### Phase 3: Remote Validation
1. Implement SSH connection setup in `RemoteNetCDFValidator`
2. Create Python script injection for remote validation
3. Implement remote check methods

### Phase 4: Integration
1. Create validation orchestrator in DataSourceEditor
2. Add validation UI components
3. Display validation results in preview page

## Testing Strategy

### Unit Tests

Test each method in isolation:
- Test with mocked xarray datasets
- Test with mocked SSH connections
- Test edge cases (empty files, missing dimensions)

### Integration Tests

Test complete validation flow:
- Validate real NetCDF files
- Test remote validation with SSH
- Verify UI updates correctly

## Error Messages

All error messages are in English:

| Check | Pass Message | Fail Message |
|-------|-------------|--------------|
| file_exists | "File exists: {path}" | "File not found: {path}" |
| variable_exists | "Variable '{var}' exists" | "Variable '{var}' not found, available: [...]" |
| time_range | "Time range OK ({start}-{end})" | "Time range insufficient: data covers {start}-{end}, needs {req_start}-{req_end}" |
| spatial_range | "Spatial range OK" | "Spatial range insufficient: data covers lat={lat_range}, lon={lon_range}" |

## Dependencies

- `xarray`: NetCDF file reading
- `netCDF4`: NetCDF backend
- `paramiko`: SSH connections (optional, for remote validation)

## File Location

All validation code is in `core/data_validator.py`.
