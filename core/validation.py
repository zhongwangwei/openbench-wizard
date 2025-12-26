# core/validation.py
# -*- coding: utf-8 -*-
"""
Validation framework for OpenBench Wizard.

Provides real-time validation with blocking error popups and auto-focus.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import QWidget


@dataclass
class ValidationError:
    """Single validation error."""
    field_name: str
    message: str
    page_id: str
    widget: Optional[QWidget] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Validation result containing validity status and errors."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
