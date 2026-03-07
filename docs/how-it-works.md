# How It Works

`saferaise` has two complementary mechanisms:

## The Import Hook (`register`)

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

!!! note
    `register` requires no cleanup and has no scope - it instruments the named package for the lifetime of the process. `enable()` is separate because it *does* have scope: it activates checking for a specific portion of code, and cleans up after itself.

## The `@raises` Decorator

Decorates a function to declare its exceptions. When called inside an active watching context, it validates that every declared exception is in the watched set (i.e., someone upstream has a `try/except` for it).

```python
@raises(ConnectionError, TimeoutError)
async def fetch(url: str) -> bytes:
    ...
```

Works with both sync and async functions. The watched set is tracked via `contextvars`, so concurrent async tasks are fully isolated.

!!! warning "Threads"
    For **threads**, `enable()` must be called within each thread - `contextvars` give each thread its own context, so a parent thread's watched set is not inherited.

## Subclass Handling

Exception subclasses are accepted when a parent is watched:

```python
class AppError(Exception): ...
class NotFoundError(AppError): ...

try:
    find_user(42)  # @raises(NotFoundError) - OK, AppError covers it
except AppError:
    ...
```

## Checking Instrumentation with `is_registered`

Inside an instrumented module, you can call `is_registered()` to check at runtime whether the current module has been processed by the import hook:

```python
# myapp/services/auth.py
from saferaise import is_registered

if is_registered():
    print("saferaise is active for this module")
```

This is useful for conditional debug output or assertions:

```python
from saferaise import is_registered, raises

assert is_registered(), "This module must be loaded via saferaise.register()"

@raises(PermissionError)
def check_access(user_id: int) -> None:
    ...
```

`is_registered()` inspects the caller's globals for the injected watcher key, so it works correctly across relative imports and subpackages — any module loaded through the hook will return `True`.

!!! note
    `is_registered()` reflects whether the **calling module** was instrumented, not whether a watching context is currently active. Use `enable()` to activate enforcement; `is_registered()` only tells you the hook was applied at import time.

## Performance

AST rewriting happens **at import time only**, and only for packages explicitly passed to `register`. There is no per-call overhead from instrumentation.

The runtime check inside `@raises` is fail-fast: it iterates over the function's declared exceptions and checks each against the current watched set. This is O(N*M) in the worst case, where N is the number of exceptions declared by `@raises` and M is the size of the current watched set - but it exits on the first unhandled exception found. In practice, both N and M are small and the overhead is negligible.

!!! tip "Zero overhead in production"
    If you are in a context where even this is a concern, `disable()` reduces the check to O(1) by bypassing it entirely. This means `saferaise` can be used at test time and dev time for full validation, and selectively disabled in hot paths at runtime if needed.
