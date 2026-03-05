from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

from ._errors import NotEnteredError

_watched_exceptions: ContextVar[frozenset[type[BaseException]] | None] = ContextVar(
    "_watched_exceptions",
    default=None,
)


def _add_exceptions(*exceptions: type[BaseException]) -> Token[frozenset[type[BaseException]] | None]:
    if (current := _watched_exceptions.get()) is not None:
        token = _watched_exceptions.set(current | frozenset(exceptions))
    else:
        token = _watched_exceptions.set(None)
    return token


def get_exceptions() -> frozenset[type[BaseException]] | None:
    return _watched_exceptions.get()


def _reset_exceptions(token: Token[frozenset[type[BaseException]] | None]) -> None:
    _watched_exceptions.reset(token)


class watch_exceptions:  # noqa: N801
    def __init__(self, *exceptions: type[BaseException]) -> None:
        self._exceptions: tuple[type[BaseException], ...] = exceptions
        self._token: Token[frozenset[type[BaseException]] | None] | None = None

    def __enter__(self) -> None:
        self._token = _add_exceptions(*self._exceptions)

    def __exit__(self, *_: object) -> None:
        if self._token is None:
            raise NotEnteredError(self.__class__.__qualname__)
        _reset_exceptions(self._token)


@contextmanager
def enable() -> Iterator[None]:
    """Enable exception watching with an empty watched set.

    Inside this context, any ``@raises``-decorated function will validate that
    its declared exceptions are being watched.

    Yields:
        None
    """
    token = _watched_exceptions.set(frozenset())
    try:
        yield
    finally:
        _watched_exceptions.reset(token)


@contextmanager
def disable() -> Iterator[None]:
    """Temporarily disable exception watching.

    Inside this context, ``@raises`` validation is skipped entirely,
    regardless of any outer ``enable`` or ``watch_exceptions`` context.

    Yields:
        None
    """
    token = _watched_exceptions.set(None)
    try:
        yield
    finally:
        _watched_exceptions.reset(token)


@contextmanager
def unsafe(*exceptions: type[BaseException]) -> Iterator[None]:
    """Add exceptions to the watched set without validating callers.

    Useful for code that needs to handle exceptions not declared by its
    own ``@raises`` decorator, such as top-level error boundaries.

    Args:
        *exceptions: Exception types to add to the watched set.

    Yields:
        None
    """
    token = _add_exceptions(*exceptions)
    try:
        yield
    finally:
        _reset_exceptions(token)


__all__ = ("disable", "enable", "get_exceptions", "unsafe", "watch_exceptions")
