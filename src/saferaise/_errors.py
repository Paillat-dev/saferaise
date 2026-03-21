"""A module defining custom exceptions related to the saferaise library.

This module provides base and specialized exception classes for handling
errors in the saferaise library, including issues related to unwatched
raises, context management, and name collisions.

Classes:
    SafeRaiseError: Base exception for all saferaise library errors.
    UnwatchedRaiseError: Raised when declared exceptions are not in the watched set.
    NotEnteredError: Raised when a context manager is exited without being entered.
    NameCollisionError: Raised when a name collision occurs in a module's namespace.
"""

from typing import override


class SafeRaiseError(BaseException):
    """Base error for all saferaise library errors."""


class UnwatchedRaiseError(SafeRaiseError):
    """A @raises-decorated function declared exceptions not in the current watched set.

    Attrs:
        func_name: The name of the function that declared the missing exception.
        declared: The tuple of exceptions declared by the function.
        missing: The exception not in the current watched set.
    """

    def __init__(self, func_name: str, declared: tuple[type[BaseException], ...], missing: type[BaseException]) -> None:
        self.func_name: str = func_name
        self.declared: tuple[type[BaseException], ...] = declared
        self.missing: type[BaseException] = missing
        super().__init__(func_name, declared, missing)

    @override
    def __str__(self) -> str:
        """Return a human-readable error message."""
        declared_names = ", ".join(e.__name__ for e in self.declared)
        return (
            f"Function {self.func_name} declares raises({declared_names})"
            + f" but {self.missing.__name__} is not in the current watched set."
            + f" Wrap the call with `unsafe({self.missing.__name__})` or an appropriate try/except block."
        )


class NotEnteredError(SafeRaiseError):
    """A context manager was exited without being entered.

    Attrs:
        context_name: The name of the context manager that was not entered.
    """

    @override
    def __init__(self, context_name: str) -> None:
        self.context_name: str = context_name
        super().__init__(context_name)

    @override
    def __str__(self) -> str:
        """Return a human-readable error message."""
        return f"{self.context_name} was not entered"


class NameCollisionError(SafeRaiseError):
    """The injected watcher key already exists in a module's namespace.

    Attrs:
        module_name: The name of the module where the collision occurred.
        key: The name of the key that caused the collision.
    """

    def __init__(self, module_name: str, key: str) -> None:
        self.module_name: str = module_name
        self.key: str = key
        super().__init__(module_name, key)

    @override
    def __str__(self) -> str:
        """Return a human-readable error message."""
        return f"Module {self.module_name} already has {self.key}, possible name collision"


__all__ = ("NameCollisionError", "NotEnteredError", "SafeRaiseError", "UnwatchedRaiseError")
