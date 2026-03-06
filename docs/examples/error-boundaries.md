# Error Boundaries

Error boundaries are the top-level points in your application where you catch and handle all exceptions. This guide shows how to use `saferaise` at these boundaries.

## Application Entry Point

The most common error boundary is your application's entry point:

```python
# main.py
import saferaise

saferaise.register("myapp")

import myapp

def main():
    with saferaise.enable():
        try:
            myapp.run()
        except Exception:
            print("Fatal error")
            raise

if __name__ == "__main__":
    main()
```

## Web Framework Middleware

For web frameworks, you typically wrap the request handler:

```python
# entrypoint.py
import saferaise

saferaise.register("myapp")

from myapp.app import create_app

app = create_app()
```

```python
# myapp/middleware.py
from saferaise import enable

class SafeRaiseMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        with enable():
            try:
                await self.app(scope, receive, send)
            except Exception:
                # your error handling here
                raise
```

## Manual Exception Watching with `unsafe`

!!! warning "Use `unsafe()` sparingly"
    `unsafe()` bypasses the normal try/except flow. Only use it at bootstrapping boundaries where a `try/except` would be artificial.

At boundaries where you know certain exceptions will be handled but there's no natural `try/except`, use `unsafe()`:

```python
from saferaise import enable, unsafe, raises

@raises(ValueError)
def parse_config(path: str) -> dict:
    ...

def bootstrap():
    """Bootstrap the application. Crashes are acceptable here."""
    with enable():
        with unsafe(ValueError):
            # We accept that ValueError might crash the process during bootstrap
            config = parse_config("config.yaml")
    return config
```

## Layered Error Handling

In larger applications, you might have multiple layers of error boundaries:

```python
from saferaise import raises

class DatabaseError(Exception): ...
class NotFoundError(DatabaseError): ...
class ConnectionLostError(DatabaseError): ...

@raises(NotFoundError, ConnectionLostError)
def get_user(user_id: int) -> dict:
    ...

@raises(ConnectionLostError)
def get_user_or_none(user_id: int) -> dict | None:
    """Wraps get_user, handling NotFoundError but propagating ConnectionLostError."""
    try:
        return get_user(user_id)
    except NotFoundError:
        return None

def handle_request(user_id: int) -> str:
    """Top-level handler that catches everything."""
    try:
        user = get_user_or_none(user_id)
        if user is None:
            return "User not found"
        return f"Hello, {user['name']}"
    except ConnectionLostError:
        return "Database unavailable"
```

!!! example "How `@raises` composes"
    Each layer declares only the exceptions it doesn't handle. `saferaise` verifies the chain at runtime, ensuring no exception escapes without a handler.

## Disabling in Production

!!! tip
    Use `saferaise` for full validation in dev/test, and `disable()` to skip checks in production hot paths without removing instrumentation.

```python
import os
import saferaise

saferaise.register("myapp")

import myapp

def main():
    ctx = saferaise.enable if os.getenv("ENV") != "production" else saferaise.disable
    with ctx():
        myapp.run()
```
