"""
Module providing utility functions for checking and registering components.

This module contains functionality to determine whether a component is
registered and to register new components using pre-defined hooks. Only the
`is_registered` and `register` functions are publicly accessible and
serve as entry points for external code.

Exported functions:
- is_registered
- register
"""

from ._common import is_registered
from ._hook import register

__all__ = ("is_registered", "register")
