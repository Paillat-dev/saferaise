"""Tests for _patcher/_hook.py."""

import sys

import pytest

from saferaise import enable
from saferaise._patcher._common import WATCHER_KEY
from saferaise._patcher._hook import _TryCtxFinder, register  # pyright: ignore[reportPrivateUsage]

from .conftest import PackageFactory


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


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestRegisterEndToEnd:
    def test_imported_module_has_watcher_key(self, make_package: PackageFactory) -> None:
        pkg = make_package("samplepkg")
        pkg.add_module(
            "mod.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except ValueError:\n"
            + "    pass\n",
        )
        pkg.install()
        register("samplepkg")
        with enable():
            mod = pkg.import_module("mod")
        assert WATCHER_KEY in mod.__dict__

    def test_try_body_sees_watched_exceptions(self, make_package: PackageFactory) -> None:
        pkg = make_package("samplepkg")
        pkg.add_module(
            "mod.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except ValueError:\n"
            + "    pass\n",
        )
        pkg.install()
        register("samplepkg")
        with enable():
            mod = pkg.import_module("mod")
        assert mod.result is not None
        assert ValueError in mod.result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestIsRegistered:
    def test_returns_true_in_instrumented_module(self, make_package: PackageFactory) -> None:
        pkg = make_package("is_reg_pkg")
        pkg.add_module(
            "mod.py",
            "from saferaise import is_registered\nresult = is_registered()\n",
        )
        pkg.install()
        register("is_reg_pkg")
        mod = pkg.import_module("mod")
        assert mod.result is True

    def test_returns_false_in_non_instrumented_module(self, make_package: PackageFactory) -> None:
        pkg = make_package("is_reg_pkg2")
        pkg.add_module(
            "mod.py",
            "from saferaise import is_registered\nresult = is_registered()\n",
        )
        pkg.install()
        # register() is NOT called - module is not instrumented
        mod = pkg.import_module("mod")
        assert mod.result is False

    def test_returns_true_in_subpackage_module(self, make_package: PackageFactory) -> None:
        pkg = make_package("is_reg_pkg3")
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/auth.py",
            "from saferaise import is_registered\nresult = is_registered()\n",
        )
        pkg.install()
        register("is_reg_pkg3")
        mod = pkg.import_module("services.auth")
        assert mod.result is True

    def test_returns_false_for_unregistered_root_even_if_sibling_registered(self, make_package: PackageFactory) -> None:
        pkg_a = make_package("is_reg_pkg4a")
        pkg_a.add_module(
            "mod.py",
            "from saferaise import is_registered\nresult = is_registered()\n",
        )
        pkg_a.install()

        pkg_b = make_package("is_reg_pkg4b")
        pkg_b.add_module(
            "mod.py",
            "from saferaise import is_registered\nresult = is_registered()\n",
        )
        pkg_b.install()

        register("is_reg_pkg4a")  # only register pkg_a

        mod_a = pkg_a.import_module("mod")
        mod_b = pkg_b.import_module("mod")
        assert mod_a.result is True
        assert mod_b.result is False
