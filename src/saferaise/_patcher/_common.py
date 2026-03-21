"""
A module that provides utilities to check and manage saferaise exception
watching registration.

This module contains functionality to determine whether saferaise has been
registered for the current file. It also exposes a constant key used for
registration tracking.
"""

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
