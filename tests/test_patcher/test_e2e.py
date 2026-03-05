"""End-to-end tests for the import hook patcher with various package layouts."""

import pytest

from saferaise import enable, register, unsafe
from saferaise._errors import UnwatchedRaiseError
from saferaise._patcher._common import WATCHER_KEY

from .conftest import PackageFactory

TRY_MODULE = (
    "from saferaise._watched_exceptions import get_exceptions\n"
    "result = None\n"
    "try:\n"
    "    result = get_exceptions()\n"
    "except {exc}:\n"
    "    pass\n"
)


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestRegularPackage:
    def test_root_module(self, make_package: PackageFactory) -> None:
        pkg = make_package("regpkg")
        pkg.add_module("mod.py", TRY_MODULE.format(exc="ValueError"))
        pkg.install()
        register("regpkg")
        with enable():
            mod = pkg.import_module("mod")
        assert mod.result is not None
        assert ValueError in mod.result

    def test_subpackage_module(self, make_package: PackageFactory) -> None:
        pkg = make_package("regpkg2")
        pkg.add_module("sub/__init__.py", "")
        pkg.add_module("sub/deep.py", TRY_MODULE.format(exc="TypeError"))
        pkg.install()
        register("regpkg2")
        with enable():
            mod = pkg.import_module("sub.deep")
        assert mod.result is not None
        assert TypeError in mod.result

    def test_deeply_nested_subpackage(self, make_package: PackageFactory) -> None:
        pkg = make_package("regpkg3")
        pkg.add_module("a/__init__.py", "")
        pkg.add_module("a/b/__init__.py", "")
        pkg.add_module("a/b/c.py", TRY_MODULE.format(exc="KeyError"))
        pkg.install()
        register("regpkg3")
        with enable():
            mod = pkg.import_module("a.b.c")
        assert mod.result is not None
        assert KeyError in mod.result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestNamespacePackage:
    """Namespace packages have no __init__.py at the root level."""

    def test_namespace_inner_module(self, make_package: PackageFactory) -> None:
        pkg = make_package("nspkg", namespace=True)
        pkg.add_module("inner/__init__.py", "")
        pkg.add_module("inner/mod.py", TRY_MODULE.format(exc="KeyError"))
        pkg.install()
        register("nspkg")
        with enable():
            mod = pkg.import_module("inner.mod")
        assert mod.result is not None
        assert KeyError in mod.result

    def test_namespace_nested_subpackages(self, make_package: PackageFactory) -> None:
        pkg = make_package("nspkg2", namespace=True)
        pkg.add_module("sub/__init__.py", "")
        pkg.add_module("sub/inner/__init__.py", "")
        pkg.add_module("sub/inner/mod.py", TRY_MODULE.format(exc="RuntimeError"))
        pkg.install()
        register("nspkg2")
        with enable():
            mod = pkg.import_module("sub.inner.mod")
        assert mod.result is not None
        assert RuntimeError in mod.result

    def test_namespace_multiple_inner_packages(self, make_package: PackageFactory) -> None:
        pkg = make_package("nspkg3", namespace=True)
        pkg.add_module("alpha/__init__.py", "")
        pkg.add_module("alpha/mod.py", TRY_MODULE.format(exc="ValueError"))
        pkg.add_module("beta/__init__.py", "")
        pkg.add_module("beta/mod.py", TRY_MODULE.format(exc="TypeError"))
        pkg.install()
        register("nspkg3")
        with enable():
            alpha = pkg.import_module("alpha.mod")
            beta = pkg.import_module("beta.mod")
        assert alpha.result is not None
        assert ValueError in alpha.result
        assert beta.result is not None
        assert TypeError in beta.result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestMultipleExceptHandlers:
    def test_tuple_except(self, make_package: PackageFactory) -> None:
        pkg = make_package("multiexc")
        pkg.add_module(
            "mod.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except (ValueError, TypeError):\n"
            + "    pass\n",
        )
        pkg.install()
        register("multiexc")
        with enable():
            mod = pkg.import_module("mod")
        assert mod.result is not None
        assert ValueError in mod.result
        assert TypeError in mod.result

    def test_multiple_except_clauses(self, make_package: PackageFactory) -> None:
        pkg = make_package("multiexc2")
        pkg.add_module(
            "mod.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except ValueError:\n"
            + "    pass\n"
            + "except KeyError:\n"
            + "    pass\n",
        )
        pkg.install()
        register("multiexc2")
        with enable():
            mod = pkg.import_module("mod")
        assert mod.result is not None
        assert ValueError in mod.result
        assert KeyError in mod.result

    def test_bare_except(self, make_package: PackageFactory) -> None:
        pkg = make_package("bareexc")
        pkg.add_module(
            "mod.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except:\n"
            + "    pass\n",
        )
        pkg.install()
        register("bareexc")
        with enable():
            mod = pkg.import_module("mod")
        assert mod.result is not None
        assert BaseException in mod.result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestNestedTry:
    def test_nested_try_blocks(self, make_package: PackageFactory) -> None:
        pkg = make_package("nestedtry")
        pkg.add_module(
            "mod.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "outer_result = None\n"
            + "inner_result = None\n"
            + "try:\n"
            + "    outer_result = get_exceptions()\n"
            + "    try:\n"
            + "        inner_result = get_exceptions()\n"
            + "    except TypeError:\n"
            + "        pass\n"
            + "except ValueError:\n"
            + "    pass\n",
        )
        pkg.install()
        register("nestedtry")
        with enable():
            mod = pkg.import_module("mod")
        assert mod.outer_result is not None
        assert mod.inner_result is not None
        assert ValueError in mod.outer_result
        assert TypeError in mod.inner_result
        assert ValueError in mod.inner_result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestDecoratorWithHook:
    """Tests combining @raises decorator with the import hook."""

    def test_raises_and_hook_together(self, make_package: PackageFactory) -> None:
        pkg = make_package("decpkg")
        pkg.add_module(
            "mod.py",
            "from saferaise import raises\n"
            + "from saferaise._watched_exceptions import get_exceptions\n"
            + "\n"
            + "@raises(ValueError)\n"
            + "def fn():\n"
            + "    result = None\n"
            + "    try:\n"
            + "        result = get_exceptions()\n"
            + "    except TypeError:\n"
            + "        pass\n"
            + "    return result\n",
        )
        pkg.install()
        register("decpkg")
        with enable():
            mod = pkg.import_module("mod")
            with unsafe(ValueError):
                result = mod.fn()
        assert result is not None
        assert ValueError in result
        assert TypeError in result

    def test_raises_unwatched_in_hooked_module(self, make_package: PackageFactory) -> None:
        pkg = make_package("decpkg2")
        pkg.add_module(
            "mod.py",
            "from saferaise import raises\n\n@raises(ValueError)\ndef fn():\n    return 'ok'\n",
        )
        pkg.install()
        register("decpkg2")
        with enable():
            mod = pkg.import_module("mod")
            with pytest.raises(UnwatchedRaiseError):
                mod.fn()

    def test_raises_with_unsafe_in_hooked_module(self, make_package: PackageFactory) -> None:
        pkg = make_package("decpkg3")
        pkg.add_module(
            "mod.py",
            "from saferaise import raises\n\n@raises(ValueError)\ndef fn():\n    return 'ok'\n",
        )
        pkg.install()
        register("decpkg3")
        with enable():
            mod = pkg.import_module("mod")
            with unsafe(ValueError):
                assert mod.fn() == "ok"

    def test_cross_module_calls(self, make_package: PackageFactory) -> None:
        pkg = make_package("crosspkg")
        pkg.add_module(
            "caller.py",
            "from saferaise import raises\n"
            + "from crosspkg.callee import inner\n"
            + "\n"
            + "@raises(ValueError)\n"
            + "def outer():\n"
            + "    return inner()\n",
        )
        pkg.add_module(
            "callee.py",
            "from saferaise import raises\n\n@raises(TypeError)\ndef inner():\n    return 'deep'\n",
        )
        pkg.install()
        register("crosspkg")
        with enable():
            with unsafe(ValueError, TypeError):
                mod = pkg.import_module("caller")
                assert mod.outer() == "deep"


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestAsyncWithHook:
    async def test_async_raises_with_hook(self, make_package: PackageFactory) -> None:
        pkg = make_package("asyncpkg")
        pkg.add_module(
            "mod.py",
            "import asyncio\n"
            + "from saferaise import raises\n"
            + "from saferaise._watched_exceptions import get_exceptions\n"
            + "\n"
            + "@raises(ValueError)\n"
            + "async def fn():\n"
            + "    await asyncio.sleep(0)\n"
            + "    result = None\n"
            + "    try:\n"
            + "        result = get_exceptions()\n"
            + "    except TypeError:\n"
            + "        pass\n"
            + "    return result\n",
        )
        pkg.install()
        register("asyncpkg")
        with enable():
            mod = pkg.import_module("mod")
            with unsafe(ValueError):
                result = await mod.fn()
        assert result is not None
        assert ValueError in result
        assert TypeError in result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestModuleWithoutTry:
    def test_module_without_try_still_gets_watcher(self, make_package: PackageFactory) -> None:
        pkg = make_package("notrypkg")
        pkg.add_module("mod.py", "x = 42\n")
        pkg.install()
        register("notrypkg")
        with enable():
            mod = pkg.import_module("mod")
        assert WATCHER_KEY in mod.__dict__
        assert mod.x == 42


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestMultipleRoots:
    def test_register_multiple_roots(self, make_package: PackageFactory) -> None:
        pkg_a = make_package("rootpkg_a")
        pkg_a.add_module("mod.py", TRY_MODULE.format(exc="ValueError"))
        pkg_a.install()

        pkg_b = make_package("rootpkg_b")
        pkg_b.add_module("mod.py", TRY_MODULE.format(exc="TypeError"))
        pkg_b.install()

        register("rootpkg_a", "rootpkg_b")
        with enable():
            mod_a = pkg_a.import_module("mod")
            mod_b = pkg_b.import_module("mod")

        assert mod_a.result is not None
        assert ValueError in mod_a.result
        assert mod_b.result is not None
        assert TypeError in mod_b.result
