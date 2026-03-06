# Testing

`saferaise` is designed to be used as a validation tool during development and testing. This guide shows patterns for integrating it into your test suite.

## Pytest Fixtures

Create a fixture that enables exception watching for all tests:

```python
# conftest.py
import pytest
import saferaise

saferaise.register("myapp")

@pytest.fixture(autouse=True)
def _enable_saferaise():
    with saferaise.enable():
        yield
```

With this fixture, every test automatically validates that `@raises`-decorated functions have their exceptions properly handled.

!!! tip
    Place `saferaise.register("myapp")` at the top of `conftest.py` - it only needs to be called once, before any test imports your package.

## Testing That Exceptions Are Raised

Use standard pytest patterns - `saferaise` doesn't change how exceptions work, it only validates that they're declared and handled:

```python
# myapp/parser.py
from saferaise import raises

@raises(ValueError)
def parse_int(raw: str) -> int:
    return int(raw)
```

```python
# tests/test_parser.py
import pytest
from saferaise import unsafe
from myapp.parser import parse_int

def test_parse_valid():
    try:
        result = parse_int("42")
    except ValueError:
        pytest.fail("Should not raise")
    assert result == 42

def test_parse_invalid():
    with pytest.raises(ValueError):
        with unsafe(ValueError):  # tell saferaise we're intentionally handling this
            parse_int("abc")
```

## Using `unsafe` in Tests

!!! note
    When testing that a function raises an exception, you need `unsafe()` to tell `saferaise` that you're intentionally handling the exception:

```python
def test_connection_error():
    with unsafe(ConnectionError):
        with pytest.raises(ConnectionError):
            fetch_data("https://invalid.example.com")
```

## Using `disable` in Tests

If you want to temporarily skip all `saferaise` validation in a specific test:

```python
from saferaise import disable

def test_without_validation():
    with disable():
        # No @raises validation happens here
        result = parse_int("42")
        assert result == 42
```

## Async Tests

Works the same way with `pytest-asyncio`:

```python
# conftest.py
import pytest
import saferaise

saferaise.register("myapp")

@pytest.fixture(autouse=True)
def _enable_saferaise():
    with saferaise.enable():
        yield
```

```python
# tests/test_client.py
import pytest
from saferaise import unsafe
from myapp.client import fetch

@pytest.mark.asyncio
async def test_fetch():
    try:
        data = await fetch("https://example.com")
    except (ConnectionError, TimeoutError):
        pytest.skip("Network unavailable")
    assert len(data) > 0
```
