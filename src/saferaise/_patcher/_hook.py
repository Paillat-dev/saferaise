import importlib.abc
import importlib.machinery
import sys
import types
from collections.abc import Sequence
from pathlib import Path
from typing import override

from saferaise._errors import NameCollisionError
from saferaise._watched_exceptions import watch_exceptions

from ._common import WATCHER_KEY
from ._parser import transform_source


class TryCtxLoader(importlib.abc.Loader):
    def __init__(self, source_path: str) -> None:
        self._source_path: str = source_path

    @override
    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:
        return None

    @override
    def exec_module(self, module: types.ModuleType) -> None:
        source = Path(self._source_path).read_text()
        if WATCHER_KEY in module.__dict__:
            raise NameCollisionError(module.__name__, WATCHER_KEY)

        module.__dict__[WATCHER_KEY] = watch_exceptions
        code = transform_source(source, self._source_path)
        exec(code, module.__dict__)  # noqa: S102


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
