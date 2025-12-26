# Deep Data Validation Design

## Overview

Add a "Validate Data" button to Reference Data and Simulation Data pages that performs deep validation of configured data sources, checking file existence, variable names, time range, and spatial range in NetCDF files.

## Features

### Validation Checks

1. **File Existence** - Generate file paths based on root_dir, prefix/suffix, and data_groupby, verify files exist
2. **Variable Name** - Open NetCDF file and verify configured varname exists
3. **Time Range** - Check if data time dimension covers configured syear-eyear
4. **Spatial Range** - Check if data lat/lon covers configured min/max_lat/lon

### User Interaction Flow

```
User clicks "验证数据" button
       │
       ▼
  Show progress dialog (progress bar + current item)
       │
       ▼
  Check each data source...
       │
       ▼
  Show results dialog
  ┌─────────────────────────────────┐
  │ 数据验证结果                      │
  ├─────────────────────────────────┤
  │ ✓ Evapotranspiration/GLEAM     │
  │ ✗ Latent_Heat/FLUXCOM          │
  │   - 变量 'LE' 不存在            │
  │   - 时间范围不足 (2005-2018)    │
  │ ✓ GPP/MODIS                    │
  └─────────────────────────────────┘
```

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    DataValidator                         │
│  - validate_source(source_config) -> ValidationReport   │
│  - validate_all(sources) -> List[ValidationReport]      │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │FileChecker  │ │VarChecker   │ │RangeChecker │
   │Check file   │ │Check varname│ │Check ranges │
   │existence    │ │in NetCDF    │ │time & space │
   └─────────────┘ └─────────────┘ └─────────────┘
```

### Local vs Remote Mode

| Mode | File Check | NetCDF Read |
|------|------------|-------------|
| Local | `os.path.exists()` | `xarray.open_dataset()` |
| Remote | SSH `test -f` | SSH execute Python script |

### Remote Validation Strategy

In remote mode, send validation script to server:

```python
# Execute on remote server
import xarray as xr
import json

ds = xr.open_dataset('/path/to/file.nc')
result = {
    'exists': True,
    'variables': list(ds.data_vars),
    'time_range': [str(ds.time.min().values), str(ds.time.max().values)],
    'lat_range': [float(ds.lat.min()), float(ds.lat.max())],
    'lon_range': [float(ds.lon.min()), float(ds.lon.max())]
}
print(json.dumps(result))
```

## File Path Generation

Based on `data_groupby` setting:

| data_groupby | File Path Pattern | Example |
|--------------|-------------------|---------|
| Single | `{root_dir}/{sub_dir}/{prefix}{suffix}.nc` | `data/ET/gleam_v4.nc` |
| Year | `{root_dir}/{sub_dir}/{prefix}{year}{suffix}.nc` | `data/ET/gleam_2000.nc` |
| Month | `{root_dir}/{sub_dir}/{prefix}{year}{month:02d}{suffix}.nc` | `data/ET/gleam_200001.nc` |
| Day | `{root_dir}/{sub_dir}/{prefix}{year}{month:02d}{day:02d}{suffix}.nc` | `data/ET/gleam_20000101.nc` |

### File Check Strategy

- **Single**: Check single file
- **Year/Month/Day**: Sample check (first year, last year, middle year) to avoid checking too many files

## Validation Rules

| Check | Content | Error Message Example |
|-------|---------|----------------------|
| File exists | Check if generated file path exists | "文件不存在: /data/ET/gleam_2000.nc" |
| Variable name | Check if varname exists in NetCDF variables | "变量 'LE' 不存在，可用变量: ['E', 'Ep', 'Ei']" |
| Time range | Check if data time covers syear-eyear | "时间范围不足: 数据 2005-2018，需要 2000-2020" |
| Spatial range | Check if data lat/lon covers configured area | "空间范围不足: 数据纬度 -60~60，需要 -90~90" |

### Dimension Name Handling

NetCDF files may use different dimension names:

```python
# Common time dimension names
TIME_DIMS = ['time', 'Time', 'TIME', 't', 'date']
# Common latitude dimension names
LAT_DIMS = ['lat', 'latitude', 'Lat', 'LAT', 'y']
# Common longitude dimension names
LON_DIMS = ['lon', 'longitude', 'Lon', 'LON', 'x']
```

Validator will automatically try to match these common names.

## UI Components

### Validate Button

Add button at bottom of PageRefData and PageSimData:

```
┌─────────────────────────────────────────────────────────┐
│  Reference Data                                          │
├─────────────────────────────────────────────────────────┤
│  [Evapotranspiration]  [+ Add] [Copy] [Edit] [Remove]   │
│  ├─ GLEAM_v4.2a                                         │
│  └─ FLUXCOM                                             │
│                                                          │
│  [Latent_Heat]         [+ Add] [Copy] [Edit] [Remove]   │
│  └─ FLUXNET                                             │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                              [ 验证数据 ]                │
└─────────────────────────────────────────────────────────┘
```

### Progress Dialog

```
┌─────────────────────────────────────────┐
│  正在验证数据...                         │
├─────────────────────────────────────────┤
│                                          │
│  [████████░░░░░░░░░░░░]  3/8             │
│                                          │
│  当前: Evapotranspiration / GLEAM_v4.2a │
│  检查: 变量名验证                        │
│                                          │
│                          [ 取消 ]        │
└─────────────────────────────────────────┘
```

### Results Dialog

```
┌─────────────────────────────────────────────────────────┐
│  数据验证结果                                  [ × ]     │
├─────────────────────────────────────────────────────────┤
│  验证完成: 6 通过, 2 失败                               │
├─────────────────────────────────────────────────────────┤
│  ✓ Evapotranspiration / GLEAM_v4.2a                     │
│  ✓ Evapotranspiration / FLUXCOM                         │
│  ✗ Latent_Heat / FLUXNET                                │
│    └─ 变量 'LE' 不存在，可用变量: ['H', 'Rn', 'G']      │
│  ✓ GPP / MODIS                                          │
│  ✗ GPP / FLUXNET                                        │
│    └─ 时间范围不足: 数据 2005-2018, 需要 2000-2020      │
│    └─ 文件不存在: /data/gpp/flux_2019.nc               │
│  ✓ ...                                                  │
├─────────────────────────────────────────────────────────┤
│                                      [ 确定 ] [ 导出 ]  │
└─────────────────────────────────────────────────────────┘
```

- **Export button**: Export validation results to text file

## Error Handling

| Scenario | Handling |
|----------|----------|
| xarray not installed | Prompt "需要安装 xarray: pip install xarray netCDF4" |
| File cannot be opened | Record error "文件损坏或格式不支持: {path}" |
| SSH connection failed | Prompt "远程连接失败，请检查 SSH 配置" |
| Remote xarray not installed | Prompt "远程服务器需要安装 xarray" |
| Validation timeout | Single file check timeout 30s, skip and record |
| User cancel | Stop validation, show completed results |

## Dependencies

```
# Local validation requires
xarray
netCDF4  # or h5netcdf

# Remote validation requires (on remote server)
xarray
netCDF4
```

## Files to Create/Modify

| File | Changes |
|------|---------|
| `core/data_validator.py` | New - Data validation core logic |
| `ui/widgets/validation_dialog.py` | New - Progress and results dialogs |
| `ui/pages/page_ref_data.py` | Add validate button and handler |
| `ui/pages/page_sim_data.py` | Add validate button and handler |

---

*Document Version: 1.0*
*Created: 2025-12-27*
