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


class FieldValidator:
    """Field validator with static methods for common validation rules."""

    @staticmethod
    def required(
        value: Any,
        field_name: str,
        message: str,
        page_id: str = "",
        widget: QWidget = None
    ) -> Optional[ValidationError]:
        """
        Validate that a field is not empty.

        Args:
            value: The value to validate
            field_name: Name of the field for error reporting
            message: Error message if validation fails
            page_id: Page ID for error context
            widget: Widget to focus on error

        Returns:
            ValidationError if invalid, None if valid
        """
        if value is None:
            return ValidationError(field_name, message, page_id, widget)

        if isinstance(value, str) and not value.strip():
            return ValidationError(field_name, message, page_id, widget)

        return None

    @staticmethod
    def path_exists(
        path: str,
        field_name: str,
        message: str,
        page_id: str = "",
        widget: QWidget = None
    ) -> Optional[ValidationError]:
        """
        Validate that a path exists.

        Args:
            path: Path to validate
            field_name: Name of the field for error reporting
            message: Error message if validation fails
            page_id: Page ID for error context
            widget: Widget to focus on error

        Returns:
            ValidationError if invalid, None if valid
        """
        import os

        # Empty path is OK (optional field)
        if not path or not path.strip():
            return None

        if not os.path.exists(path):
            full_message = f"{message}: {path}"
            return ValidationError(field_name, full_message, page_id, widget)

        return None
