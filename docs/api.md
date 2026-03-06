# API Reference

## Top-level API

::: saferaise
    options:
      show_root_heading: false
      members:
        - raises
        - register
        - enable
        - disable
        - unsafe

## Errors

All errors inherit from `SafeRaiseError`, which itself inherits from `BaseException` rather than `Exception`. This is intentional: a bare `except Exception` block should never silently swallow a saferaise violation.

!!! note
    Import error classes directly from `saferaise._errors` or catch them by type - they are raised as `BaseException` subclasses, not `Exception`.

::: saferaise._errors.SafeRaiseError

::: saferaise._errors.UnwatchedRaiseError

::: saferaise._errors.NotEnteredError

::: saferaise._errors.NameCollisionError