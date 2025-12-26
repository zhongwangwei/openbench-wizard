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
