# saferaise

[![Alpha](https://img.shields.io/badge/status-alpha-orange)](https://github.com/Paillat-dev/saferaise)
[![PyPI](https://img.shields.io/pypi/v/saferaise)](https://pypi.org/project/saferaise/)
[![py.typed](https://img.shields.io/badge/typing-py.typed-blue)](https://peps.python.org/pep-0561/)
[![CI](https://github.com/Paillat-dev/saferaise/actions/workflows/CI.yaml/badge.svg)](https://github.com/Paillat-dev/saferaise/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Checked exceptions for Python.** Declare what your functions raise, and let `saferaise` enforce it - using your existing `try/except` blocks.

Python's exception system is powerful but unstructured: any function can raise anything, anywhere. `saferaise` brings discipline to error handling. Decorate functions with `@raises`, register your packages, and every `try/except` automatically tells saferaise which exceptions are being handled. No boilerplate, no wrappers - just your normal Python code, now validated.

`saferaise` is designed to complement static analysis tools, not replace them. Use it alongside type checkers (basedpyright, mypy) for static guarantees, and alongside linter rules like [`RET506`](https://docs.astral.sh/ruff/rules/docstring-missing-exception/) for documentation coverage. `saferaise` adds the **runtime enforcement layer** - catching what static tools can't, such as a `@raises` function being called outside any handling context.

> \[!CAUTION]
> **Alpha:** The API may change between releases, and using this right now might very well break your code in weird ways, so don't use it in production.

## Contents

* [Installation](#installation)
* [Quick Start](#quick-start)
* [Preamble](#preamble)
* [How It Works](#how-it-works)
  * [1. The Import Hook (`register`)](#1-the-import-hook-register)
  * [2. The `@raises` Decorator](#2-the-raises-decorator)
  * [Subclass Handling](#subclass-handling)
* [Performance](#performance)
* [Advanced Usage](#advanced-usage)
* [Full API Reference](#full-api-reference)
* [Errors](#errors)
* [Development](#development)
* [Built With](#built-with)
* [License](#license)

## Installation

```bash
pip install saferaise
```

> Requires Python 3.13+

<!-- quick start -->

## Quick Start

`register` must be called **before** a package is imported - and in a separate file from the code being instrumented. This is a hard requirement: the import hook only rewrites modules at load time, so any module imported before `register` is called will not be instrumented.

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

## Preamble

This project was *not* particularly inspired by [returns](https://github.com/dry-python/returns), but I'd like to note that it was after reading its README at 2am that I came up with the idea for saferaise. It was a lot of fun to build, and I learned a lot about Python's import system and AST manipulation.

Whether runtime-enforced checked exceptions are actually a good idea for Python is an open question - I have my own thoughts, and I'd love to hear yours. Feel free to open a discussion on GitHub.

## How It Works

`saferaise` has two complementary mechanisms:

### 1. The Import Hook (`register`)

When you call `saferaise.register("mypackage")`, an import hook rewrites every `try/except` block in that package at load time. The body of each `try` is wrapped so the caught exception types are added to the **watched set** - the set of exceptions that `@raises` validates against.

This means your existing `try/except` blocks are all you need. No special syntax, no manual annotation of call sites.

```python
saferaise.register("myapp")

# In myapp/service.py, this try/except:
try:
    result = do_something()  # if do_something() is @raises(KeyError), it just works
except KeyError:
    handle_missing_key()
```

`register` requires no cleanup and has no scope - it instruments the named package for the lifetime of the process. `enable()` is separate because it *does* have scope: it activates checking for a specific portion of code, and cleans up after itself. You can and should call `enable()` tightly around the code you want to validate.

### 2. The `@raises` Decorator

Decorates a function to declare its exceptions. When called inside an active watching context, it validates that every declared exception is in the watched set (i.e., someone upstream has a `try/except` for it).

```python
@raises(ConnectionError, TimeoutError)
async def fetch(url: str) -> bytes:
    ...
```

Works with both sync and async functions. The watched set is tracked via `contextvars`, so concurrent async tasks are fully isolated. For **threads**, `enable()` must be called within each thread - `contextvars` give each thread its own context, so a parent thread's watched set is not inherited.

### Subclass Handling

Exception subclasses are accepted when a parent is watched:

```python
class AppError(Exception): ...
class NotFoundError(AppError): ...

try:
    find_user(42)  # @raises(NotFoundError) - OK, AppError covers it
except AppError:
    ...
```

## Performance

AST rewriting happens **at import time only**, and only for packages explicitly passed to `register`. There is no per-call overhead from instrumentation.

The runtime check inside `@raises` is fail-fast: it iterates over the function's declared exceptions and checks each against the current watched set. This is O(N\*M) in the worst case, where N is the number of exceptions declared by `@raises` and M is the size of the current watched set - but it exits on the first unhandled exception found. In practice, both N and M are small and the overhead is negligible.

If you are in a context where even this is a concern, `disable()` reduces the check to O(1) by bypassing it entirely. This means `saferaise` can be used at **test time and dev time** for full validation, and selectively disabled in hot paths at runtime if needed - the instrumentation stays in place, only the check is skipped.

## Advanced Usage

For cases where you need to manage the watched set manually - entry points, test harnesses, or calling into third-party code - you can use the low-level context managers directly.

| Symbol         | Type            | Description                                   |
| -------------- | --------------- | --------------------------------------------- |
| `enable()`     | Context manager | Activate exception watching with an empty set |
| `disable()`    | Context manager | Bypass all `@raises` checks completely        |
| `unsafe(*exc)` | Context manager | Add exceptions to the watched set manually    |

```python
from saferaise import enable, unsafe, raises

@raises(ValueError)
def parse(raw: str) -> int:
    return int(raw)

with enable():
    with unsafe(ValueError):
        parse("abc")  # OK - ValueError is manually added to the watched set
```

**`unsafe()`** is intentionally named to signal that you are bypassing the normal flow. Prefer `try/except` with `register()` for all application code; reach for `unsafe()` only at bootstrapping boundaries where a `try/except` would be artificial.

**`disable()`** is distinct from `unsafe(BaseException)`. `unsafe(BaseException)` satisfies the check - it marks all exceptions as handled. `disable()` *skips* the check entirely inside `@raises`, regardless of what is in the watched set. Use `disable()` when you want the instrumentation to remain in place but the enforcement to be inactive (e.g., in a production hot path, or temporarily during migration).

## Full API Reference

| Symbol             | Type            | Description                                     |
| ------------------ | --------------- | ----------------------------------------------- |
| `@raises(*exc)`    | Decorator       | Declare exceptions a function may raise         |
| `register(*roots)` | Function        | Install the import hook for given package roots |
| `enable()`         | Context manager | Activate exception watching (empty set)         |
| `disable()`        | Context manager | Bypass all `@raises` checks                     |
| `unsafe(*exc)`     | Context manager | Add exceptions to the watched set               |

## Errors

All errors inherit from `SafeRaiseError`, which itself inherits from `BaseException` rather than `Exception`. This is intentional: a bare `except Exception` block should never silently swallow a saferaise violation.

| Error                 | When                                                                                                      |
| --------------------- | --------------------------------------------------------------------------------------------------------- |
| `UnwatchedRaiseError` | A `@raises` function declares an exception not in the watched set                                         |
| `NotEnteredError`     | A context manager was exited without being entered                                                        |
| `NameCollisionError`  | The import hook's injected name `_saferaise_watch_exceptions` conflicts with an existing module attribute |

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run tox

# Type checking
uv run basedpyright

# Linting
uv run ruff check # Optiobally add --fix

# Formatting
uv run ruff format
```

## Built With

* [basedpyright](https://github.com/DetachHead/basedpyright)
* [ruff](https://github.com/astral-sh/ruff)
* [tox](https://github.com/tox-dev/tox)
* [uv](https://github.com/astral-sh/uv)
* [remark](https://github.com/remarkjs/remark)
* Love :blue\_heart:

## License

MIT License. See [LICENSE](LICENSE) for details.
