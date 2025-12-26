# -*- coding: utf-8 -*-
"""
Data validation for NetCDF files.

Validates file existence, variable names, time range, and spatial range.
Supports both local and remote (SSH) validation.
"""

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
