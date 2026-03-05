class SafeRaiseError(BaseException):
    """Base error for all saferaise library errors."""


class UnwatchedRaiseError(SafeRaiseError):
    """A @raises-decorated function declared exceptions not in the current watched set."""

    def __init__(self, func_name: str, declared: tuple[type[BaseException], ...], missing: type[BaseException]) -> None:
        self.func_name: str = func_name
        self.declared: tuple[type[BaseException], ...] = declared
        self.missing: type[BaseException] = missing
        declared_names = ", ".join(e.__name__ for e in declared)
        super().__init__(
            f"Function {func_name} declares raises({declared_names})"
            + f" but {missing.__name__} is not in the current watched set."
            + f" Wrap the call with `unsafe({missing.__name__})` or an appropriate try/except block."
        )


class NotEnteredError(SafeRaiseError):
    """A context manager was exited without being entered."""

    def __init__(self, context_name: str) -> None:
        self.context_name: str = context_name
        super().__init__(f"{context_name} was not entered")


class NameCollisionError(SafeRaiseError):
    """The injected watcher key already exists in a module's namespace."""

    def __init__(self, module_name: str, key: str) -> None:
        self.module_name: str = module_name
        self.key: str = key
        super().__init__(f"Module {module_name} already has {key}, possible name collision")


__all__ = ("NameCollisionError", "NotEnteredError", "SafeRaiseError", "UnwatchedRaiseError")
