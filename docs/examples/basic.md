# Basic Usage

This guide walks through the core workflow of `saferaise`: registering packages, decorating functions, and handling exceptions.

## Setup

Every project using `saferaise` needs two things:

1. A call to `register()` **before** importing the instrumented package.
2. An `enable()` context to activate checking.

```python
# main.py
import saferaise

saferaise.register("myapp")

import myapp

with saferaise.enable():
    myapp.run()
```

!!! danger "Two-file requirement"
    `register()` must be called in a **separate file** from the code it instruments. The import hook rewrites modules at load time, so the calling module itself is never rewritten.

## Declaring Exceptions with `@raises`

Use the `@raises` decorator to declare what exceptions a function may raise:

```python
# myapp/parser.py
from saferaise import raises

@raises(ValueError)
def parse_int(raw: str) -> int:
    """Parse a string into an integer."""
    return int(raw)

@raises(KeyError, ValueError)
def get_config_value(config: dict, key: str) -> int:
    """Get a config value and parse it as an integer."""
    return int(config[key])
```

## Handling Exceptions

When a registered package uses `try/except`, `saferaise` automatically tracks which exceptions are being handled. No extra code needed:

```python
# myapp/app.py
from myapp.parser import parse_int

def process_input(raw: str) -> int | None:
    try:
        return parse_int(raw)  # OK - ValueError is caught below
    except ValueError:
        print(f"Invalid input: {raw}")
        return None
```

## What Happens Without Handling

If you call a `@raises` function without catching its declared exceptions, you get an `UnwatchedRaiseError`:

```python
# myapp/app.py
from myapp.parser import parse_int

def process_input(raw: str) -> int:
    return parse_int(raw)  # UnwatchedRaiseError!
```

The error message tells you exactly what's missing:

!!! failure "UnwatchedRaiseError"
    ```
    UnwatchedRaiseError: Function parse_int declares raises(ValueError)
    but ValueError is not in the current watched set.
    Wrap the call with `unsafe(ValueError)` or an appropriate try/except block.
    ```

## Subclass Matching

You don't need to catch the exact exception type. Catching a parent class works:

```python
class AppError(Exception): ...
class ValidationError(AppError): ...
class NotFoundError(AppError): ...

@raises(ValidationError)
def validate(data: dict) -> None:
    ...

try:
    validate(data)  # OK - AppError covers ValidationError
except AppError:
    print("Something went wrong")
```

## Multiple Exception Types

Functions can declare multiple exception types, and all of them must be handled:

```python
@raises(ConnectionError, TimeoutError)
def fetch_data(url: str) -> bytes:
    ...

try:
    data = fetch_data("https://example.com")
except ConnectionError:
    print("Connection failed")
except TimeoutError:
    print("Request timed out")
```

Or catch them together:

```python
try:
    data = fetch_data("https://example.com")
except (ConnectionError, TimeoutError):
    print("Network error")
```
