"""End-to-end tests for the import hook patcher with realistic app-like package layouts."""

import pytest

from saferaise import enable, register, unsafe
from saferaise._errors import UnwatchedRaiseError
from saferaise._patcher._common import WATCHER_KEY

from .conftest import PackageFactory


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestBasicInstrumentation:
    """register() instruments try/except blocks at import time."""

    def test_try_except_in_app_module(self, make_package: PackageFactory) -> None:
        # myapp/
        #   __init__.py  (calls register)
        #   parser.py    (has try/except)
        pkg = make_package("myapp")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp')\n",
        )
        pkg.add_module(
            "parser.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except ValueError:\n"
            + "    pass\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("parser")
        assert mod.result is not None
        assert ValueError in mod.result

    def test_try_except_in_subpackage(self, make_package: PackageFactory) -> None:
        # myapp2/
        #   __init__.py  (calls register)
        #   db/
        #     __init__.py
        #     query.py   (has try/except)
        pkg = make_package("myapp2")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp2')\n",
        )
        pkg.add_module("db/__init__.py", "")
        pkg.add_module(
            "db/query.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except KeyError:\n"
            + "    pass\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("db.query")
        assert mod.result is not None
        assert KeyError in mod.result

    def test_deeply_nested_subpackage(self, make_package: PackageFactory) -> None:
        # myapp3/
        #   __init__.py  (calls register)
        #   services/
        #     auth/
        #       tokens.py  (has try/except)
        pkg = make_package("myapp3")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp3')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module("services/auth/__init__.py", "")
        pkg.add_module(
            "services/auth/tokens.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except RuntimeError:\n"
            + "    pass\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("services.auth.tokens")
        assert mod.result is not None
        assert RuntimeError in mod.result

    def test_module_without_try_still_gets_watcher(self, make_package: PackageFactory) -> None:
        pkg = make_package("myapp4")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp4')\n",
        )
        pkg.add_module("config.py", "DEBUG = True\n")
        pkg.install()
        with enable():
            mod = pkg.import_module("config")
        assert WATCHER_KEY in mod.__dict__
        assert mod.DEBUG is True


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestExceptHandlerVariants:
    """Different try/except forms are all instrumented correctly."""

    def test_tuple_except(self, make_package: PackageFactory) -> None:
        pkg = make_package("myapp5")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp5')\n",
        )
        pkg.add_module(
            "routes/handler.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except (ValueError, TypeError):\n"
            + "    pass\n",
        )
        pkg.add_module("routes/__init__.py", "")
        pkg.install()
        with enable():
            mod = pkg.import_module("routes.handler")
        assert mod.result is not None
        assert ValueError in mod.result
        assert TypeError in mod.result

    def test_multiple_except_clauses(self, make_package: PackageFactory) -> None:
        pkg = make_package("myapp6")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp6')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/user.py",
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
        with enable():
            mod = pkg.import_module("services.user")
        assert mod.result is not None
        assert ValueError in mod.result
        assert KeyError in mod.result

    def test_bare_except(self, make_package: PackageFactory) -> None:
        pkg = make_package("myapp7")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp7')\n",
        )
        pkg.add_module(
            "middleware.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except:\n"
            + "    pass\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("middleware")
        assert mod.result is not None
        assert BaseException in mod.result

    def test_nested_try_blocks(self, make_package: PackageFactory) -> None:
        pkg = make_package("myapp8")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp8')\n",
        )
        pkg.add_module(
            "pipeline.py",
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
        with enable():
            mod = pkg.import_module("pipeline")
        assert mod.outer_result is not None
        assert mod.inner_result is not None
        assert ValueError in mod.outer_result
        assert TypeError in mod.inner_result
        assert ValueError in mod.inner_result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestDecoratorWithHook:
    """@raises enforcement works in instrumented modules."""

    def test_raises_with_watched_try_except(self, make_package: PackageFactory) -> None:
        # services/parser.py has @raises(ValueError) and a try/except TypeError inside
        pkg = make_package("myapp9")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp9')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/parser.py",
            "from saferaise import raises\n"
            + "from saferaise._watched_exceptions import get_exceptions\n"
            + "\n"
            + "@raises(ValueError)\n"
            + "def parse(raw):\n"
            + "    result = None\n"
            + "    try:\n"
            + "        result = get_exceptions()\n"
            + "    except TypeError:\n"
            + "        pass\n"
            + "    return result\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("services.parser")
            with unsafe(ValueError):
                result = mod.parse("x")
        assert result is not None
        assert ValueError in result
        assert TypeError in result

    def test_raises_unwatched_raises_error(self, make_package: PackageFactory) -> None:
        pkg = make_package("myapp10")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp10')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/auth.py",
            "from saferaise import raises\n\n@raises(PermissionError)\ndef check():\n    return True\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("services.auth")
            with pytest.raises(UnwatchedRaiseError):
                mod.check()

    def test_raises_with_unsafe(self, make_package: PackageFactory) -> None:
        pkg = make_package("myapp11")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp11')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/auth.py",
            "from saferaise import raises\n\n@raises(PermissionError)\ndef check():\n    return True\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("services.auth")
            with unsafe(PermissionError):
                assert mod.check() is True

    def test_cross_module_calls_with_absolute_import(self, make_package: PackageFactory) -> None:
        # routes/views.py calls services/user.py via absolute import
        pkg = make_package("myapp12")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp12')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/user.py",
            "from saferaise import raises\n\n@raises(LookupError)\ndef get_user(uid):\n    return uid\n",
        )
        pkg.add_module("routes/__init__.py", "")
        pkg.add_module(
            "routes/views.py",
            "from saferaise import raises\n"
            + "from myapp12.services.user import get_user\n"
            + "\n"
            + "@raises(ValueError)\n"
            + "def view(uid):\n"
            + "    return get_user(uid)\n",
        )
        pkg.install()
        with enable():
            with unsafe(ValueError, LookupError):
                mod = pkg.import_module("routes.views")
                assert mod.view(1) == 1


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestRelativeImports:
    """Modules using relative imports are correctly instrumented."""

    def test_sibling_module_instrumented_via_relative_import(self, make_package: PackageFactory) -> None:
        # routes/views.py does `from .helpers import format_response`
        # both should be instrumented
        pkg = make_package("myapp13")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp13')\n",
        )
        pkg.add_module("routes/__init__.py", "")
        pkg.add_module(
            "routes/helpers.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except ValueError:\n"
            + "    pass\n",
        )
        pkg.add_module(
            "routes/views.py",
            "from .helpers import result\n"
            + "from saferaise._watched_exceptions import get_exceptions\n"
            + "own_result = None\n"
            + "try:\n"
            + "    own_result = get_exceptions()\n"
            + "except TypeError:\n"
            + "    pass\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("routes.views")
        assert mod.result is not None
        assert ValueError in mod.result
        assert mod.own_result is not None
        assert TypeError in mod.own_result

    def test_relative_import_does_not_break_hook(self, make_package: PackageFactory) -> None:
        # db/models.py imports from db/base.py via relative import
        # the hook should still instrument db/models.py
        pkg = make_package("myapp14")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp14')\n",
        )
        pkg.add_module("db/__init__.py", "")
        pkg.add_module("db/base.py", "TABLE = 'users'\n")
        pkg.add_module(
            "db/models.py",
            "from .base import TABLE\n"
            + "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except KeyError:\n"
            + "    pass\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("db.models")
        assert mod.TABLE == "users"
        assert mod.result is not None
        assert KeyError in mod.result

    def test_raises_enforced_on_relatively_imported_module(self, make_package: PackageFactory) -> None:
        # services/email.py has @raises; routes/views.py imports it via relative import
        # enforcement should still work
        pkg = make_package("myapp15")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp15')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/email.py",
            "from saferaise import raises\n\n@raises(ConnectionError)\ndef send(to):\n    return 'sent'\n",
        )
        pkg.add_module(
            "services/notify.py",
            "from .email import send\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("services.notify")
            with pytest.raises(UnwatchedRaiseError):
                mod.send("user@example.com")

    def test_cross_module_calls_with_relative_import(self, make_package: PackageFactory) -> None:
        # services/order.py calls services/payment.py via relative import
        pkg = make_package("myapp16")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp16')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/payment.py",
            "from saferaise import raises\n\n@raises(ValueError)\ndef charge(amount):\n    return amount\n",
        )
        pkg.add_module(
            "services/order.py",
            "from saferaise import raises\n"
            + "from .payment import charge\n"
            + "\n"
            + "@raises(TypeError)\n"
            + "def place(amount):\n"
            + "    return charge(amount)\n",
        )
        pkg.install()
        with enable():
            with unsafe(ValueError, TypeError):
                mod = pkg.import_module("services.order")
                assert mod.place(100) == 100


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestAsyncWithHook:
    async def test_async_raises_with_hook(self, make_package: PackageFactory) -> None:
        pkg = make_package("myapp17")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('myapp17')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/fetcher.py",
            "import asyncio\n"
            + "from saferaise import raises\n"
            + "from saferaise._watched_exceptions import get_exceptions\n"
            + "\n"
            + "@raises(TimeoutError)\n"
            + "async def fetch(url):\n"
            + "    await asyncio.sleep(0)\n"
            + "    result = None\n"
            + "    try:\n"
            + "        result = get_exceptions()\n"
            + "    except ConnectionError:\n"
            + "        pass\n"
            + "    return result\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("services.fetcher")
            with unsafe(TimeoutError):
                result = await mod.fetch("http://example.com")
        assert result is not None
        assert TimeoutError in result
        assert ConnectionError in result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestNamespacePackage:
    """Namespace packages (no __init__.py at root) are instrumented correctly."""

    def test_namespace_inner_subpackage(self, make_package: PackageFactory) -> None:
        # nspkg/ (no __init__.py)
        #   api/
        #     __init__.py
        #     endpoints.py
        pkg = make_package("nspkg", namespace=True)
        pkg.add_module("api/__init__.py", "")
        pkg.add_module(
            "api/endpoints.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except KeyError:\n"
            + "    pass\n",
        )
        pkg.install()
        register("nspkg")
        with enable():
            mod = pkg.import_module("api.endpoints")
        assert mod.result is not None
        assert KeyError in mod.result

    def test_namespace_multiple_subpackages(self, make_package: PackageFactory) -> None:
        # nspkg2/ (no __init__.py)
        #   core/endpoints.py
        #   admin/views.py
        pkg = make_package("nspkg2", namespace=True)
        pkg.add_module("core/__init__.py", "")
        pkg.add_module(
            "core/endpoints.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except ValueError:\n"
            + "    pass\n",
        )
        pkg.add_module("admin/__init__.py", "")
        pkg.add_module(
            "admin/views.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except TypeError:\n"
            + "    pass\n",
        )
        pkg.install()
        register("nspkg2")
        with enable():
            core = pkg.import_module("core.endpoints")
            admin = pkg.import_module("admin.views")
        assert core.result is not None
        assert ValueError in core.result
        assert admin.result is not None
        assert TypeError in admin.result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestMultipleRoots:
    def test_two_separate_apps_registered_together(self, make_package: PackageFactory) -> None:
        # Two independent apps registered in one register() call
        app_a = make_package("app_a")
        app_a.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('app_a', 'app_b')\n",
        )
        app_a.add_module("services/__init__.py", "")
        app_a.add_module(
            "services/user.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except ValueError:\n"
            + "    pass\n",
        )
        app_a.install()

        app_b = make_package("app_b")
        app_b.add_module("services/__init__.py", "")
        app_b.add_module(
            "services/order.py",
            "from saferaise._watched_exceptions import get_exceptions\n"
            + "result = None\n"
            + "try:\n"
            + "    result = get_exceptions()\n"
            + "except TypeError:\n"
            + "    pass\n",
        )
        app_b.install()

        with enable():
            mod_a = app_a.import_module("services.user")
            mod_b = app_b.import_module("services.order")

        assert mod_a.result is not None
        assert ValueError in mod_a.result
        assert mod_b.result is not None
        assert TypeError in mod_b.result


