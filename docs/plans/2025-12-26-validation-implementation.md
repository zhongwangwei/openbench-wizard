# Validation Implementation Plan

## Overview

Implementation plan for field-level validation in OpenBench Wizard. This covers form validation (required fields, path existence, value ranges) rather than data validation.

## Validation Types

### Field Validators

| Validator | Purpose | Example |
|-----------|---------|---------|
| `required` | Check non-empty value | Project name cannot be empty |
| `path_exists` | Check path exists | Directory does not exist |
| `number_range` | Check value in range | Latitude must be -90 to 90 |
| `min_max` | Check min <= max | Start year cannot be greater than end year |
| `at_least_one` | At least one filled | File prefix and suffix must have at least one |
| `selection_required` | At least one selected | Please select at least one evaluation item |

## Implementation

### ValidationError

```python
@dataclass
class ValidationError:
    """Represents a validation error."""
    field_name: str              # Field identifier
    message: str                 # Error message
    page_id: str = ""           # Page where error occurred
    widget: QWidget = None      # Widget to focus
    context: Dict[str, Any] = field(default_factory=dict)
```

### FieldValidator

```python
class FieldValidator:
    """Static methods for common validation rules."""

    @staticmethod
    def required(value, field_name, message, page_id="", widget=None):
        """Validate non-empty value."""
        if value is None or str(value).strip() == "":
            return ValidationError(field_name, message, page_id, widget)
        return None

    @staticmethod
    def path_exists(path, field_name, message, page_id="", widget=None):
        """Validate path exists."""
        if path and path.strip():
            if not os.path.exists(path):
                return ValidationError(field_name, message, page_id, widget)
        return None

    @staticmethod
    def number_range(value, min_val, max_val, field_name, message, page_id="", widget=None):
        """Validate number in range."""
        if value < min_val or value > max_val:
            return ValidationError(field_name, message, page_id, widget)
        return None

    @staticmethod
    def min_max(min_val, max_val, field_name, message, page_id="", widget=None):
        """Validate min <= max."""
        if min_val > max_val:
            return ValidationError(field_name, message, page_id, widget)
        return None

    @staticmethod
    def at_least_one(values, field_names, message, page_id="", widget=None):
        """Validate at least one value is provided."""
        if not any(v and str(v).strip() for v in values):
            return ValidationError(field_names[0], message, page_id, widget)
        return None

    @staticmethod
    def selection_required(selection_dict, field_name, message, page_id="", widget=None):
        """Validate at least one item selected."""
        if not any(selection_dict.values()):
            return ValidationError(field_name, message, page_id, widget)
        return None
```

### ValidationManager

```python
class ValidationManager:
    """Manages validation flow and error display."""

    def __init__(self, parent_widget=None):
        self._parent = parent_widget

    def show_error_and_focus(self, error: ValidationError):
        """Show error message and focus on field."""
        QMessageBox.warning(self._parent, "Validation Error", error.message)
        if error.widget:
            error.widget.setFocus()
```

## Page Integration

Each page implements a `validate()` method:

```python
class PageGeneral(BasePage):
    def validate(self) -> Tuple[bool, str]:
        # Required field check
        error = FieldValidator.required(
            self.project_name.text(),
            "project_name",
            "Project name cannot be empty"
        )
        if error:
            return False, error.message

        # Year range check
        error = FieldValidator.min_max(
            self.start_year.value(),
            self.end_year.value(),
            "year",
            "Start year cannot be greater than end year"
        )
        if error:
            return False, error.message

        return True, ""
```

## Error Messages

All validation messages are in English:

| Field | Message |
|-------|---------|
| project_name | Project name cannot be empty |
| basedir | Directory does not exist |
| start_year/end_year | Start year cannot be greater than end year |
| min_lat/max_lat | Invalid latitude range (-90 to 90) |
| min_lon/max_lon | Invalid longitude range (-180 to 180) |
| evaluation_items | Please select at least one evaluation item |
| metrics/scores | Please select at least one metric or score item |

## Testing

Unit tests verify each validator:
- Test with valid values (should return None)
- Test with invalid values (should return ValidationError)
- Test edge cases (boundaries, empty strings, whitespace)

Test file: `tests/test_validation.py`
