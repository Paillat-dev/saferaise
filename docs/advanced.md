# Advanced Usage

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

!!! warning "`unsafe()` is a last resort"
    `unsafe()` is intentionally named to signal that you are bypassing the normal flow. Prefer `try/except` with `register()` for all application code; reach for `unsafe()` only at bootstrapping boundaries where a `try/except` would be artificial.

!!! info "`disable()` vs `unsafe(BaseException)`"
    These are not the same. `unsafe(BaseException)` satisfies the check - it marks all exceptions as handled. `disable()` *skips* the check entirely inside `@raises`, regardless of what is in the watched set. Use `disable()` when you want the instrumentation to remain in place but the enforcement to be inactive (e.g., in a production hot path, or temporarily during migration).
