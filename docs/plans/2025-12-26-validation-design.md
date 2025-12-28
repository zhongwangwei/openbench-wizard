# Validation Design

## Purpose

Design document for the form validation system in OpenBench Wizard.

## Goals

1. Provide immediate feedback on invalid input
2. Prevent navigation to next page with invalid data
3. Clear, actionable error messages in English
4. Focus on first invalid field

## Validation Architecture

### Three Layers

```
┌─────────────────────────────────────────┐
│          Page-Level Validation           │
│   (Called on "Next" button click)        │
├─────────────────────────────────────────┤
│         Field-Level Validation           │
│   (Individual field checks)              │
├─────────────────────────────────────────┤
│           Validation Manager             │
│   (Error display and focus management)   │
└─────────────────────────────────────────┘
```

### Validation Flow

```
User clicks "Next"
        │
        ▼
Page.validate() called
        │
        ▼
Run field validators
        │
    ┌───┴───┐
    │       │
    ▼       ▼
  Pass    Fail
    │       │
    ▼       ▼
Navigate  Show error
to next   Focus field
```

## Design Decisions

### Decision 1: When to Validate

**Options:**
- A) On every keystroke (real-time)
- B) On field blur
- C) On "Next" button click

**Chosen: C** - Less intrusive, better performance

### Decision 2: Error Display

**Options:**
- A) Inline error text
- B) Modal dialog
- C) Status bar message

**Chosen: B** - Modal dialog ensures user sees error

### Decision 3: Multiple Errors

**Options:**
- A) Show all errors at once
- B) Show first error only

**Chosen: B** - Less overwhelming, guides user through fixes

## Validator Methods

All validator methods are static methods on `FieldValidator` class:

```python
FieldValidator.required(value, field_name, message)
FieldValidator.path_exists(path, field_name, message)
FieldValidator.number_range(value, min, max, field_name, message)
FieldValidator.min_max(min_val, max_val, field_name, message)
FieldValidator.at_least_one(values, field_names, message)
FieldValidator.selection_required(dict, field_name, message)
```

All methods return:
- `None` if validation passes
- `ValidationError` if validation fails

## UI Integration

1. Each `BasePage` subclass implements `validate()`
2. `WizardController.next_page()` calls current page's `validate()`
3. If validation fails, `ValidationManager.show_error_and_focus()` is called
4. User corrects error and clicks "Next" again

## File Structure

```
core/
├── validation.py      # ValidationError, FieldValidator, ValidationManager

ui/pages/
├── base_page.py       # validate() method signature
├── page_general.py    # validate() implementation
├── ...

tests/
├── test_validation.py # Unit tests for validators
```
