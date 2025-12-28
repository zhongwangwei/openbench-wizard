# Data Validation Design

## Purpose

Design document for the data validation feature in OpenBench Wizard. This feature validates NetCDF data files to ensure they meet the requirements for evaluation.

## Requirements

### Functional Requirements

1. **File Existence Check**: Verify that data files exist at specified paths
2. **Variable Check**: Verify that required variables exist in files
3. **Time Range Check**: Verify that data covers required time period
4. **Spatial Range Check**: Verify that data covers required spatial extent

### Non-Functional Requirements

1. **Performance**: Validation should complete within seconds for typical datasets
2. **Usability**: Clear, actionable error messages
3. **Extensibility**: Easy to add new validation checks

## Design Decisions

### Decision 1: Local vs Remote Validation

**Options:**
- A) Local-only validation (require data to be locally accessible)
- B) Remote validation via SSH
- C) Support both local and remote

**Chosen: C** - Support both for maximum flexibility

### Decision 2: Validation Library

**Options:**
- A) Use xarray for all NetCDF operations
- B) Use netCDF4 directly
- C) Use xarray with netCDF4 backend

**Chosen: C** - xarray provides cleaner API while netCDF4 handles low-level operations

### Decision 3: Error Reporting

**Options:**
- A) First error stops validation
- B) Collect all errors before reporting

**Chosen: B** - Users see complete picture of all issues at once

## Class Diagram

```
┌─────────────────────────────────────┐
│         ValidationCheck             │
├─────────────────────────────────────┤
│ + name: str                         │
│ + passed: bool                      │
│ + message: str                      │
├─────────────────────────────────────┤
│                                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│      SourceValidationResult         │
├─────────────────────────────────────┤
│ + var_name: str                     │
│ + source_name: str                  │
│ + checks: List[ValidationCheck]     │
├─────────────────────────────────────┤
│ + is_valid: bool (property)         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│       DataValidationReport          │
├─────────────────────────────────────┤
│ + results: List[SourceValidationResult]  │
│ + timestamp: datetime               │
├─────────────────────────────────────┤
│ + all_valid: bool (property)        │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│       LocalNetCDFValidator          │
├─────────────────────────────────────┤
│ + TIME_DIMS: List[str]              │
│ + LAT_DIMS: List[str]               │
│ + LON_DIMS: List[str]               │
├─────────────────────────────────────┤
│ + check_file_exists()               │
│ + check_variable()                  │
│ + check_time_range()                │
│ + check_spatial_range()             │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│      RemoteNetCDFValidator          │
├─────────────────────────────────────┤
│ - host: str                         │
│ - username: str                     │
│ - _ssh_client: SSHClient            │
├─────────────────────────────────────┤
│ + check_file_exists()               │
│ + check_variable()                  │
│ + check_time_range()                │
│ + check_spatial_range()             │
│ - _run_remote_script()              │
└─────────────────────────────────────┘
```

## Validation Flow

```
User configures data source
         │
         ▼
Click "Validate" button
         │
         ▼
Determine if local or remote
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  Local    Remote
Validator  Validator
    │         │
    └────┬────┘
         │
         ▼
Run all checks:
  1. file_exists
  2. variable_exists
  3. time_range
  4. spatial_range
         │
         ▼
Generate ValidationResult
         │
         ▼
Display results in UI
```

## UI Integration Points

1. **DataSourceEditor**: Add "Validate" button
2. **Validation Results Panel**: Show pass/fail for each check
3. **Preview Page**: Summary validation status

## Error Message Guidelines

- Keep messages concise but informative
- Include actual vs expected values for failures
- Use consistent formatting
- All messages in English
