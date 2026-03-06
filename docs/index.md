# saferaise

**Checked exceptions for Python.** Declare what your functions raise, and let `saferaise` enforce it - using your existing `try/except` blocks.

Python's exception system is powerful but unstructured: any function can raise anything, anywhere. `saferaise` brings discipline to error handling. Decorate functions with `@raises`, register your packages, and every `try/except` automatically tells saferaise which exceptions are being handled. No boilerplate, no wrappers - just your normal Python code, now validated.

!!! warning
    **Alpha:** The API may change between releases, and using this right now might very well break your code in weird ways, so don't use it in production.

## Installation

```bash
pip install saferaise
```

Requires Python 3.13+.

## Quick Start

!!! tip "Two-file rule"
    `register` must be called **before** a package is imported - and in a **separate file** from the code being instrumented. The import hook only rewrites modules at load time, so any module imported before `register` is called will not be instrumented.

```python
# entrypoint.py
import saferaise

saferaise.register("app")   # instrument app's try/except blocks before importing it

import app
with saferaise.enable():    # activate checking for this scope
    app.main()
```

```python
# app.py
from saferaise import raises

@raises(ValueError)
def parse_input(raw: str) -> int:
    return int(raw)

def main():
    try:
        parse_input("abc")  # ValueError is caught here - @raises is satisfied
    except ValueError:
        print("bad input")
```

If `parse_input` is called outside a `try/except` that catches `ValueError`:

```python
def main():
    parse_input("abc")  # UnwatchedRaiseError - nobody is catching ValueError
```
