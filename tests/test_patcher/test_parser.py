"""Tests for _patcher/_parser.py."""

import types

import pytest

from saferaise import enable
from saferaise._patcher._common import WATCHER_KEY
from saferaise._patcher._parser import transform_source
from saferaise._watched_exceptions import get_exceptions, watch_exceptions


class TestTransformSource:
    def test_returns_code_type(self):
        code = transform_source("x = 1", "<test>")
        assert isinstance(code, types.CodeType)

    def test_invalid_source_raises_syntax_error(self):
        with pytest.raises(SyntaxError):
            transform_source("def (:", "<test>")

    def test_simple_try_except(self):
        source = """\
try:
    x = 1
except ValueError:
    pass
"""
        code = transform_source(source, "<test>")
        ns = {WATCHER_KEY: watch_exceptions}
        with enable():
            exec(code, ns)

    def test_bare_except_uses_base_exception(self):
        source = """\
try:
    x = 1
except:
    pass
"""
        code = transform_source(source, "<test>")
        captured = {}

        class capturing_watch(watch_exceptions):
            def __init__(self, *exceptions: type[BaseException]):
                captured["exceptions"] = exceptions
                super().__init__(*exceptions)

        ns = {WATCHER_KEY: capturing_watch}
        with enable():
            exec(code, ns)
        assert BaseException in captured["exceptions"]

    def test_multiple_handlers_merge(self):
        source = """\
try:
    x = 1
except ValueError:
    pass
except TypeError:
    pass
"""
        code = transform_source(source, "<test>")
        captured = {}

        class capturing_watch(watch_exceptions):
            def __init__(self, *exceptions: type[BaseException]):
                captured["exceptions"] = exceptions
                super().__init__(*exceptions)

        ns = {WATCHER_KEY: capturing_watch}
        with enable():
            exec(code, ns)
        assert ValueError in captured["exceptions"]
        assert TypeError in captured["exceptions"]

    def test_tuple_handler_expands(self):
        source = """\
try:
    x = 1
except (ValueError, TypeError):
    pass
"""
        code = transform_source(source, "<test>")
        captured = {}

        class capturing_watch(watch_exceptions):
            def __init__(self, *exceptions: type[BaseException]):
                captured["exceptions"] = exceptions
                super().__init__(*exceptions)

        ns = {WATCHER_KEY: capturing_watch}
        with enable():
            exec(code, ns)
        assert ValueError in captured["exceptions"]
        assert TypeError in captured["exceptions"]

    def test_nested_try_blocks(self):
        source = """\
try:
    try:
        x = 1
    except TypeError:
        pass
except ValueError:
    pass
"""
        code = transform_source(source, "<test>")
        calls: list[tuple[type[BaseException], ...]] = []

        class capturing_watch(watch_exceptions):
            def __init__(self, *exceptions: type[BaseException]):
                calls.append(exceptions)
                super().__init__(*exceptions)

        ns = {WATCHER_KEY: capturing_watch}
        with enable():
            exec(code, ns)
        assert len(calls) == 2

    def test_try_star_transformed(self):
        source = """\
try:
    x = 1
except* ValueError:
    pass
"""
        code = transform_source(source, "<test>")
        captured = {}

        class capturing_watch(watch_exceptions):
            def __init__(self, *exceptions: type[BaseException]):
                captured["exceptions"] = exceptions
                super().__init__(*exceptions)

        ns = {WATCHER_KEY: capturing_watch}
        with enable():
            exec(code, ns)
        assert ValueError in captured["exceptions"]

    def test_watch_exceptions_active_in_try_body(self):
        source = """\
try:
    result = _get_exceptions()
except ValueError:
    pass
"""
        code = transform_source(source, "<test>")
        ns = {WATCHER_KEY: watch_exceptions, "_get_exceptions": get_exceptions}
        with enable():
            exec(code, ns)

        result = ns["result"]
        assert isinstance(result, frozenset)
        assert ValueError in result
