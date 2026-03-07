import inspect

WATCHER_KEY: str = "_saferaise_watch_exceptions"


def is_registered() -> bool:
    """Check if saferaise is registered for the current file.

    Returns:
        bool: True if saferaise is registered, False otherwise.
    """
    if (frame := inspect.currentframe()) and (prev_frame := frame.f_back):
        return WATCHER_KEY in prev_frame.f_globals
    return False


__all__ = ("WATCHER_KEY", "is_registered")