@pytest.mark.usefixtures("_cleanup_meta_path")
class TestIsRegistered:
    """is_registered() reports whether the calling module has been instrumented."""

    def test_true_in_registered_package(self, make_package: PackageFactory) -> None:
        # myapp/__init__.py registers the package, services/auth.py checks is_registered
        pkg = make_package("is_reg_e2e1")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('is_reg_e2e1')\n",
        )
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/auth.py",
            "from saferaise import is_registered\nresult = is_registered()\n",
        )
        pkg.install()
        mod = pkg.import_module("services.auth")
        assert mod.result is True

    def test_false_in_unregistered_package(self, make_package: PackageFactory) -> None:
        pkg = make_package("is_reg_e2e2")
        pkg.add_module("services/__init__.py", "")
        pkg.add_module(
            "services/auth.py",
            "from saferaise import is_registered\nresult = is_registered()\n",
        )
        pkg.install()
        # no register() call
        mod = pkg.import_module("services.auth")
        assert mod.result is False

    def test_true_after_relative_import_chain(self, make_package: PackageFactory) -> None:
        # __init__.py registers, db/models.py uses relative import from db/base.py
        # is_registered() in db/models.py should still return True
        pkg = make_package("is_reg_e2e3")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('is_reg_e2e3')\n",
        )
        pkg.add_module("db/__init__.py", "")
        pkg.add_module("db/base.py", "TABLE = 'users'\n")
        pkg.add_module(
            "db/models.py",
            "from .base import TABLE\nfrom saferaise import is_registered\nresult = is_registered()\n",
        )
        pkg.install()
        mod = pkg.import_module("db.models")
        assert mod.TABLE == "users"
        assert mod.result is True

    def test_is_registered_used_as_guard(self, make_package: PackageFactory) -> None:
        # A module uses is_registered() to conditionally add debug info
        pkg = make_package("is_reg_e2e4")
        pkg.add_module(
            "__init__.py",
            "import saferaise\nsaferaise.register('is_reg_e2e4')\n",
        )
        pkg.add_module(
            "utils.py",
            "from saferaise import is_registered, raises\n"
            + "\n"
            + "instrumented = is_registered()\n"
            + "\n"
            + "@raises(ValueError)\n"
            + "def parse(raw):\n"
            + "    return int(raw)\n",
        )
        pkg.install()
        with enable():
            mod = pkg.import_module("utils")
        assert mod.instrumented is True
        with enable():
            with unsafe(ValueError):
                assert mod.parse("42") == 42
