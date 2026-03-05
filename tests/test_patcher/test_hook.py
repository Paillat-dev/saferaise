"""Tests for _patcher/_hook.py."""

import importlib
import sys
from pathlib import Path

import pytest

from saferaise import enable
from saferaise._patcher._common import WATCHER_KEY
from saferaise._patcher._hook import _TryCtxFinder, register  # pyright: ignore[reportPrivateUsage]


@pytest.fixture
def _cleanup_meta_path():  # pyright: ignore[reportUnusedFunction]
    original = sys.meta_path.copy()
    yield
    sys.meta_path[:] = original


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestRegister:
    def test_adds_finder_to_meta_path(self):
        before = len(sys.meta_path)
        register("some_root")
        assert len(sys.meta_path) == before + 1
        assert isinstance(sys.meta_path[0], _TryCtxFinder)

    def test_finder_at_position_zero(self):
        register("some_root")
        assert isinstance(sys.meta_path[0], _TryCtxFinder)


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestTryCtxFinder:
    def test_skips_non_matching_modules(self):
        finder = _TryCtxFinder("my_app")
        result = finder.find_spec("other_module", None)
        assert result is None

    def test_matches_root_module(self):
        finder = _TryCtxFinder("my_app")
        result = finder.find_spec("my_app", None)
        assert result is None

    def test_matches_submodule(self):
        finder = _TryCtxFinder("my_app")
        result = finder.find_spec("my_app.sub", None)
        assert result is None

    def test_does_not_match_prefix_collision(self):
        finder = _TryCtxFinder("my_app")
        result = finder.find_spec("my_app_extra", None)
        assert result is None


@pytest.fixture
def sample_package(tmp_path: Path):
    """Create a temporary package that register() can intercept."""
    pkg = tmp_path / "samplepkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text(
        "from saferaise._watched_exceptions import get_exceptions\n"
        + "result = None\n"
        + "try:\n"
        + "    result = get_exceptions()\n"
        + "except ValueError:\n"
        + "    pass\n"
    )
    sys.path.insert(0, str(tmp_path))
    yield "samplepkg.mod"
    sys.path.remove(str(tmp_path))
    sys.modules.pop("samplepkg.mod", None)
    sys.modules.pop("samplepkg", None)


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestRegisterEndToEnd:
    def test_imported_module_has_watcher_key(self, sample_package: str):
        register("samplepkg")
        with enable():
            mod = importlib.import_module(sample_package)
        assert WATCHER_KEY in mod.__dict__

    def test_try_body_sees_watched_exceptions(self, sample_package: str):
        register("samplepkg")
        with enable():
            mod = importlib.import_module(sample_package)
        assert mod.result is not None
        assert ValueError in mod.result
