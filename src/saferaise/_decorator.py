import inspect
from collections.abc import Callable
from functools import wraps

from ._errors import UnwatchedRaiseError
from ._watched_exceptions import get_exceptions, watch_exceptions


def _validate_exceptions(func_name: str, exceptions: tuple[type[BaseException], ...]) -> UnwatchedRaiseError | None:
    current = get_exceptions()
    if current is not None:
        for exc in exceptions:
            if not any(issubclass(exc, e) for e in current):
                return UnwatchedRaiseError(func_name, exceptions, exc)
    return None


def raises[T: Callable[..., object]](*exceptions: type[BaseException]) -> Callable[[T], T]:
    """Declare the exceptions a function may raise.

    At runtime, validates that each declared exception is in the current
    watched set (see ``enable``). Adds the declared exceptions to the
    watched set for the duration of the call.

    Args:
        *exceptions: Exception types the decorated function is allowed to raise.

    Returns:
        A decorator that wraps the function with exception validation.

    Raises:
        UnwatchedRaiseError: If a declared exception is not in the watched set.
    """

    def decorator(func: T) -> T:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: object, **kwargs: object) -> object:
                if error := _validate_exceptions(func.__name__, exceptions):
                    raise error.with_traceback(None)
                with watch_exceptions(*exceptions):
                    return await func(*args, **kwargs)

            return async_wrapper  # pyright: ignore[reportReturnType]

        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> object:
            if error := _validate_exceptions(func.__name__, exceptions):
                raise error.with_traceback(None)
            with watch_exceptions(*exceptions):
                return func(*args, **kwargs)

        return wrapper  # pyright: ignore[reportReturnType]

    return decorator


__all__ = ("raises",)
