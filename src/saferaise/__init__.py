"""Safe exception handling through compile-time and runtime validation of raised exceptions."""

from ._decorator import raises
from ._patcher import is_registered, register
from ._watched_exceptions import disable, enable, unsafe

__all__ = ("disable", "enable", "is_registered", "raises", "register", "unsafe")
