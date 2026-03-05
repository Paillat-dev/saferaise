"""Shared fixtures for patcher tests."""

import importlib
import sys
import types
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest


class PackageBuilder:
    """Builder for creating temporary packages in tmp_path.

    Usage::

        def test_something(make_package):
            pkg = make_package("mypkg")
            pkg.add_module("mod.py", "x = 1")
            pkg.add_module("sub/__init__.py", "")
            pkg.add_module("sub/deep.py", "y = 2")
            pkg.install()

            import mypkg.mod

            assert mypkg.mod.x == 1

    For namespace packages (no __init__.py at root), use ``namespace=True``::

        pkg = make_package("ns_pkg", namespace=True)
        pkg.add_module("inner/__init__.py", "")
        pkg.add_module("inner/mod.py", "x = 1")
    """

    def __init__(self, tmp_path: Path, name: str, *, namespace: bool = False) -> None:
        self._tmp_path: Path = tmp_path
        self._name: str = name
        self._namespace: bool = namespace
        self._pkg_dir: Path = tmp_path / name
        self._pkg_dir.mkdir(parents=True, exist_ok=True)
        self._modules: list[str] = []
        if not namespace:
            (self._pkg_dir / "__init__.py").write_text("")

    @property
    def name(self) -> str:
        return self._name

    @property
    def root(self) -> Path:
        return self._pkg_dir

    def add_module(self, relative_path: str, source: str) -> "PackageBuilder":
        full = self._pkg_dir / relative_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(source)
        module_name = self._name + "." + relative_path.removesuffix(".py").removesuffix("/__init__").replace("/", ".")
        self._modules.append(module_name)
        return self

    def install(self) -> None:
        if str(self._tmp_path) not in sys.path:
            sys.path.insert(0, str(self._tmp_path))

    def import_module(self, relative: str) -> types.ModuleType:
        module_name = self._name + "." + relative.replace("/", ".")
        return importlib.import_module(module_name)

    def cleanup(self) -> None:
        if str(self._tmp_path) in sys.path:
            sys.path.remove(str(self._tmp_path))
        to_remove = [k for k in sys.modules if k == self._name or k.startswith(self._name + ".")]
        for k in to_remove:
            del sys.modules[k]


PackageFactory = Callable[..., PackageBuilder]


@pytest.fixture
def make_package(tmp_path: Path) -> Iterator[PackageFactory]:
    builders: list[PackageBuilder] = []

    def _factory(name: str, *, namespace: bool = False) -> PackageBuilder:
        builder = PackageBuilder(tmp_path, name, namespace=namespace)
        builders.append(builder)
        return builder

    yield _factory

    for b in builders:
        b.cleanup()


@pytest.fixture
def _cleanup_meta_path():  # pyright: ignore[reportUnusedFunction]
    original = sys.meta_path.copy()
    yield
    sys.meta_path[:] = original
