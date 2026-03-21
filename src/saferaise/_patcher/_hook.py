"""
An import hook for injecting exception-watching logic into specified modules.

This module provides functionality to dynamically rewrite `try/except` blocks
during module imports to track caught exceptions. It is used to enhance runtime
behavior by instrumenting specified package roots.

Classes:
- TryCtxLoader: A loader that injects exception-watching logic into imported
  module code.
- _TryCtxFinder: A meta path finder used to locate and transform modules
  before they are loaded.

Functions:
- register: Installs the import hook for top-level package names, enabling
  exception tracking for all caught exceptions under those packages.
"""

from collections.abc import Sequence
import importlib.abc
import importlib.machinery
from pathlib import Path
import sys
import types
from typing import override

from saferaise._errors import NameCollisionError
from saferaise._watched_exceptions import watch_exceptions

from ._common import WATCHER_KEY
from ._parser import transform_source


class TryCtxLoader(importlib.abc.Loader):
    """
    Loader that injects exception-watching logic into imported module code.
    """

    def __init__(self, source_path: str) -> None:
        self._source_path: str = source_path

    @override
    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:  # noqa: U100
        """
        Creates a module for the given spec.

        Args:
            spec: The module specification.
        """
        return

    @override
    def exec_module(self, module: types.ModuleType) -> None:
        """
        Executes the module with exception-watching logic injected.

        Args:
            module: The module to be executed.
        """
        source = Path(self._source_path).read_text(encoding="utf-8")
        if WATCHER_KEY in module.__dict__:
            raise NameCollisionError(module.__name__, WATCHER_KEY)

        module.__dict__[WATCHER_KEY] = watch_exceptions
        code = transform_source(source, self._source_path)
        exec(code, module.__dict__)  # pylint: disable=exec-used


class _TryCtxFinder(importlib.abc.MetaPathFinder):
    def __init__(self, *roots: str) -> None:
        self._roots: tuple[str, ...] = roots

    @override
    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        """
        Finds the module spec for the given module name and path.

        If the module name is in the list of roots, it is transformed into a
        module loader that injects exception watching logic into try blocks.

        Args:
            fullname: The fully qualified name of the module.
            path: The path to search for the module.
            target: The target module to load.

        Returns:
            The module spec with injected exception watching logic, or None if
            the module is not in the roots list.
        """
        if not any(fullname == r or fullname.startswith(r + ".") for r in self._roots):
            return None

        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or spec.origin is None:
            return None

        spec.loader = TryCtxLoader(str(spec.origin))
        return spec


def register(*roots: str) -> None:
    """Install the import hook for the given package roots.

    Must be called **before** importing the packages you want to instrument,
    and in a separate file from those packages. The hook rewrites every
    ``try/except`` block at import time so that caught exception types are
    automatically added to the watched set.

    Args:
        *roots: Top-level package names to instrument (e.g. ``"myapp"``).

    Example:
        ```python
        import saferaise

        saferaise.register("myapp")  # must come before `import myapp`

        import myapp

        with saferaise.enable():
            myapp.run()
        ```

    Raises:
        NameCollisionError: If an instrumented module already has an attribute
            named ``_saferaise_watch_exceptions``.
    """
    sys.meta_path.insert(0, _TryCtxFinder(*roots))
