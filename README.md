# saferaise

[![Alpha](https://img.shields.io/badge/status-alpha-orange)](https://github.com/Paillat-dev/saferaise)
[![PyPI](https://img.shields.io/pypi/v/saferaise)](https://pypi.org/project/saferaise/)
[![py.typed](https://img.shields.io/badge/typing-py.typed-blue)](https://peps.python.org/pep-0561/)
[![CI](https://github.com/Paillat-dev/saferaise/actions/workflows/CI.yaml/badge.svg)](https://github.com/Paillat-dev/saferaise/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Checked exceptions for Python.** Declare what your functions raise, and let `saferaise` enforce it - using your existing `try/except` blocks.

> \[!CAUTION]
> **Alpha:** The API may change between releases, and using this right now might very well break your code in weird ways, so don't use it in production.

## Installation

```bash
pip install saferaise
```

> Requires Python 3.13+

<!-- quick start -->

## Quick Start

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

`register` must be called **before** importing the package it instruments, and in a **separate file** from the code being instrumented.

## Documentation

Full documentation is available at **[https://paillat.dev/saferaise](https://paillat.dev/saferaise)**

* [How It Works](https://paillat.dev/saferaise/how-it-works/)
* [Advanced Usage](https://paillat.dev/saferaise/advanced/)
* [API Reference](https://paillat.dev/saferaise/api/)

## License

MIT License. See [LICENSE](LICENSE) for details.
